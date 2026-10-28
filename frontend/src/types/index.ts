export interface DocumentRecord {
  id: string
  filename: string
  extension: string
  original_path: string
  file_hash: string
  file_size: number | null
  parsing_status: string
  indexing_status: string
  parsing_error: string | null
  page_count: number | null
  char_count: number | null
  chunk_count: number
  imported_at: string | null
  modified_at_source: string | null
  last_indexed_at: string | null
}

export interface ChunkRecord {
  id: string
  document_id: string
  content: string
  chunk_index: number
  page_number: number | null
  heading: string | null
  start_char: number | null
  end_char: number | null
}

export interface SearchResult {
  chunk_id: string
  document_id: string
  document_name: string
  extension: string
  content: string
  snippet: string
  page_number: number | null
  heading: string | null
  score: number | null
  highlights: string[]
  match_type: string
  explanation: string
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
  query: string
  mode: string
  response_time_ms: number
  notes: string[]
}

export type SearchMode = 'fulltext' | 'semantic' | 'hybrid'

export interface IndexingJob {
  id: string
  status: string
  job_type: string
  total_files: number
  processed_files: number
  failed_files: number
  current_file: string | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string | null
}

export interface Stats {
  document_count: number
  chunk_count: number
  total_source_bytes: number
  indexed_documents: number
  failed_documents: number
  pending_documents: number
  query_count: number
  average_response_time_ms: number
  embedding_count: number
  embedding_model: string | null
  embedding_coverage_percent: number
  last_indexed_at: string | null
  storage_backend: string
}

export interface AppSettings {
  app_name: string
  version: string
  database_url: string
  allowed_import_dirs: string[]
  max_file_size_mb: number
  chunk_size: number
  chunk_overlap: number
  supported_extensions: string[]
  enable_semantic_search: boolean
  embedding_model: string
  embedding_available: boolean
  embedding_storage_estimate_mb: number
  enable_ai_assistant: boolean
  ai_provider: string
  ai_model: string
  ai_provider_configured: boolean
  ollama_base_url: string
  require_ai_consent: boolean
  store_search_history: boolean
  disable_telemetry: boolean
}

export interface SourceReference {
  index: number
  chunk_id: string
  document_id: string
  document_name: string
  page_number: number | null
  heading: string | null
  excerpt: string
  score: number | null
}

export interface AssistantResponse {
  answer: string
  sources: SourceReference[]
  provider: string
  model: string
  grounded: boolean
  insufficient_evidence: boolean
  invalid_citations: number[]
  warning: string | null
  retrieval_mode: string
  notes: string[]
}

export interface Paged<T> {
  items: T[]
  total: number
}

export interface ImportResponse {
  job_id: string
  accepted: string[]
  rejected: { filename: string; reason: string }[]
  queued_count: number
}

export interface FolderImportResponse {
  job_id: string
  queued_count: number
  directory: string
  files: string[]
}

export interface Collection {
  id: string
  name: string
  description: string | null
  document_count: number
  created_at: string | null
}
