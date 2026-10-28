import { beforeEach, describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SearchPage from '@/pages/Search'
import { renderWithProviders } from '@/test/utils'
import type { SearchResponse } from '@/types'

const searchMock = vi.fn()

vi.mock('@/lib/api', () => ({
  searchApi: {
    search: (...args: unknown[]) => searchMock(...args),
  },
  extractErrorMessage: (error: unknown) =>
    error instanceof Error ? error.message : 'Unexpected error',
}))

const response: SearchResponse = {
  results: [
    {
      chunk_id: 'chunk-1',
      document_id: 'doc-1',
      document_name: 'deploy.md',
      extension: '.md',
      content: 'The deployment uses port 8080 by default.',
      snippet: 'The deployment uses port 8080 by default.',
      page_number: 3,
      heading: 'Deployment',
      score: -1.2,
      highlights: ['deployment'],
      match_type: 'fulltext',
      explanation: 'Keyword match on: deployment',
    },
  ],
  total: 1,
  query: 'deployment',
  mode: 'fulltext',
  response_time_ms: 12,
  notes: [],
}

describe('Search page', () => {
  beforeEach(() => {
    searchMock.mockReset()
    searchMock.mockResolvedValue(response)
  })

  it('runs a search from the URL and renders a highlighted snippet', async () => {
    renderWithProviders(<SearchPage />, { route: '/search?q=deployment' })

    const fileName = await screen.findByText('deploy.md')
    expect(fileName).toBeInTheDocument()

    const highlighted = screen.getByText('deployment')
    expect(highlighted.tagName.toLowerCase()).toBe('mark')

    expect(screen.getByText('1 result in 12 ms')).toBeInTheDocument()
    expect(searchMock).toHaveBeenCalledWith(
      expect.objectContaining({ query: 'deployment', mode: 'fulltext', limit: 20 }),
    )
  })

  it('opens the source preview with page, heading and chunk id', async () => {
    const user = userEvent.setup()
    renderWithProviders(<SearchPage />, { route: '/search?q=deployment' })

    const resultButton = await screen.findByRole('button', { name: /deploy\.md/ })
    await user.click(resultButton)

    const preview = await screen.findByRole('complementary', { name: 'Source preview' })
    expect(preview).toHaveTextContent('Page 3')
    expect(preview).toHaveTextContent('Section: Deployment')
    expect(preview).toHaveTextContent('Keyword match on: deployment')
    expect(preview).toHaveTextContent('chunk: chunk-1')
  })

  it('shows backend warnings such as semantic search being unavailable', async () => {
    searchMock.mockResolvedValue({
      ...response,
      results: [],
      total: 0,
      notes: ['Semantic search unavailable: model not downloaded'],
    })

    renderWithProviders(<SearchPage />, { route: '/search?q=deployment' })

    expect(
      await screen.findByText('Semantic search unavailable: model not downloaded'),
    ).toBeInTheDocument()
    expect(screen.getByText('No matching passages')).toBeInTheDocument()
  })

  it('shows an error state and retries', async () => {
    searchMock.mockRejectedValueOnce(new Error('Network down'))
    searchMock.mockResolvedValueOnce(response)

    const user = userEvent.setup()
    renderWithProviders(<SearchPage />, { route: '/search?q=deployment' })

    expect(await screen.findByRole('alert')).toHaveTextContent('Network down')
    await user.click(screen.getByRole('button', { name: 'Try again' }))

    await waitFor(() => expect(screen.getByText('deploy.md')).toBeInTheDocument())
  })

  it('does not search for an empty query', async () => {
    renderWithProviders(<SearchPage />, { route: '/search' })

    expect(await screen.findByText('Search across your indexed documents')).toBeInTheDocument()
    expect(searchMock).not.toHaveBeenCalled()
  })
})
