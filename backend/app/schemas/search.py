"""Search schemas."""
from typing import List, Optional

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    document_ids: Optional[List[str]] = None
    extensions: Optional[List[str]] = None


class SearchRequest(BaseModel):
    query: str = Field(default="", max_length=2000)
    mode: str = Field(default="fulltext", pattern="^(fulltext|semantic|hybrid)$")
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    filters: Optional[SearchFilters] = None
    fts_weight: float = Field(default=1.0, ge=0.0, le=10.0)
    semantic_weight: float = Field(default=1.0, ge=0.0, le=10.0)
    max_per_document: int = Field(default=2, ge=1, le=20)


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    extension: str = ""
    content: str
    snippet: str
    page_number: Optional[int] = None
    heading: Optional[str] = None
    score: Optional[float] = None
    highlights: List[str] = []
    match_type: str = "fulltext"  # fulltext | semantic | hybrid
    explanation: str = ""


class SearchResponse(BaseModel):
    results: List[SearchResultItem]
    total: int
    query: str
    mode: str
    response_time_ms: int
    notes: List[str] = []
