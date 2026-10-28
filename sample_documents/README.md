# Sample Documents

These files are **synthetic** test content. "Atlas" is a fictional product; the
people, systems, metrics and policies described here do not exist. The corpus is
safe to import into Local Knowledge Engine and is used by the end-to-end test and
the retrieval benchmark.

| File | Format | Exercises |
|------|--------|-----------|
| `atlas-handbook.md` | Markdown | headings, deployment and backup details |
| `atlas-onboarding.txt` | plain text | setext headings, onboarding checklist |
| `atlas-security.md` | Markdown | access control, encryption |
| `atlas-release-notes.md` | Markdown | release history |
| `atlas-faq.md` | Markdown | question-style headings |
| `atlas-service-metrics.csv` | CSV | tabular numeric data |
| `atlas-database-runbook.html` | HTML | HTML-to-text extraction |

## Try these searches

- `Which port does the Atlas API use?` → 8080 (`atlas-handbook.md`)
- `How often are database backups taken?` → nightly at 02:00 UTC
- `Project Halyard` → onboarding guide
- `How long do tokens last?` → 60 minutes (`atlas-security.md`)
- `Who approves production deployments?` → service owner and on-call engineer
- `failover` → database runbook

## Import them

Upload the files from the Documents page, or import the folder after adding its
absolute path to **Settings → Allowed import directories**:

```bash
curl -X POST http://127.0.0.1:8000/api/documents/import-folder \
  -H "Content-Type: application/json" \
  -d '{"directory": "/absolute/path/to/sample_documents", "recursive": true}'
```

On Windows, use the full path with escaped backslashes or forward slashes.
