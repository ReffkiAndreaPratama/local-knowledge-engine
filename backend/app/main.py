"""FastAPI main application."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    assistant,
    collections,
    documents,
    health,
    indexing,
    search,
    stats,
)
from app.api import (
    settings as settings_api,
)
from app.core.config import settings
from app.database.base import Base, SessionLocal, engine
from app.search.fts import ensure_fts_table
from app.services.settings_service import apply_overrides_to_settings

# Create data directories
os.makedirs(os.path.join("data", "documents"), exist_ok=True)

# Create tables
Base.metadata.create_all(bind=engine)

# Create FTS index and apply persisted settings
_db = SessionLocal()
try:
    ensure_fts_table(_db)
    apply_overrides_to_settings(_db)
finally:
    _db.close()

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Privacy-first local document search engine. "
        "All data stays on this machine by default."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(indexing.router, prefix="/api/indexing", tags=["indexing"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["assistant"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])
app.include_router(stats.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(collections.router, prefix="/api/collections", tags=["collections"])
app.include_router(
    collections.saved_search_router, prefix="/api/saved-searches", tags=["saved-searches"]
)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "0.1.0",
        "status": "running",
        "docs": "/api/docs",
    }
