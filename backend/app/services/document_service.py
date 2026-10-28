"""Document service: import, listing, deletion and re-indexing."""
from __future__ import annotations

import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.paths import (
    iter_document_files,
    require_allowed_path,
    sanitize_filename,
)
from app.indexing.jobs import create_job, start_import_job, start_reindex_job
from app.indexing.pipeline import IndexingPipeline, sha256_file
from app.models.document import Document, DocumentChunk
from app.parsers.registry import is_supported

UPLOAD_DIR = os.path.join("data", "documents")


class DocumentService:
    def __init__(self, db: Session):
        self.db = db

    # -- import: uploaded files -------------------------------------------
    async def import_files(self, files: List[UploadFile]) -> dict:
        """Persist uploads to the managed document directory and start a job."""
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        specs = []
        rejected = []

        for file in files:
            original_name = sanitize_filename(file.filename or "document")
            ext = os.path.splitext(original_name)[1].lower()

            if ext not in settings.allowed_extensions_list or not is_supported(original_name):
                rejected.append({"filename": original_name, "reason": f"Unsupported file type '{ext}'"})
                continue

            target = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
            try:
                with open(target, "wb") as out:
                    shutil.copyfileobj(file.file, out)
            except Exception as exc:  # noqa: BLE001
                rejected.append({"filename": original_name, "reason": f"Could not save file: {exc}"})
                continue
            finally:
                await file.close()

            if os.path.getsize(target) == 0:
                os.remove(target)
                rejected.append({"filename": original_name, "reason": "File is empty"})
                continue

            if os.path.getsize(target) > settings.max_file_size_bytes:
                os.remove(target)
                rejected.append(
                    {
                        "filename": original_name,
                        "reason": f"Exceeds {settings.MAX_FILE_SIZE_MB} MB limit",
                    }
                )
                continue

            specs.append({"path": target, "filename": original_name})

        job = create_job(self.db, "import", total_files=len(specs))
        if specs:
            start_import_job(job.id, specs)

        return {
            "job_id": job.id,
            "accepted": [s["filename"] for s in specs],
            "rejected": rejected,
            "queued_count": len(specs),
        }

    # -- import: folder ----------------------------------------------------
    def import_folder(self, directory: str, recursive: bool = True) -> dict:
        resolved = require_allowed_path(directory)
        if not os.path.isdir(resolved):
            raise ValueError("Directory not found")

        if recursive:
            files = iter_document_files(resolved)
        else:
            files = [
                os.path.join(resolved, name)
                for name in os.listdir(resolved)
                if os.path.isfile(os.path.join(resolved, name)) and is_supported(name)
            ]

        specs = [{"path": path, "filename": os.path.basename(path)} for path in files]
        job = create_job(self.db, "import", total_files=len(specs))
        if specs:
            start_import_job(job.id, specs)

        return {
            "job_id": job.id,
            "queued_count": len(specs),
            "directory": resolved,
            "files": [s["filename"] for s in specs[:50]],
        }

    # -- listing ----------------------------------------------------------
    def list_documents(
        self,
        skip: int = 0,
        limit: int = 100,
        filename: Optional[str] = None,
        extension: Optional[str] = None,
        status: Optional[str] = None,
    ):
        query = self.db.query(Document)
        if filename:
            query = query.filter(Document.filename.ilike(f"%{filename}%"))
        if extension:
            query = query.filter(Document.extension == extension.lower())
        if status:
            query = query.filter(Document.indexing_status == status)
        total = query.count()
        items = (
            query.order_by(Document.imported_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    def get_document(self, document_id: str) -> Optional[Document]:
        return self.db.query(Document).filter(Document.id == document_id).first()

    def get_chunks(self, document_id: str, skip: int = 0, limit: int = 100):
        query = self.db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        )
        total = query.count()
        items = (
            query.order_by(DocumentChunk.chunk_index).offset(skip).limit(limit).all()
        )
        return items, total

    # -- deletion / re-index ----------------------------------------------
    def delete_document(self, document_id: str) -> bool:
        document = self.get_document(document_id)
        if document is None:
            return False

        pipeline = IndexingPipeline(self.db)
        pipeline.purge_document(document_id)

        # Remove the managed copy only if it lives in our upload directory
        try:
            path = os.path.realpath(document.original_path)
            upload_root = os.path.realpath(UPLOAD_DIR)
            if os.path.commonpath([path, upload_root]) == upload_root and os.path.exists(path):
                os.remove(path)
        except (OSError, ValueError):
            pass

        self.db.delete(document)
        self.db.commit()
        return True

    def reindex_documents(self, document_ids: List[str]) -> Optional[str]:
        existing = (
            self.db.query(Document)
            .filter(Document.id.in_(document_ids))
            .all()
        )
        if not existing:
            return None
        job = create_job(self.db, "reindex", total_files=len(existing))
        start_reindex_job(job.id, [d.id for d in existing])
        return job.id

    # -- change detection --------------------------------------------------
    def scan_for_changes(self) -> dict:
        """Compare stored hashes with the filesystem."""
        documents = self.db.query(Document).all()
        changed, missing, unchanged = [], [], 0

        for document in documents:
            path = document.original_path
            if not os.path.exists(path):
                missing.append({"id": document.id, "filename": document.filename})
                continue
            try:
                current_hash = sha256_file(path)
            except OSError:
                missing.append({"id": document.id, "filename": document.filename})
                continue
            if current_hash != document.file_hash:
                changed.append(
                    {
                        "id": document.id,
                        "filename": document.filename,
                        "modified_at_source": datetime.fromtimestamp(
                            os.path.getmtime(path), tz=timezone.utc
                        ).isoformat(),
                    }
                )
            else:
                unchanged += 1

        job_id = None
        changed_ids = [c["id"] for c in changed]
        if changed_ids:
            for document_id in changed_ids:
                document = self.get_document(document_id)
                if document is None:
                    continue
                document.file_hash = sha256_file(document.original_path)
                self.db.commit()
            job_id = self.reindex_documents(changed_ids)

        return {
            "changed": changed,
            "missing": missing,
            "unchanged": unchanged,
            "reindex_job_id": job_id,
        }
