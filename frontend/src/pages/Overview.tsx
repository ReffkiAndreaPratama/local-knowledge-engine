import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle,
  ArrowRight,
  Database,
  FileText,
  Layers,
  Search,
  Sparkles,
} from 'lucide-react'
import { Card, CardBody, CardHeader, ErrorState, Spinner, StatusDot } from '@/components/ui'
import { documentsApi, jobsApi, statsApi } from '@/lib/api'
import { formatBytes, formatDate } from '@/lib/utils'

function Metric({
  label,
  value,
  hint,
  icon,
  tone = 'default',
}: {
  label: string
  value: string | number
  hint?: string
  icon: React.ReactNode
  tone?: 'default' | 'success' | 'danger' | 'warning'
}) {
  const valueClass =
    tone === 'success'
      ? 'text-success'
      : tone === 'danger'
        ? 'text-danger'
        : tone === 'warning'
          ? 'text-warning'
          : 'text-foreground'

  return (
    <Card>
      <CardBody className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-muted">{label}</p>
          <p className={`mt-1.5 text-2xl font-semibold tracking-tight ${valueClass}`}>{value}</p>
          {hint && <p className="mt-1 text-[11px] text-muted">{hint}</p>}
        </div>
        <span className="rounded-lg bg-elevated p-2 text-muted">{icon}</span>
      </CardBody>
    </Card>
  )
}

export default function Overview() {
  const stats = useQuery({ queryKey: ['stats'], queryFn: statsApi.get, refetchInterval: 15_000 })
  const recent = useQuery({
    queryKey: ['documents', 'recent'],
    queryFn: () => documentsApi.list({ limit: 6 }),
  })
  const jobs = useQuery({ queryKey: ['jobs', 'recent'], queryFn: () => jobsApi.list(5) })

  if (stats.isLoading) return <Spinner label="Loading workspace…" />
  if (stats.isError) {
    return (
      <ErrorState
        message="Could not reach the backend. Make sure it is running on port 8000."
        onRetry={() => stats.refetch()}
      />
    )
  }

  const data = stats.data!

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
          <p className="mt-1 text-sm text-muted">
            Everything is stored locally on this machine. Last index:{' '}
            {formatDate(data.last_indexed_at)}
          </p>
        </div>
        <Link
          to="/search"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          <Search className="h-4 w-4" />
          Start searching
        </Link>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Index metrics">
        <Metric
          label="Documents"
          value={data.document_count}
          hint={`${formatBytes(data.total_source_bytes)} of source files`}
          icon={<FileText className="h-4 w-4" />}
        />
        <Metric
          label="Chunks"
          value={data.chunk_count}
          hint="Searchable passages"
          icon={<Layers className="h-4 w-4" />}
        />
        <Metric
          label="Indexed"
          value={data.indexed_documents}
          hint={`${data.pending_documents} pending`}
          tone="success"
          icon={<Database className="h-4 w-4" />}
        />
        <Metric
          label="Failed"
          value={data.failed_documents}
          hint="Parsing or indexing errors"
          tone={data.failed_documents > 0 ? 'danger' : 'default'}
          icon={<AlertTriangle className="h-4 w-4" />}
        />
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Recently added"
            description="Newest documents in the local index"
            action={
              <Link
                to="/documents"
                className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
              >
                View all <ArrowRight className="h-3 w-3" />
              </Link>
            }
          />
          <CardBody className="p-0">
            {recent.isLoading ? (
              <Spinner />
            ) : !recent.data || recent.data.items.length === 0 ? (
              <div className="px-5 py-10 text-center text-sm text-muted">
                No documents yet. Import files from the Documents page.
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {recent.data.items.map((document) => (
                  <li key={document.id} className="flex items-center gap-3 px-5 py-3">
                    <FileText className="h-4 w-4 shrink-0 text-muted" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{document.filename}</p>
                      <p className="text-[11px] text-muted">
                        {document.chunk_count} chunks · {formatBytes(document.file_size)} ·{' '}
                        {formatDate(document.imported_at)}
                      </p>
                    </div>
                    <span className="flex items-center gap-1.5 text-[11px] text-muted">
                      <StatusDot status={document.indexing_status} />
                      {document.indexing_status}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader title="Search health" />
            <CardBody className="space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-muted">Queries run</span>
                <span className="font-medium">{data.query_count}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted">Average latency</span>
                <span className="font-medium">{data.average_response_time_ms.toFixed(1)} ms</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted">Storage backend</span>
                <span className="font-medium uppercase">{data.storage_backend}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted">Embedding coverage</span>
                <span className="font-medium">{data.embedding_coverage_percent.toFixed(1)}%</span>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Recent jobs" />
            <CardBody className="p-0">
              {jobs.isLoading ? (
                <Spinner />
              ) : !jobs.data || jobs.data.items.length === 0 ? (
                <p className="px-5 py-6 text-center text-xs text-muted">No indexing jobs yet.</p>
              ) : (
                <ul className="divide-y divide-border text-xs">
                  {jobs.data.items.map((job) => (
                    <li key={job.id} className="flex items-center justify-between px-5 py-2.5">
                      <span className="flex items-center gap-2">
                        <StatusDot status={job.status} />
                        <span className="capitalize">{job.job_type}</span>
                      </span>
                      <span className="text-muted">
                        {job.processed_files}/{job.total_files}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardBody className="flex items-start gap-3">
              <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <p className="text-xs text-muted">
                Semantic search and the AI assistant are optional. Search works fully offline
                without any model or API key.
              </p>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}
