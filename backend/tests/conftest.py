"""Pytest configuration and shared fixtures."""
import os
import sys
import tempfile

# Configure an isolated environment before the app is imported
_TEST_DIR = tempfile.mkdtemp(prefix="lke-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_TEST_DIR, 'test.db').replace(os.sep, '/')}"
os.environ["ALLOWED_IMPORT_DIRS"] = _TEST_DIR
os.environ["ENABLE_SEMANTIC_SEARCH"] = "false"
os.environ["ENABLE_AI_ASSISTANT"] = "false"
os.environ["STORE_SEARCH_HISTORY"] = "true"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event, text  # noqa: E402

from app.database.base import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.search.fts import clear_fts, ensure_fts_table  # noqa: E402


# SQLite on Windows can spend seconds on fsync for each DDL statement.
# Tests do not need durability, so turn that off for the test database only.
@event.listens_for(engine, "connect")
def _test_sqlite_pragmas(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA synchronous=OFF")
    cursor.close()


_BASELINE = {
    "CHUNK_SIZE": __import__("app.core.config", fromlist=["settings"]).settings.CHUNK_SIZE,
    "CHUNK_OVERLAP": __import__("app.core.config", fromlist=["settings"]).settings.CHUNK_OVERLAP,
    "MAX_FILE_SIZE_MB": __import__("app.core.config", fromlist=["settings"]).settings.MAX_FILE_SIZE_MB,
    "ALLOWED_IMPORT_DIRS": _TEST_DIR,
}


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def temp_dir():
    return tempfile.mkdtemp(prefix="lke-files-", dir=_TEST_DIR)


@pytest.fixture(autouse=True)
def clean_database():
    """Reset stored rows between tests without paying DDL costs."""
    from app.indexing.jobs import wait_for_jobs

    wait_for_jobs(timeout=30.0)

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        ensure_fts_table(session)
        # Delete in dependency order
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(text(f"DELETE FROM {table.name}"))
        session.commit()
        clear_fts(session)
    finally:
        session.close()

    from app.core.config import settings

    for attribute, value in _BASELINE.items():
        setattr(settings, attribute, value)

    yield

    wait_for_jobs(timeout=30.0)
