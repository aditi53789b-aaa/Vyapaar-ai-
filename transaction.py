
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TransactionType


class TransactionItemIn(BaseModel):
    product_id: int | None = None
    name: str | None = Field(default=None, max_length=255)
    quantity: Decimal = Field(default=Decimal("1"), gt=0, decimal_places=3)
    unit_price: Decimal = Field(ge=0, decimal_places=2)


class TransactionCreate(BaseModel):
    type: TransactionType
    customer_id: int | None = None
    items: list[TransactionItemIn] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)
    occurred_at: datetime | None = None
    idempotency_key: str | None = Field(default=None, max_length=64)


class TransactionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None
    name: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    customer_id: int | None
    type: TransactionType
    total_amount: Decimal
    status: str
    notes: str | None
    occurred_at: datetime | None
    created_at: datetime
    items: list[TransactionItemOut] = Field(default_factory=list)