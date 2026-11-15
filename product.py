
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    unit: str = Field(default="pcs", max_length=20)
    price: Decimal = Field(ge=0, decimal_places=2)
    stock_quantity: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    unit: str | None = Field(default=None, max_length=20)
    price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    stock_quantity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    name: str
    description: str | None
    unit: str
    price: Decimal
    stock_quantity: int
    is_active: bool
    created_at: datetime