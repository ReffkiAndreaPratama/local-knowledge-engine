"""Robust document indexing pipeline.

Each stage is isolated so that one unreadable file never aborts a batch.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.embeddings import EmbeddingEngine, EmbeddingUnavailable
from app.indexing.chunker import Chunk, chunk_document
from app.models.document import Document, DocumentChunk
from app.models.embedding import EmbeddingMetadata
from app.parsers.base import ParseError
from app.parsers.registry import is_supported, parse_document
from app.search.fts import delete_document_chunks, index_chunk
from app.search.semantic import store_embeddings


def sha256_file(path: str, block_size: int = 1024 * 1024) -> str:
    """Hash a file without reading it fully into memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


class IndexingPipeline:
    def __init__(
        self,
        db: Session,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.db = db
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap if chunk_overlap is not None else settings.CHUNK_OVERLAP

    # -- validation -------------------------------------------------------
    def validate(self, path: str) -> None:
        if not os.path.isfile(path):
            raise ParseError("Not a regular file")
        ext = os.path.splitext(path)[1].lower()
        if ext not in settings.allowed_extensions_list:
            raise ParseError(f"Extension '{ext}' is not allowed")
        if not is_supported(path):
            raise ParseError(f"No parser available for '{ext}'")
        size = os.path.getsize(path)
        if size == 0:
            raise ParseError("File is empty")
        if size > settings.max_file_size_bytes:
            raise ParseError(
                f"File is larger than the {settings.MAX_FILE_SIZE_MB} MB limit"
            )

    # -- main entry point -------------------------------------------------
    def index_document(self, document: Document, compute_embeddings: bool = True) -> Document:
        """Parse, chunk and index a single document. Returns the updated model."""
        document.parsing_status = "processing"
        document.indexing_status = "processing"
        document.parsing_error = None
        self.db.commit()

        try:
            self.validate(document.original_path)

            parsed = parse_document(document.original_path)
            document.parsing_status = "completed"
            document.char_count = parsed.char_count
            if parsed.page_count:
                document.page_count = parsed.page_count

            chunks = chunk_document(
                parsed,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
            if not chunks:
                raise ParseError("Document produced no chunks")

            self._replace_chunks(document, chunks)
            document.indexing_status = "completed"
            document.chunk_count = len(chunks)
            document.last_indexed_at = datetime.now(timezone.utc)
            self.db.commit()

            if compute_embeddings and settings.ENABLE_SEMANTIC_SEARCH:
                self._try_embeddings(document)

            return document

        except Exception as exc:  # noqa: BLE001 - failure must be recorded, not raised
            self.db.rollback()
            document = self.db.query(Document).filter(Document.id == document.id).first()
            if document is not None:
                document.parsing_status = "failed"
                document.indexing_status = "failed"
                document.parsing_error = str(exc)[:2000]
                self.db.commit()
                return document
            raise

    # -- helpers ----------------------------------------------------------
    def _replace_chunks(self, document: Document, chunks: List[Chunk]) -> None:
        """Atomically replace chunk rows and their FTS entries."""
        delete_document_chunks(self.db, document.id)
        self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id
        ).delete(synchronize_session=False)

        for chunk in chunks:
            row = DocumentChunk(
                document_id=document.id,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                heading=chunk.heading,
            )
            self.db.add(row)
            self.db.flush()

            index_chunk(
                self.db,
                chunk_id=row.id,
                document_id=document.id,
                content=row.content,
                filename=document.filename,
                extension=document.extension or "",
                heading=row.heading,
            )
        self.db.commit()

    def _try_embeddings(self, document: Document) -> None:
        """Compute embeddings, but never fail indexing because of them."""
        engine = EmbeddingEngine.get_instance()
        try:
            engine.ensure_available(allow_download=engine.is_loaded)
            chunks = (
                self.db.query(DocumentChunk)
                .filter(DocumentChunk.document_id == document.id)
                .order_by(DocumentChunk.chunk_index)
                .all()
            )
            if chunks:
                store_embeddings(self.db, document.id, chunks, engine)
        except EmbeddingUnavailable:
            self.db.rollback()
        except Exception:
            self.db.rollback()

    def purge_document(self, document_id: str) -> None:
        """Remove chunks, FTS rows and embeddings for a document."""
        delete_document_chunks(self.db, document_id)
        self.db.query(EmbeddingMetadata).filter(
            EmbeddingMetadata.document_id == document_id
        ).delete(synchronize_session=False)
        self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).delete(synchronize_session=False)
        self.db.commit()
