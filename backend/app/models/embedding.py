"""Embedding models."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.base import Base
import uuid


class EmbeddingMetadata(Base):
    """Embedding vector plus the model that produced it.

    The model name and dimension are stored so that stale embeddings are
    never compared against vectors from a different model without a check.
    """
    __tablename__ = "embedding_metadata"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_id = Column(String, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, unique=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    model_name = Column(String, nullable=False)
    model_version = Column(String)
    embedding_dim = Column(Integer)
    vector = Column(LargeBinary, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    chunk = relationship("DocumentChunk", back_populates="embedding")
