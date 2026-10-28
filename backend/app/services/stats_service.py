"""Stats/analytics service."""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document, DocumentChunk
from app.models.embedding import EmbeddingMetadata
from app.models.search import SearchHistory


def compute_stats(db: Session) -> dict:
    document_count = db.query(func.count(Document.id)).scalar() or 0
    chunk_count = db.query(func.count(DocumentChunk.id)).scalar() or 0
    total_bytes = db.query(func.coalesce(func.sum(Document.file_size), 0)).scalar() or 0

    indexed = (
        db.query(func.count(Document.id))
        .filter(Document.indexing_status == "completed")
        .scalar()
        or 0
    )
    failed = (
        db.query(func.count(Document.id))
        .filter(Document.indexing_status == "failed")
        .scalar()
        or 0
    )
    pending = (
        db.query(func.count(Document.id))
        .filter(Document.indexing_status.in_(["pending", "processing"]))
        .scalar()
        or 0
    )

    query_count = db.query(func.count(SearchHistory.id)).scalar() or 0
    avg_ms = db.query(func.coalesce(func.avg(SearchHistory.response_time_ms), 0.0)).scalar() or 0.0

    embedding_count = db.query(func.count(EmbeddingMetadata.id)).scalar() or 0
    embedding_model = (
        db.query(EmbeddingMetadata.model_name).limit(1).scalar()
    )
    coverage = (embedding_count / chunk_count * 100.0) if chunk_count else 0.0

    last_indexed = (
        db.query(func.max(Document.last_indexed_at)).scalar()
    )

    return {
        "document_count": int(document_count),
        "chunk_count": int(chunk_count),
        "total_source_bytes": int(total_bytes),
        "indexed_documents": int(indexed),
        "failed_documents": int(failed),
        "pending_documents": int(pending),
        "query_count": int(query_count),
        "average_response_time_ms": round(float(avg_ms), 2),
        "embedding_count": int(embedding_count),
        "embedding_model": embedding_model,
        "embedding_coverage_percent": round(coverage, 2),
        "last_indexed_at": last_indexed.isoformat() if last_indexed else None,
        "storage_backend": "postgresql" if "postgres" in settings.DATABASE_URL else "sqlite",
    }
