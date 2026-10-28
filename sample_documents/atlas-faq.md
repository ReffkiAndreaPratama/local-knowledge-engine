# Atlas Frequently Asked Questions

## Which port does the API use?

The API uses port 8080 by default. Override it with `ATLAS_API_PORT`.

## How long are audit logs kept?

Audit logs are retained for 400 days. Security incidents may require a legal hold
that extends retention until the matter is closed.

## Can I index a folder outside my home directory?

No. The importer only reads directories explicitly listed as allowed import
directories. Add the directory in Settings first, then restart the import.

## What happens if a file cannot be parsed?

The file is marked as failed with a readable error, and the rest of the batch
continues. Fix the file or remove it, then re-index the document. A failure never
deletes the original file.

## Is my data sent to the cloud?

Full-text search and local AI providers keep data on the machine. An external AI
provider is only used after explicit consent, and the application never sends
document text in the background.

## How do I reset the search history?

Open Settings and choose "Clear search history". The action removes stored
queries and result counts but does not touch documents or embeddings.
