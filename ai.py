
"""Backend support for Gauri's AI assistant.

These endpoints expose read-only, structured financial data from the actual
merchant records. Her module calls these to ground answers - the AI never
writes anything and never touches balances directly.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_business
from app.models import Business
from app.schemas.transaction import TransactionOut
from app.services import dashboard as dashboard_service
from app.services import khata as khata_service
from app.utils.responses import ok

router = APIRouter(prefix="/ai", tags=["AI Assistant Data"])


@router.get("/merchant-context")
def merchant_context(business: Business = Depends(get_current_business),
                     db: Session = Depends(get_db)):
    summary = dashboard_service.summary(db, business)
    top_customers = khata_service.customers_with_outstanding(db, business.id)[:5]
    return ok({
        "business": {"id": business.id, "name": business.name},
        "summary": {k: (str(v) if not isinstance(v, (int, list)) else v)
                    for k, v in summary.items() if k != "recent_transactions"},
        "top_customers_with_udhar": top_customers,
        "recent_transactions": [
            TransactionOut.model_validate(t).model_dump() for t in summary["recent_transactions"]
        ],
    })


@router.get("/customers/{customer_id}/context")
def customer_context(customer_id: int,
                     business: Business = Depends(get_current_business),
                     db: Session = Depends(get_db)):
    ledger = khata_service.customer_ledger(db, business, customer_id)
    ledger["transactions"] = [
        TransactionOut.model_validate(t).model_dump() for t in ledger["transactions"][:20]
    ]
    return ok(ledger)