"""Application settings model."""
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from app.database.base import Base


class ApplicationSetting(Base):
    """Application settings model."""
    __tablename__ = "application_settings"
    
    key = Column(String, primary_key=True)
    value = Column(Text)
    description = Column(Text)
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
