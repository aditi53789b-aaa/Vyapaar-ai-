
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_business
from app.models import Business, Payment
from app.schemas.payment import PaymentCreate, PaymentOut
from app.services import payments as payment_service
from app.utils.responses import fail, ok

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", status_code=201)
def create_payment(payload: PaymentCreate,
                   business: Business = Depends(get_current_business),
                   db: Session = Depends(get_db)):
    payment, existed = payment_service.record_payment(
        db, business,
        customer_id=payload.customer_id,
        amount=payload.amount,
        method=payload.method,
        credit_transaction_id=payload.credit_transaction_id,
        notes=payload.notes,
        idempotency_key=payload.idempotency_key,
    )
    data = PaymentOut.model_validate(payment).model_dump()
    data["already_existed"] = existed
    return ok(data)


@router.get("")
def list_payments(customer_id: int | None = None,
                  skip: int = Query(default=0, ge=0),
                  limit: int = Query(default=50, ge=1, le=200),
                  business: Business = Depends(get_current_business),
                  db: Session = Depends(get_db)):
    stmt = select(Payment).where(Payment.business_id == business.id)
    if customer_id is not None:
        stmt = stmt.where(Payment.customer_id == customer_id)
    rows = db.execute(stmt.order_by(Payment.created_at.desc(), Payment.id.desc())
                      .offset(skip).limit(limit)).scalars().all()
    return ok({"items": [PaymentOut.model_validate(r).model_dump() for r in rows],
               "skip": skip, "limit": limit})


@router.get("/{payment_id}")
def get_payment(payment_id: int,
                business: Business = Depends(get_current_business),
                db: Session = Depends(get_db)):
    payment = db.get(Payment, payment_id)
    if payment is None or payment.business_id != business.id:
        fail(404, "PAYMENT_NOT_FOUND", "Payment not found in this business.")
    return ok(PaymentOut.model_validate(payment).model_dump())