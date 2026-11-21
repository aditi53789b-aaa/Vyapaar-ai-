from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from datetime import datetime, timezone
from app.core.database import Base

class SchemeAssessment(Base):
    __tablename__ = "scheme_assessments"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_id = Column(Integer, ForeignKey("government_schemes.id", ondelete="CASCADE"), nullable=False, index=True)
    
    match_score = Column(Float, nullable=False, default=0.0)  # 0 to 100
    
    # Status: HIGHLY_RECOMMENDED, POTENTIALLY_ELIGIBLE, INELIGIBLE, INSUFFICIENT_DATA
    eligibility_status = Column(String(50), nullable=False, default="POTENTIALLY_ELIGIBLE", index=True)
    
    satisfied_criteria = Column(Text, nullable=True)     # JSON array string
    missing_criteria = Column(Text, nullable=True)       # JSON array string
    unverified_criteria = Column(Text, nullable=True)    # JSON array string
    
    ai_explanation = Column(Text, nullable=False)
    ai_explanation_hindi = Column(Text, nullable=True)
    recommended_actions = Column(Text, nullable=True)    # JSON array string
    
    assessed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
