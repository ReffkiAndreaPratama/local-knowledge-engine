# Development guide

Everything you need to change the code, run the tests and understand the
conventions. Installation steps for end users live in the
[README](../README.md); architecture is in [architecture.md](architecture.md).

## Requirements

- Python **3.10+** (the test machine used 3.12.10)
- Node.js **18+** and npm (the test machine used 24.19.0)
- No GPU, database server or cloud account

## Setup

```bash
git clone <your fork>
cd local-knowledge-engine/backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
```

`requirements-dev.txt` pulls in the core runtime plus pytest and ruff.

Semantic search is an optional extra:

```bash
pip install -r requirements-semantic.txt
python ../scripts/download_embedding_model.py   # explicit, downloads ~90 MB
```

The core install and all backend tests run **without** `sentence-transformers`.
Do not add it to `requirements.txt`; the optional-dependency split is deliberate.

Frontend:

```bash
cd frontend
npm install
```

## Running locally

Terminal 1:

```bash
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
cd frontend
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` to `http://127.0.0.1:8000`.
Override the proxy target with `VITE_API_TARGET` for an isolated backend.

Useful URLs:

- `http://127.0.0.1:8000/api/docs` — Swagger UI
- `http://127.0.0.1:8000/api/health/` — health check
- `http://127.0.0.1:5173` — app

## Tests

### Backend

```bash
cd backend
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --no-cov
```

Notes:

- `tests/conftest.py` sets `DATABASE_URL` to a fresh temporary SQLite file **before
  the app is imported**. Tests never touch `data/knowledge.db`.
- `PRAGMA synchronous=OFF` is applied to the test database only, because fsync for
  every DDL statement is slow on Windows and tests do not need durability.
- Between tests the suite deletes rows instead of dropping/recreating tables.
- Background jobs are awaited with `wait_for_jobs()` so assertions are not racy.
- Settings changed through the API are restored to their baseline after each test.

Coverage by file:

| File | Focus |
|------|-------|
| `test_parsers.py` | every parser, malformed and empty input |
| `test_chunker.py` | overlap, section boundaries, offsets |
| `test_indexing_search.py` | import → index → search, duplicates, deletion |
| `test_search_ranking.py` | FTS query escaping, AND→OR fallback, RRF, per-document cap |
| `test_citations.py` | citation validation, insufficient evidence, consent gate |
| `test_api.py` | endpoint contracts, settings, stats, collections, saved searches |

### Frontend unit tests

```bash
cd frontend
node node_modules/vitest/vitest.mjs run     # or: npm test
```

Vitest + jsdom + Testing Library. Each page test mocks `@/lib/api` and renders
through `renderWithProviders` (`src/test/utils.tsx`), which supplies the query
client, router and toast provider.

### End-to-end

```bash
cd frontend
node node_modules/playwright/cli.js install chromium   # first time only
node node_modules/@playwright/test/cli.js test --reporter=list
```

`playwright.config.ts` starts **both** servers itself:

- backend on `127.0.0.1:8011` with `DATABASE_URL=sqlite:///./data/e2e.db` and
  semantic/AI/history disabled;
- Vite on `127.0.0.1:5174` with `VITE_API_TARGET` pointing at that backend.

The single flow imports `sample_documents/atlas-onboarding.txt`, waits for the
background job, searches for "Project Halyard", opens the source preview, deletes
the document and verifies it is gone. Because the database persists between runs,
the test tolerates a previously imported document: duplicates are skipped by hash
but the existing row is still found and deleted.

> On Windows PowerShell, `npx`/`npm.ps1` may be blocked by the execution policy.
> Use `npm.cmd`, or call the CLI through `node node_modules/...` as shown above.

## Linting and types

```bash
cd backend
.venv\Scripts\python.exe -m ruff check app tests

cd frontend
node node_modules/typescript/bin/tsc --noEmit
```

`ruff check` enforces the import/error rules selected in `pyproject.toml`
(`E`, `F`, `I`, `W`, with `E501` deferred to the editor). `tsc` is the same
type-check that `npm run build` performs. There is no mypy step because the
codebase is not currently annotated strictly enough to make it meaningful.

