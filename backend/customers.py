from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.customer import Customer
from app.models.business import BusinessProfile
from app.services.auth_service import get_current_business
from app.schemas.customer import CustomerCreate, CustomerResponse

router = APIRouter(prefix="/customers", tags=["Customers & Khata"])

@router.get("", response_model=List[CustomerResponse])
def get_customers(business: BusinessProfile = Depends(get_current_business), db: Session = Depends(get_db)):
    return db.query(Customer).filter(Customer.business_id == business.id).all()

@router.post("", response_model=CustomerResponse)
def add_customer(
    data: CustomerCreate,
    business: BusinessProfile = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    cust = Customer(
        business_id=business.id,
        name=data.name,
        phone=data.phone,
        address=data.address,
        credit_limit=data.credit_limit,
        current_balance=data.initial_balance
    )
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust
