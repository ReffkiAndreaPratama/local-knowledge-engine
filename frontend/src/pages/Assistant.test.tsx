import { beforeEach, describe, expect, it, vi } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Assistant from '@/pages/Assistant'
import { renderWithProviders } from '@/test/utils'
import type { AppSettings, AssistantResponse } from '@/types'

const askMock = vi.fn()
const settingsMock = vi.fn()

vi.mock('@/lib/api', () => ({
  assistantApi: {
    ask: (...args: unknown[]) => askMock(...args),
  },
  settingsApi: {
    get: (...args: unknown[]) => settingsMock(...args),
  },
  extractErrorMessage: (error: unknown) =>
    error instanceof Error ? error.message : 'Unexpected error',
}))

const settings: AppSettings = {
  app_name: 'Local Knowledge Engine',
  version: '0.1.0',
  database_url: 'sqlite:///./data/knowledge.db',
  allowed_import_dirs: ['C:/notes'],
  max_file_size_mb: 100,
  chunk_size: 512,
  chunk_overlap: 50,
  supported_extensions: ['.md', '.txt'],
  enable_semantic_search: false,
  embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
  embedding_available: false,
  embedding_storage_estimate_mb: 90,
  enable_ai_assistant: false,
  ai_provider: 'ollama',
  ai_model: 'llama3.2',
  ai_provider_configured: false,
  ollama_base_url: 'http://localhost:11434',
  require_ai_consent: true,
  store_search_history: true,
  disable_telemetry: true,
}

const grounded: AssistantResponse = {
  answer: 'The deployment uses port 8080 [1].',
  sources: [
    {
      index: 1,
      chunk_id: 'chunk-1',
      document_id: 'doc-1',
      document_name: 'deploy.md',
      page_number: 3,
      heading: 'Deployment',
      excerpt: 'The deployment uses port 8080 by default.',
      score: 0.91,
    },
  ],
  provider: 'ollama',
  model: 'llama3.2',
  grounded: true,
  insufficient_evidence: false,
  invalid_citations: [],
  warning: null,
  retrieval_mode: 'hybrid',
  notes: [],
}

describe('Assistant page', () => {
  beforeEach(() => {
    askMock.mockReset()
    settingsMock.mockReset()
    settingsMock.mockResolvedValue(settings)
  })

  it('shows that the assistant is disabled when settings say so', async () => {
    renderWithProviders(<Assistant />)
    expect(await screen.findByText('Assistant disabled')).toBeInTheDocument()
    expect(await screen.findByText('ollama · llama3.2')).toBeInTheDocument()
  })

  it('submits the question and renders the cited answer', async () => {
    askMock.mockResolvedValue(grounded)
    const user = userEvent.setup()
    renderWithProviders(<Assistant />)

    await user.type(
      await screen.findByLabelText('Question'),
      'Which port does the deployment use?',
    )
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText('The deployment uses port 8080 [1].')).toBeInTheDocument()
    expect(askMock).toHaveBeenCalledWith(
      expect.objectContaining({
        question: 'Which port does the deployment use?',
        mode: 'hybrid',
        limit: 6,
      }),
    )

    // "Sources" lives inside CardHeader inside the Card; walk up to the Card element.
    const sourcesCard = screen.getByText('1 cited passage(s)').closest('div')!
      .parentElement!.parentElement! as HTMLElement
    expect(within(sourcesCard).getByText('[1]')).toBeInTheDocument()
    expect(within(sourcesCard).getByText('deploy.md')).toBeInTheDocument()
    expect(within(sourcesCard).getByText('Page 3')).toBeInTheDocument()
    expect(screen.getByText('Grounded')).toBeInTheDocument()
  })

  it('renders the search-only fallback without claiming a grounded answer', async () => {
    askMock.mockResolvedValue({
      ...grounded,
      answer:
        'AI answering is unavailable, so here are the retrieved sources instead. Reason: not configured.',
      provider: 'none',
      model: 'none',
      grounded: false,
      insufficient_evidence: true,
    })

    const user = userEvent.setup()
    renderWithProviders(<Assistant />)
    await user.type(await screen.findByLabelText('Question'), 'What port?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText('Search only')).toBeInTheDocument()
    expect(screen.getByText(/AI answering is unavailable/)).toBeInTheDocument()
  })

  it('shows a warning when citations were removed', async () => {
    askMock.mockResolvedValue({
      ...grounded,
      answer: 'The port is 8080 [1].',
      invalid_citations: [7],
      warning: 'The answer contained no valid source citations.',
    })

    const user = userEvent.setup()
    renderWithProviders(<Assistant />)
    await user.type(await screen.findByLabelText('Question'), 'What port?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(
      await screen.findByText('Removed 1 citation(s) that did not match any retrieved source.'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('The answer contained no valid source citations.'),
    ).toBeInTheDocument()
  })

  it('shows an error when the request fails', async () => {
    askMock.mockRejectedValue(new Error('Assistant exploded'))
    const user = userEvent.setup()
    renderWithProviders(<Assistant />)
    await user.type(await screen.findByLabelText('Question'), 'What port?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Assistant exploded')
  })

  it('asks for consent before using an external provider', async () => {
    settingsMock.mockResolvedValue({
      ...settings,
      enable_ai_assistant: true,
      ai_provider: 'openai',
      ai_provider_configured: true,
    })
    askMock.mockResolvedValue(grounded)

    const user = userEvent.setup()
    renderWithProviders(<Assistant />)

    const consent = await screen.findByLabelText(
      'Allow sending retrieved text to the external provider',
    )
    expect(consent).not.toBeChecked()

    await user.type(screen.getByLabelText('Question'), 'What port?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    await waitFor(() =>
      expect(askMock).toHaveBeenCalledWith(
        expect.objectContaining({ consent_to_external_provider: false }),
      ),
    )

    await user.click(consent)
    expect(consent).toBeChecked()
  })
})
