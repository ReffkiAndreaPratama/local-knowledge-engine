"""Integration tests for indexing, search, deletion and change detection."""
import os

import pytest

from app.indexing.pipeline import IndexingPipeline, sha256_file
from app.models.document import Document, DocumentChunk
from app.models.embedding import EmbeddingMetadata
from app.schemas.search import SearchRequest
from app.services.search_service import SearchService


def make_document(db, path: str, filename: str | None = None) -> Document:
    document = Document(
        filename=filename or os.path.basename(path),
        original_path=path,
        file_hash=sha256_file(path),
        file_size=os.path.getsize(path),
        extension=os.path.splitext(path)[1].lower(),
        parsing_status="pending",
        indexing_status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def index_file(db, path: str, filename: str | None = None) -> Document:
    document = make_document(db, path, filename)
    IndexingPipeline(db).index_document(document)
    db.refresh(document)
    return document


@pytest.fixture()
def corpus(db, tmp_path):
    files = {
        "db_troubleshooting.md": (
            "# Database troubleshooting\n\n"
            "If the application fails to connect to the SQL server, verify the "
            "connection string and confirm the database service is running.\n"
        ),
        "installation.md": (
            "# Installation\n\n"
            "Install the backend with pip install -e . and start it with uvicorn.\n"
        ),
        "payments.csv": "customer,amount\nacme,500\nbeta,150\n",
    }
    documents = {}
    for name, content in files.items():
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        documents[name] = index_file(db, str(path))
    return documents


def test_indexing_creates_chunks_and_fts_rows(db, corpus):
    document = corpus["installation.md"]
    assert document.indexing_status == "completed"
    assert document.parsing_status == "completed"
    assert document.chunk_count >= 1


def test_fulltext_search_finds_relevant_document(db, corpus):
    response = __import__("asyncio").run(
        SearchService(db).search(SearchRequest(query="uvicorn", mode="fulltext"))
    )
    assert response.total >= 1
    assert any("installation.md" in r.document_name for r in response.results)
    assert response.results[0].highlights


def test_search_returns_snippet_and_source_location(db, corpus):
    import asyncio

    response = asyncio.run(
        SearchService(db).search(SearchRequest(query="connection string"))
    )
    assert response.results
    top = response.results[0]
    assert "connection string" in top.content.lower()
    assert top.document_id
    assert top.chunk_id


def test_empty_query_returns_no_results_without_error(db, corpus):
    import asyncio

    response = asyncio.run(SearchService(db).search(SearchRequest(query="")))
    assert response.results == []
    assert response.total == 0
    assert response.notes


def test_search_with_special_characters_does_not_crash(db, corpus):
    import asyncio

    response = asyncio.run(
        SearchService(db).search(SearchRequest(query='"; DROP TABLE documents; --'))
    )
    assert response.total >= 0
    # The documents table must still exist
    assert db.query(Document).count() >= 3


def test_extension_filter_limits_results(db, corpus):
    import asyncio

    response = asyncio.run(
        SearchService(db).search(
            SearchRequest(
                query="customer",
                mode="fulltext",
                filters={"extensions": [".md"]},
            )
        )
    )
    assert all(r.extension == ".md" for r in response.results)


def test_document_filter_limits_results(db, corpus):
    import asyncio

    target = corpus["installation.md"]
    response = asyncio.run(
        SearchService(db).search(
            SearchRequest(
                query="install",
                mode="fulltext",
                filters={"document_ids": [target.id]},
            )
        )
    )
    assert response.results
    assert all(r.document_id == target.id for r in response.results)


def test_delete_removes_chunks_embeddings_and_fts(db, corpus):
    from app.services.document_service import DocumentService

    document = corpus["db_troubleshooting.md"]
    assert db.query(DocumentChunk).filter_by(document_id=document.id).count() > 0

    success = DocumentService(db).delete_document(document.id)
    assert success
    assert db.query(DocumentChunk).filter_by(document_id=document.id).count() == 0
    assert db.query(EmbeddingMetadata).filter_by(document_id=document.id).count() == 0

    import asyncio

    response = asyncio.run(
        SearchService(db).search(SearchRequest(query="troubleshooting"))
    )
    assert all(r.document_id != document.id for r in response.results)


def test_reindex_after_file_change_updates_content(db, tmp_path):
    path = tmp_path / "changing.txt"
    path.write_text("The first version mentions bananas.", encoding="utf-8")
    document = index_file(db, str(path))

    path.write_text("The second version mentions oranges.", encoding="utf-8")
    document.file_hash = sha256_file(str(path))
    db.commit()
    IndexingPipeline(db).index_document(document)

    assert db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document.id,
        DocumentChunk.content.ilike("%oranges%"),
    ).count() == 1
    assert db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document.id,
        DocumentChunk.content.ilike("%bananas%"),
    ).count() == 0


def test_parse_failure_does_not_stop_other_documents(db, tmp_path):
    good = tmp_path / "good.txt"
    good.write_text("This file parses correctly.", encoding="utf-8")
    good_document = index_file(db, str(good))

    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 not really a pdf")
    bad_document = index_file(db, str(bad))

    assert good_document.indexing_status == "completed"
    assert bad_document.indexing_status == "failed"
    assert bad_document.parsing_error


def test_oversized_file_rejected(db, tmp_path, monkeypatch):
    from app.core.config import settings

    path = tmp_path / "big.txt"
    path.write_text("x" * 4096, encoding="utf-8")
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 0)
    document = index_file(db, str(path))
    assert document.indexing_status == "failed"
    assert "limit" in (document.parsing_error or "").lower()


def test_duplicate_documents_are_detected_by_hash(db, tmp_path):
    path = tmp_path / "dup.txt"
    path.write_text("identical content for duplicate detection", encoding="utf-8")
    first = make_document(db, str(path))
    second = make_document(db, str(path))
    assert first.file_hash == second.file_hash


def test_scan_for_changes_detects_modified_and_missing(db, tmp_path):
    from app.services.document_service import DocumentService

    changed_path = tmp_path / "changed.txt"
    changed_path.write_text("original text", encoding="utf-8")
    index_file(db, str(changed_path))

    missing_path = tmp_path / "missing.txt"
    missing_path.write_text("temporary file", encoding="utf-8")
    index_file(db, str(missing_path))

    changed_path.write_text("modified text that changes the hash", encoding="utf-8")
    os.remove(missing_path)

    result = DocumentService(db).scan_for_changes()
    assert len(result["changed"]) == 1
    assert len(result["missing"]) == 1