## Benchmark

See [benchmark.md](benchmark.md). Short version:

```bash
cd backend
.venv\Scripts\python.exe ..\scripts\benchmark.py --json ..\docs\benchmark-results.json
```

## Code map

| Area | Where | Notes |
|------|-------|-------|
| HTTP layer | `backend/app/api/` | thin routers; validation via Pydantic schemas |
| Business logic | `backend/app/services/` | document, search, assistant, settings, stats, collections |
| Indexing | `backend/app/indexing/` | pipeline, chunker, thread jobs |
| Retrieval | `backend/app/search/` | FTS5, semantic, RRF |
| Prompt/citations | `backend/app/retrieval/context.py` | the only place prompts are built |
| Providers | `backend/app/providers/` | Ollama, OpenAI-compatible |
| Parsers | `backend/app/parsers/` | one function per format + registry |
| UI primitives | `frontend/src/components/ui/` | single barrel export |
| Pages | `frontend/src/pages/` | one component per route |

## Conventions

- **Backend**: type hints everywhere, `from __future__ import annotations` for
  modules that need it, no business logic in routers, no raw SQL outside
  `app/search/`.
- **Frontend**: function components, TanStack Query for server state, Lucide icons,
  Tailwind utility classes with the design tokens in `src/index.css`. UI components
  are imported from `@/components/ui`.
- **Errors**: backend raises `ValueError`/`HTTPException` with a human-readable
  message; frontend surfaces it through `extractErrorMessage`.
- **Degradation**: a missing optional dependency must produce a visible `notes` or
  `warning`, never a silent empty result.

## Known limitations

These are real gaps in the MVP, not TODOs that are already half-finished:

- **SQLite only for search.** FTS5 is SQLite-specific. PostgreSQL is not supported
  as a search backend. The SQLAlchemy models would port, but `app/search/fts.py`
  and `fulltext.py` would need a different implementation.
- **No authentication.** Single-user, localhost-only. Do not expose it.
- **In-memory vector scan.** Semantic search loads all vectors and computes cosine
  similarity in NumPy. Fine for thousands of chunks; it does not scale to millions
  and has no ANN index.
- **Single-process job runner.** Indexing uses daemon threads in the API process.
  Running multiple uvicorn workers would give each worker its own job registry. Use
  one worker.
- **Cancellation is cooperative.** The current file finishes before the job stops.
- **No OCR.** Image-only PDFs import as empty/failed. There is no Tesseract
  integration.
- **Chunk-level indexing only.** There is no table-aware or layout-aware extraction
  for complex PDFs, and no reranker.
- **Semantic model is a manual download.** Nothing downloads automatically; that is
  intentional, but it means semantic search is off until you opt in.
- **Provider support is narrow.** Ollama and OpenAI-compatible endpoints only. The
  registry has no native Anthropic adapter.
- **No migrations workflow in use.** Tables are created with
  `Base.metadata.create_all`; no Alembic revisions are shipped. Changing a column
  type requires a manual migration or a fresh database.
- **Offset pagination only.** Deep pagination is not optimised.
- **No accessibility audit.** Basic semantics and focus styles are present, but the
  app has not been tested with a screen reader.
- **Benchmark corpus is small and synthetic.** Seven documents cannot prove
  real-world retrieval quality. See [benchmark.md](benchmark.md).
- **No Docker image.** Docker was not available on the development machine, so no
  untested Dockerfile is shipped.

## Adding a parser

1. Write `parse_x(path) -> ParsedDocument` in `app/parsers/`.
2. Populate `ParsedSection.text`, and `page_number`/`heading` when known.
3. Raise `ParseError` with a readable message on failure.
4. Register the extension in `app/parsers/registry.py`.
5. Add a fixture and a test in `tests/test_parsers.py`.
6. Add the extension to `ALLOWED_EXTENSIONS` in `app/core/config.py` and
   `.env.example`.
