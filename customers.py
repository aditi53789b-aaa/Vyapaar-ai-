
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_business
from app.models import Business, Customer, Payment
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate
from app.services import khata as khata_service
from app.utils.responses import fail, ok

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("", status_code=201)
def create_customer(
    payload: CustomerCreate,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    customer = Customer(
        business_id=business.id,
        name=payload.name,
        phone=payload.phone,
        address=payload.address,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return ok(CustomerOut.model_validate(customer).model_dump())


@router.get("")
def list_customers(
    search: str | None = Query(default=None, max_length=100),
    include_inactive: bool = False,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    stmt = select(Customer).where(Customer.business_id == business.id)
    if not include_inactive:
        stmt = stmt.where(Customer.is_active.is_(True))
    if search:
        like = f"%{search}%"
        stmt = stmt.where((Customer.name.ilike(like)) | (Customer.phone.ilike(like)))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(Customer.name).offset(skip).limit(limit)).scalars().all()
    return ok({"items": [CustomerOut.model_validate(r).model_dump() for r in rows],
               "total": total, "skip": skip, "limit": limit})


@router.get("/{customer_id}")
def get_customer(
    customer_id: int,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    customer = db.get(Customer, customer_id)
    if customer is None or customer.business_id != business.id:
        fail(404, "CUSTOMER_NOT_FOUND", "Customer not found in this business.")
    _, _, outstanding = khata_service.customer_totals(db, business.id, customer.id)
    data = CustomerOut.model_validate(customer).model_dump()
    data["outstanding_balance"] = outstanding
    return ok(data)


@router.patch("/{customer_id}")
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    customer = db.get(Customer, customer_id)
    if customer is None or customer.business_id != business.id:
        fail(404, "CUSTOMER_NOT_FOUND", "Customer not found in this business.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return ok(CustomerOut.model_validate(customer).model_dump())


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Safe delete: hard-deletes only if the customer has no ledger history,
    otherwise deactivates so the khata/ledger stays intact."""
    customer = db.get(Customer, customer_id)
    if customer is None or customer.business_id != business.id:
        fail(404, "CUSTOMER_NOT_FOUND", "Customer not found in this business.")

    has_history = db.execute(
        select(func.count()).select_from(Payment.__table__).where(Payment.customer_id == customer.id)
    ).scalar_one() > 0
    has_txns = any(True for _ in customer.transactions)

    if has_history or has_txns:
        customer.is_active = False
        db.commit()
        return ok({"deleted": False, "deactivated": True,
                   "message": "Customer has transaction history, so they were deactivated instead of deleted."})
    db.delete(customer)
    db.commit()
    return ok({"deleted": True, "deactivated": False})