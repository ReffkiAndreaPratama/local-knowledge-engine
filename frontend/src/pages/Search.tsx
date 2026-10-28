import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  FileText,
  Filter,
  Info,
  Loader2,
  Search as SearchIcon,
  Sparkles,
  X,
} from 'lucide-react'
import { Badge, Button, Card, EmptyState, ErrorState, Select } from '@/components/ui'
import { extractErrorMessage, searchApi } from '@/lib/api'
import { formatDuration, splitHighlighted } from '@/lib/utils'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import type { SearchMode, SearchResult } from '@/types'

const MODES: { id: SearchMode; label: string; hint: string }[] = [
  { id: 'fulltext', label: 'Full-text', hint: 'Exact keyword matching (SQLite FTS5)' },
  { id: 'hybrid', label: 'Hybrid', hint: 'Keyword + semantic, fused with RRF' },
  { id: 'semantic', label: 'Semantic', hint: 'Meaning-based retrieval (needs embeddings)' },
]

function HighlightedText({ text, highlights }: { text: string; highlights: string[] }) {
  const parts = useMemo(() => splitHighlighted(text, highlights), [text, highlights])
  return (
    <>
      {parts.map((part, index) =>
        part.match ? <mark key={index}>{part.text}</mark> : <span key={index}>{part.text}</span>,
      )}
    </>
  )
}

function SourcePreview({ result, onClose }: { result: SearchResult; onClose: () => void }) {
  return (
    <aside
      aria-label="Source preview"
      className="animate-fade-in rounded-xl border border-border bg-surface shadow-panel lg:sticky lg:top-4"
    >
      <div className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{result.document_name}</p>
          <p className="mt-0.5 text-[11px] text-muted">
            {result.page_number ? `Page ${result.page_number} · ` : ''}
            {result.heading ? `Section: ${result.heading} · ` : ''}
            {result.extension}
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close preview">
          <X className="h-4 w-4" />
        </Button>
      </div>
      <div className="max-h-[60vh] overflow-auto px-4 py-3">
        <p className="whitespace-pre-wrap text-xs leading-relaxed text-foreground">
          <HighlightedText text={result.content} highlights={result.highlights} />
        </p>
      </div>
      <div className="border-t border-border px-4 py-3 text-[11px] text-muted">
        <p className="flex items-start gap-1.5">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {result.explanation || 'Match found in this passage.'}
        </p>
        {result.score !== null && (
          <p className="mt-1">
            Score: <span className="font-mono">{result.score.toFixed(4)}</span>
          </p>
        )}
        <p className="mt-1 break-all font-mono text-[10px]">chunk: {result.chunk_id}</p>
      </div>
    </aside>
  )
}

