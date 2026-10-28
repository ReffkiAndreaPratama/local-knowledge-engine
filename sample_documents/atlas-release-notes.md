# Atlas Release Notes (synthetic)

## 2.4.0 — 2026-03-18

- Added cursor pagination to the document search endpoint.
- Reduced p95 latency for full-text queries by 18% after rebuilding the index.
- Fixed a bug where deleted collections still appeared in the sidebar.
- The audit log now records settings changes, including who changed them.

## 2.3.1 — 2026-02-27

- Fixed an encoding issue with CSV files containing non-ASCII characters.
- Improved the error message shown when an upload exceeds the size limit.
- Backup verification now fails loudly if the checksum does not match.

## 2.3.0 — 2026-02-10

- Introduced saved searches with optional collection filters.
- Added a health endpoint that reports database and worker status.
- Removed the deprecated `/v1/preview` route. Clients should use `/v2/preview`.

## 2.2.0 — 2026-01-14

- Initial support for DOCX and HTML imports.
- Search history can now be disabled by an administrator.
- The importer skips hidden directories and dependency folders by default.
