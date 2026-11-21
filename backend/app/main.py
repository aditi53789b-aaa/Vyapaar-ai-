from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

APP_ENV = os.getenv("APP_ENV", "development").lower()
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    if APP_ENV == "production":
        raise RuntimeError("SECRET_KEY is required in production. Generate a random 32+ byte secret.")
    SECRET_KEY = secrets.token_urlsafe(48)
if APP_ENV == "production" and len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY must contain at least 32 characters in production.")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bolokhaata.sqlite3")
if APP_ENV == "production" and not DATABASE_URL.startswith(("postgresql://", "postgresql+psycopg2://")):
    raise RuntimeError("Production requires PostgreSQL. Set DATABASE_URL to a managed PostgreSQL connection.")
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
OTP_MINUTES = int(os.getenv("EMAIL_OTP_EXPIRE_MINUTES", "10"))
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",") if x.strip()]
ALLOWED_HOSTS = [x.strip() for x in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if x.strip()]
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)

engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    terms_accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    terms_version: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    verification_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    verification_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verification_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    login_failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    login_locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reset_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reset_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reset_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    business: Mapped[Optional["Business"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class Business(Base):
    __tablename__ = "businesses"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    business_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    merchant_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    business_category: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    annual_income: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(20), default="hi")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user: Mapped[User] = relationship(back_populates="business")


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(24), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    invoice_number: Mapped[str] = mapped_column(String(40), index=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    item_description: Mapped[str] = mapped_column(String(500), default="")
    payment_status: Mapped[str] = mapped_column(String(12), default="paid")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class GovernmentScheme(Base):
    __tablename__ = "government_schemes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(80), index=True)
    department: Mapped[str] = mapped_column(String(200), default="Government of India")
    official_portal_url: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    merchant_type: Optional[str] = Field(default=None, max_length=80)
    business_type: Optional[str] = Field(default=None, max_length=80)
    business_name: Optional[str] = Field(default=None, max_length=160)
    annual_income: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    business_category: Optional[str] = None
    preferred_language: str = "hi"
    accepted_terms: bool = False


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class EmailIn(BaseModel):
    email: EmailStr


class VerifyIn(EmailIn):
    otp: str = Field(pattern=r"^\d{6}$")


class ResetIn(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=10, max_length=128)


class TransactionIn(BaseModel):
    kind: str = Field(pattern=r"^(SALE|CREDIT_GIVEN|PAYMENT_RECEIVED|EXPENSE)$")
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    customer_name: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = Field(default=None, max_length=500)


class VoiceIn(BaseModel):
    transcript: str = Field(min_length=2, max_length=1000)


class DeleteAccountIn(BaseModel):
    password: str


class InvoiceIn(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    item_description: str = Field(default="", max_length=500)
    total: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_status: str = Field(default="paid", pattern=r"^(paid|udhar)$")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def aware_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def token_hash(value: str) -> str:
    return hmac.new(SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


def send_email(to: str, subject: str, body: str) -> None:
    host, user, password = os.getenv("SMTP_HOST"), os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD")
    if not all([host, user, password]):
        if APP_ENV == "production":
            raise HTTPException(status_code=503, detail="Email delivery is not configured. Please try again later.")
        print(f"[DEVELOPMENT EMAIL to={to}] {subject}\n{body}")
        return
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, os.getenv("SMTP_FROM", user), to
    msg.set_content(body)
    port = int(os.getenv("SMTP_PORT", "587"))
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=15) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(user, password)
                server.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        raise HTTPException(status_code=503, detail="Unable to send email right now. Please try again later.") from exc


def issue_access_token(user: User) -> str:
    now = utcnow()
    return jwt.encode({"sub": str(user.id), "ver": user.token_version, "iat": now, "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES)}, SECRET_KEY, algorithm=ALGORITHM)


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(db_session)) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = db.get(User, user_id)
    if not user or not user.is_active or not user.email_verified_at or payload.get("ver") != user.token_version:
        raise HTTPException(status_code=401, detail="Account unavailable or session expired")
    return user


def require_business(user: User, db: Session) -> Business:
    business = db.query(Business).filter(Business.user_id == user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business profile not found")
    return business


def parse_voice(text: str) -> dict:
    normalized = text.strip()
    amount_match = re.search(r"(?:₹|rs\.?|inr\s*)?\s*(\d+(?:\.\d{1,2})?)", normalized, re.I)
    if not amount_match:
        raise HTTPException(status_code=422, detail="Could not identify an amount. Please say the amount clearly.")
    amount = Decimal(amount_match.group(1))
    low = normalized.lower()
    if any(x in low for x in ("udhar", "baaki", "credit")):
        kind = "CREDIT_GIVEN"
    elif any(x in low for x in ("kharch", "expense", "petrol", "diesel", "rent")):
        kind = "EXPENSE"
    elif any(x in low for x in ("jama", "payment mila", "received", "paid back", "wapas")):
        kind = "PAYMENT_RECEIVED"
    else:
        kind = "SALE"
    match = re.search(r"([A-Za-z\u0900-\u097F]{2,})\s+(?:ko|ne|from|to)", normalized, re.I)
    customer = match.group(1).strip().title() if match else None
    return {"raw_transcript": normalized, "amount": str(amount), "transaction_type": kind, "customer_name": customer, "status": "DRAFT_REQUIRES_CONFIRMATION"}


app = FastAPI(title="BoloKhaata API", version="1.0.0", docs_url="/docs" if APP_ENV != "production" else None, redoc_url=None, openapi_url="/openapi.json" if APP_ENV != "production" else None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(self), camera=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self' https:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if APP_ENV == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.on_event("startup")
def startup():
    if APP_ENV == "production":
        required = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "PASSWORD_RESET_URL"]
        if not ALLOWED_HOSTS or "localhost" in ALLOWED_HOSTS:
            raise RuntimeError("Set ALLOWED_HOSTS to your deployed domain(s) in production.")
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise RuntimeError("Missing production configuration: " + ", ".join(missing))
        if "*" in CORS_ORIGINS:
            raise RuntimeError("Wildcard CORS origins are forbidden in production.")
    # Local development bootstrap only. Production schema changes are applied with Alembic.
    if APP_ENV != "production":
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            if db.query(GovernmentScheme).count() == 0:
                db.add_all([
                    GovernmentScheme(name="PM SVANidhi", description="Official programme portal for street-vendor support. Review current guidelines and application requirements on the government portal.", category="Street Vendor Support", department="Ministry of Housing and Urban Affairs", official_portal_url="https://pmsvanidhi.mohua.gov.in/"),
                    GovernmentScheme(name="Pradhan Mantri MUDRA Yojana (PMMY)", description="Official portal for information about the MUDRA programme. Product details and lending decisions are determined by participating lenders and current official guidelines.", category="Credit and Enterprise", department="Department of Financial Services, Ministry of Finance", official_portal_url="https://www.mudra.org.in/"),
                    GovernmentScheme(name="PM Vishwakarma", description="Official programme portal for eligible traditional artisans and craftspeople. Review current trade lists and application requirements on the government portal.", category="Artisan Support", department="Ministry of MSME", official_portal_url="https://pmvishwakarma.gov.in/")
                ])
                db.commit()


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return {"status": "ok", "database": "connected", "environment": APP_ENV}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.post("/api/v1/auth/register", status_code=202)
def register(data: RegisterIn, db: Session = Depends(db_session)):
    email = str(data.email).lower().strip()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    if APP_ENV == "production" and not all(os.getenv(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD")):
        raise HTTPException(status_code=503, detail="Email verification is not configured")
    user = User(email=email, full_name=data.full_name.strip(), password_hash=pwd_context.hash(data.password), terms_accepted_at=utcnow(), terms_version=os.getenv("TERMS_VERSION", "2026-11-21"))
    business = Business(user=user, merchant_type=data.merchant_type or data.business_type, business_name=data.business_name, annual_income=data.annual_income, state=data.state, district=data.district, business_category=data.business_category, preferred_language=data.preferred_language)
    otp = f"{secrets.randbelow(1_000_000):06d}"
    user.verification_hash = token_hash(otp)
    user.verification_expires_at = utcnow() + timedelta(minutes=OTP_MINUTES)
    user.verification_sent_at = utcnow()
    db.add(user)
    db.add(business)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Unable to create account. Check whether this email is already registered.")
    send_email(email, "Verify your BoloKhaata account", f"Your BoloKhaata verification code is {otp}. It expires in {OTP_MINUTES} minutes. Do not share this code.")
    return {"message": "Account created. Check your email for the verification code.", "email": email, "expires_in_seconds": OTP_MINUTES * 60}


@app.post("/api/v1/auth/verify-email")
def verify_email(data: VerifyIn, db: Session = Depends(db_session)):
    user = db.query(User).filter(func.lower(User.email) == str(data.email).lower()).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    if user.email_verified_at:
        return {"message": "Email already verified"}
    if user.verification_attempts >= 5 or not user.verification_expires_at or aware_utc(user.verification_expires_at) < utcnow() or not hmac.compare_digest(user.verification_hash or "", token_hash(data.otp)):
        user.verification_attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    user.email_verified_at = utcnow()
    user.verification_hash = None
    user.verification_expires_at = None
    user.verification_attempts = 0
    db.commit()
    return {"message": "Email verified successfully. You can now sign in."}


@app.post("/api/v1/auth/resend-verification")
def resend_verification(data: EmailIn, db: Session = Depends(db_session)):
    user = db.query(User).filter(func.lower(User.email) == str(data.email).lower()).first()
    if user and not user.email_verified_at:
        if user.verification_sent_at and (utcnow() - aware_utc(user.verification_sent_at)).total_seconds() < 60:
            return {"message": "If the account requires verification, a new code can be requested after 60 seconds."}
        otp = f"{secrets.randbelow(1_000_000):06d}"
        user.verification_hash = token_hash(otp)
        user.verification_expires_at = utcnow() + timedelta(minutes=OTP_MINUTES)
        user.verification_attempts = 0
        user.verification_sent_at = utcnow()
        db.commit()
        send_email(user.email, "Your BoloKhaata verification code", f"Your new verification code is {otp}. It expires in {OTP_MINUTES} minutes.")
    return {"message": "If the account requires verification, a new code has been sent."}


@app.post("/api/v1/auth/login")
def login(data: LoginIn, db: Session = Depends(db_session)):
    user = db.query(User).filter(func.lower(User.email) == str(data.email).lower()).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if user.login_locked_until and aware_utc(user.login_locked_until) > utcnow():
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")
    if not pwd_context.verify(data.password, user.password_hash):
        user.login_failed_attempts += 1
        if user.login_failed_attempts >= 5:
            user.login_locked_until = utcnow() + timedelta(minutes=15)
            user.login_failed_attempts = 0
        db.commit()
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    user.login_failed_attempts = 0
    user.login_locked_until = None
    db.commit()
    if not user.email_verified_at:
        raise HTTPException(status_code=403, detail="Please verify your email before signing in")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is disabled")
    business = db.query(Business).filter(Business.user_id == user.id).first()
    return {"access_token": issue_access_token(user), "token_type": "bearer", "user": {"id": user.id, "email": user.email, "full_name": user.full_name}, "business_id": business.id if business else None}


@app.get("/api/v1/auth/me")
def me(user: User = Depends(current_user), db: Session = Depends(db_session)):
    business = db.query(Business).filter(Business.user_id == user.id).first()
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "business_name": business.business_name if business else None, "email_verified": bool(user.email_verified_at)}



@app.get("/api/v1/auth/me/export")
def export_account_data(user: User = Depends(current_user), db: Session = Depends(db_session)):
    business = require_business(user, db)
    customers = db.query(Customer).filter(Customer.business_id == business.id).all()
    transactions = db.query(Transaction).filter(Transaction.business_id == business.id).order_by(Transaction.created_at.asc()).all()
    invoices = db.query(Invoice).filter(Invoice.business_id == business.id).order_by(Invoice.created_at.asc()).all()
    return {
        "exported_at": utcnow().isoformat(),
        "account": {"email": user.email, "full_name": user.full_name, "created_at": user.created_at.isoformat(), "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None},
        "business": {"business_name": business.business_name, "merchant_type": business.merchant_type, "business_category": business.business_category, "annual_income": business.annual_income, "state": business.state, "district": business.district, "preferred_language": business.preferred_language},
        "customers": [{"id": x.id, "name": x.name, "phone": x.phone, "balance": str(x.balance)} for x in customers],
        "transactions": [{"id": x.id, "kind": x.kind, "amount": str(x.amount), "notes": x.notes, "created_at": x.created_at.isoformat()} for x in transactions],
        "invoices": [{"id": x.id, "invoice_number": x.invoice_number, "customer_name": x.customer_name, "item_description": x.item_description, "total": str(x.total), "payment_status": x.payment_status, "created_at": x.created_at.isoformat()} for x in invoices]
    }


@app.delete("/api/v1/auth/me", status_code=204)
def delete_account(data: DeleteAccountIn, user: User = Depends(current_user), db: Session = Depends(db_session)):
    if not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Password confirmation failed")
    db.delete(user)
    db.commit()
    return None

@app.post("/api/v1/auth/forgot-password")
def forgot_password(data: EmailIn, db: Session = Depends(db_session)):
    user = db.query(User).filter(func.lower(User.email) == str(data.email).lower()).first()
    if user and user.email_verified_at:
        raw = secrets.token_urlsafe(36)
        if user.reset_sent_at and (utcnow() - aware_utc(user.reset_sent_at)).total_seconds() < 60:
            return {"message": "If the account exists, password reset instructions will be sent."}
        user.reset_hash = token_hash(raw)
        user.reset_expires_at = utcnow() + timedelta(minutes=20)
        user.reset_sent_at = utcnow()
        db.commit()
        reset_url = os.getenv("PASSWORD_RESET_URL", "").rstrip("/")
        if reset_url:
            separator = "&" if "?" in reset_url else "?"
            send_email(user.email, "Reset your BoloKhaata password", f"Use this single-use reset link within 20 minutes: {reset_url}{separator}token={raw}")
    return {"message": "If the account exists, password reset instructions will be sent."}


@app.post("/api/v1/auth/reset-password")
def reset_password(data: ResetIn, db: Session = Depends(db_session)):
    user = db.query(User).filter(User.reset_hash == token_hash(data.token)).first()
    if not user or not user.reset_expires_at or aware_utc(user.reset_expires_at) < utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    user.password_hash = pwd_context.hash(data.new_password)
    user.token_version += 1
    user.reset_hash = None
    user.reset_expires_at = None
    db.commit()
    return {"message": "Password updated. Please sign in again."}


@app.get("/api/v1/dashboard/summary")
def dashboard_summary(user: User = Depends(current_user), db: Session = Depends(db_session)):
    business = require_business(user, db)
    business_tz = ZoneInfo(os.getenv("BUSINESS_TIMEZONE", "Asia/Kolkata"))
    now_local = datetime.now(business_tz)
    start_day = now_local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    start_month = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    def total(kind_filter, since=None):
        query = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.business_id == business.id, Transaction.kind.in_(kind_filter))
        if since:
            query = query.filter(Transaction.created_at >= since)
        return float(query.scalar() or 0)
    recent = db.query(Transaction).filter(Transaction.business_id == business.id).order_by(Transaction.created_at.desc()).limit(10).all()
    return {"today_sales": total(["SALE"], start_day), "month_sales": total(["SALE"], start_month), "total_sales": total(["SALE"]), "total_expenses": total(["EXPENSE"]), "total_outstanding_udhar": float(db.query(func.coalesce(func.sum(Customer.balance), 0)).filter(Customer.business_id == business.id, Customer.balance > 0).scalar() or 0), "total_customers": db.query(Customer).filter(Customer.business_id == business.id).count(), "total_transactions_count": db.query(Transaction).filter(Transaction.business_id == business.id).count(), "recent_transactions": [{"id": t.id, "type": t.kind, "amount": float(t.amount), "notes": t.notes, "date": t.created_at.isoformat()} for t in recent]}


@app.post("/api/v1/voice/parse")
def voice_parse(data: VoiceIn, user: User = Depends(current_user)):
    return parse_voice(data.transcript)


@app.post("/api/v1/voice/confirm")
def voice_confirm(data: TransactionIn, user: User = Depends(current_user), db: Session = Depends(db_session)):
    business = require_business(user, db)
    customer = None
    if data.customer_name:
        customer = db.query(Customer).filter(Customer.business_id == business.id, func.lower(Customer.name) == data.customer_name.lower()).first()
        if not customer:
            customer = Customer(business_id=business.id, name=data.customer_name)
            db.add(customer)
            db.flush()
    txn = Transaction(business_id=business.id, customer_id=customer.id if customer else None, kind=data.kind, amount=data.amount, notes=data.notes)
    db.add(txn)
    if customer:
        if data.kind == "CREDIT_GIVEN":
            customer.balance = Decimal(customer.balance or 0) + data.amount
        elif data.kind == "PAYMENT_RECEIVED":
            customer.balance = max(Decimal("0"), Decimal(customer.balance or 0) - data.amount)
    db.commit()
    return {"message": "Transaction recorded", "transaction_id": txn.id}


@app.post("/api/v1/transactions")
def create_transaction(data: TransactionIn, user: User = Depends(current_user), db: Session = Depends(db_session)):
    business = require_business(user, db)
    customer = None
    if data.customer_name:
        customer = db.query(Customer).filter(Customer.business_id == business.id, func.lower(Customer.name) == data.customer_name.lower()).first()
        if not customer:
            customer = Customer(business_id=business.id, name=data.customer_name)
            db.add(customer)
            db.flush()
    txn = Transaction(business_id=business.id, customer_id=customer.id if customer else None, kind=data.kind, amount=data.amount, notes=data.notes)
    db.add(txn)
    if customer and data.kind == "CREDIT_GIVEN":
        customer.balance = Decimal(customer.balance or 0) + data.amount
    elif customer and data.kind == "PAYMENT_RECEIVED":
        customer.balance = max(Decimal("0"), Decimal(customer.balance or 0) - data.amount)
    db.commit()
    return {"id": txn.id, "kind": txn.kind, "amount": str(txn.amount), "created_at": txn.created_at.isoformat()}


@app.post("/api/v1/invoices")
def create_invoice(data: InvoiceIn, user: User = Depends(current_user), db: Session = Depends(db_session)):
    business = require_business(user, db)
    number = f"BK-{business.id}-{secrets.token_hex(4).upper()}"
    customer = db.query(Customer).filter(Customer.business_id == business.id, func.lower(Customer.name) == data.customer_name.lower()).first()
    if not customer:
        customer = Customer(business_id=business.id, name=data.customer_name)
        db.add(customer)
        db.flush()
    invoice = Invoice(business_id=business.id, invoice_number=number, customer_name=data.customer_name, total=data.total, item_description=data.item_description, payment_status=data.payment_status)
    db.add(invoice)
    kind = "CREDIT_GIVEN" if data.payment_status == "udhar" else "SALE"
    db.add(Transaction(business_id=business.id, customer_id=customer.id, kind=kind, amount=data.total, notes=f"Invoice {number}: {data.item_description}"))
    if data.payment_status == "udhar":
        customer.balance = Decimal(customer.balance or 0) + data.total
    db.commit()
    return {"id": invoice.id, "invoice_number": number, "customer_name": invoice.customer_name, "total": str(invoice.total), "item_description": invoice.item_description, "payment_status": invoice.payment_status, "created_at": invoice.created_at.isoformat()}


@app.get("/api/v1/invoices")
def list_invoices(user: User = Depends(current_user), db: Session = Depends(db_session)):
    business = require_business(user, db)
    rows = db.query(Invoice).filter(Invoice.business_id == business.id).order_by(Invoice.created_at.desc()).limit(100).all()
    return {"items": [{"id": x.id, "invoice_number": x.invoice_number, "customer_name": x.customer_name, "total": str(x.total), "item_description": x.item_description, "payment_status": x.payment_status, "created_at": x.created_at.isoformat()} for x in rows]}



@app.get("/api/v1/customers")
def list_customers(user: User = Depends(current_user), db: Session = Depends(db_session)):
    business = require_business(user, db)
    rows = db.query(Customer).filter(Customer.business_id == business.id).order_by(Customer.name.asc()).limit(500).all()
    return {"items": [{"id": x.id, "name": x.name, "phone": x.phone, "balance": str(x.balance or 0)} for x in rows]}


@app.get("/api/v1/customers/{customer_id}/transactions")
def customer_transactions(customer_id: int, user: User = Depends(current_user), db: Session = Depends(db_session)):
    business = require_business(user, db)
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.business_id == business.id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    rows = db.query(Transaction).filter(Transaction.business_id == business.id, Transaction.customer_id == customer.id).order_by(Transaction.created_at.desc()).limit(200).all()
    return {"customer": {"id": customer.id, "name": customer.name, "balance": str(customer.balance or 0)}, "items": [{"id": x.id, "kind": x.kind, "amount": str(x.amount), "notes": x.notes, "created_at": x.created_at.isoformat()} for x in rows]}


@app.get("/api/v1/transactions")
def list_transactions(user: User = Depends(current_user), db: Session = Depends(db_session), limit: int = 100):
    business = require_business(user, db)
    rows = db.query(Transaction).filter(Transaction.business_id == business.id).order_by(Transaction.created_at.desc()).limit(min(max(limit, 1), 500)).all()
    return {"items": [{"id": x.id, "kind": x.kind, "amount": str(x.amount), "customer_id": x.customer_id, "notes": x.notes, "created_at": x.created_at.isoformat()} for x in rows]}


@app.get("/api/v1/invoices/{invoice_id}")
def get_invoice(invoice_id: int, user: User = Depends(current_user), db: Session = Depends(db_session)):
    business = require_business(user, db)
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.business_id == business.id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"id": invoice.id, "invoice_number": invoice.invoice_number, "customer_name": invoice.customer_name, "item_description": invoice.item_description, "total": str(invoice.total), "payment_status": invoice.payment_status, "created_at": invoice.created_at.isoformat()}

@app.get("/api/v1/government-schemes")
def schemes(query: Optional[str] = None, category: Optional[str] = None, state: Optional[str] = None, limit: int = 100, db: Session = Depends(db_session)):
    q = db.query(GovernmentScheme).filter(GovernmentScheme.is_active.is_(True))
    if query:
        term = f"%{query.strip()}%"
        q = q.filter(GovernmentScheme.name.ilike(term) | GovernmentScheme.description.ilike(term))
    if category:
        q = q.filter(GovernmentScheme.category == category)
    rows = q.order_by(GovernmentScheme.name).limit(min(max(limit, 1), 100)).all()
    items = [{"id": s.id, "name": s.name, "description": s.description, "category": s.category, "department": s.department, "official_portal_url": s.official_portal_url} for s in rows]
    return {"items": items, "schemes": items, "categories": sorted({s.category for s in db.query(GovernmentScheme).filter(GovernmentScheme.is_active.is_(True)).all()})}


@app.get("/api/v1/government-schemes/categories")
def scheme_categories(db: Session = Depends(db_session)):
    return sorted({s.category for s in db.query(GovernmentScheme).filter(GovernmentScheme.is_active.is_(True)).all()})


@app.get("/api/v1/government-schemes/sources")
def scheme_sources(db: Session = Depends(db_session)):
    return [{"name": s.department, "url": s.official_portal_url} for s in db.query(GovernmentScheme).filter(GovernmentScheme.is_active.is_(True)).all()]


@app.post("/api/v1/government-schemes/{scheme_id}/assess")
def assess_scheme(scheme_id: int, user: User = Depends(current_user), db: Session = Depends(db_session)):
    business = require_business(user, db)
    scheme = db.get(GovernmentScheme, scheme_id)
    if not scheme or not scheme.is_active:
        raise HTTPException(status_code=404, detail="Scheme not found")
    missing = []
    if not business.business_category:
        missing.append("Business category")
    if not business.merchant_type:
        missing.append("Business type")
    if not business.state:
        missing.append("State")
    if not business.annual_income:
        missing.append("Approximate annual turnover")
    return {"scheme_id": scheme.id, "scheme_name": scheme.name, "assessment_status": "PROFILE_INCOMPLETE" if missing else "READY_FOR_MANUAL_REVIEW", "missing_profile_fields": missing, "official_portal_url": scheme.official_portal_url, "disclaimer": "This is a profile completeness check only, not a legal eligibility determination, government verification, application, loan approval or guarantee. Confirm all current criteria on the official portal."}


FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", str(Path(__file__).resolve().parents[2] / "frontend")))

@app.get("/")
def root():
    index = FRONTEND_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"service": "BoloKhaata API", "version": app.version}

if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
