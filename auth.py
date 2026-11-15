
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Business, User
from app.utils.responses import fail
from app.utils.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        fail(401, "UNAUTHENTICATED", "Missing Authorization header.")
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        fail(401, "INVALID_TOKEN", "Token is invalid or expired.")
    user = db.get(User, user_id)
    if user is None:
        fail(401, "INVALID_TOKEN", "User no longer exists.")
    return user


def get_current_business(
    x_business_id: int = Header(alias="X-Business-Id"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Business:
    """Resolves the business from the X-Business-Id header AND verifies the
    current user actually owns it. Attach this to every business-scoped route."""
    business = db.get(Business, x_business_id)
    if business is None or business.user_id != current_user.id:
        fail(404, "BUSINESS_NOT_FOUND", "Business not found for this user.")
    return business





from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=20)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    phone: str | None
    created_at: datetime


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    business_type: str | None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
    business_id: int



from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import Business, User
from app.schemas.auth import TokenOut, UserCreate, UserLogin, UserOut
from app.utils.responses import fail, ok
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=None, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        fail(409, "EMAIL_TAKEN", "An account with this email already exists.")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        fail(409, "EMAIL_TAKEN", "An account with this email already exists.")

    business = Business(user_id=user.id, name=f"{payload.full_name}'s Business")
    db.add(business)
    db.commit()
    db.refresh(user)

    return ok({
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "user": UserOut.model_validate(user),
        "business_id": business.id,
    })


@router.post("/login", response_model=None)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        fail(401, "INVALID_CREDENTIALS", "Email or password is incorrect.")

    business = db.execute(
        select(Business).where(Business.user_id == user.id)
    ).scalars().first()
    return ok({
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "user": UserOut.model_validate(user),
        "business_id": business.id if business else None,
    })


@router.get("/me")
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    businesses = db.execute(
        select(Business).where(Business.user_id == current_user.id)
    ).scalars().all()
    return ok({
        "user": UserOut.model_validate(current_user),
        "businesses": [{"id": b.id, "name": b.name, "business_type": b.business_type}
                       for b in businesses],
    })