# Architecture

Local Knowledge Engine is a single-user, local-first document search application.
It is deliberately small enough to understand and audit: one FastAPI service, one
SQLite database, and one React single-page application.

## System overview

```
┌──────────────────────────── browser (localhost) ────────────────────────────┐
│  React 18 + TypeScript + Vite + Tailwind                                     │
│  Overview · Search · Documents · Collections · Assistant · Jobs · Settings   │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │ HTTP /api (Vite proxy in development)
┌───────────────────────────────────▼──────────────────────────────────────────┐
│  FastAPI (uvicorn, 127.0.0.1 by default)                                     │
│                                                                              │
│  api/            thin HTTP routers + Pydantic validation                     │
│  services/       document, search, assistant, settings, stats, collections   │
│  indexing/       validation → parsing → chunking → FTS → optional embeddings │
│  search/         FTS5 full-text · cosine semantic · RRF hybrid               │
│  retrieval/      evidence prompt construction + citation validation          │
│  providers/      Ollama (local) · OpenAI-compatible (external, opt-in)       │
│  parsers/        PDF, DOCX, XLSX, CSV, JSON, HTML, MD, TXT, source code      │
└───────────────┬───────────────────────────────────┬──────────────────────────┘
                │                                   │
       ┌────────▼─────────┐                ┌────────▼──────────────┐
       │  SQLite           │                │  data/documents/      │
       │  metadata, chunks │                │  managed uploads      │
       │  FTS5, embeddings │                │  (original files)     │
       │  jobs, settings   │                └───────────────────────┘
       └───────────────────┘
```

Background imports run in daemon threads; their progress is persisted to the
`indexing_jobs` table so the UI can poll it even if the page reloads.

## Directory layout

```
backend/
  app/
    api/            HTTP endpoints
    core/           configuration and path-safety helpers
    database/       SQLAlchemy engine/session
    embeddings/     lazy sentence-transformers wrapper
    indexing/       chunker, pipeline, background jobs
    models/         SQLAlchemy models
    parsers/        per-format parsers and registry
    providers/      AI provider adapters
    retrieval/      prompt construction and citation validation
    schemas/        Pydantic request/response models
    search/         FTS5, semantic and hybrid retrieval
    services/       business logic used by the API
  tests/            pytest suite (isolated temporary database)
frontend/
  src/
    components/     layout, dialogs, UI primitives
    hooks/          theme and debounce hooks
    lib/            API client, toasts, formatting helpers
    pages/          one component per route
    test/           Vitest setup and shared render helper
  e2e/              Playwright end-to-end flow
sample_documents/   synthetic corpus used by tests and the benchmark
scripts/            dev launcher, model downloader, retrieval benchmark
docs/               this documentation
```

## Data model

| Table | Purpose |
|-------|---------|
| `documents` | One row per imported file: path, SHA-256, size, status, counts, timestamps |
| `document_chunks` | Chunk text plus source location (`page_number`, `heading`, char offsets) |
| `document_chunks_fts` | SQLite FTS5 virtual table: content, filename, extension, heading |
| `embedding_metadata` | One L2-normalised float32 vector per chunk, model name/dimension |
| `collections` / `collection_documents` | Virtual document groups (many-to-many) |
| `saved_searches` | Named query + mode |
| `search_history` | Query, mode, result count and latency (can be disabled) |
| `indexing_jobs` | Persisted background-job status and counters |
| `application_settings` | Runtime settings that override environment defaults |

The FTS table is updated manually (insert/delete on re-index) rather than through
SQL triggers. That keeps the write path explicit and avoids duplicate FTS rows
when a document is replaced.

## Ingestion pipeline

1. **Validate** — extension allowlist, non-empty file, size limit, parser exists.
2. **Hash** — SHA-256 is compared against existing documents; unchanged duplicates
   are skipped.
3. **Parse** — format-specific parser returns sections with optional page or
   heading metadata. A parser error fails only that file.
