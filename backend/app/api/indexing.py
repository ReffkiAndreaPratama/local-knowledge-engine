"""Indexing API endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.indexing.jobs import cancel_job
from app.models.indexing import IndexingJob
from app.schemas.indexing import IndexingJobListResponse, IndexingJobResponse

router = APIRouter()


@router.get("/jobs", response_model=IndexingJobListResponse)
@router.get("/jobs/", response_model=IndexingJobListResponse, include_in_schema=False)
async def get_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(IndexingJob)
    if status:
        query = query.filter(IndexingJob.status == status)
    total = query.count()
    jobs = (
        query.order_by(IndexingJob.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"items": jobs, "total": total}


@router.get("/jobs/{job_id}", response_model=IndexingJobResponse)
async def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(IndexingJob).filter(IndexingJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/cancel")
async def cancel_indexing_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(IndexingJob).filter(IndexingJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in {"completed", "failed", "cancelled"}:
        raise HTTPException(status_code=409, detail=f"Job already {job.status}")
    accepted = cancel_job(job_id)
    return {"cancelled": accepted, "job_id": job_id}
