from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    phone: str = Field(..., description="10-digit mobile number")
    full_name: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=4)
    role: Optional[str] = "merchant"

class UserLogin(BaseModel):
    phone: str
    password: str

class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    business_id: Optional[int] = None