4. **Chunk** — 512 characters with 50 characters of overlap by default. Chunks
   never span two sections, and prefer paragraph/sentence boundaries. Each chunk
   keeps its page, heading and character offsets.
5. **Persist** — replace previous chunks and FTS rows atomically in one commit.
6. **Embed (optional)** — only when semantic search is enabled and the model is
   already cached. Embedding failures never fail indexing; the document remains
   searchable by keywords.
7. **Record** — status, counts and job counters are persisted for the UI.

Validation and per-file failure isolation mean one corrupt PDF does not abort a
500-file import.

## Retrieval

### Full-text (SQLite FTS5)

Every user term is quoted before being placed in an FTS5 `MATCH` expression, so
operators such as `AND`, `OR`, `NEAR`, `*` or `"` are treated as literal text.
The builder first tries an AND of all terms, then falls back to an OR of
meaningful terms (stopwords removed) for natural-language questions. Results are
ranked by FTS5 `bm25` and return a highlighted snippet.

### Semantic

`sentence-transformers` is imported lazily and only when explicitly enabled. The
query and stored chunk vectors are L2-normalised float32 arrays; similarity is a
dot product (equal to cosine similarity). Vectors whose model name or dimension
do not match the current model are ignored, preventing silent cross-model
comparisons. If the dependency or model is missing, search returns a clear
`notes` message instead of pretending semantic search worked.

### Hybrid

Full-text and semantic scores are not comparable (bm25 is unbounded and lower is
better; cosine lies in `[-1, 1]`). Hybrid ranking therefore uses **Reciprocal
Rank Fusion** over the two ranked lists:

```
score(chunk) = Σ weight_i / (k + rank_i(chunk)),  k = 60
```

A per-document cap (default 2 chunks) prevents one long document from filling the
page. Ties are broken deterministically by best rank, first-seen position and
chunk id. Every result carries an `explanation` field describing the match.

## AI assistant

1. Retrieval runs first; without evidence the assistant returns the fixed
   "not enough information" answer and no sources.
2. Retrieved chunks are numbered and wrapped in `<document>` delimiters. The
   system prompt states that document text is untrusted data and must never be
   followed as instructions (prompt-injection defence).
3. The provider is resolved from the registry. Ollama is treated as local; an
   OpenAI-compatible endpoint is external and requires the per-request
   `consent_to_external_provider` flag.
4. Every `[n]` citation in the answer is checked against the retrieved sources.
   Invalid citations are removed and reported; an answer with no valid citation
   is marked unverifiable.
5. If the model or provider is unavailable, the API returns the retrieved sources
   in a "search-only" response rather than inventing an answer.

## Configuration

Environment variables are read by `pydantic-settings`. A non-secret subset can be
changed at runtime through `PUT /api/settings`; those values are stored in
`application_settings` and applied in-process. API keys are **not** in that
subset: they are read only from environment variables.

## Design decisions and trade-offs

- **Build from scratch, standard libraries.** No reference project code was
  copied; see `ATTRIBUTIONS.md`.
- **SQLite first.** FTS5 and WAL mode are built in, require no server, and keep
  the privacy story simple. PostgreSQL is not supported for search in this MVP
  because the FTS implementation is SQLite-specific.
- **Rank fusion, not score addition.** RRF behaves predictably when one retriever
  is unavailable or its score scale changes.
- **Explicit model download.** A local app must not download a model as a side
  effect of indexing. Downloading is a separate script and an explicit setting.
- **Persisted jobs.** The thread-based runner is simple and dependency-free, but
  progress survives reloads because state lives in SQLite, not in memory alone.
- **Graceful degradation.** Missing optional dependencies produce warnings and
  fallbacks; the core keyword path always works.

## Known limitations

See [development.md](development.md#known-limitations) for the complete list,
including single-process job execution, in-memory vector scanning, SQLite-only
search and the lack of authentication.
