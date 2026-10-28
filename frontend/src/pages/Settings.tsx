import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Database, Lock, Save, ShieldCheck, Sparkles, Trash2 } from 'lucide-react'
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  ErrorState,
  Input,
  Modal,
  Spinner,
} from '@/components/ui'
import { extractErrorMessage, settingsApi } from '@/lib/api'
import { useToast } from '@/lib/toast'
import type { AppSettings } from '@/types'

export default function Settings() {
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const [form, setForm] = useState<AppSettings | null>(null)
  const [dirs, setDirs] = useState('')
  const [clearOpen, setClearOpen] = useState(false)

  const settings = useQuery({ queryKey: ['settings'], queryFn: settingsApi.get })

  useEffect(() => {
    if (settings.data) {
      setForm(settings.data)
      setDirs(settings.data.allowed_import_dirs.join(', '))
    }
  }, [settings.data])

  const save = useMutation({
    mutationFn: () => {
      if (!form) throw new Error('Settings not loaded')
      return settingsApi.update({
        allowed_import_dirs: dirs
          .split(',')
          .map((value) => value.trim())
          .filter(Boolean),
        max_file_size_mb: form.max_file_size_mb,
        chunk_size: form.chunk_size,
        chunk_overlap: form.chunk_overlap,
        enable_semantic_search: form.enable_semantic_search,
        embedding_model: form.embedding_model,
        enable_ai_assistant: form.enable_ai_assistant,
        ai_provider: form.ai_provider,
        ai_model: form.ai_model,
        ollama_base_url: form.ollama_base_url,
        require_ai_consent: form.require_ai_consent,
        store_search_history: form.store_search_history,
      })
    },
    onSuccess: (data) => {
      setForm(data)
      notify('Settings saved.', 'success')
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
    onError: (error) => notify(extractErrorMessage(error), 'error'),
  })

  const clearHistory = useMutation({
    mutationFn: settingsApi.clearSearchHistory,
    onSuccess: (result) => {
      notify(`Deleted ${result.deleted} search history entries.`, 'success')
      setClearOpen(false)
    },
    onError: (error) => notify(extractErrorMessage(error), 'error'),
  })

  if (settings.isLoading || !form) return <Spinner label="Loading settings…" />
  if (settings.isError) {
    return <ErrorState message={extractErrorMessage(settings.error)} onRetry={() => settings.refetch()} />
  }

  const update = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) =>
    setForm((current) => (current ? { ...current, [key]: value } : current))

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
          <p className="mt-1 text-sm text-muted">
            API keys are read from environment variables on the server and are never exposed here.
          </p>
        </div>
        <Button onClick={() => save.mutate()} loading={save.isPending}>
          <Save className="h-4 w-4" /> Save changes
        </Button>
      </header>

      <Card>
        <CardHeader title="Storage & import" description="Where data lives and what may be indexed" />
        <CardBody className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label className="mb-1.5 block text-xs font-medium text-muted">Database</label>
            <Input value={form.database_url} readOnly className="font-mono text-xs" />
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="allowed-dirs" className="mb-1.5 block text-xs font-medium text-muted">
              Allowed import directories (comma separated)
            </label>
            <Input
              id="allowed-dirs"
              value={dirs}
              onChange={(event) => setDirs(event.target.value)}
              placeholder="C:\\Users\\you\\Documents"
            />
            <p className="mt-1 text-[11px] text-muted">
              Paths outside these directories are rejected, including <code>..</code> traversal
              attempts.
            </p>
          </div>
          <div>
            <label htmlFor="max-size" className="mb-1.5 block text-xs font-medium text-muted">
              Max file size (MB)
            </label>
            <Input
              id="max-size"
              type="number"
              min={1}
              value={form.max_file_size_mb}
              onChange={(event) => update('max_file_size_mb', Number(event.target.value))}
            />
          </div>
          <div>
            <label htmlFor="chunk-size" className="mb-1.5 block text-xs font-medium text-muted">
              Chunk size (characters)
            </label>
            <Input
              id="chunk-size"
              type="number"
              min={64}
              value={form.chunk_size}
              onChange={(event) => update('chunk_size', Number(event.target.value))}
            />
          </div>
          <div>
            <label htmlFor="chunk-overlap" className="mb-1.5 block text-xs font-medium text-muted">
              Chunk overlap
            </label>
            <Input
              id="chunk-overlap"
              type="number"
              min={0}
              value={form.chunk_overlap}
              onChange={(event) => update('chunk_overlap', Number(event.target.value))}
            />
          </div>
          <div className="sm:col-span-2">
            <p className="mb-1.5 text-xs font-medium text-muted">Supported extensions</p>
            <div className="flex flex-wrap gap-1">
              {form.supported_extensions.map((ext) => (
                <Badge key={ext}>{ext}</Badge>
              ))}
            </div>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title={
            <span className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" /> Semantic search
            </span>
          }
          description="Optional local embeddings. Disabled by default."
        />
        <CardBody className="space-y-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.enable_semantic_search}
              onChange={(event) => update('enable_semantic_search', event.target.checked)}
              className="h-4 w-4"
            />
            Enable semantic search
          </label>
          <div>
            <label htmlFor="embedding-model" className="mb-1.5 block text-xs font-medium text-muted">
              Embedding model
            </label>
            <Input
              id="embedding-model"
              value={form.embedding_model}
              onChange={(event) => update('embedding_model', event.target.value)}
              className="font-mono text-xs"
            />
          </div>
          <p className="text-[11px] text-muted">
            The model is downloaded only after you confirm; expect roughly{' '}
            {form.embedding_storage_estimate_mb} MB on disk for the selected model. Until it is
            available, semantic mode returns a clear notice and full-text search keeps working.
          </p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="AI provider"
          description="Optional. Search works without any provider."
        />
        <CardBody className="grid gap-4 sm:grid-cols-2">
          <label className="flex items-center gap-2 text-sm sm:col-span-2">
            <input
              type="checkbox"
              checked={form.enable_ai_assistant}
              onChange={(event) => update('enable_ai_assistant', event.target.checked)}
              className="h-4 w-4"
            />
            Enable AI assistant
          </label>
          <div>
            <label htmlFor="ai-provider" className="mb-1.5 block text-xs font-medium text-muted">
              Provider
            </label>
            <select
              id="ai-provider"
              value={form.ai_provider}
              onChange={(event) => update('ai_provider', event.target.value)}
              className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm"
            >
              <option value="ollama">Ollama (local)</option>
              <option value="openai">OpenAI-compatible (external)</option>
            </select>
          </div>
          <div>
            <label htmlFor="ai-model" className="mb-1.5 block text-xs font-medium text-muted">
              Model
            </label>
            <Input
              id="ai-model"
              value={form.ai_model}
              onChange={(event) => update('ai_model', event.target.value)}
              className="font-mono text-xs"
            />
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="ollama-url" className="mb-1.5 block text-xs font-medium text-muted">
              Ollama base URL
            </label>
            <Input
              id="ollama-url"
              value={form.ollama_base_url}
              onChange={(event) => update('ollama_base_url', event.target.value)}
              className="font-mono text-xs"
            />
          </div>
          <label className="flex items-center gap-2 text-sm sm:col-span-2">
            <input
              type="checkbox"
              checked={form.require_ai_consent}
              onChange={(event) => update('require_ai_consent', event.target.checked)}
              className="h-4 w-4"
            />
            Require explicit consent before sending document text to an external provider
          </label>
          <div className="sm:col-span-2">
            <Badge tone={form.ai_provider_configured ? 'success' : 'warning'}>
              {form.ai_provider_configured ? 'Provider configured' : 'Provider not configured'}
            </Badge>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title={
            <span className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-success" /> Privacy
            </span>
          }
        />
        <CardBody className="space-y-3 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.store_search_history}
              onChange={(event) => update('store_search_history', event.target.checked)}
              className="h-4 w-4"
            />
            Store local search history for statistics
          </label>
          <p className="flex items-center gap-2 text-[11px] text-muted">
            <Lock className="h-3.5 w-3.5" />
            Telemetry is {form.disable_telemetry ? 'disabled' : 'enabled'} — no data leaves this
            machine by default.
          </p>
          <Button variant="secondary" onClick={() => setClearOpen(true)}>
            <Trash2 className="h-4 w-4" /> Clear search history
          </Button>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="About" />
        <CardBody className="flex items-center gap-2 text-xs text-muted">
          <Database className="h-4 w-4" />
          {form.app_name} v{form.version} · MIT licensed · Local-first
        </CardBody>
      </Card>

      <Modal
        open={clearOpen}
        title="Clear search history"
        onClose={() => setClearOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setClearOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={() => clearHistory.mutate()} loading={clearHistory.isPending}>
              Delete history
            </Button>
          </>
        }
      >
        <p className="text-sm">
          All stored queries and response times will be deleted. Documents are not affected.
        </p>
      </Modal>
    </div>
  )
}
