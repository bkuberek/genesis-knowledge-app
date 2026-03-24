import { getToken } from './keycloak'
import type {
  ChatSession,
  ChatMessage,
  DocumentResponse,
  DocumentUploadResponse,
  EntitySearchResult,
} from './types'

const API_BASE = '/api'

async function fetchApi(path: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers)
  headers.set('Authorization', `Bearer ${getToken()}`)
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (!response.ok) {
    const text = await response.text().catch(() => 'Unknown error')
    throw new Error(`API ${response.status}: ${text}`)
  }

  return response
}

export const api = {
  // ---- Documents ----
  async uploadDocument(file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    const headers = new Headers()
    headers.set('Authorization', `Bearer ${getToken()}`)
    const response = await fetch(`${API_BASE}/documents`, {
      method: 'POST',
      headers,
      body: formData,
    })
    if (!response.ok) throw new Error(`Upload failed: ${response.status}`)
    return response.json() as Promise<DocumentUploadResponse>
  },

  async listDocuments(): Promise<{ documents: DocumentResponse[] }> {
    const r = await fetchApi('/documents')
    return r.json() as Promise<{ documents: DocumentResponse[] }>
  },

  async getDocument(id: string): Promise<DocumentResponse> {
    const r = await fetchApi(`/documents/${id}`)
    return r.json() as Promise<DocumentResponse>
  },

  // ---- Chat sessions ----
  async createSession(title?: string): Promise<ChatSession> {
    const r = await fetchApi('/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({ title: title || 'New Chat' }),
    })
    return r.json() as Promise<ChatSession>
  },

  async listSessions(): Promise<ChatSession[]> {
    const r = await fetchApi('/chat/sessions')
    return r.json() as Promise<ChatSession[]>
  },

  async getSessionMessages(sessionId: string): Promise<ChatMessage[]> {
    const r = await fetchApi(`/chat/sessions/${sessionId}/messages`)
    return r.json() as Promise<ChatMessage[]>
  },

  async deleteSession(id: string): Promise<void> {
    await fetchApi(`/chat/sessions/${id}`, { method: 'DELETE' })
  },

  // ---- Search ----
  async searchEntities(query: string, entityType?: string): Promise<EntitySearchResult> {
    const params = new URLSearchParams({ q: query })
    if (entityType) params.set('entity_type', entityType)
    const r = await fetchApi(`/graph/search?${params.toString()}`)
    return r.json() as Promise<EntitySearchResult>
  },
}
