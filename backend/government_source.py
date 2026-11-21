from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime, timezone
from app.core.database import Base

class GovernmentSource(Base):
    __tablename__ = "government_sources"

    id = Column(Integer, primary_key=True, index=True)
    source_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    ministry = Column(String(200), nullable=False)
    portal_url = Column(String(500), nullable=False)
    api_endpoint = Column(String(500), nullable=True)
    
    # Integration Tier: TIER_1_PUBLIC_API, TIER_2_AUTHORIZED_GATEWAY, TIER_3_ASSISTED_PORTAL, TIER_4_VERIFIED_REPOSITORY
    integration_tier = Column(String(50), nullable=False, default="TIER_3_ASSISTED_PORTAL")
    
    # Auth: NONE, API_KEY, OAUTH2, AADHAAR_OTP, DIGILOCKER
    auth_requirements = Column(String(100), default="NONE")
    
    # Status: ACTIVE, VERIFIED, MAINTENANCE
    status = Column(String(30), default="VERIFIED", index=True)
    is_official = Column(Boolean, default=True)
    
    last_sync_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    verification_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
