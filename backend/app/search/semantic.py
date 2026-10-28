"""Semantic search over stored local embeddings."""
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from sqlalchemy.orm import Session

from app.embeddings import EmbeddingEngine
from app.models.document import Document, DocumentChunk
from app.models.embedding import EmbeddingMetadata


@dataclass
class SemanticHit:
    chunk_id: str
    document_id: str
    filename: str
    extension: str
    content: str
    snippet: str
    heading: Optional[str]
    page_number: Optional[int]
    score: float


def search_semantic(
    db: Session,
    query: str,
    limit: int = 20,
    offset: int = 0,
    document_ids: Optional[List[str]] = None,
    extensions: Optional[List[str]] = None,
) -> tuple[List[SemanticHit], int]:
    """Cosine-similarity search over locally stored chunk embeddings."""
    engine = EmbeddingEngine.get_instance()
    engine.ensure_available(allow_download=engine.is_loaded)

    query_vector = engine.embed_query(query)

    query_builder = (
        db.query(EmbeddingMetadata, DocumentChunk, Document)
        .join(DocumentChunk, EmbeddingMetadata.chunk_id == DocumentChunk.id)
        .join(Document, EmbeddingMetadata.document_id == Document.id)
    )
    if document_ids:
        query_builder = query_builder.filter(Document.id.in_(document_ids))
    if extensions:
        query_builder = query_builder.filter(Document.extension.in_([e.lower() for e in extensions]))

    rows = query_builder.all()
    if not rows:
        return [], 0

    scored = []
    for meta, chunk, document in rows:
        # Never mix vectors from a different model/dimension
        if meta.model_name != engine.model_name:
            continue
        if not meta.vector:
            continue
        vector = np.frombuffer(meta.vector, dtype=np.float32)
        if vector.shape[0] != query_vector.shape[0]:
            continue
        score = float(np.dot(vector, query_vector))
        scored.append((score, meta, chunk, document))

    scored.sort(key=lambda item: item[0], reverse=True)
    total = len(scored)
    window = scored[offset : offset + limit]

    hits = []
    for score, _meta, chunk, document in window:
        content = chunk.content or ""
        snippet = content[:300] + (" …" if len(content) > 300 else "")
        hits.append(
            SemanticHit(
                chunk_id=chunk.id,
                document_id=document.id,
                filename=document.filename,
                extension=document.extension or "",
                content=content,
                snippet=snippet,
                heading=chunk.heading,
                page_number=chunk.page_number,
                score=score,
            )
        )

    return hits, total


def store_embeddings(
    db: Session,
    document_id: str,
    chunks,
    engine: EmbeddingEngine | None = None,
) -> int:
    """Compute and persist embeddings for a document's chunks."""
    engine = engine or EmbeddingEngine.get_instance()
    if not chunks:
        return 0

    texts = [c.content for c in chunks]
    vectors = engine.embed(texts)

    db.query(EmbeddingMetadata).filter(
        EmbeddingMetadata.document_id == document_id
    ).delete(synchronize_session=False)

    for chunk, vector in zip(chunks, vectors):
        db.add(
            EmbeddingMetadata(
                chunk_id=chunk.id,
                document_id=document_id,
                model_name=engine.model_name,
                model_version=getattr(engine, "model_version", None),
                embedding_dim=int(vector.shape[0]),
                vector=vector.astype(np.float32).tobytes(),
            )
        )
    db.commit()
    return len(chunks)
