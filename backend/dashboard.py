from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.business import BusinessProfile
from app.services.auth_service import get_current_business
from app.services.dashboard_service import get_dashboard_summary
from app.schemas.transaction import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["Dashboard Reports"])

@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(business: BusinessProfile = Depends(get_current_business), db: Session = Depends(get_db)):
    return get_dashboard_summary(db, business.id)