export default function SearchPage() {
  const [params, setParams] = useSearchParams()
  const initialQuery = params.get('q') ?? ''
  const [input, setInput] = useState(initialQuery)
  const [mode, setMode] = useState<SearchMode>('fulltext')
  const [extension, setExtension] = useState('')
  const [submitted, setSubmitted] = useState(initialQuery)
  const [selected, setSelected] = useState<SearchResult | null>(null)

  const debouncedInput = useDebouncedValue(input, 400)

  useEffect(() => {
    const next = params.get('q') ?? ''
    if (next !== input) {
      setInput(next)
      setSubmitted(next)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params])

  // Live search as the user types, without losing the explicit submit path.
  useEffect(() => {
    if (debouncedInput.trim() && debouncedInput !== submitted) {
      setSubmitted(debouncedInput.trim())
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedInput])

  const search = useQuery({
    queryKey: ['search', submitted, mode, extension],
    queryFn: () =>
      searchApi.search({
        query: submitted,
        mode,
        limit: 20,
        filters: extension ? { extensions: [extension] } : undefined,
      }),
    enabled: submitted.trim().length > 0,
    staleTime: 30_000,
  })

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const trimmed = input.trim()
    setSubmitted(trimmed)
    setSelected(null)
    setParams(trimmed ? { q: trimmed } : {})
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Search</h1>
        <p className="mt-1 text-sm text-muted">
          Every result links back to a document, page and heading so it can be verified.
        </p>
      </header>

      <Card>
        <form onSubmit={onSubmit} className="space-y-3 p-4">
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              autoFocus
              placeholder="Ask a question or enter keywords…"
              aria-label="Search query"
              className="h-11 w-full rounded-lg border border-border bg-background pl-9 pr-10 text-sm"
            />
            {search.isFetching && (
              <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted" />
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div role="tablist" aria-label="Search mode" className="flex rounded-lg border border-border p-0.5">
              {MODES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  aria-selected={mode === item.id}
                  title={item.hint}
                  onClick={() => setMode(item.id)}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                    mode === item.id
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted hover:text-foreground'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="ml-auto flex items-center gap-2">
              <Filter className="h-3.5 w-3.5 text-muted" aria-hidden />
              <Select
                aria-label="Filter by file type"
                value={extension}
                onChange={(event) => setExtension(event.target.value)}
                className="h-8 text-xs"
              >
                <option value="">All file types</option>
                {['.pdf', '.md', '.txt', '.docx', '.csv', '.json', '.html', '.py', '.ts'].map(
                  (ext) => (
                    <option key={ext} value={ext}>
                      {ext}
                    </option>
                  ),
                )}
              </Select>
            </div>
          </div>

          <p className="text-[11px] text-muted">
            {MODES.find((item) => item.id === mode)?.hint}
          </p>
        </form>
      </Card>

      {!submitted.trim() ? (
        <Card>
          <EmptyState
            icon={<SearchIcon className="h-8 w-8" />}
            title="Search across your indexed documents"
            description="Try a phrase from a PDF, a function name from source code, or a question about your notes."
          />
        </Card>
      ) : search.isLoading ? (
        <Card>
          <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted">
            <Loader2 className="h-4 w-4 animate-spin" /> Searching…
          </div>
        </Card>
      ) : search.isError ? (
        <Card>
          <ErrorState message={extractErrorMessage(search.error)} onRetry={() => search.refetch()} />
        </Card>
      ) : search.data ? (
        <div className="grid gap-4 lg:grid-cols-5">
          <section className="space-y-3 lg:col-span-3" aria-live="polite">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
              <span>
                {search.data.total} result{search.data.total === 1 ? '' : 's'} in{' '}
                {formatDuration(search.data.response_time_ms)}
              </span>
              <span className="flex items-center gap-1.5">
                <Badge tone="primary">
                  {search.data.mode === 'hybrid' ? (
                    <>
                      <Sparkles className="h-3 w-3" /> Hybrid
                    </>
                  ) : (
                    search.data.mode
                  )}
                </Badge>
              </span>
            </div>

            {search.data.notes.map((note, index) => (
              <div
                key={index}
                className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning"
              >
                <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {note}
              </div>
            ))}

            {search.data.results.length === 0 ? (
              <Card>
                <EmptyState
                  icon={<FileText className="h-8 w-8" />}
                  title="No matching passages"
                  description="Try fewer keywords, a different mode, or remove the file type filter."
                />
              </Card>
            ) : (
              <ul className="space-y-3">
                {search.data.results.map((result) => {
                  const isActive = selected?.chunk_id === result.chunk_id
                  return (
                    <li key={result.chunk_id}>
                      <button
                        type="button"
                        onClick={() => setSelected(result)}
                        aria-pressed={isActive}
                        className={`w-full rounded-xl border bg-surface p-4 text-left transition-colors hover:border-primary/50 ${
                          isActive ? 'border-primary' : 'border-border'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="flex min-w-0 items-center gap-2 text-sm font-medium">
                            <FileText className="h-3.5 w-3.5 shrink-0 text-muted" />
                            <span className="truncate">{result.document_name}</span>
                          </span>
                          <span className="shrink-0 text-[11px] text-muted">
                            {result.page_number ? `p. ${result.page_number}` : result.extension}
                          </span>
                        </div>
                        {result.heading && (
                          <p className="mt-1 truncate text-[11px] text-muted">{result.heading}</p>
                        )}
                        <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-foreground/90">
                          <HighlightedText text={result.snippet} highlights={result.highlights} />
                        </p>
                        <p className="mt-2 line-clamp-1 text-[11px] text-muted">{result.explanation}</p>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>

          <div className="lg:col-span-2">
            {selected ? (
              <SourcePreview result={selected} onClose={() => setSelected(null)} />
            ) : (
              <Card className="lg:sticky lg:top-4">
                <EmptyState
                  icon={<FileText className="h-7 w-7" />}
                  title="Open a result"
                  description="Select a result to read the passage in context, with page and heading information."
                />
              </Card>
            )}
          </div>
        </div>
      ) : null}
    </div>
  )
}
