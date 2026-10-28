"""API tests: import, listing, deletion, path traversal and settings."""
import io

from tests.helpers import wait_for_job


def test_health_endpoint(client):
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_import_uploaded_file_and_wait_for_indexing(client):
    content = b"# Database guide\n\nThe database connection uses port 5432 by default.\n"
    response = client.post(
        "/api/documents/import",
        files=[("files", ("db-guide.md", io.BytesIO(content), "text/markdown"))],
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["queued_count"] == 1
    job = wait_for_job(client, payload["job_id"])
    assert job["status"] == "completed"
    assert job["processed_files"] == 1

    listing = client.get("/api/documents").json()
    assert listing["total"] == 1
    document = listing["items"][0]
    assert document["indexing_status"] == "completed"
    assert document["chunk_count"] >= 1

    chunks = client.get(f"/api/documents/{document['id']}/chunks").json()
    assert chunks["total"] >= 1
    assert "5432" in chunks["items"][0]["content"]


def test_upload_rejects_disallowed_extension(client):
    response = client.post(
        "/api/documents/import",
        files=[("files", ("malware.exe", io.BytesIO(b"MZ binary"), "application/octet-stream"))],
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["queued_count"] == 0
    assert payload["rejected"]
    assert payload["rejected"][0]["filename"] == "malware.exe"


def test_upload_sanitizes_path_traversal_filename(client):
    response = client.post(
        "/api/documents/import",
        files=[("files", ("../../evil.txt", io.BytesIO(b"content"), "text/plain"))],
    )
    assert response.status_code == 200
    payload = response.json()
    accepted = payload["accepted"]
    assert accepted
    assert ".." not in accepted[0]
    assert "/" not in accepted[0]
    wait_for_job(client, payload["job_id"])


def test_folder_import_outside_allowed_dirs_is_rejected(client):
    response = client.post(
        "/api/documents/import-folder",
        json={"directory": "C:\\Windows\\System32", "recursive": True},
    )
    assert response.status_code == 400
    assert "outside the allowed" in response.json()["detail"].lower()


def test_folder_import_requires_existing_directory(client):
    response = client.post(
        "/api/documents/import-folder",
        json={"directory": "Z:\\definitely\\missing\\path", "recursive": True},
    )
    assert response.status_code == 400


def test_folder_import_inside_allowed_dir(client, temp_dir):
    import os

    with open(os.path.join(temp_dir, "note.txt"), "w", encoding="utf-8") as handle:
        handle.write("Folder import works for plain text files.")

    response = client.post(
        "/api/documents/import-folder",
        json={"directory": temp_dir, "recursive": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["queued_count"] == 1
    job = wait_for_job(client, payload["job_id"])
    assert job["status"] == "completed"
    assert client.get("/api/documents").json()["total"] == 1


def test_search_endpoint_returns_structured_results(client):
    content = b"Hybrid search combines keyword matching with vector similarity.\n"
    payload = client.post(
        "/api/documents/import",
        files=[("files", ("hybrid.txt", io.BytesIO(content), "text/plain"))],
    ).json()
    wait_for_job(client, payload["job_id"])

    response = client.post(
        "/api/search/", json={"query": "vector similarity", "mode": "fulltext"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    first = body["results"][0]
    assert first["document_name"] == "hybrid.txt"
    assert first["snippet"]
    assert first["match_type"] == "fulltext"


def test_search_highlights_terms(client):
    content = b"The migration script adds the payments table.\n"
    payload = client.post(
        "/api/documents/import",
        files=[("files", ("migration.txt", io.BytesIO(content), "text/plain"))],
    ).json()
    wait_for_job(client, payload["job_id"])

    body = client.post("/api/search/", json={"query": "migration", "mode": "fulltext"}).json()
    first = body["results"][0]
    assert "migration" in [h.lower() for h in first["highlights"]]
    assert "<" not in first["snippet"]


def test_search_rejects_invalid_mode(client):
    response = client.post("/api/search/", json={"query": "x", "mode": "bogus"})
    assert response.status_code == 422


def test_semantic_mode_without_model_degrades_gracefully(client):
    content = b"Semantic retrieval requires an embedding model.\n"
    payload = client.post(
        "/api/documents/import",
        files=[("files", ("semantic.txt", io.BytesIO(content), "text/plain"))],
    ).json()
    wait_for_job(client, payload["job_id"])

    response = client.post("/api/search/", json={"query": "embedding", "mode": "semantic"})
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert any("unavailable" in note.lower() for note in body["notes"])


def test_hybrid_mode_falls_back_to_fulltext(client):
    content = b"Hybrid retrieval fuses rankings from two retrievers.\n"
    payload = client.post(
        "/api/documents/import",
        files=[("files", ("fuse.txt", io.BytesIO(content), "text/plain"))],
    ).json()
    wait_for_job(client, payload["job_id"])

    body = client.post("/api/search/", json={"query": "fuses rankings", "mode": "hybrid"}).json()
    assert body["total"] >= 1
    assert body["results"][0]["document_name"] == "fuse.txt"
    assert any("fell back" in note.lower() for note in body["notes"])


def test_delete_document_endpoint(client):
    content = b"Temporary document for deletion test.\n"
    payload = client.post(
        "/api/documents/import",
        files=[("files", ("temp.txt", io.BytesIO(content), "text/plain"))],
    ).json()
    wait_for_job(client, payload["job_id"])

    listing = client.get("/api/documents").json()
    assert listing["total"] == 1
    document_id = listing["items"][0]["id"]
    delete_response = client.delete(f"/api/documents/{document_id}")
    assert delete_response.status_code == 200

    assert client.get(f"/api/documents/{document_id}").status_code == 404
    assert client.get("/api/documents").json()["total"] == 0

    search = client.post("/api/search/", json={"query": "temporary", "mode": "fulltext"}).json()
    assert search["total"] == 0


def test_delete_missing_document_returns_404(client):
    assert client.delete("/api/documents/does-not-exist").status_code == 404


def test_document_listing_filters(client, temp_dir):
    import os

    standalone = os.path.join(temp_dir, "alpha.md")
    with open(standalone, "w", encoding="utf-8") as handle:
        handle.write("Alpha document about indexing.\n")

    payload = client.post(
        "/api/documents/import-folder",
        json={"directory": temp_dir, "recursive": False},
    ).json()
    wait_for_job(client, payload["job_id"])

    assert client.get("/api/documents?extension=.md").json()["total"] == 1
    assert client.get("/api/documents?extension=.pdf").json()["total"] == 0
    assert client.get("/api/documents?filename=alpha").json()["total"] == 1
    assert client.get("/api/documents?filename=zzz").json()["total"] == 0


def test_reindex_endpoint_starts_job(client):
    content = b"Reindexing should be possible from the API.\n"
    payload = client.post(
        "/api/documents/import",
        files=[("files", ("reindex.txt", io.BytesIO(content), "text/plain"))],
    ).json()
    wait_for_job(client, payload["job_id"])

    document_id = client.get("/api/documents").json()["items"][0]["id"]
    response = client.post(f"/api/documents/{document_id}/reindex")
    assert response.status_code == 200
    job = wait_for_job(client, response.json()["job_id"])
    assert job["status"] == "completed"


def test_settings_are_readable_and_secrets_masked(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    payload = response.json()
    assert "chunk_size" in payload
    assert "OPENAI_API_KEY" not in payload
    assert payload["disable_telemetry"] is True


def test_settings_can_be_updated(client):
    response = client.put("/api/settings", json={"chunk_size": 256, "chunk_overlap": 20})
    assert response.status_code == 200
    payload = response.json()
    assert payload["chunk_size"] == 256
    assert payload["chunk_overlap"] == 20


def test_settings_reject_invalid_chunk_size(client):
    response = client.put("/api/settings", json={"chunk_size": 1})
    assert response.status_code == 422


def test_settings_reject_secret_fields(client):
    # API keys are environment-only; the settings API must not accept them.
    response = client.put("/api/settings", json={"openai_api_key": "sk-should-not-be-stored"})
    assert response.status_code == 422
    response = client.put("/api/settings", json={"OPENAI_API_KEY": "sk-should-not-be-stored"})
    assert response.status_code == 422


def test_assistant_without_sources_reports_insufficient_evidence(client):
    response = client.post(
        "/api/assistant/ask",
        json={"question": "What is the meaning of life?", "mode": "fulltext"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["insufficient_evidence"] is True
    assert payload["sources"] == []


def test_assistant_with_sources_but_no_provider_returns_sources(client):
    content = b"The deployment port is 8080 and it is configured in compose.yaml.\n"
    payload = client.post(
        "/api/documents/import",
        files=[("files", ("deploy.txt", io.BytesIO(content), "text/plain"))],
    ).json()
    wait_for_job(client, payload["job_id"])

    response = client.post(
        "/api/assistant/ask",
        json={"question": "Which port is used for deployment?", "mode": "fulltext"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sources"]
    assert body["provider"] == "none"
    assert body["grounded"] is False


def test_analytics_endpoint(client):
    response = client.get("/api/analytics/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["document_count"] == 0
    assert payload["storage_backend"] in {"sqlite", "postgresql"}


def test_search_history_can_be_cleared(client):
    client.post("/api/search/", json={"query": "anything", "mode": "fulltext"})
    response = client.delete("/api/settings/search-history")
    assert response.status_code == 200
    assert response.json()["deleted"] >= 1


def test_unknown_document_returns_404(client):
    assert client.get("/api/documents/unknown-id").status_code == 404


def test_job_not_found_returns_404(client):
    assert client.get("/api/indexing/jobs/nope").status_code == 404
