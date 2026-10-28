"""Document models."""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.base import Base
import uuid


class Document(Base):
    """Document model."""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    file_hash = Column(String, nullable=False, index=True)
    mime_type = Column(String)
    file_size = Column(BigInteger)
    extension = Column(String, index=True)
    
    # Status
    parsing_status = Column(String, default="pending")  # pending, processing, completed, failed
    indexing_status = Column(String, default="pending")  # pending, processing, completed, failed
    parsing_error = Column(Text)
    
    # Metadata
    page_count = Column(Integer)
    char_count = Column(Integer)
    chunk_count = Column(Integer, default=0)
    
    # Timestamps
    imported_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at_source = Column(DateTime(timezone=True))
    last_indexed_at = Column(DateTime(timezone=True))
    
    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    collection_documents = relationship("CollectionDocument", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Document chunk model."""
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    
    # Source location
    page_number = Column(Integer)
    start_char = Column(Integer)
    end_char = Column(Integer)
    heading = Column(String)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    embedding = relationship("EmbeddingMetadata", back_populates="chunk", uselist=False, cascade="all, delete-orphan")
