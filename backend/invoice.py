from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class InvoiceItemBase(BaseModel):
    product_name: str
    quantity: float = 1.0
    unit_price: float
    tax_rate: float = 0.0
    total: float

class InvoiceItemCreate(InvoiceItemBase):
    pass

class InvoiceItemResponse(InvoiceItemBase):
    id: int
    invoice_id: int

    model_config = ConfigDict(from_attributes=True)

class InvoiceCreate(BaseModel):
    customer_id: Optional[int] = None
    invoice_number: str
    subtotal: float
    tax_amount: float = 0.0
    total_amount: float
    payment_status: str = "PAID"
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[InvoiceItemCreate]

class InvoiceResponse(BaseModel):
    id: int
    business_id: int
    customer_id: Optional[int]
    invoice_number: str
    subtotal: float
    tax_amount: float
    total_amount: float
    payment_status: str
    created_at: datetime
    items: List[InvoiceItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
