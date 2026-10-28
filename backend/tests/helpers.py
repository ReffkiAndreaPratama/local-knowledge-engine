"""Shared helpers for API tests."""
import time


def wait_for_job(client, job_id: str, timeout: float = 30.0) -> dict:
    """Poll an indexing job until it reaches a terminal state."""
    deadline = time.monotonic() + timeout
    job = {"status": "unknown"}
    while time.monotonic() < deadline:
        response = client.get(f"/api/indexing/jobs/{job_id}")
        if response.status_code == 200:
            job = response.json()
            if job["status"] in {"completed", "failed", "cancelled"}:
                return job
        time.sleep(0.05)
    return job
