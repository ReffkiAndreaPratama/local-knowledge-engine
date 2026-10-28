import axios from 'axios'
import type {
  AppSettings,
  AssistantResponse,
  ChunkRecord,
  Collection,
  DocumentRecord,
  FolderImportResponse,
  ImportResponse,
  IndexingJob,
  Paged,
  SearchMode,
  SearchResponse,
  Stats,
} from '@/types'

export const api = axios.create({
  baseURL: '/api',
  timeout: 120_000,
})

export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((d) => d.msg ?? String(d)).join('; ')
    }
    return error.message
  }
  if (error instanceof Error) return error.message
  return 'Unexpected error'
}

export interface DocumentFilters {
  filename?: string
  extension?: string
  status?: string
  skip?: number
  limit?: number
}

export const documentsApi = {
  async list(filters: DocumentFilters = {}): Promise<Paged<DocumentRecord>> {
    const { data } = await api.get<Paged<DocumentRecord>>('/documents', { params: filters })
    return data
  },
  async get(id: string): Promise<DocumentRecord> {
    const { data } = await api.get<DocumentRecord>(`/documents/${id}`)
    return data
  },
  async chunks(id: string, limit = 200): Promise<Paged<ChunkRecord>> {
    const { data } = await api.get<Paged<ChunkRecord>>(`/documents/${id}/chunks`, {
      params: { limit },
    })
    return data
  },
  async upload(files: File[]): Promise<ImportResponse> {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))
    const { data } = await api.post<ImportResponse>('/documents/import', form)
    return data
  },
  async importFolder(directory: string, recursive = true): Promise<FolderImportResponse> {
    const { data } = await api.post<FolderImportResponse>('/documents/import-folder', {
      directory,
      recursive,
    })
    return data
  },
  async remove(id: string): Promise<void> {
    await api.delete(`/documents/${id}`)
  },
  async reindex(id: string): Promise<{ job_id: string }> {
    const { data } = await api.post(`/documents/${id}/reindex`)
    return data
  },
  async scanChanges(): Promise<{
    changed: { id: string; filename: string }[]
    missing: { id: string; filename: string }[]
    unchanged: number
    reindex_job_id: string | null
  }> {
    const { data } = await api.post('/documents/scan-changes')
    return data
  },
}

export const searchApi = {
  async search(params: {
    query: string
    mode: SearchMode
    limit?: number
    offset?: number
    filters?: { document_ids?: string[]; extensions?: string[] }
  }): Promise<SearchResponse> {
    const { data } = await api.post<SearchResponse>('/search/', params)
    return data
  },
}

export const jobsApi = {
  async list(limit = 20): Promise<Paged<IndexingJob>> {
    const { data } = await api.get<Paged<IndexingJob>>('/indexing/jobs', { params: { limit } })
    return data
  },
  async cancel(id: string): Promise<void> {
    await api.post(`/indexing/jobs/${id}/cancel`)
  },
}

export const assistantApi = {
  async ask(params: {
    question: string
    mode: SearchMode
    limit?: number
    consent_to_external_provider?: boolean
  }): Promise<AssistantResponse> {
    const { data } = await api.post<AssistantResponse>('/assistant/ask', params)
    return data
  },
}

export const settingsApi = {
  async get(): Promise<AppSettings> {
    const { data } = await api.get<AppSettings>('/settings')
    return data
  },
  async update(patch: Partial<AppSettings>): Promise<AppSettings> {
    const { data } = await api.put<AppSettings>('/settings', patch)
    return data
  },
  async clearSearchHistory(): Promise<{ deleted: number }> {
    const { data } = await api.delete('/settings/search-history')
    return data
  },
}

export const statsApi = {
  async get(): Promise<Stats> {
    const { data } = await api.get<Stats>('/analytics/stats')
    return data
  },
}

export const collectionsApi = {
  async list(): Promise<Paged<Collection>> {
    const { data } = await api.get<Paged<Collection>>('/collections')
    return data
  },
  async create(name: string, description?: string): Promise<Collection> {
    const { data } = await api.post<Collection>('/collections', { name, description })
    return data
  },
  async remove(id: string): Promise<void> {
    await api.delete(`/collections/${id}`)
  },
  async documentIds(id: string): Promise<string[]> {
    const { data } = await api.get<{ document_ids: string[] }>(`/collections/${id}/document-ids`)
    return data.document_ids
  },
  async addDocuments(id: string, documentIds: string[]): Promise<{ added: number }> {
    const { data } = await api.post(`/collections/${id}/documents`, {
      document_ids: documentIds,
    })
    return data
  },
  async removeDocument(id: string, documentId: string): Promise<void> {
    await api.delete(`/collections/${id}/documents/${documentId}`)
  },
}
