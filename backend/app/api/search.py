"""Search API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import SearchService

router = APIRouter()


@router.post("/", response_model=SearchResponse)
async def search(request: SearchRequest, db: Session = Depends(get_db)):
    """Perform search."""
    service = SearchService(db)
    results = await service.search(request)
    return results
