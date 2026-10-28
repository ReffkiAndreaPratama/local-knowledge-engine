# Attributions and licence review

Local Knowledge Engine is released under the [MIT License](../LICENSE).

It was **written from scratch** for this project. No source code, templates, UI
assets or prompt text were copied from the reference projects below. They were
studied for product and architectural ideas (local-first search, hybrid retrieval,
citation display) and are credited here.

Licences were checked on **2026-10-27** against the installed package metadata and
each project's public repository. Versions are the ones actually used by the
development environment, not the minimums in `requirements.txt`.

## Reference projects (inspiration only, no code used)

| Project | Licence | What was learned |
|---------|---------|------------------|
| [Soma](https://github.com/AwesomeDog/soma) | MIT | Local-first hybrid search UX, single-binary deployment goal |
| [QMD](https://github.com/tobi/qmd) | MIT | BM25 + vector fusion with RRF, CLI-first knowledge search |
| [Open WebUI](https://github.com/open-webui/open-webui) | Custom BSD-3-style licence with a branding clause (see note) | Knowledge-base and source-citation UX patterns |
| [SeekX](https://github.com/oceanbase/seekx) | MIT | Hybrid search and realtime-index architecture discussion |
| [GNO](https://github.com/gmickel/gno) | MIT | Local document workspace and MCP-oriented design ideas |

**Open WebUI note:** its licence is *not* plain BSD-3-Clause. It adds a clause
prohibiting removal or alteration of "Open WebUI" branding in most deployments.
This project does not include, link to, fork or redistribute Open WebUI code, so
the clause does not apply. It is listed only to be explicit about what was
reviewed. If you ever copy code or assets from it, read that licence first.

## Runtime dependencies

### Backend (Python)

| Package | Version used | Licence |
|---------|--------------|---------|
| FastAPI | 0.162.0 | MIT |
| Uvicorn | 0.54.0 | BSD-3-Clause |
| Pydantic / pydantic-settings | 2.14.1 / 2.16.1 | MIT |
| SQLAlchemy | 2.1.6 | MIT |
| **PyMuPDF** | **2.0** | **AGPL-3.0 or Artifex commercial — see below** |
| python-docx | 1.2.0 | MIT |
| openpyxl | 3.1.5 | MIT |
| BeautifulSoup4 | 4.15.0 | MIT |
| lxml | 6.1.3 | BSD-3-Clause |
| NumPy | 2.5.4 | BSD-3-Clause (with 0BSD/MIT/Zlib/CC0 components) |
| HTTPX | 0.28.1 | BSD-3-Clause |
| python-multipart | 0.0.32 | Apache-2.0 |
| `sentence-transformers` (optional) | 6.2.0 | Apache-2.0 |
| PyTorch (optional, CPU) | 2.14.1+cpu | BSD-3-Clause |

### Frontend (npm)

| Package | Version used | Licence |
|---------|--------------|---------|
| React / React DOM | 18.3.1 | MIT |
| React Router DOM | 6.30.6 | MIT |
| TanStack Query | 5.105.0 | MIT |
| Axios | 1.21.0 | MIT |
| Tailwind CSS | 3.4.19 | MIT |
| class-variance-authority | 0.7.1 | Apache-2.0 |
| clsx | 2.1.1 | MIT |
| tailwind-merge | 2.6.1 | MIT |
| lucide-react | 0.454.0 | ISC |
| Vite | 5.4.21 | MIT |
| TypeScript | 5.9.3 | Apache-2.0 |
| Vitest | 2.1.9 | MIT |
| Playwright | 1.64.1 | Apache-2.0 |

Transitive dependencies keep their own licences; run `pip-licenses` or
`npx license-checker` for a complete inventory before distributing a binary.

### Model

`sentence-transformers/all-MiniLM-L6-v2` is licensed **Apache-2.0** (verified on
its Hugging Face model card). It is not bundled; the user downloads it explicitly
with `scripts/download_embedding_model.py`.

## Important licence caveat: PyMuPDF is AGPL-3.0

PyMuPDF is dual-licensed: **GNU AGPL-3.0** or a paid Artifex commercial licence.

This matters if you distribute the application:

- Running it locally, for yourself, is generally fine under AGPL terms.
- **Distributing binaries or a hosted service that includes PyMuPDF requires
  compliance with the AGPL**, which for a network service includes offering the
  corresponding source code to users.
- The MIT licence of this project does **not** override PyMuPDF's licence. The
  combined distribution is effectively AGPL-constrained unless you obtain a
  commercial PyMuPDF licence.

Options if you need a permissive distribution:

1. Buy a commercial PyMuPDF licence.
2. Replace the PDF parser with a permissive alternative (`pypdf` is BSD-3-Clause;
   `pdfplumber`/`pdfminer.six` are MIT). Text extraction quality on complex PDFs
   will differ.
3. Keep PyMuPDF as an optional extra and ship the core without it.

This project does not hide the issue: the backend README and this file state it
plainly.

## Sample corpus

Everything in [`sample_documents/`](../sample_documents/) was written for this
project. "Atlas" is a fictional product. The documents contain no real people,
companies, credentials, customer data or third-party text.

## Fonts and visual assets

The UI uses the operating system's default sans-serif stack and system emoji.
There are no bundled web fonts, icon packs or stock images. Icons come from
Lucide (ISC) as React components.

## Trademarks

"Local Knowledge Engine" is a descriptive project name. All other product names
mentioned in the documentation belong to their respective owners and are used
only for identification.
