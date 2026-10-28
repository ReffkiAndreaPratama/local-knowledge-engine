"""Collection and saved-search schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)


class CollectionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    document_count: int = 0
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CollectionListResponse(BaseModel):
    items: List[CollectionResponse]
    total: int


class CollectionMembersRequest(BaseModel):
    document_ids: List[str] = Field(min_length=1)


class SavedSearchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    query: str = Field(min_length=1, max_length=2000)
    search_mode: str = Field(default="fulltext", pattern="^(fulltext|semantic|hybrid)$")


class SavedSearchResponse(BaseModel):
    id: str
    name: str
    query: str
    search_mode: str
    created_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SavedSearchListResponse(BaseModel):
    items: List[SavedSearchResponse]
    total: int
