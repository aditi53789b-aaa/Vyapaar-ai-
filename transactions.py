
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_business
from app.models import Business, Transaction, TransactionType
from app.schemas.transaction import TransactionCreate, TransactionOut
from app.services import transactions as txn_service
from app.utils.responses import fail, ok

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("", status_code=201)
def create_transaction(payload: TransactionCreate,
                       business: Business = Depends(get_current_business),
                       db: Session = Depends(get_db)):
    txn, existed = txn_service.create_transaction(
        db, business,
        txn_type=payload.type,
        customer_id=payload.customer_id,
        items=payload.items,
        notes=payload.notes,
        occurred_at=payload.occurred_at,
        idempotency_key=payload.idempotency_key,
    )
    data = TransactionOut.model_validate(txn).model_dump()
    data["already_existed"] = existed
    return ok(data)


@router.get("")
def list_transactions(type: TransactionType | None = None,
                      customer_id: int | None = None,
                      skip: int = Query(default=0, ge=0),
                      limit: int = Query(default=50, ge=1, le=200),
                      business: Business = Depends(get_current_business),
                      db: Session = Depends(get_db)):
    stmt = select(Transaction).where(Transaction.business_id == business.id)
    if type is not None:
        stmt = stmt.where(Transaction.type == type)
    if customer_id is not None:
        stmt = stmt.where(Transaction.customer_id == customer_id)
    rows = db.execute(stmt.order_by(Transaction.created_at.desc(), Transaction.id.desc())
                      .offset(skip).limit(limit)).scalars().all()
    return ok({"items": [TransactionOut.model_validate(r).model_dump() for r in rows],
               "skip": skip, "limit": limit})


@router.get("/{transaction_id}")
def get_transaction(transaction_id: int,
                    business: Business = Depends(get_current_business),
                    db: Session = Depends(get_db)):
    txn = db.get(Transaction, transaction_id)
    if txn is None or txn.business_id != business.id:
        fail(404, "TRANSACTION_NOT_FOUND", "Transaction not found in this business.")
    return ok(TransactionOut.model_validate(txn).model_dump())


@router.patch("/{transaction_id}")
def update_transaction(transaction_id: int,
                       notes: str | None = Query(default=None, max_length=500),
                       business: Business = Depends(get_current_business),
                       db: Session = Depends(get_db)):
    """Financial values are immutable: only notes can be edited. To change an
    amount, create a correcting entry (keeps the ledger auditable)."""
    txn = db.get(Transaction, transaction_id)
    if txn is None or txn.business_id != business.id:
        fail(404, "TRANSACTION_NOT_FOUND", "Transaction not found in this business.")
    txn.notes = notes
    db.commit()
    db.refresh(txn)
    return ok(TransactionOut.model_validate(txn).model_dump())


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int,
                       business: Business = Depends(get_current_business),
                       db: Session = Depends(get_db)):
    txn = db.get(Transaction, transaction_id)
    if txn is None or txn.business_id != business.id:
        fail(404, "TRANSACTION_NOT_FOUND", "Transaction not found in this business.")
    db.delete(txn)
    db.commit()
    return ok({"deleted": True})