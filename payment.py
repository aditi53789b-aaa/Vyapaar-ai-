
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentMethod


class PaymentCreate(BaseModel):
    customer_id: int
    credit_transaction_id: int | None = None  # optional: the udhar sale being settled
    amount: Decimal = Field(gt=0, decimal_places=2)
    method: PaymentMethod = PaymentMethod.CASH
    notes: str | None = Field(default=None, max_length=500)
    idempotency_key: str | None = Field(default=None, max_length=64)


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    customer_id: int
    transaction_id: int
    credit_transaction_id: int | None
    amount: Decimal
    method: PaymentMethod
    notes: str | None
    created_at: datetime