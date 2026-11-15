
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.transaction import TransactionOut


class CustomerLedgerOut(BaseModel):
    customer_id: int
    customer_name: str
    total_credit_sales: Decimal       # sum of all CREDIT_SALE transactions
    total_payments_received: Decimal  # sum of all PAYMENT transactions
    outstanding_balance: Decimal      # credit - payments, computed from ledger records
    transactions: list[TransactionOut]


class CustomerOutstandingOut(BaseModel):
    customer_id: int
    customer_name: str
    phone: str | None
    outstanding_balance: Decimal



"""Digital Khata: all balances are derived from actual ledger records."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Customer, Payment, Transaction, TransactionType
from app.utils.responses import fail


def _sum(db: Session, business_id: int, txn_type: TransactionType, customer_id: int | None = None):
    stmt = select(func.coalesce(func.sum(Transaction.total_amount), 0)).where(
        Transaction.business_id == business_id,
        Transaction.type == txn_type,
    )
    if customer_id is not None:
        stmt = stmt.where(Transaction.customer_id == customer_id)
    return Decimal(str(db.execute(stmt).scalar_one()))


def customer_totals(db: Session, business_id: int, customer_id: int):
    credit = _sum(db, business_id, TransactionType.CREDIT_SALE, customer_id)
    paid = _sum(db, business_id, TransactionType.PAYMENT, customer_id)
    return credit, paid, credit - paid


def customer_ledger(db: Session, business, customer_id: int) -> dict:
    customer = db.get(Customer, customer_id)
    if customer is None or customer.business_id != business.id:
        fail(404, "CUSTOMER_NOT_FOUND", "Customer not found in this business.")

    credit, paid, outstanding = customer_totals(db, business.id, customer.id)
    transactions = db.execute(
        select(Transaction)
        .where(Transaction.business_id == business.id, Transaction.customer_id == customer.id)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
    ).scalars().all()

    return {
        "customer_id": customer.id,
        "customer_name": customer.name,
        "total_credit_sales": credit,
        "total_payments_received": paid,
        "outstanding_balance": outstanding,
        "transactions": transactions,
    }


def business_outstanding(db: Session, business_id: int) -> Decimal:
    credit = _sum(db, business_id, TransactionType.CREDIT_SALE)
    paid = _sum(db, business_id, TransactionType.PAYMENT)
    return credit - paid


def customers_with_outstanding(db: Session, business_id: int) -> list[dict]:
    credit_rows = db.execute(
        select(Transaction.customer_id, func.sum(Transaction.total_amount))
        .where(Transaction.business_id == business_id, Transaction.type == TransactionType.CREDIT_SALE)
        .group_by(Transaction.customer_id)
    ).all()
    payment_rows = db.execute(
        select(Transaction.customer_id, func.sum(Transaction.total_amount))
        .where(Transaction.business_id == business_id, Transaction.type == TransactionType.PAYMENT)
        .group_by(Transaction.customer_id)
    ).all()
    credit_map = {row[0]: Decimal(str(row[1])) for row in credit_rows}
    payment_map = {row[0]: Decimal(str(row[1])) for row in payment_rows}

    customers = db.execute(
        select(Customer).where(Customer.business_id == business_id, Customer.is_active.is_(True))
    ).scalars().all()
    result = []
    for customer in customers:
        outstanding = credit_map.get(customer.id, Decimal("0")) - payment_map.get(customer.id, Decimal("0"))
        result.append({
            "customer_id": customer.id,
            "customer_name": customer.name,
            "phone": customer.phone,
            "outstanding_balance": outstanding,
        })
    result.sort(key=lambda row: row["outstanding_balance"], reverse=True)
    return result