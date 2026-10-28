# Atlas Platform Handbook

> Synthetic sample content. Atlas is a fictional product created for testing
> Local Knowledge Engine. Nothing here describes a real company or system.

## Deployment

The Atlas API listens on port **8080** by default. Change the bind port with the
`ATLAS_API_PORT` environment variable. Health checks are served at
`GET /healthz` on the same port.

Production deployments require two approvals: one from the service owner and
one from the on-call engineer. Deploy windows are Monday through Thursday,
09:00–16:00 UTC. Friday deployments need an incident commander's approval.

## Backups

The primary PostgreSQL database is backed up nightly at **02:00 UTC**. Backups
are encrypted with the platform key, copied to a second region, and retained for
35 days. A restore drill runs on the first Tuesday of every month and is
recorded in the operations log.

## On-call

The on-call rotation changes every Monday at 10:00 UTC. The primary responder
acknowledges pages within five minutes. If the primary does not acknowledge in
five minutes, the secondary is paged automatically. Handovers must include open
incidents, recent deploys, and any silenced alerts.

## Service levels

The availability target for the public API is 99.9% measured monthly. The
latency target is a p95 under 300 ms for read requests at 500 requests per
second. Error budgets are reviewed in the monthly reliability meeting.
