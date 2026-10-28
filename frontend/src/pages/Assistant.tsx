import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Bot, FileText, Send, ShieldAlert, Sparkles } from 'lucide-react'
import { Badge, Button, Card, CardBody, CardHeader, EmptyState } from '@/components/ui'
import { assistantApi, extractErrorMessage, settingsApi } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { AssistantResponse, SearchMode } from '@/types'

const MODES: { id: SearchMode; label: string }[] = [
  { id: 'hybrid', label: 'Hybrid' },
  { id: 'fulltext', label: 'Full-text' },
  { id: 'semantic', label: 'Semantic' },
]

export default function Assistant() {
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<SearchMode>('hybrid')
  const [consent, setConsent] = useState(false)
  const [answer, setAnswer] = useState<AssistantResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const settings = useQuery({ queryKey: ['settings'], queryFn: settingsApi.get })

  const ask = useMutation({
    mutationFn: () =>
      assistantApi.ask({
        question: question.trim(),
        mode,
        limit: 6,
        consent_to_external_provider: consent,
      }),
    onSuccess: (data) => {
      setAnswer(data)
      setError(null)
    },
    onError: (err) => {
      setError(extractErrorMessage(err))
      setAnswer(null)
    },
  })

  const externalProvider =
    settings.data && settings.data.ai_provider !== 'ollama' && settings.data.enable_ai_assistant

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">AI Assistant</h1>
        <p className="mt-1 text-sm text-muted">
          Answers are limited to retrieved passages. Every cited source can be opened and checked.
        </p>
      </header>

      <Card>
        <CardBody className="flex flex-wrap items-center gap-2 text-xs">
          <Badge tone={settings.data?.enable_ai_assistant ? 'success' : 'neutral'}>
            <Sparkles className="h-3 w-3" />
            {settings.data?.enable_ai_assistant ? 'Assistant enabled' : 'Assistant disabled'}
          </Badge>
          <Badge tone={settings.data?.ai_provider_configured ? 'primary' : 'warning'}>
            {settings.data?.ai_provider ?? '—'} · {settings.data?.ai_model ?? '—'}
          </Badge>
          {settings.data?.enable_ai_assistant && !settings.data?.ai_provider_configured && (
            <span className="text-[11px] text-warning">
              Provider not reachable. Search-only fallback will be used.
            </span>
          )}
        </CardBody>
      </Card>

      <Card>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (question.trim()) ask.mutate()
          }}
          className="space-y-3 p-4"
        >
          <label htmlFor="assistant-question" className="sr-only">
            Question
          </label>
          <textarea
            id="assistant-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={3}
            placeholder="e.g. Which port does the deployment use, according to the docs?"
            className="w-full resize-y rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex rounded-lg border border-border p-0.5" role="tablist" aria-label="Retrieval mode">
              {MODES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  aria-selected={mode === item.id}
                  onClick={() => setMode(item.id)}
                  className={cn(
                    'rounded-md px-3 py-1.5 text-xs font-medium',
                    mode === item.id
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted hover:text-foreground',
                  )}
                >
                  {item.label}
                </button>
              ))}
            </div>

            {externalProvider && (
              <label className="flex items-center gap-2 text-[11px] text-warning">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(event) => setConsent(event.target.checked)}
                  className="h-3.5 w-3.5"
                />
                Allow sending retrieved text to the external provider
              </label>
            )}

            <Button type="submit" className="ml-auto" loading={ask.isPending} disabled={!question.trim()}>
              <Send className="h-4 w-4" /> Ask
            </Button>
          </div>
        </form>
      </Card>

      {error && (
        <div role="alert" className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-xs text-danger">
          {error}
        </div>
      )}

      {!answer && !ask.isPending && (
        <Card>
          <EmptyState
            icon={<Bot className="h-8 w-8" />}
            title="Ask a question about your documents"
            description="If no evidence is found, the assistant says so instead of guessing. You can also use search only."
          />
        </Card>
      )}

      {ask.isPending && (
        <Card>
          <CardBody className="flex items-center gap-2 text-sm text-muted">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            Retrieving passages and composing an answer…
          </CardBody>
        </Card>
      )}

      {answer && (
        <div className="grid gap-4 lg:grid-cols-5">
          <Card className="lg:col-span-3">
            <CardHeader
              title="Answer"
              description={`Provider: ${answer.provider}${answer.model !== 'none' ? ` · ${answer.model}` : ''}`}
              action={
                answer.grounded ? (
                  <Badge tone="success">Grounded</Badge>
                ) : (
                  <Badge tone="warning">
                    <ShieldAlert className="h-3 w-3" /> Search only
                  </Badge>
                )
              }
            />
            <CardBody className="space-y-3">
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{answer.answer}</p>

              {answer.warning && (
                <p className="rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-[11px] text-warning">
                  {answer.warning}
                </p>
              )}
              {answer.invalid_citations.length > 0 && (
                <p className="text-[11px] text-danger">
                  Removed {answer.invalid_citations.length} citation(s) that did not match any
                  retrieved source.
                </p>
              )}
              {answer.notes.map((note, index) => (
                <p key={index} className="text-[11px] text-muted">
                  {note}
                </p>
              ))}
            </CardBody>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader title="Sources" description={`${answer.sources.length} cited passage(s)`} />
            <CardBody className="space-y-2">
              {answer.sources.length === 0 ? (
                <p className="text-xs text-muted">No source was cited by the answer.</p>
              ) : (
                <ol className="space-y-2">
                  {answer.sources.map((source) => (
                    <li
                      key={source.chunk_id}
                      className="rounded-lg border border-border bg-background p-3 text-[11px]"
                    >
                      <p className="flex items-center gap-1.5 font-medium">
                        <span className="rounded bg-primary-soft px-1.5 py-0.5 text-primary">
                          [{source.index}]
                        </span>
                        <FileText className="h-3 w-3 text-muted" />
                        <span className="truncate">{source.document_name}</span>
                      </p>
                      {source.page_number && (
                        <p className="mt-1 text-muted">Page {source.page_number}</p>
                      )}
                      <p className="mt-1 line-clamp-4 text-foreground/80">{source.excerpt}</p>
                    </li>
                  ))}
                </ol>
              )}
            </CardBody>
          </Card>
        </div>
      )}
    </div>
  )
}
