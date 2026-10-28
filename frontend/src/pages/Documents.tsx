import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  FileText,
  FolderOpen,
  RefreshCw,
  Search,
  Trash2,
  Upload,
} from 'lucide-react'
import {
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  ErrorState,
  Input,
  Modal,
  Select,
  Spinner,
  statusTone,
} from '@/components/ui'
import { documentsApi, extractErrorMessage } from '@/lib/api'
import { formatBytes, formatDate } from '@/lib/utils'
import { useToast } from '@/lib/toast'
import type { DocumentRecord } from '@/types'

export default function Documents() {
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const fileInput = useRef<HTMLInputElement>(null)

  const [filename, setFilename] = useState('')
  const [extension, setExtension] = useState('')
  const [status, setStatus] = useState('')
  const [detail, setDetail] = useState<DocumentRecord | null>(null)
  const [pendingDelete, setPendingDelete] = useState<DocumentRecord | null>(null)
  const [folderPath, setFolderPath] = useState('')
  const [folderOpen, setFolderOpen] = useState(false)
  const [polling, setPolling] = useState(false)
  const pollTimer = useRef<number | null>(null)

  // Indexing happens in a background job, so keep refetching for a while after
  // an import or re-index instead of showing a stale (often empty) list.
  const pollWhileIndexing = () => {
    setPolling(true)
    if (pollTimer.current !== null) window.clearTimeout(pollTimer.current)
    pollTimer.current = window.setTimeout(() => setPolling(false), 30_000)
  }

  useEffect(
    () => () => {
      if (pollTimer.current !== null) window.clearTimeout(pollTimer.current)
    },
    [],
  )

  const documents = useQuery({
    queryKey: ['documents', { filename, extension, status }],
    queryFn: () =>
      documentsApi.list({
        filename: filename || undefined,
        extension: extension || undefined,
        status: status || undefined,
        limit: 200,
      }),
    refetchInterval: polling ? 1_500 : false,
  })

  const chunks = useQuery({
    queryKey: ['chunks', detail?.id],
    queryFn: () => documentsApi.chunks(detail!.id, 100),
    enabled: Boolean(detail),
  })

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ['documents'] })
    queryClient.invalidateQueries({ queryKey: ['stats'] })
    queryClient.invalidateQueries({ queryKey: ['jobs'] })
  }

  const upload = useMutation({
    mutationFn: (files: File[]) => documentsApi.upload(files),
    onSuccess: (result) => {
      const rejected = result.rejected.length
      notify(
        `${result.queued_count} file(s) queued${rejected ? `, ${rejected} rejected` : ''}.`,
        rejected && !result.queued_count ? 'error' : 'success',
      )
      if (result.rejected.length) {
        result.rejected.forEach((item) => notify(`${item.filename}: ${item.reason}`, 'error'))
      }
      pollWhileIndexing()
      refreshAll()
    },
    onError: (error) => notify(extractErrorMessage(error), 'error'),
  })

  const importFolder = useMutation({
    mutationFn: () => documentsApi.importFolder(folderPath.trim(), true),
    onSuccess: (result) => {
      notify(`${result.queued_count} file(s) queued from ${result.directory}`, 'success')
      setFolderOpen(false)
      pollWhileIndexing()
      refreshAll()
    },
    onError: (error) => notify(extractErrorMessage(error), 'error'),
  })

  const reindex = useMutation({
    mutationFn: (id: string) => documentsApi.reindex(id),
    onSuccess: () => {
      notify('Re-indexing queued.', 'success')
      pollWhileIndexing()
      refreshAll()
    },
    onError: (error) => notify(extractErrorMessage(error), 'error'),
  })

  const remove = useMutation({
    mutationFn: (id: string) => documentsApi.remove(id),
    onSuccess: () => {
      notify('Document removed from the index.', 'success')
      setPendingDelete(null)
      setDetail(null)
      refreshAll()
    },
    onError: (error) => notify(extractErrorMessage(error), 'error'),
  })

  const scanChanges = useMutation({
    mutationFn: documentsApi.scanChanges,
    onSuccess: (result) => {
      notify(
        `Scan complete: ${result.changed.length} changed, ${result.missing.length} missing, ${result.unchanged} unchanged.`,
        'info',
      )
      refreshAll()
    },
    onError: (error) => notify(extractErrorMessage(error), 'error'),
  })

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Documents</h1>
          <p className="mt-1 text-sm text-muted">
            Import files or a whole folder. Unchanged files are skipped using their SHA-256 hash.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() => scanChanges.mutate()}
            loading={scanChanges.isPending}
          >
            <RefreshCw className="h-4 w-4" />
            Scan for changes
          </Button>
          <Button variant="secondary" onClick={() => setFolderOpen(true)}>
            <FolderOpen className="h-4 w-4" />
            Import folder
          </Button>
          <Button onClick={() => fileInput.current?.click()} loading={upload.isPending}>
            <Upload className="h-4 w-4" />
            Import files
          </Button>
          <input
            ref={fileInput}
            type="file"
            multiple
            hidden
            aria-label="Choose files to import"
            onChange={(event) => {
              const files = Array.from(event.target.files ?? [])
              if (files.length) upload.mutate(files)
              event.target.value = ''
            }}
          />
        </div>
      </header>

      <Card>
        <CardBody className="flex flex-wrap items-end gap-3">
          <div className="min-w-[200px] flex-1">
            <label htmlFor="filter-name" className="mb-1.5 block text-xs font-medium text-muted">
              File name
            </label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
              <Input
                id="filter-name"
                value={filename}
                onChange={(event) => setFilename(event.target.value)}
                placeholder="Filter by name…"
                className="pl-8"
              />
            </div>
          </div>
          <div>
            <label htmlFor="filter-ext" className="mb-1.5 block text-xs font-medium text-muted">
              Type
            </label>
            <Select
              id="filter-ext"
              value={extension}
              onChange={(event) => setExtension(event.target.value)}
            >
              <option value="">All</option>
              {['.pdf', '.md', '.txt', '.docx', '.csv', '.json', '.html', '.py', '.ts'].map(
                (ext) => (
                  <option key={ext} value={ext}>
                    {ext}
                  </option>
                ),
              )}
            </Select>
          </div>
          <div>
            <label htmlFor="filter-status" className="mb-1.5 block text-xs font-medium text-muted">
              Status
            </label>
            <Select
              id="filter-status"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
            >
              <option value="">All</option>
              <option value="completed">Completed</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
            </Select>
          </div>
          <Button
            variant="ghost"
            onClick={() => {
              setFilename('')
              setExtension('')
              setStatus('')
            }}
          >
            Reset filters
          </Button>
        </CardBody>
      </Card>

      <Card>
        {documents.isLoading ? (
          <Spinner label="Loading documents…" />
        ) : documents.isError ? (
          <ErrorState
            message={extractErrorMessage(documents.error)}
            onRetry={() => documents.refetch()}
          />
        ) : !documents.data || documents.data.items.length === 0 ? (
          <EmptyState
            icon={<FileText className="h-8 w-8" />}
            title="No documents match"
            description="Import PDF, Markdown, TXT, DOCX, CSV, JSON, HTML or source code files to start building your local knowledge base."
            action={
              <Button size="sm" onClick={() => fileInput.current?.click()}>
                <Upload className="h-4 w-4" /> Import files
              </Button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border text-[11px] uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-5 py-3 font-medium">Document</th>
                  <th className="px-3 py-3 font-medium">Type</th>
                  <th className="px-3 py-3 font-medium">Size</th>
                  <th className="px-3 py-3 font-medium">Chunks</th>
                  <th className="px-3 py-3 font-medium">Status</th>
                  <th className="px-3 py-3 font-medium">Imported</th>
                  <th className="px-5 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {documents.data.items.map((document) => (
                  <tr key={document.id} className="hover:bg-elevated/60">
                    <td className="max-w-[280px] px-5 py-3">
                      <button
                        type="button"
                        onClick={() => setDetail(document)}
                        className="block truncate text-left font-medium hover:text-primary"
                      >
                        {document.filename}
                      </button>
                      {document.parsing_error && (
                        <span className="mt-0.5 flex items-center gap-1 text-[11px] text-danger">
                          <AlertTriangle className="h-3 w-3" /> {document.parsing_error.slice(0, 80)}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-xs text-muted">{document.extension || '—'}</td>
                    <td className="px-3 py-3 text-xs text-muted">{formatBytes(document.file_size)}</td>
                    <td className="px-3 py-3 text-xs text-muted">{document.chunk_count}</td>
                    <td className="px-3 py-3">
                      <Badge tone={statusTone(document.indexing_status)}>
                        {document.indexing_status}
                      </Badge>
                    </td>
                    <td className="px-3 py-3 text-xs text-muted">{formatDate(document.imported_at)}</td>
                    <td className="px-5 py-3">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Re-index ${document.filename}`}
                          onClick={() => reindex.mutate(document.id)}
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Delete ${document.filename}`}
                          onClick={() => setPendingDelete(document)}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-danger" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal
        open={Boolean(detail)}
        title={detail?.filename ?? 'Document'}
        onClose={() => setDetail(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDetail(null)}>
              Close
            </Button>
            {detail && (
              <Button onClick={() => reindex.mutate(detail.id)} loading={reindex.isPending}>
                <RefreshCw className="h-4 w-4" /> Re-index
              </Button>
            )}
          </>
        }
      >
        {detail && (
          <div className="space-y-3">
            <dl className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <dt className="text-muted">Status</dt>
                <dd className="font-medium">{detail.indexing_status}</dd>
              </div>
              <div>
                <dt className="text-muted">Type</dt>
                <dd className="font-medium">{detail.extension}</dd>
              </div>
              <div>
                <dt className="text-muted">Size</dt>
                <dd className="font-medium">{formatBytes(detail.file_size)}</dd>
              </div>
              <div>
                <dt className="text-muted">Chunks</dt>
                <dd className="font-medium">{detail.chunk_count}</dd>
              </div>
              <div>
                <dt className="text-muted">Characters</dt>
                <dd className="font-medium">{detail.char_count ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-muted">Pages</dt>
                <dd className="font-medium">{detail.page_count ?? '—'}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-muted">Source path</dt>
                <dd className="break-all font-mono text-[11px]">{detail.original_path}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-muted">SHA-256</dt>
                <dd className="break-all font-mono text-[11px]">{detail.file_hash}</dd>
              </div>
              {detail.parsing_error && (
                <div className="col-span-2">
                  <dt className="text-muted">Error</dt>
                  <dd className="text-danger">{detail.parsing_error}</dd>
                </div>
              )}
            </dl>

            <div>
              <p className="mb-1 text-xs font-medium text-muted">First chunks</p>
              {chunks.isLoading ? (
                <Spinner />
              ) : (
                <ul className="max-h-56 space-y-2 overflow-auto rounded-lg border border-border bg-background p-2 text-[11px]">
                  {(chunks.data?.items ?? []).slice(0, 8).map((chunk) => (
                    <li key={chunk.id} className="border-b border-border/60 pb-1.5 last:border-0">
                      <p className="line-clamp-3 whitespace-pre-wrap">{chunk.content}</p>
                      <p className="mt-1 text-[10px] text-muted">
                        #{chunk.chunk_index}
                        {chunk.page_number ? ` · page ${chunk.page_number}` : ''}
                        {chunk.heading ? ` · ${chunk.heading}` : ''}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </Modal>

      <Modal
        open={folderOpen}
        title="Import a folder"
        onClose={() => setFolderOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setFolderOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => importFolder.mutate()}
              loading={importFolder.isPending}
              disabled={!folderPath.trim()}
            >
              Import
            </Button>
          </>
        }
      >
        <div className="space-y-2">
          <label htmlFor="folder-path" className="text-xs font-medium text-muted">
            Directory path
          </label>
          <Input
            id="folder-path"
            value={folderPath}
            onChange={(event) => setFolderPath(event.target.value)}
            placeholder="C:\\Users\\you\\Documents"
          />
          <p className="text-[11px] text-muted">
            Only directories listed in Settings → Allowed import directories can be indexed.
            Hidden folders and dependency directories are skipped.
          </p>
        </div>
      </Modal>

      <Modal
        open={Boolean(pendingDelete)}
        title="Remove document"
        onClose={() => setPendingDelete(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setPendingDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => pendingDelete && remove.mutate(pendingDelete.id)}
              loading={remove.isPending}
            >
              Delete permanently
            </Button>
          </>
        }
      >
        <p className="text-sm">
          <strong>{pendingDelete?.filename}</strong> will be removed from the index, including all
          chunks and embeddings. This cannot be undone.
        </p>
      </Modal>
    </div>
  )
}
