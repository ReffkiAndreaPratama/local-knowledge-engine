"""Analytics API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.schemas.settings import StatsResponse
from app.services.stats_service import compute_stats

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """Local-only usage statistics. No external telemetry is collected."""
    return compute_stats(db)
