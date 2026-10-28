"""Settings and stats schemas."""
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PublicSettings(BaseModel):
    app_name: str
    version: str
    database_url: str
    allowed_import_dirs: List[str]
    max_file_size_mb: int
    chunk_size: int
    chunk_overlap: int
    supported_extensions: List[str]
    enable_semantic_search: bool
    embedding_model: str
    embedding_available: bool
    embedding_storage_estimate_mb: int
    enable_ai_assistant: bool
    ai_provider: str
    ai_model: str
    ai_provider_configured: bool
    ollama_base_url: str
    require_ai_consent: bool
    store_search_history: bool
    disable_telemetry: bool


class SettingsUpdate(BaseModel):
    # Reject unknown keys (including secrets) instead of silently ignoring them.
    model_config = ConfigDict(extra="forbid")

    allowed_import_dirs: Optional[List[str]] = None
    max_file_size_mb: Optional[int] = Field(default=None, ge=1, le=2048)
    chunk_size: Optional[int] = Field(default=None, ge=64, le=8192)
    chunk_overlap: Optional[int] = Field(default=None, ge=0, le=4096)
    enable_semantic_search: Optional[bool] = None
    embedding_model: Optional[str] = None
    enable_ai_assistant: Optional[bool] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ollama_base_url: Optional[str] = None
    require_ai_consent: Optional[bool] = None
    store_search_history: Optional[bool] = None


class StatsResponse(BaseModel):
    document_count: int
    chunk_count: int
    total_source_bytes: int
    indexed_documents: int
    failed_documents: int
    pending_documents: int
    query_count: int
    average_response_time_ms: float
    embedding_count: int
    embedding_model: Optional[str]
    embedding_coverage_percent: float
    last_indexed_at: Optional[str]
    storage_backend: str
