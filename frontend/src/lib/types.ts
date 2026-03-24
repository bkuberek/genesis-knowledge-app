/** Shared TypeScript types matching the backend Pydantic schemas. */

export interface DocumentResponse {
  id: string
  filename: string
  file_path: string | null
  content_type: string | null
  status: string
  stage: number
  source_type: string
  visibility: string
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface DocumentUploadResponse {
  id: string
  filename: string
  status: string
  created_at: string
}

export interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id?: string
  role: 'user' | 'assistant' | 'tool'
  content: string
  created_at?: string
}

export interface EntityResponse {
  id: string
  name: string
  canonical_name: string
  type: string
  properties: Record<string, unknown>
  source_count: number
}

export interface EntitySearchResult {
  entities: EntityResponse[]
  total: number
}

export interface WebSocketMessage {
  type: 'session' | 'message'
  session_id?: string
  history?: Array<{ role: string; content: string; created_at: string }>
  role?: string
  content?: string
}
