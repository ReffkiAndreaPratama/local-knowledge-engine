"""Background indexing jobs.

Jobs run in a single worker thread with their own DB session. Progress is
persisted to the `indexing_jobs` table so the UI can poll it.
"""
from __future__ import annotations

import os
import threading
import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from app.database.base import SessionLocal
from app.indexing.pipeline import IndexingPipeline, sha256_file
from app.models.document import Document
from app.models.indexing import IndexingJob

_JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()
_THREADS: dict[str, threading.Thread] = {}


def create_job(db: Session, job_type: str, total_files: int = 0) -> IndexingJob:
    job = IndexingJob(
        id=str(uuid.uuid4()),
        status="pending",
        job_type=job_type,
        total_files=total_files,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _update_job(job_id: str, **fields) -> None:
    with _LOCK:
        _JOBS.setdefault(job_id, {}).update(fields)
    db = SessionLocal()
    try:
        job = db.query(IndexingJob).filter(IndexingJob.id == job_id).first()
        if job:
            for key, value in fields.items():
                setattr(job, key, value)
            db.commit()
    finally:
        db.close()


def is_cancelled(job_id: str) -> bool:
    with _LOCK:
        return bool(_JOBS.get(job_id, {}).get("cancelled"))


def cancel_job(job_id: str) -> bool:
    with _LOCK:
        if job_id in _JOBS:
            _JOBS[job_id]["cancelled"] = True
            return True
    return False


def start_import_job(job_id: str, file_specs: List[dict]) -> None:
    """Start a background thread importing the given files.

    Each spec is {"path": str, "filename": str}.
    """
    thread = threading.Thread(
        target=_run_import, args=(job_id, file_specs), daemon=True
    )
    with _LOCK:
        _THREADS[job_id] = thread
    thread.start()


def wait_for_jobs(timeout: float = 60.0) -> None:
    """Block until all started jobs have finished (used by tests/shutdown)."""
    with _LOCK:
        threads = list(_THREADS.values())
    for thread in threads:
        thread.join(timeout=timeout)


def _run_import(job_id: str, file_specs: List[dict]) -> None:
    db = SessionLocal()
    try:
        _update_job(
            job_id,
            status="running",
            started_at=datetime.now(timezone.utc),
            total_files=len(file_specs),
        )
        pipeline = IndexingPipeline(db)
        processed = 0
        failed = 0

        for spec in file_specs:
            if is_cancelled(job_id):
                _update_job(
                    job_id,
                    status="cancelled",
                    completed_at=datetime.now(timezone.utc),
                    processed_files=processed,
                    failed_files=failed,
                )
                return

            path = spec["path"]
            filename = spec.get("filename") or os.path.basename(path)
            _update_job(job_id, current_file=filename)

            try:
                file_hash = sha256_file(path)
                existing = (
                    db.query(Document).filter(Document.file_hash == file_hash).first()
                )
                if existing:
                    processed += 1
                    _update_job(job_id, processed_files=processed, failed_files=failed)
                    continue

                ext = os.path.splitext(path)[1].lower()
                document = Document(
                    filename=filename,
                    original_path=path,
                    file_hash=file_hash,
                    file_size=os.path.getsize(path),
                    extension=ext,
                    parsing_status="pending",
                    indexing_status="pending",
                    modified_at_source=datetime.fromtimestamp(
                        os.path.getmtime(path), tz=timezone.utc
                    ),
                )
                db.add(document)
                db.commit()
                db.refresh(document)

                result = pipeline.index_document(document)
                if result.indexing_status == "completed":
                    processed += 1
                else:
                    failed += 1

            except Exception as exc:  # noqa: BLE001
                failed += 1
                db.rollback()
                _update_job(job_id, error_message=str(exc)[:500])

            _update_job(job_id, processed_files=processed, failed_files=failed)

        _update_job(
            job_id,
            status="completed",
            completed_at=datetime.now(timezone.utc),
            processed_files=processed,
            failed_files=failed,
            current_file=None,
        )
    finally:
        db.close()


def start_reindex_job(job_id: str, document_ids: List[str]) -> None:
    thread = threading.Thread(
        target=_run_reindex, args=(job_id, document_ids), daemon=True
    )
    with _LOCK:
        _THREADS[job_id] = thread
    thread.start()


def _run_reindex(job_id: str, document_ids: List[str]) -> None:
    db = SessionLocal()
    try:
        _update_job(
            job_id,
            status="running",
            started_at=datetime.now(timezone.utc),
            total_files=len(document_ids),
        )
        pipeline = IndexingPipeline(db)
        processed = 0
        failed = 0

        for document_id in document_ids:
            if is_cancelled(job_id):
                _update_job(job_id, status="cancelled", completed_at=datetime.now(timezone.utc))
                return

            document = db.query(Document).filter(Document.id == document_id).first()
            if document is None:
                failed += 1
                continue

            _update_job(job_id, current_file=document.filename)
            result = pipeline.index_document(document)
            if result.indexing_status == "completed":
                processed += 1
            else:
                failed += 1
            _update_job(job_id, processed_files=processed, failed_files=failed)

        _update_job(
            job_id,
            status="completed",
            completed_at=datetime.now(timezone.utc),
            processed_files=processed,
            failed_files=failed,
            current_file=None,
        )
    finally:
        db.close()
