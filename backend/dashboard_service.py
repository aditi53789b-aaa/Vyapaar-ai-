from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from app.models.transaction import Transaction
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.schemas.transaction import DashboardSummary, TransactionResponse

def get_dashboard_summary(db: Session, business_id: int) -> DashboardSummary:
    sales = db.query(func.sum(Transaction.amount)).filter(
        Transaction.business_id == business_id,
        Transaction.type.in_(["SALE", "CREDIT_GIVEN"])
    ).scalar() or 0.0

    expenses = db.query(func.sum(Transaction.amount)).filter(
        Transaction.business_id == business_id,
        Transaction.type == "EXPENSE"
    ).scalar() or 0.0

    outstanding_udhar = db.query(func.sum(Customer.current_balance)).filter(
        Customer.business_id == business_id,
        Customer.current_balance > 0
    ).scalar() or 0.0

    customer_count = db.query(Customer).filter(Customer.business_id == business_id).count()
    txns_count = db.query(Transaction).filter(Transaction.business_id == business_id).count()

    recent_txns = db.query(Transaction).filter(
        Transaction.business_id == business_id
    ).order_by(Transaction.date.desc()).limit(10).all()

    return DashboardSummary(
        total_sales=float(sales),
        total_expenses=float(expenses),
        total_outstanding_udhar=float(outstanding_udhar),
        total_customers=customer_count,
        total_transactions_count=txns_count,
        net_cashflow=float(sales - expenses),
        recent_transactions=[TransactionResponse.model_validate(t) for t in recent_txns]
    )
