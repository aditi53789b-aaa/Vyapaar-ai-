from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models.transaction import Transaction
from app.models.customer import Customer
from app.models.business import BusinessProfile
from app.schemas.transaction import TransactionCreate

def record_transaction(db: Session, business_id: int, data: TransactionCreate) -> Transaction:
    txn = Transaction(
        business_id=business_id,
        customer_id=data.customer_id,
        type=data.type.upper(),
        amount=data.amount,
        payment_mode=data.payment_mode,
        notes=data.notes,
        date=data.date or datetime.now(timezone.utc)
    )
    db.add(txn)
    
    # Update customer balance if linked
    if data.customer_id:
        customer = db.query(Customer).filter(
            Customer.id == data.customer_id, 
            Customer.business_id == business_id
        ).first()
        if customer:
            if txn.type == "CREDIT_GIVEN":
                customer.current_balance += data.amount
            elif txn.type == "PAYMENT_RECEIVED":
                customer.current_balance -= data.amount
    
    # Update business turnover on sales
    if txn.type in ["SALE", "CREDIT_GIVEN"]:
        business = db.query(BusinessProfile).filter(BusinessProfile.id == business_id).first()
        if business:
            business.annual_turnover = (business.annual_turnover or 0.0) + data.amount

    db.commit()
    db.refresh(txn)
    return txn
