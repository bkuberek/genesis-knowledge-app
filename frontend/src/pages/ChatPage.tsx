import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { api } from '../lib/api'
import { WebSocketManager } from '../lib/websocket'
import type { ChatSession, ChatMessage, WebSocketMessage } from '../lib/types'

/**
 * A pending message is one the user sent but hasn't been confirmed by the server yet.
 * It carries a local ID so we can match and promote it to confirmed messages.
 */
interface PendingMessage {
  localId: number
  role: 'user'
  content: string
  created_at: string
}

let nextLocalId = 1

function formatTimestamp(iso?: string): string {
  if (!iso) return ''
  try {
    const date = new Date(iso)
    return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [pendingMessages, setPendingMessages] = useState<PendingMessage[]>([])
  const [input, setInput] = useState('')
  const [isWaiting, setIsWaiting] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocketManager | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Load sessions on mount
  useEffect(() => {
    api.listSessions().then(setSessions).catch(console.error)
  }, [])

  // Scroll to bottom when messages or pending messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, pendingMessages])

  // Handle WebSocket messages — fixes the race condition
  const handleWsMessage = useCallback((data: WebSocketMessage) => {
    if (data.type === 'session' && data.session_id) {
      setActiveSessionId(data.session_id)

      // Convert server history to ChatMessage format
      const serverHistory: ChatMessage[] = (data.history ?? []).map((m) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
        created_at: m.created_at,
      }))

      // MERGE: set confirmed messages from server, but keep pending messages intact.
      // The pending messages render separately, so we don't lose the user's optimistic input.
      setMessages(serverHistory)

      // Refresh sessions list to pick up any newly-created session
      api.listSessions().then(setSessions).catch(console.error)
    } else if (data.type === 'title_updated' && data.session_id && data.title) {
      setSessions((prev) =>
        prev.map((s) =>
          s.id === data.session_id ? { ...s, title: data.title! } : s,
        ),
      )
    } else if (data.type === 'message' && data.content) {
      // When the assistant responds, promote the oldest pending user message
      // to confirmed messages and add the assistant response.
      setPendingMessages((prev) => {
        const oldest = prev[0]
        const remaining = prev.slice(1)

        // Promote the pending user message to confirmed
        if (oldest) {
          setMessages((confirmed) => [
            ...confirmed,
            { role: 'user', content: oldest.content, created_at: oldest.created_at },
            {
              role: (data.role ?? 'assistant') as 'user' | 'assistant',
              content: data.content!,
            },
          ])
        } else {
          // No pending message — just add the assistant response
          setMessages((confirmed) => [
            ...confirmed,
            {
              role: (data.role ?? 'assistant') as 'user' | 'assistant',
              content: data.content!,
            },
          ])
        }

        return remaining
      })

      setIsWaiting(false)
    }
  }, [])

  // Connect WebSocket for a session
  const connectToSession = useCallback(
    (sessionId?: string) => {
      if (wsRef.current) {
        wsRef.current.disconnect()
      }
      const ws = new WebSocketManager()
      wsRef.current = ws
      ws.onMessage(handleWsMessage)
      ws.connect(sessionId)
    },
    [handleWsMessage],
  )

  // Clean up on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.disconnect()
    }
  }, [])

  // Session switching — disconnect old WS, connect to new session
  const handleSelectSession = useCallback(
    (session: ChatSession) => {
      if (session.id === activeSessionId) return
      setMessages([])
      setPendingMessages([])
      setIsWaiting(false)
      connectToSession(session.id)
    },
    [activeSessionId, connectToSession],
  )

  const handleNewChat = useCallback(() => {
    setMessages([])
    setPendingMessages([])
    setActiveSessionId(null)
    setIsWaiting(false)
    if (wsRef.current) {
      wsRef.current.disconnect()
      wsRef.current = null
    }
  }, [])

  const handleDeleteSession = useCallback(
    async (sessionId: string) => {
      try {
        await api.deleteSession(sessionId)
        setSessions((prev) => prev.filter((s) => s.id !== sessionId))
        if (activeSessionId === sessionId) {
          setActiveSessionId(null)
          setMessages([])
          setPendingMessages([])
          wsRef.current?.disconnect()
          wsRef.current = null
        }
      } catch (err) {
        console.error('Failed to delete session:', err)
      }
    },
    [activeSessionId],
  )

  const handleSend = useCallback(() => {
    const content = input.trim()
    if (!content || isWaiting) return

    // Add to pending messages (optimistic UI)
    const pending: PendingMessage = {
      localId: nextLocalId++,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    setPendingMessages((prev) => [...prev, pending])
    setInput('')
    setIsWaiting(true)
    inputRef.current?.focus()

    // If no WebSocket connection, start one — message gets queued automatically
    if (!wsRef.current || !wsRef.current.isConnected()) {
      connectToSession()
      // Use sendOrQueue — it will buffer until WS opens, then flush
      // We need a short delay for the wsRef to be assigned
      requestAnimationFrame(() => {
        wsRef.current?.sendOrQueue(content)
      })
    } else {
      wsRef.current.sendOrQueue(content)
    }
  }, [input, isWaiting, connectToSession])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  // Auto-resize textarea
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    const textarea = e.target
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
  }, [])

  // Combined view: confirmed messages + pending (optimistic) messages
  const allMessages: Array<ChatMessage | PendingMessage> = [
    ...messages,
    ...pendingMessages,
  ]

  const activeSession = sessions.find((s) => s.id === activeSessionId)

  return (
    <div className="flex h-full">
      {/* Session sidebar */}
      {sidebarOpen && (
        <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-surface-raised">
          <div className="flex items-center justify-between px-4 py-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Sessions
            </span>
            <button
              onClick={handleNewChat}
              className="rounded-md bg-accent/15 px-2.5 py-1 text-xs font-medium text-accent transition-colors hover:bg-accent/25"
            >
              + New
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-2">
            {sessions.length === 0 && (
              <p className="px-2 py-4 text-center text-xs text-ink-muted">
                No conversations yet
              </p>
            )}
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`group mb-0.5 flex items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors cursor-pointer ${
                  activeSessionId === session.id
                    ? 'bg-accent/15 text-accent'
                    : 'text-ink-muted hover:bg-surface-overlay hover:text-ink'
                }`}
                onClick={() => handleSelectSession(session)}
              >
                <span className="truncate">{session.title}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDeleteSession(session.id).catch(console.error)
                  }}
                  className="ml-2 hidden shrink-0 rounded p-0.5 text-ink-muted opacity-0 transition-opacity hover:text-danger group-hover:opacity-100 group-hover:block"
                  aria-label="Delete session"
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 16 16"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <path d="M4 4l8 8M12 4l-8 8" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </aside>
      )}

      {/* Chat area */}
      <div className="flex flex-1 flex-col">
        {/* Top bar with sidebar toggle and session title */}
        <div className="flex h-10 shrink-0 items-center border-b border-border px-3">
          <button
            onClick={() => setSidebarOpen((p) => !p)}
            className="rounded p-1 text-ink-muted transition-colors hover:bg-surface-overlay hover:text-ink"
            aria-label="Toggle sidebar"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            >
              <path d="M2 4h12M2 8h12M2 12h12" />
            </svg>
          </button>
          {activeSession ? (
            <span className="ml-3 truncate text-xs text-ink-muted">
              {activeSession.title}
            </span>
          ) : null}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl px-4 py-6">
            {allMessages.length === 0 && !isWaiting && (
              <div className="flex flex-col items-center justify-center pt-24 text-center">
                <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent/10 text-accent">
                  <svg
                    width="32"
                    height="32"
                    viewBox="0 0 32 32"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <circle cx="16" cy="16" r="12" />
                    <path d="M12 16l3 3 5-6" />
                  </svg>
                </div>
                <h2 className="mb-2 text-lg font-semibold text-ink">
                  Ask your knowledge base
                </h2>
                <p className="max-w-sm text-sm leading-relaxed text-ink-muted">
                  Upload documents and ask questions. The AI will search your
                  extracted entities, relationships, and data to find answers.
                </p>
              </div>
            )}

            {allMessages.map((msg, idx) => {
              const isPending = 'localId' in msg
              const timestamp = formatTimestamp(msg.created_at)
              const isUser = msg.role === 'user'

              return (
                <div
                  key={isPending ? `pending-${msg.localId}` : `msg-${idx}`}
                  className={`mb-4 flex ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
                    <div
                      className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                        isUser
                          ? `bg-accent text-surface ${isPending ? 'opacity-70' : ''}`
                          : 'bg-surface-raised text-ink'
                      }`}
                    >
                      {msg.role === 'assistant' ? (
                        <div className="prose-chat">
                          <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                      ) : (
                        <span className="whitespace-pre-wrap">{msg.content}</span>
                      )}
                    </div>
                    {timestamp ? (
                      <div
                        className={`mt-1 text-[10px] text-ink-muted/60 ${
                          isUser ? 'text-right' : 'text-left'
                        }`}
                      >
                        {timestamp}
                      </div>
                    ) : null}
                  </div>
                </div>
              )
            })}

            {isWaiting && (
              <div className="mb-4 flex justify-start">
                <div className="flex gap-1.5 rounded-2xl bg-surface-raised px-5 py-4">
                  <span className="typing-dot h-2 w-2 rounded-full bg-ink-muted" />
                  <span className="typing-dot h-2 w-2 rounded-full bg-ink-muted" />
                  <span className="typing-dot h-2 w-2 rounded-full bg-ink-muted" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input area */}
        <div className="shrink-0 border-t border-border bg-surface-raised p-4">
          <div className="mx-auto flex max-w-3xl items-end gap-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Type a message..."
              rows={1}
              className="flex-1 resize-none rounded-xl border border-border bg-surface px-4 py-3 text-sm text-ink placeholder:text-ink-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              style={{ maxHeight: '120px' }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isWaiting}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent text-surface transition-colors hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="Send message"
            >
              <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
                <path d="M1 1l14 7-14 7V9l10-1-10-1V1z" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
