from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from datetime import datetime, timezone
from app.core.database import Base

class VoiceDraft(Base):
    __tablename__ = "voice_drafts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_transcript = Column(Text, nullable=False)
    detected_language = Column(String(20), default="hi-IN")
    intent = Column(String(50), default="ADD_TRANSACTION")
    customer_name = Column(String(100), nullable=True)
    amount = Column(Float, nullable=True)
    transaction_type = Column(String(30), nullable=True)  # CREDIT_GIVEN, PAYMENT_RECEIVED, SALE, EXPENSE
    status = Column(String(20), default="PENDING")  # PENDING, CONFIRMED, DISCARDED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
