import { getToken } from './keycloak'
import type { WebSocketMessage } from './types'

export type MessageHandler = (data: WebSocketMessage) => void

const MAX_RECONNECT_ATTEMPTS = 5

export class WebSocketManager {
  private ws: WebSocket | null = null
  private handlers: MessageHandler[] = []
  private reconnectAttempts = 0
  private shouldReconnect = true
  private sessionId: string | null = null
  private messageQueue: string[] = []

  connect(sessionId?: string): void {
    this.shouldReconnect = true
    this.sessionId = sessionId ?? null
    this.doConnect()
  }

  private doConnect(): void {
    if (this.ws) {
      this.ws.onclose = null
      this.ws.close()
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const token = getToken()
    let url = `${protocol}//${window.location.host}/ws/chat?token=${encodeURIComponent(token)}`
    if (this.sessionId) {
      url += `&session_id=${encodeURIComponent(this.sessionId)}`
    }

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      this.flushQueue()
    }

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string) as WebSocketMessage
        for (const handler of this.handlers) {
          handler(data)
        }
      } catch {
        // Ignore unparseable messages
      }
    }

    this.ws.onclose = () => {
      if (this.shouldReconnect && this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30_000)
        setTimeout(() => {
          this.reconnectAttempts++
          this.doConnect()
        }, delay)
      }
    }

    this.ws.onerror = () => {
      // onclose will fire after this
    }
  }

  /**
   * Send a message immediately if connected, otherwise queue it
   * to be flushed once the WebSocket opens.
   */
  sendOrQueue(content: string): void {
    const payload = JSON.stringify({ content })
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(payload)
    } else {
      this.messageQueue.push(payload)
    }
  }

  send(content: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ content }))
    }
  }

  private flushQueue(): void {
    while (this.messageQueue.length > 0) {
      const payload = this.messageQueue.shift()
      if (payload && this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(payload)
      }
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.push(handler)
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler)
    }
  }

  disconnect(): void {
    this.shouldReconnect = false
    this.messageQueue = []
    this.ws?.close()
    this.ws = null
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  getSessionId(): string | null {
    return this.sessionId
  }

  setSessionId(id: string): void {
    this.sessionId = id
  }
}
