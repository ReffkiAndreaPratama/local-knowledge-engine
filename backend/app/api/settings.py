"""Settings API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.base import get_db
from app.models.search import SearchHistory
from app.schemas.settings import PublicSettings, SettingsUpdate
from app.services.settings_service import get_public_settings, update_settings

router = APIRouter()


@router.get("", response_model=PublicSettings)
@router.get("/", response_model=PublicSettings, include_in_schema=False)
async def read_settings(db: Session = Depends(get_db)):
    """Return settings safe to display in the UI."""
    return get_public_settings(db)


@router.put("", response_model=PublicSettings)
@router.put("/", response_model=PublicSettings, include_in_schema=False)
async def write_settings(update: SettingsUpdate, db: Session = Depends(get_db)):
    """Update configurable settings. Secrets are never accepted here."""
    update_settings(db, update.model_dump(exclude_none=True))
    return get_public_settings(db)


@router.delete("/search-history")
async def clear_search_history(db: Session = Depends(get_db)):
    """Delete all stored search history."""
    deleted = db.query(SearchHistory).delete()
    db.commit()
    return {"deleted": deleted}
