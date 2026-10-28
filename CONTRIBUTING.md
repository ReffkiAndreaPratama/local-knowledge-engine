# Contributing

Thanks for taking a look. Local Knowledge Engine is a small MVP; focused bug fixes
and tests are more useful than large rewrites.

## Before you start

- Open an issue for anything larger than a typo or a one-file fix.
- For security problems, follow [SECURITY.md](SECURITY.md) instead of opening a
  public issue.
- By contributing you agree that your contribution is licensed under the project's
  [MIT License](LICENSE).

## Development setup

See [docs/development.md](docs/development.md). The short version:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cd ../frontend
npm install
```

Semantic search is optional; do not make it a hard requirement for the core
backend or for the test suite.

## What a good change looks like

- **Tests come with behaviour.** Backend changes need a pytest case; UI changes
  need a Vitest case; user-visible flows belong in the Playwright spec.
- **No fake implementations.** Do not stub an endpoint, hard-code a benchmark
  number, or add a feature that only looks like it works.
- **Degrade visibly.** If an optional component is missing, return a `notes` or
  `warning` message. Never return an empty result that looks successful.
- **Keep the privacy story intact.** No telemetry, remote fonts, CDNs, auto-update
  pings or silent model downloads.
- **Respect the layering.** Routers stay thin; logic lives in `app/services/`;
  SQL stays in `app/search/`. The frontend imports UI primitives from
  `@/components/ui`.
- **Match the surrounding style.** No reformatting of untouched files.

## Checks to run

All of these must pass before a pull request is reviewable:

```bash
# Backend
cd backend
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --no-cov
.venv/Scripts/python.exe -m ruff check app tests

# Frontend
cd frontend
npm test
npm run build
node node_modules/@playwright/test/cli.js test --reporter=list
```

On PowerShell, use `npm.cmd` or the `node node_modules/...` form if `npm.ps1` is
blocked by the execution policy.

If your change affects retrieval, also run:

```bash
cd backend
.venv/Scripts/python.exe ../scripts/benchmark.py
```

and mention whether the metrics moved.

## Commit messages

Short imperative subject, blank line, then why. Example:

```
Fix documents list not refreshing after background import

The list query had no refetch interval, so a completed job left the
table stale until the user navigated away.
```

## Pull requests

- Keep the diff focused. Separate refactors from behaviour changes.
- Describe what you tested and how, with the actual command output if relevant.
- Note any new dependency and its licence (update
  [ATTRIBUTIONS.md](ATTRIBUTIONS.md)).
- Note any migration or data-compatibility impact.

## What is out of scope for this MVP

Please discuss before working on: authentication, multi-user tenancy, PostgreSQL
search, a distributed job queue, a vector database, OCR, a Docker image, or
telemetry of any kind.
