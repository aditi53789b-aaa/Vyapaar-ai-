from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.invoice import Invoice
from app.models.business import BusinessProfile
from app.services.auth_service import get_current_business
from app.services.invoice_service import create_invoice
from app.schemas.invoice import InvoiceCreate, InvoiceResponse

router = APIRouter(prefix="/invoices", tags=["Invoices"])

@router.get("", response_model=List[InvoiceResponse])
def get_invoices(business: BusinessProfile = Depends(get_current_business), db: Session = Depends(get_db)):
    return db.query(Invoice).filter(Invoice.business_id == business.id).order_by(Invoice.created_at.desc()).all()

@router.post("", response_model=InvoiceResponse)
def add_invoice(
    data: InvoiceCreate,
    business: BusinessProfile = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    return create_invoice(db, business.id, data)
