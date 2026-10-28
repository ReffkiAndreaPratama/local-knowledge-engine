# Atlas Security Handbook

> Synthetic sample content for Local Knowledge Engine testing.

## Access control

Production access uses short-lived tokens issued by the identity provider.
Tokens expire after **60 minutes** and must never be written to disk, committed
to a repository, or pasted into chat. Use the secrets manager for service
credentials. Human accounts require a second factor; shared accounts are
prohibited.

## Encryption

Data is encrypted in transit with TLS 1.2 or newer. Databases and object storage
use AES-256 encryption at rest. Encryption keys are rotated every 90 days by the
security team. Application teams must not export encryption keys.

## Incident response

Report a suspected security incident in #atlas-incidents and page the security
on-call immediately. Do not investigate alone and do not delete logs. The
security team opens a written incident record within one hour and decides
whether notification obligations apply.

## Dependency policy

Dependencies must be pinned to a specific version, scanned for known
vulnerabilities before release, and reviewed when a new direct dependency is
added. Licences must be compatible with the project's distribution model.
