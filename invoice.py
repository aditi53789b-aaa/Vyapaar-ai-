
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InvoiceItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    quantity: Decimal = Field(default=Decimal("1"), gt=0, decimal_places=3)
    unit_price: Decimal = Field(ge=0, decimal_places=2)


class InvoiceCreate(BaseModel):
    customer_id: int | None = None
    transaction_id: int | None = None  # optional link to an existing sale
    items: list[InvoiceItemIn] = Field(min_length=1)
    tax_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100, decimal_places=2)
    notes: str | None = Field(default=None, max_length=500)


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    customer_id: int | None
    transaction_id: int | None
    invoice_number: str
    subtotal: Decimal
    tax_percent: Decimal
    tax_amount: Decimal
    total: Decimal
    notes: str | None
    created_at: datetime