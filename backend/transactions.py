from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.transaction import Transaction
from app.models.business import BusinessProfile
from app.services.auth_service import get_current_business
from app.services.transaction_service import record_transaction
from app.schemas.transaction import TransactionCreate, TransactionResponse

router = APIRouter(prefix="/transactions", tags=["Transactions & Ledger"])

@router.get("", response_model=List[TransactionResponse])
def get_transactions(
    customer_id: Optional[int] = Query(None),
    type: Optional[str] = Query(None),
    limit: int = Query(50),
    business: BusinessProfile = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    q = db.query(Transaction).filter(Transaction.business_id == business.id)
    if customer_id:
        q = q.filter(Transaction.customer_id == customer_id)
    if type:
        q = q.filter(Transaction.type == type.upper())
    return q.order_by(Transaction.date.desc()).limit(limit).all()

@router.post("", response_model=TransactionResponse)
def create_transaction(
    data: TransactionCreate,
    business: BusinessProfile = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    return record_transaction(db, business.id, data)
