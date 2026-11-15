
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_business
from app.models import Business, Customer, Invoice, Transaction
from app.schemas.invoice import InvoiceCreate, InvoiceOut
from app.utils.money import PAISE, to_money
from app.utils.responses import fail, ok

router = APIRouter(prefix="/invoices", tags=["Invoices"])


def _next_invoice_number(db: Session, business_id: int) -> str:
    count = db.execute(select(func.count(Invoice.id)).where(Invoice.business_id == business_id)).scalar_one()
    return f"INV-{business_id}-{(count + 1):05d}"


@router.post("", status_code=201)
def create_invoice(payload: InvoiceCreate,
                   business: Business = Depends(get_current_business),
                   db: Session = Depends(get_db)):
    customer = None
    if payload.customer_id is not None:
        customer = db.get(Customer, payload.customer_id)
        if customer is None or customer.business_id != business.id:
            fail(404, "CUSTOMER_NOT_FOUND", "Customer not found in this business.")

    txn = None
    if payload.transaction_id is not None:
        txn = db.get(Transaction, payload.transaction_id)
        if txn is None or txn.business_id != business.id:
            fail(404, "TRANSACTION_NOT_FOUND", "Transaction not found in this business.")

    # Server-side totals — never trust frontend-supplied amounts.
    subtotal = Decimal("0.00")
    for item in payload.items:
        qty = Decimal(str(item.quantity)).quantize(Decimal("0.001"))
        subtotal += (qty * to_money(item.unit_price)).quantize(PAISE)
    tax_amount = (subtotal * to_money(payload.tax_percent) / Decimal("100")).quantize(PAISE)
    total = subtotal + tax_amount

    invoice = Invoice(
        business_id=business.id,
        customer_id=customer.id if customer else None,
        transaction_id=txn.id if txn else None,
        invoice_number=_next_invoice_number(db, business.id),
        subtotal=subtotal,
        tax_percent=to_money(payload.tax_percent),
        tax_amount=tax_amount,
        total=total,
        notes=payload.notes,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return ok(InvoiceOut.model_validate(invoice).model_dump())


@router.get("")
def list_invoices(customer_id: int | None = None,
                  skip: int = Query(default=0, ge=0),
                  limit: int = Query(default=50, ge=1, le=200),
                  business: Business = Depends(get_current_business),
                  db: Session = Depends(get_db)):
    stmt = select(Invoice).where(Invoice.business_id == business.id)
    if customer_id is not None:
        stmt = stmt.where(Invoice.customer_id == customer_id)
    rows = db.execute(stmt.order_by(Invoice.created_at.desc(), Invoice.id.desc())
                      .offset(skip).limit(limit)).scalars().all()
    return ok({"items": [InvoiceOut.model_validate(r).model_dump() for r in rows],
               "skip": skip, "limit": limit})


@router.get("/{invoice_id}")
def get_invoice(invoice_id: int,
                business: Business = Depends(get_current_business),
                db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if invoice is None or invoice.business_id != business.id:
        fail(404, "INVOICE_NOT_FOUND", "Invoice not found in this business.")
    return ok(InvoiceOut.model_validate(invoice).model_dump())