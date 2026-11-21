from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from datetime import datetime, timezone
from app.core.database import Base

class SchemeDocument(Base):
    __tablename__ = "scheme_documents"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_id = Column(Integer, ForeignKey("government_schemes.id", ondelete="SET NULL"), nullable=True, index=True)
    
    document_type = Column(String(80), nullable=False, index=True)  # AADHAAR, PAN, UDYAM, BANK_PASSBOOK, COV, PROJECT_REPORT
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    file_hash = Column(String(64), nullable=True)  # SHA-256
    
    verification_status = Column(String(30), default="UPLOADED")  # UPLOADED, VERIFIED, REJECTED
    notes = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ApplicationReadiness(Base):
    __tablename__ = "application_readiness"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_id = Column(Integer, ForeignKey("government_schemes.id", ondelete="CASCADE"), nullable=False, index=True)
    
    readiness_percentage = Column(Float, default=0.0)
    checklist_state = Column(Text, nullable=True)        # JSON object of document and profile status
    financial_summary_snapshot = Column(Text, nullable=True) # JSON summary calculated from transactions/invoices
    
    # Status: NOT_STARTED, IN_PREPARATION, READY_TO_APPLY, APPLIED_ON_PORTAL
    application_status = Column(String(40), default="NOT_STARTED", index=True)
    portal_reference_number = Column(String(100), nullable=True)
    
    merchant_consent_given = Column(Boolean, default=False)
    consent_timestamp = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
