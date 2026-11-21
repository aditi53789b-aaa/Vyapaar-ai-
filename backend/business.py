from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class BusinessProfileBase(BaseModel):
    business_name: str
    legal_name: Optional[str] = None
    business_category: str = Field(default="retail", description="retail, street_vendor, artisan_handicrafts, micro_manufacturing, food_processing, services, agriculture")
    subcategory: Optional[str] = None
    merchant_type: str = Field(default="micro_enterprise", description="street_vendor, micro_enterprise, small_enterprise, artisan, farmer, retail_shopkeeper")
    gstin: Optional[str] = None
    pan: Optional[str] = None
    udyam_registration_no: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    district: str = "Varanasi"
    state: str = "Uttar Pradesh"
    pincode: Optional[str] = None
    annual_turnover: float = 0.0
    plant_machinery_investment: float = 0.0
    employee_count: int = 1
    operating_since_year: int = 2022
    owner_gender: str = "male"
    social_category: str = "general"
    is_differently_abled: bool = False
    bank_account_no: Optional[str] = None
    bank_ifsc: Optional[str] = None
    bank_name: Optional[str] = None

class BusinessProfileCreate(BusinessProfileBase):
    pass

class BusinessProfileUpdate(BaseModel):
    business_name: Optional[str] = None
    business_category: Optional[str] = None
    subcategory: Optional[str] = None
    merchant_type: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    udyam_registration_no: Optional[str] = None
    address: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    annual_turnover: Optional[float] = None
    operating_since_year: Optional[int] = None
    owner_gender: Optional[str] = None
    social_category: Optional[str] = None

class BusinessProfileResponse(BusinessProfileBase):
    id: int
    user_id: int
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
