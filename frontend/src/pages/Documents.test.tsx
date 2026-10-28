import { beforeEach, describe, expect, it, vi } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Documents from '@/pages/Documents'
import { renderWithProviders } from '@/test/utils'
import type { DocumentRecord, Paged } from '@/types'

const listMock = vi.fn()
const removeMock = vi.fn()
const reindexMock = vi.fn()
const chunksMock = vi.fn()
const scanMock = vi.fn()
const uploadMock = vi.fn()
const importFolderMock = vi.fn()

vi.mock('@/lib/api', () => ({
  documentsApi: {
    list: (...args: unknown[]) => listMock(...args),
    remove: (...args: unknown[]) => removeMock(...args),
    reindex: (...args: unknown[]) => reindexMock(...args),
    chunks: (...args: unknown[]) => chunksMock(...args),
    scanChanges: (...args: unknown[]) => scanMock(...args),
    upload: (...args: unknown[]) => uploadMock(...args),
    importFolder: (...args: unknown[]) => importFolderMock(...args),
  },
  extractErrorMessage: (error: unknown) =>
    error instanceof Error ? error.message : 'Unexpected error',
}))

const document: DocumentRecord = {
  id: 'doc-1',
  filename: 'deploy.md',
  extension: '.md',
  original_path: 'C:/notes/deploy.md',
  file_hash: 'abc123',
  file_size: 2048,
  parsing_status: 'completed',
  indexing_status: 'completed',
  parsing_error: null,
  page_count: null,
  char_count: 120,
  chunk_count: 3,
  imported_at: '2026-01-02T03:04:05Z',
  modified_at_source: null,
  last_indexed_at: '2026-01-02T03:04:05Z',
}

const page: Paged<DocumentRecord> = { items: [document], total: 1 }

describe('Documents page', () => {
  beforeEach(() => {
    listMock.mockReset()
    removeMock.mockReset()
    reindexMock.mockReset()
    chunksMock.mockReset()
    scanMock.mockReset()
    listMock.mockResolvedValue(page)
    chunksMock.mockResolvedValue({ items: [], total: 0 })
    removeMock.mockResolvedValue(undefined)
    reindexMock.mockResolvedValue({ job_id: 'job-1' })
  })

  it('renders documents returned by the API', async () => {
    renderWithProviders(<Documents />)

    expect(await screen.findByRole('button', { name: 'deploy.md' })).toBeInTheDocument()
    expect(screen.getByText('2.0 KB')).toBeInTheDocument()
    expect(screen.getByText('completed')).toBeInTheDocument()
  })

  it('passes the filename filter to the API', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Documents />)

    const input = await screen.findByLabelText('File name')
    await user.type(input, 'alpha')

    await waitFor(() =>
      expect(listMock).toHaveBeenLastCalledWith(
        expect.objectContaining({ filename: 'alpha', limit: 200 }),
      ),
    )
  })

  it('shows an empty state when nothing matches', async () => {
    listMock.mockResolvedValue({ items: [], total: 0 })
    renderWithProviders(<Documents />)

    expect(await screen.findByText('No documents match')).toBeInTheDocument()
  })

  it('shows an error state with a retry action', async () => {
    listMock.mockRejectedValueOnce(new Error('API exploded'))
    listMock.mockResolvedValueOnce(page)
    const user = userEvent.setup()
    renderWithProviders(<Documents />)

    expect(await screen.findByRole('alert')).toHaveTextContent('API exploded')
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'deploy.md' })).toBeInTheDocument(),
    )
  })

  it('requires confirmation before deleting a document', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Documents />)

    await user.click(await screen.findByRole('button', { name: 'Delete deploy.md' }))
    const dialog = await screen.findByRole('dialog', { name: 'Remove document' })
    expect(within(dialog).getByText(/cannot be undone/)).toBeInTheDocument()
    expect(removeMock).not.toHaveBeenCalled()

    await user.click(within(dialog).getByRole('button', { name: 'Delete permanently' }))
    await waitFor(() => expect(removeMock).toHaveBeenCalledWith('doc-1'))
  })

  it('cancelling the delete dialog keeps the document', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Documents />)

    await user.click(await screen.findByRole('button', { name: 'Delete deploy.md' }))
    const dialog = await screen.findByRole('dialog', { name: 'Remove document' })
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(removeMock).not.toHaveBeenCalled()
  })

  it('shows document details and chunks', async () => {
    chunksMock.mockResolvedValue({
      items: [
        {
          id: 'chunk-1',
          document_id: 'doc-1',
          content: 'The deployment uses port 8080.',
          chunk_index: 0,
          page_number: 3,
          heading: 'Deployment',
          start_char: 0,
          end_char: 30,
        },
      ],
      total: 1,
    })

    const user = userEvent.setup()
    renderWithProviders(<Documents />)
    await user.click(await screen.findByRole('button', { name: 'deploy.md' }))

    const dialog = await screen.findByRole('dialog', { name: 'deploy.md' })
    expect(within(dialog).getByText('The deployment uses port 8080.')).toBeInTheDocument()
    expect(within(dialog).getByText(/page 3/)).toBeInTheDocument()
    expect(within(dialog).getByText('abc123')).toBeInTheDocument()
  })

  it('requests re-indexing from the table row', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Documents />)

    await user.click(await screen.findByRole('button', { name: 'Re-index deploy.md' }))
    await waitFor(() => expect(reindexMock).toHaveBeenCalledWith('doc-1'))
  })
})
