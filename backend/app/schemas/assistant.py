"""Assistant schemas."""
from typing import List, Optional

from pydantic import BaseModel, Field


class AssistantRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    mode: str = Field(default="hybrid", pattern="^(fulltext|semantic|hybrid)$")
    limit: int = Field(default=6, ge=1, le=20)
    provider: Optional[str] = None
    consent_to_external_provider: bool = False


class SourceReference(BaseModel):
    index: int
    chunk_id: str
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    heading: Optional[str] = None
    excerpt: str
    score: Optional[float] = None


class AssistantResponse(BaseModel):
    answer: str
    sources: List[SourceReference] = []
    provider: str
    model: str
    grounded: bool
    insufficient_evidence: bool = False
    invalid_citations: List[int] = []
    warning: Optional[str] = None
    retrieval_mode: str
    notes: List[str] = []
