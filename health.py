from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Confirms the API is running AND the database is reachable."""
    db.execute(text("SELECT 1"))
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "database": "connected",
        },
    }