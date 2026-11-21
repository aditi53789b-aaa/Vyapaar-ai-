from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("business_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    hindi_name = Column(String(150), nullable=True)
    category = Column(String(50), default="General")
    price = Column(Float, nullable=False, default=0.0)
    cost_price = Column(Float, default=0.0)
    unit = Column(String(20), default="piece")  # piece, kg, litre, packet
    stock_quantity = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
