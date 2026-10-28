# Security policy

## Supported versions

Local Knowledge Engine is a 0.x MVP. Only the latest commit on the default branch
is supported. There are no backported security releases.

| Version | Supported |
|---------|-----------|
| 0.1.x (current) | Yes |
| Older | No |

## Reporting a vulnerability

Please **do not open a public issue** for a security problem.

Use GitHub's private reporting flow: open the repository's **Security** tab and
choose **Report a vulnerability** (GitHub Security Advisories). If that is not
available, contact the maintainer listed in the repository profile and ask for a
private channel before sharing details.

Please include:

- affected version or commit;
- steps to reproduce, with the smallest input that triggers it;
- the impact you believe it has;
- whether the issue requires a malicious document, a local attacker, or network
  access;
- any suggested fix.

Do not include real personal documents, credentials or customer data in the
report. A synthetic reproduction is far more useful.

## What to expect

This is a volunteer MVP. There is no formal SLA and no bug bounty. Reasonable
expectations:

- acknowledgement within about a week;
- an assessment of severity and scope;
- a fix or a documented decision on the public issue tracker once a fix is
  available;
- credit in the release notes if you want it.

## Scope

In scope:

- path traversal or symlink escape through folder imports;
- arbitrary file read/write through uploads or filenames;
- FTS/SQL injection;
- prompt-injection or citation-forgery paths that make the assistant present
  unverified text as sourced fact;
- secret exposure through the API, logs or committed files;
- dependency vulnerabilities with a realistic exploit path;
- any outbound network call that happens without explicit user action.

Out of scope (documented limitations, not vulnerabilities):

- the absence of authentication — the app binds to `127.0.0.1` and is explicitly
  single-user;
- no encryption at rest;
- the AI provider receiving excerpts you consented to send;
- denial of service by importing a very large number of documents on your own
  machine;
- the AGPL obligations of PyMuPDF (see [ATTRIBUTIONS.md](ATTRIBUTIONS.md));
- vulnerabilities in a third-party model or provider service.

## Hardening checklist for users

- Keep `HOST=127.0.0.1`. Do not expose uvicorn directly to a network.
- If you must reach it remotely, put an authenticating reverse proxy with TLS in
  front; the app itself has no login.
- Keep secrets in environment variables, never in `.env` files committed to git.
- Point `ALLOWED_IMPORT_DIRS` at the narrowest folders you actually need.
- Use full-disk encryption if the index may contain sensitive material.
- Review the sources shown by the assistant before trusting an answer.
