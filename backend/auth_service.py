from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.core.security import decode_access_token, hash_password, verify_password, create_access_token
from app.models.user import User
from app.models.business import BusinessProfile
from app.schemas.user import UserCreate, UserLogin, Token, UserResponse

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def register_user(db: Session, user_data: UserCreate) -> User:
    existing = db.query(User).filter(User.phone == user_data.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    new_user = User(
        phone=user_data.phone,
        full_name=user_data.full_name,
        hashed_password=hash_password(user_data.password),
        role=user_data.role or "merchant"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def authenticate_user(db: Session, credentials: UserLogin) -> Token:
    user = db.query(User).filter(User.phone == credentials.phone).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_access_token(data={"sub": str(user.id), "phone": user.phone, "role": user.role})
    business = db.query(BusinessProfile).filter(BusinessProfile.user_id == user.id).first()
    
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        business_id=business.id if business else None
    )

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def get_current_business(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> BusinessProfile:
    business = db.query(BusinessProfile).filter(BusinessProfile.user_id == current_user.id).first()
    if not business:
        raise HTTPException(
            status_code=404, 
            detail="Business profile not found. Please complete business onboarding first."
        )
    return business
