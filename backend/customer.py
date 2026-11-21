from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    credit_limit: float = 10000.0

class CustomerCreate(CustomerBase):
    initial_balance: float = 0.0

class CustomerResponse(CustomerBase):
    id: int
    business_id: int
    current_balance: float
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
