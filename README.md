# Local Knowledge Engine

A privacy-first, local document search engine. Import your files once, then find
the right passage with keyword, semantic or hybrid search — and optionally ask an
AI assistant that must answer **only** from your documents and cite its sources.

Everything runs on your machine. No account, no cloud, no telemetry, no GPU
required, and no internet required for the core experience.

---

## Why this exists

Desktop search finds filenames. This finds *passages*, shows the exact source
context, and can compose a grounded answer with verifiable citations. When the
evidence is missing, it says so instead of guessing.

## Features

**Search**

- Full-text search over SQLite **FTS5** with bm25 ranking and highlighted snippets
- Optional **semantic search** with local Sentence Transformers embeddings (CPU)
- **Hybrid search** using Reciprocal Rank Fusion — rank fusion, never raw score addition
- Per-document result caps, deterministic tie-breaking, and an explanation per hit
- Filters by extension and by collection/document

**Documents**

- Import individual files or whole folders recursively
- PDF, TXT, Markdown, DOCX, XLSX, CSV, JSON, HTML and source code
- SHA-256 duplicate detection, safe filenames, path-traversal protection
- Per-file failure isolation: one corrupt file never aborts a batch
- Background indexing jobs with persisted progress, cancellation and live UI polling
- Source preview with chunk text, heading, page number and character offsets
- Re-index, scan for source changes, and delete (removes index + managed copy)

**Knowledge workspace**

- Collections: virtual document groups
- Saved searches
- Search history (can be disabled or cleared)
- Local-only analytics: document/chunk counts, index health, embedding coverage

**AI assistant (optional)**

- Evidence-first: retrieval runs before the model; no evidence means no answer
- Every factual claim must carry `[n]` citations; citations are validated against
  retrieved chunks, and invalid ones are reported
- Document text is treated as untrusted data (prompt-injection defence)
- Ollama (local) or any OpenAI-compatible endpoint (external, explicit consent per request)
- If the provider is down, the response degrades to search results with a warning

**UI**

- React 18 + TypeScript + Vite + Tailwind, light/dark themes, fully offline assets
- Pages: Overview, Search, Documents, Collections, AI Assistant, Indexing Jobs, Settings

## Requirements

- Python **3.10+** (tested on 3.12.10)
- Node.js **18+** (tested on 24.19.0) and npm
- No GPU, external database or API key

## Install

```bash
git clone https://github.com/<your-username>/local-knowledge-engine.git
cd local-knowledge-engine/backend

python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Optional semantic search (adds PyTorch CPU + Sentence Transformers, downloads a
~90 MB model):

```bash
pip install -r requirements-semantic.txt
python ../scripts/download_embedding_model.py
```

Optional AI answers: install [Ollama](https://ollama.com) and pull a model
(`ollama pull llama3.2`), or configure an OpenAI-compatible endpoint. API keys go
in environment variables, never in the UI or database.

Frontend:

```bash
cd ../frontend
npm install
```

Copy `.env.example` to `.env` in the project root only if you want to override
defaults. The app works without it.

## Run

Terminal 1 — backend on `127.0.0.1:8000`:

```bash
cd backend
# Windows:
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
# macOS/Linux:
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Terminal 2 — frontend on `127.0.0.1:5173`:

```bash
cd frontend
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` to the backend. API docs live at
<http://127.0.0.1:8000/api/docs>.

Try it with the synthetic corpus in [`sample_documents/`](sample_documents/): open
**Documents**, upload the files, then search for `Project Halyard` or
`Which port does the Atlas API use?`.

## Tests

These are the real commands and the real results on the development machine
(Windows 10, 8-core CPU, no GPU).

```bash
# Backend - 74 passed
cd backend
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --no-cov

# Frontend — 33 passed (5 files)
cd frontend
node node_modules/vitest/vitest.mjs run

# Production build — succeeds
npm.cmd run build

# End-to-end — 1 passed (Chromium, real backend + UI)
node node_modules/playwright/cli.js install chromium   # first run only
node node_modules/@playwright/test/cli.js test --reporter=list
```

The backend suite uses an isolated temporary SQLite database; it never touches
`backend/data/knowledge.db`. The Playwright config starts both servers itself on
ports `8011`/`5174` with a separate `data/e2e.db`.

> PowerShell may block `npm.ps1`/`npx.ps1` under the default execution policy. Use
> `npm.cmd` or the `node node_modules/...` form shown above.

## Benchmark

Retrieval quality is measured, not claimed. The script indexes the synthetic
corpus into a throw-away database and evaluates 12 labelled queries:

```bash
cd backend
.venv\Scripts\python.exe ..\scripts\benchmark.py --json ..\docs\benchmark-results.json
# semantic + hybrid too (downloads the model on first run):
.venv\Scripts\python.exe ..\scripts\benchmark.py --download-model --json ..\docs\benchmark-results.json
```

Measured on 2026-10-27 (7 documents / 32 chunks, k=5, CPU only):

| Mode | P@1 | Hit@5 | MRR | nDCG@5 | Mean latency |
|------|-----|-------|-----|--------|--------------|
| full-text | 1.000 | 1.000 | 1.000 | 0.993 | 1.4 ms |
| semantic | 0.833 | 1.000 | 0.917 | 0.938 | 16.3 ms |
| hybrid | 0.917 | 1.000 | 0.958 | 0.969 | 32.2 ms |

