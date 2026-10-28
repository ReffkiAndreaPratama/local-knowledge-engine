"""Settings persistence and effective-value resolution."""
from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.paths import allowed_roots
from app.models.settings import ApplicationSetting
from app.parsers.registry import get_supported_extensions
from app.providers.registry import get_provider_info

# Keys the API is allowed to change at runtime
EDITABLE_KEYS = {
    "allowed_import_dirs",
    "max_file_size_mb",
    "chunk_size",
    "chunk_overlap",
    "enable_semantic_search",
    "embedding_model",
    "enable_ai_assistant",
    "ai_provider",
    "ai_model",
    "ollama_base_url",
    "require_ai_consent",
    "store_search_history",
}

DEFAULTS: Dict[str, str] = {
    "store_search_history": "true",
}

# Mapping from DB key to the Settings attribute name
_ATTR_MAP = {
    "ALLOWED_IMPORT_DIRS": "allowed_import_dirs",
    "MAX_FILE_SIZE_MB": "max_file_size_mb",
    "CHUNK_SIZE": "chunk_size",
    "CHUNK_OVERLAP": "chunk_overlap",
    "ENABLE_SEMANTIC_SEARCH": "enable_semantic_search",
    "EMBEDDING_MODEL": "embedding_model",
    "ENABLE_AI_ASSISTANT": "enable_ai_assistant",
    "AI_PROVIDER": "ai_provider",
    "AI_MODEL": "ai_model",
    "OLLAMA_BASE_URL": "ollama_base_url",
    "REQUIRE_AI_CONSENT": "require_ai_consent",
    "STORE_SEARCH_HISTORY": "store_search_history",
}


def _serialize(key: str, value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return str(value)


def _deserialize(key: str, raw: str) -> Any:
    if key in {"enable_semantic_search", "enable_ai_assistant", "require_ai_consent", "store_search_history"}:
        return raw.strip().lower() in {"true", "1", "yes", "on"}
    if key in {"max_file_size_mb", "chunk_size", "chunk_overlap"}:
        return int(raw)
    if key == "allowed_import_dirs":
        return [p.strip() for p in raw.split(",") if p.strip()]
    return raw


def load_overrides(db: Session) -> Dict[str, Any]:
    rows = db.query(ApplicationSetting).all()
    values: Dict[str, Any] = {}
    for row in rows:
        if row.key in EDITABLE_KEYS:
            try:
                values[row.key] = _deserialize(row.key, row.value or "")
            except (TypeError, ValueError):
                continue
    return values


def apply_overrides_to_settings(db: Session) -> None:
    """Apply persisted settings to the in-process Settings object."""
    for key, value in load_overrides(db).items():
        attr = _ATTR_MAP.get(key.upper())
        if attr is None:
            continue
        if attr == "allowed_import_dirs":
            setattr(settings, "ALLOWED_IMPORT_DIRS", ",".join(value))
        elif attr == "store_search_history":
            setattr(settings, "STORE_SEARCH_HISTORY", value)
        else:
            setattr(settings, attr.upper(), value)


def update_settings(db: Session, updates: Dict[str, Any]) -> None:
    for key, value in updates.items():
        if key not in EDITABLE_KEYS or value is None:
            continue
        row = db.query(ApplicationSetting).filter(ApplicationSetting.key == key).first()
        serialized = _serialize(key, value)
        if row is None:
            db.add(ApplicationSetting(key=key, value=serialized))
        else:
            row.value = serialized
    db.commit()
    apply_overrides_to_settings(db)


def store_search_history_enabled(db: Session) -> bool:
    overrides = load_overrides(db)
    return bool(overrides.get("store_search_history", True))


def get_public_settings(db: Session) -> dict:
    provider_info = get_provider_info()
    from app.embeddings import EmbeddingEngine

    engine = EmbeddingEngine.get_instance()
    return {
        "app_name": settings.APP_NAME,
        "version": "0.1.0",
        "database_url": _safe_database_url(settings.DATABASE_URL),
        "allowed_import_dirs": allowed_roots(),
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "chunk_size": settings.CHUNK_SIZE,
        "chunk_overlap": settings.CHUNK_OVERLAP,
        "supported_extensions": sorted(get_supported_extensions()),
        "enable_semantic_search": settings.ENABLE_SEMANTIC_SEARCH,
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_available": engine.is_loaded,
        "embedding_storage_estimate_mb": engine.storage_estimate_mb,
        "enable_ai_assistant": settings.ENABLE_AI_ASSISTANT,
        "ai_provider": settings.AI_PROVIDER,
        "ai_model": settings.AI_MODEL,
        "ai_provider_configured": provider_info.configured,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "require_ai_consent": settings.REQUIRE_AI_CONSENT,
        "store_search_history": store_search_history_enabled(db),
        "disable_telemetry": settings.DISABLE_TELEMETRY,
    }


def _safe_database_url(url: str) -> str:
    """Hide credentials in a database URL before exposing it."""
    if "@" not in url:
        return url
    scheme, _, rest = url.partition("://")
    if "@" not in rest:
        return url
    _, _, host_part = rest.rpartition("@")
    return f"{scheme}://***@{host_part}"
