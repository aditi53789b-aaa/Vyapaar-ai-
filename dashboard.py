
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.transaction import TransactionOut


class DashboardSummaryOut(BaseModel):
    today_sales: Decimal
    today_expenses: Decimal
    today_payments_received: Decimal
    month_sales: Decimal
    month_expenses: Decimal
    month_payments_received: Decimal
    pending_udhar: Decimal
    total_customers: int
    recent_transactions: list[TransactionOut]


class ReportOut(BaseModel):
    period_start: date
    period_end: date
    sales: Decimal                # cash sales
    credit_sales: Decimal         # udhar issued
    purchases: Decimal
    expenses: Decimal
    payments_received: Decimal
    udhar_outstanding: Decimal    # business-level outstanding at period end




from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_business
from app.models import Business
from app.schemas.dashboard import DashboardSummaryOut, ReportOut
from app.services import dashboard as dashboard_service
from app.utils.responses import ok

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Reports"])


@router.get("/summary")
def summary(business: Business = Depends(get_current_business),
            db: Session = Depends(get_db)):
    data = dashboard_service.summary(db, business)
    data["recent_transactions"] = [
        t.model_dump() if hasattr(t, "model_dump") else t for t in data["recent_transactions"]
    ]
    from app.schemas.transaction import TransactionOut
    data["recent_transactions"] = [
        TransactionOut.model_validate(t).model_dump() for t in data["recent_transactions"]
    ]
    return ok(DashboardSummaryOut(**data).model_dump())


@router.get("/reports/daily")
def daily(day: date | None = Query(default=None),
          business: Business = Depends(get_current_business),
          db: Session = Depends(get_db)):
    return ok(ReportOut(**dashboard_service.daily_report(db, business, day or date.today())).model_dump())


@router.get("/reports/weekly")
def weekly(day: date | None = Query(default=None),
           business: Business = Depends(get_current_business),
           db: Session = Depends(get_db)):
    return ok(ReportOut(**dashboard_service.weekly_report(db, business, day or date.today())).model_dump())


@router.get("/reports/monthly")
def monthly(year: int = Query(default=2026, ge=2000, le=2100),
            month: int = Query(default=11, ge=1, le=12),
            business: Business = Depends(get_current_business),
            db: Session = Depends(get_db)):
    return ok(ReportOut(**dashboard_service.monthly_report(db, business, year, month)).model_dump())