This corpus is small and keyword-friendly; full-text wins here. Read
[docs/benchmark.md](docs/benchmark.md) for per-query failures, methodology and an
explicit list of what these numbers do **not** prove.

## Configuration

Environment variables (see [`.env.example`](.env.example)):

| Variable | Default | Notes |
|----------|---------|-------|
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Keep `HOST` on loopback |
| `DATABASE_URL` | `sqlite:///./data/knowledge.db` | SQLite only for search |
| `ALLOWED_IMPORT_DIRS` | current user's home | Comma-separated absolute paths |
| `MAX_FILE_SIZE_MB` | `100` | Enforced before parsing |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated CORS origins |
| `ENABLE_SEMANTIC_SEARCH` | `false` | Requires the semantic extra + downloaded model |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Any compatible model |
| `ENABLE_AI_ASSISTANT` | `false` | Ollama or OpenAI-compatible |
| `REQUIRE_AI_CONSENT` | `true` | External providers need per-request consent |
| `STORE_SEARCH_HISTORY` | `true` | Can be disabled or cleared |
| `OPENAI_API_KEY` | unset | Environment only; never stored or returned |

A non-secret subset can be changed at runtime in **Settings**; values are persisted
in SQLite and override environment defaults.

## Documentation

- [Architecture](docs/architecture.md) — components, data model, retrieval design
- [API reference](docs/api.md) — every endpoint and payload
- [Privacy and security](docs/privacy.md) — data flows, threat model, safeguards
- [Development guide](docs/development.md) — setup, tests, conventions, limitations
- [Benchmark](docs/benchmark.md) — methodology and measured results
- [Attributions](ATTRIBUTIONS.md) — dependency licences and reference projects
- [Contributing](CONTRIBUTING.md) · [Security policy](SECURITY.md) · [Code of conduct](CODE_OF_CONDUCT.md)

## Privacy in one paragraph

Documents, chunks, the FTS index, embeddings, settings and history live in a local
SQLite file. Managed copies live in `backend/data/documents/`. The backend binds to
`127.0.0.1`. The UI loads no remote fonts, CDNs or scripts. The only outbound calls
are (a) the explicit embedding-model download and (b) the AI provider you configure
and consent to. There is no telemetry. See [docs/privacy.md](docs/privacy.md).

## Known limitations

Honest gaps in this MVP:

- **SQLite only for search.** FTS5 is SQLite-specific; PostgreSQL is not a
  supported search backend.
- **No authentication.** Single-user, localhost-only. Do not expose the port.
- **In-memory vector scan.** Fine for thousands of chunks, not millions; no ANN index.
- **Single-process job runner.** Use one uvicorn worker.
- **No OCR.** Image-only PDFs fail or import empty.
- **No reranker**, no table/layout-aware PDF extraction.
- **Semantic model must be downloaded explicitly**; it is never fetched silently.
- **Narrow provider support.** Ollama and OpenAI-compatible only (no native
  Anthropic adapter).
- **No migrations workflow in use.** Tables are created via
  `Base.metadata.create_all`; no Alembic revisions ship.
- **Small synthetic benchmark.** It cannot prove real-world quality at scale.
- **No Docker image.** Docker was not available on the development machine, so no
  untested Dockerfile is shipped.
- **PyMuPDF is AGPL-3.0/commercial.** If you distribute the app, read
  [ATTRIBUTIONS.md](ATTRIBUTIONS.md) — the MIT licence does not override it.

## Project structure

```
local-knowledge-engine/
├── backend/            FastAPI app, tests, requirements
│   ├── app/
│   │   ├── api/        HTTP routers
│   │   ├── services/   business logic
│   │   ├── indexing/   pipeline, chunker, background jobs
│   │   ├── search/     FTS5, semantic, RRF hybrid
│   │   ├── retrieval/  prompt building + citation validation
│   │   ├── providers/  Ollama, OpenAI-compatible
│   │   ├── parsers/    per-format extractors
│   │   └── ...
│   └── tests/          pytest suite (isolated temp DB)
├── frontend/           React + Vite + Tailwind
│   ├── src/pages/      one component per route
│   ├── src/components/ layout and UI primitives
│   └── e2e/            Playwright flow
├── sample_documents/   synthetic corpus used by tests and benchmark
├── scripts/            benchmark + explicit model downloader
├── docs/               architecture, API, privacy, development, benchmark
└── .github/workflows/  CI (backend, frontend, e2e)
```

## License

[MIT](LICENSE) for this project's code. Third-party components keep their own
licences — see [ATTRIBUTIONS.md](ATTRIBUTIONS.md). PyMuPDF's AGPL/commercial dual
licence is called out there explicitly.

## Acknowledgments

Inspired by [Soma](https://github.com/AwesomeDog/soma),
[QMD](https://github.com/tobi/qmd),
[Open WebUI](https://github.com/open-webui/open-webui),
[SeekX](https://github.com/oceanbase/seekx) and
[GNO](https://github.com/gmickel/gno). No code was copied; see
[ATTRIBUTIONS.md](ATTRIBUTIONS.md) for the licence review.
