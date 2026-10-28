import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ListChecks, XCircle } from 'lucide-react'
import {
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  ErrorState,
  Spinner,
  StatusDot,
  statusTone,
} from '@/components/ui'
import { extractErrorMessage, jobsApi } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { useToast } from '@/lib/toast'

export default function Jobs() {
  const queryClient = useQueryClient()
  const { notify } = useToast()

  const jobs = useQuery({
    queryKey: ['jobs', 'page'],
    queryFn: () => jobsApi.list(50),
    refetchInterval: 3_000,
  })

  const cancel = useMutation({
    mutationFn: (id: string) => jobsApi.cancel(id),
    onSuccess: () => {
      notify('Cancellation requested.', 'info')
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
    onError: (error) => notify(extractErrorMessage(error), 'error'),
  })

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Indexing Jobs</h1>
        <p className="mt-1 text-sm text-muted">
          Jobs run in the background. Progress is stored locally so it survives a page reload.
        </p>
      </header>

      <Card>
        {jobs.isLoading ? (
          <Spinner label="Loading jobs…" />
        ) : jobs.isError ? (
          <ErrorState message={extractErrorMessage(jobs.error)} onRetry={() => jobs.refetch()} />
        ) : !jobs.data || jobs.data.items.length === 0 ? (
          <EmptyState
            icon={<ListChecks className="h-8 w-8" />}
            title="No indexing jobs"
            description="Import documents to create an indexing job."
          />
        ) : (
          <ul className="divide-y divide-border">
            {jobs.data.items.map((job) => {
              const percent =
                job.total_files > 0
                  ? Math.min(100, Math.round((job.processed_files / job.total_files) * 100))
                  : 0
              const active = job.status === 'running' || job.status === 'pending'
              return (
                <li key={job.id} className="px-5 py-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusDot status={job.status} />
                    <span className="text-sm font-medium capitalize">{job.job_type}</span>
                    <Badge tone={statusTone(job.status)}>{job.status}</Badge>
                    <span className="text-[11px] text-muted">
                      {job.processed_files}/{job.total_files} processed
                      {job.failed_files > 0 ? ` · ${job.failed_files} failed` : ''}
                    </span>
                    <span className="ml-auto text-[11px] text-muted">
                      {formatDate(job.created_at)}
                    </span>
                    {active && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => cancel.mutate(job.id)}
                        loading={cancel.isPending}
                      >
                        <XCircle className="h-3.5 w-3.5" /> Cancel
                      </Button>
                    )}
                  </div>

                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-elevated">
                    <div
                      className={`h-full rounded-full transition-all ${
                        job.status === 'failed' ? 'bg-danger' : 'bg-primary'
                      }`}
                      style={{ width: `${percent}%` }}
                      role="progressbar"
                      aria-valuenow={percent}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`Indexing progress for ${job.job_type} job`}
                    />
                  </div>

                  {job.current_file && (
                    <p className="mt-1.5 truncate text-[11px] text-muted">
                      Current: {job.current_file}
                    </p>
                  )}
                  {job.error_message && (
                    <p className="mt-1.5 text-[11px] text-danger">{job.error_message}</p>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </Card>

      <Card>
        <CardBody className="text-[11px] text-muted">
          A failed file never stops the rest of a batch. Failed documents keep their error message
          and can be re-indexed individually from the Documents page.
        </CardBody>
      </Card>
    </div>
  )
}
