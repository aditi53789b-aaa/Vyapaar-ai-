from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.business import BusinessProfile
from app.schemas.business import BusinessProfileCreate, BusinessProfileUpdate

def create_or_update_business(db: Session, user_id: int, data: BusinessProfileCreate) -> BusinessProfile:
    existing = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if existing:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing
    
    business = BusinessProfile(user_id=user_id, **data.model_dump())
    db.add(business)
    db.commit()
    db.refresh(business)
    return business

def update_business_profile(db: Session, business_id: int, data: BusinessProfileUpdate) -> BusinessProfile:
    business = db.query(BusinessProfile).filter(BusinessProfile.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(business, field, value)
            
    db.commit()
    db.refresh(business)
    return business
