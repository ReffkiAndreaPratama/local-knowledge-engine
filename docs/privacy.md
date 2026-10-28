# Privacy and security

Local Knowledge Engine is designed for a single person running it on their own
machine. This document states exactly what the software does with your data, what
it never does, and where the remaining risks are.

## Data stays local by default

Everything below lives on the machine that runs the backend:

| Data | Location |
|------|----------|
| Document metadata, chunks, FTS index, embeddings, jobs, settings | `backend/data/knowledge.db` (SQLite) |
| Managed copies of imported files | `backend/data/documents/` |
| Hugging Face embedding model (optional) | Hugging Face cache (`~/.cache/huggingface` by default) |
| Frontend assets | Built into `frontend/dist/` and served locally |

The backend binds to `127.0.0.1` by default. There is no telemetry, analytics SDK,
crash reporter, font CDN, remote script or remote stylesheet in the frontend. The
only outbound network calls the application can make are:

1. **Hugging Face** — only when you explicitly run
   `scripts/download_embedding_model.py` (or the benchmark with
   `--download-model`). Never during import, indexing or search.
2. **Your chosen AI provider** — Ollama on `localhost` by default, or an
   OpenAI-compatible endpoint that you configure and consent to per request.

Search history can be disabled in Settings or cleared at any time.

## Threat model

The realistic threats for a local app are:

- malicious or accidental content in indexed documents (prompt injection,
  huge files, malformed files);
- path traversal or symlink tricks when reading folders;
- leaking secrets through the API or the database;
- a local network attacker reaching an over-permissive backend.

Account takeover, multi-tenant isolation and internet-facing deployment are out of
scope. This is a single-user app, not a hosted service.

## File handling

- **Extension allowlist.** Only configured extensions are accepted. The check is
  case-insensitive and applies to uploads and folder scans.
- **Size limit.** `MAX_FILE_SIZE_MB` (default 100) is enforced before parsing.
- **Filename sanitisation.** Uploaded names are reduced to a basename, unsafe
  characters are replaced and the result is capped at 200 characters. Files are
  stored under a random UUID with a safe extension in `data/documents/`.
- **Allowed import directories.** Folder imports must resolve inside one of
  `ALLOWED_IMPORT_DIRS` (default: the current user's home directory). Symlinks are
  resolved with `realpath` before the comparison, so a link pointing outside the
  allowed roots is rejected.
- **No execution.** Documents are parsed as data. Macros, scripts, embedded
  objects and external references are never executed. HTML is converted to text;
  scripts and styles are discarded.
- **Failure isolation.** A parser error marks that one file `failed` with a
  message. The rest of the batch continues and the original file is preserved.

## Database safety

- All queries use SQLAlchemy parameters or bound parameters. The FTS query itself
  is built by quoting every user term, so FTS5 operators (`AND`, `OR`, `NEAR`, `*`,
  `"`, parentheses) cannot change the query structure.
- The FTS table and application tables are local to the SQLite file. SQLite runs
  with `foreign_keys=ON`, WAL journaling and a 15-second busy timeout.
- Deleting a document removes its chunks, FTS rows and embeddings in the same
  transaction so no orphaned text is searchable.
- Model names and vector dimensions are stored with every embedding. Vectors from
  a different model are ignored rather than compared, which prevents nonsense
  results after a model change.

## Secrets

- API keys (`OPENAI_API_KEY`, etc.) are read from environment variables only.
- They are not accepted by `PUT /api/settings`, not stored in SQLite and not
  returned by `GET /api/settings`.
- `SECRET_KEY` has an insecure development default. It is not currently used for
  signing anything in this MVP, but you should still set a random value before any
  shared deployment.
- `.env`, `*.db`, model files and virtual environments are excluded by
  `.gitignore`.

## AI assistant safeguards

Document text is **untrusted data**, not instructions.

1. The system prompt tells the model to answer only from the numbered sources,
   cite every factual statement, and never follow instructions found inside
   documents.
2. Retrieved chunks are wrapped in `<document>` delimiters with explicit
   "untrusted data" framing so the boundary is unambiguous to the model.
3. Answers are post-processed: every `[n]` citation must match a retrieved source.
   Unknown citations are removed and reported in `invalid_citations`.
4. If there is no relevant evidence, the assistant returns a fixed "not enough
   information" answer with no sources. It does not call the model to improvise.
5. If the model is unavailable, the response degrades to search-only results with
   a warning. It never fabricates an answer.
6. External providers require an explicit `consent_to_external_provider: true` on
   each request when `REQUIRE_AI_CONSENT` is enabled (the default). The UI does
   not set it unless you tick the consent checkbox.

Prompt injection is mitigated, not eliminated. A sufficiently adversarial document
can still influence a small model's output. That is why citations are validated and
every answer links back to the source text for human verification.

## What is deliberately not collected

- No usage analytics, crash reports, device fingerprints or install IDs.
- No remote logging.
- No automatic update checks.
- No telemetry endpoint exists in the codebase.

## Residual risks and limitations

- **No authentication.** Anyone who can reach the port can read and modify the
  index. Keep it bound to `127.0.0.1`. If you must expose it, put an authenticating
  reverse proxy in front and use TLS.
- **No encryption at rest.** SQLite, managed copies and embeddings are plain files.
  Use OS full-disk encryption (BitLocker, FileVault, LUKS) if that matters.
- **The AI provider sees the retrieved excerpts.** Using a local Ollama model keeps
  that on-device. An external provider receives the numbered excerpts you consented
  to send. Do not enable an external provider for material you cannot share.
- **Indexed content may contain secrets.** Importing a folder that holds credentials
  makes them searchable on your machine. Curate your allowed import directories.
- **Backups are your responsibility.** There is no built-in backup or export.
- **No audit log.** Settings changes and searches are not attributed to a user,
  because there is only one user.

## Reporting a vulnerability

See [SECURITY.md](../SECURITY.md). Please do not open a public issue for a
security problem. Report it privately so it can be assessed before disclosure.
