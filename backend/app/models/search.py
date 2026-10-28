"""Search models."""
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.database.base import Base
import uuid


class SavedSearch(Base):
    """Saved search model."""
    __tablename__ = "saved_searches"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    query = Column(Text, nullable=False)
    search_mode = Column(String, default="fulltext")  # fulltext, semantic, hybrid
    filters = Column(Text)  # JSON string of filters
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True))


class SearchHistory(Base):
    """Search history model."""
    __tablename__ = "search_history"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    query = Column(Text, nullable=False)
    search_mode = Column(String)
    result_count = Column(Integer)
    response_time_ms = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
