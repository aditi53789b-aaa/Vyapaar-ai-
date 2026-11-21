from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class TransactionBase(BaseModel):
    customer_id: Optional[int] = None
    type: str = Field(..., description="SALE, EXPENSE, CREDIT_GIVEN, PAYMENT_RECEIVED")
    amount: float
    payment_mode: str = "CASH"
    notes: Optional[str] = None
    date: Optional[datetime] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: int
    business_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DashboardSummary(BaseModel):
    total_sales: float
    total_expenses: float
    total_outstanding_udhar: float
    total_customers: int
    total_transactions_count: int
    net_cashflow: float
    recent_transactions: List[TransactionResponse]
