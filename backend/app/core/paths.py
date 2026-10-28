"""Filesystem path safety helpers."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

from app.core.config import settings

_UNSAFE_NAME = re.compile(r"[^\w\-. ]", re.UNICODE)


def sanitize_filename(name: str, fallback: str = "document") -> str:
    """Return a safe basename, never containing directory separators."""
    name = os.path.basename(name.replace("\\", "/"))
    name = name.strip().strip(".")
    name = _UNSAFE_NAME.sub("_", name)
    name = name[:200]
    if not name or name in {".", ".."}:
        return fallback
    return name


def allowed_roots() -> List[str]:
    """Return the resolved directories the app may read from."""
    raw = (settings.ALLOWED_IMPORT_DIRS or "").strip()
    if raw:
        roots = [p.strip() for p in raw.split(",") if p.strip()]
    else:
        roots = [str(Path.home())]
    resolved = []
    for root in roots:
        try:
            resolved.append(os.path.realpath(os.path.expanduser(root)))
        except OSError:
            continue
    return resolved


def is_path_allowed(path: str) -> bool:
    """True when `path` resolves inside one of the allowed roots.

    Prevents path traversal (`../`) and symlink escapes.
    """
    try:
        resolved = os.path.realpath(os.path.expanduser(path))
    except OSError:
        return False

    for root in allowed_roots():
        try:
            if os.path.commonpath([resolved, root]) == root:
                return True
        except ValueError:
            # Different drives on Windows
            continue
    return False


def require_allowed_path(path: str) -> str:
    """Return the resolved path or raise ValueError when outside allowed roots."""
    if not is_path_allowed(path):
        raise ValueError(
            "Path is outside the allowed import directories. "
            "Add the directory in Settings before indexing it."
        )
    return os.path.realpath(os.path.expanduser(path))


def iter_document_files(directory: str, max_files: int = 5000) -> List[str]:
    """Walk a directory recursively collecting supported files."""
    from app.parsers.registry import is_supported

    collected: List[str] = []
    for root, dirs, files in os.walk(directory):
        # Skip hidden and dependency directories
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".") and d not in {"node_modules", "__pycache__", "venv", ".venv"}
        ]
        for filename in files:
            if filename.startswith("."):
                continue
            full = os.path.join(root, filename)
            if is_supported(full):
                collected.append(full)
                if len(collected) >= max_files:
                    return collected
    return collected
