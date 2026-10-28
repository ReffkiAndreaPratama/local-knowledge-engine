# Local Knowledge Engine — backend

FastAPI service for the Local Knowledge Engine. See the
[project README](../README.md) and [documentation](../docs/architecture.md) for
architecture, installation and API details.

Quick commands (from this directory):

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
pytest -q
```

Semantic search is optional: install `requirements-semantic.txt`, run
`python ../scripts/download_embedding_model.py`, then enable it in Settings.
