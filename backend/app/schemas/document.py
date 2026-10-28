"""Document schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentBase(BaseModel):
    filename: str
    extension: str


class DocumentResponse(DocumentBase):
    id: str
    original_path: str
    file_hash: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    parsing_status: str
    indexing_status: str
    parsing_error: Optional[str] = None
    page_count: Optional[int] = None
    char_count: Optional[int] = None
    chunk_count: int = 0
    imported_at: Optional[datetime] = None
    modified_at_source: Optional[datetime] = None
    last_indexed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    heading: Optional[str] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ChunkListResponse(BaseModel):
    items: List[ChunkResponse]
    total: int


class RejectedFile(BaseModel):
    filename: str
    reason: str


class DocumentImportResponse(BaseModel):
    job_id: str
    accepted: List[str] = []
    rejected: List[RejectedFile] = []
    queued_count: int = 0


class FolderImportRequest(BaseModel):
    directory: str = Field(min_length=1)
    recursive: bool = True


class FolderImportResponse(BaseModel):
    job_id: str
    queued_count: int
    directory: str
    files: List[str] = []


class ReindexRequest(BaseModel):
    document_ids: List[str] = Field(min_length=1)


class ReindexResponse(BaseModel):
    job_id: str
