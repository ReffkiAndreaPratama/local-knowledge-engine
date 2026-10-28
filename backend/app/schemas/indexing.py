"""Indexing job schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class IndexingJobResponse(BaseModel):
    id: str
    status: str
    job_type: str
    total_files: int
    processed_files: int
    failed_files: int
    current_file: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class IndexingJobListResponse(BaseModel):
    items: list[IndexingJobResponse]
    total: int
