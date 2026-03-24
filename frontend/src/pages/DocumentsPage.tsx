import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../lib/api'
import type { DocumentResponse } from '../lib/types'

const POLL_INTERVAL_MS = 5_000

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  queued: { bg: 'bg-yellow-500/15', text: 'text-yellow-400', label: 'Queued' },
  processing: { bg: 'bg-accent/15', text: 'text-accent', label: 'Processing' },
  complete: { bg: 'bg-success/15', text: 'text-success', label: 'Complete' },
  error: { bg: 'bg-danger/15', text: 'text-danger', label: 'Error' },
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadDocuments = useCallback(async () => {
    try {
      const data = await api.listDocuments()
      setDocuments(data.documents)
    } catch (err) {
      console.error('Failed to load documents:', err)
    }
  }, [])

  // Initial load
  useEffect(() => {
    loadDocuments().catch(console.error)
  }, [loadDocuments])

  // Poll for status updates when any document is processing
  useEffect(() => {
    const hasProcessing = documents.some(
      (d) => d.status === 'queued' || d.status === 'processing',
    )

    if (hasProcessing && !pollRef.current) {
      pollRef.current = setInterval(() => {
        loadDocuments().catch(console.error)
      }, POLL_INTERVAL_MS)
    } else if (!hasProcessing && pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [documents, loadDocuments])

  const handleUpload = useCallback(
    async (files: FileList) => {
      setError(null)
      setUploading(true)
      try {
        for (const file of Array.from(files)) {
          await api.uploadDocument(file)
        }
        await loadDocuments()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed')
      } finally {
        setUploading(false)
      }
    },
    [loadDocuments],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      if (e.dataTransfer.files.length > 0) {
        handleUpload(e.dataTransfer.files).catch(console.error)
      }
    },
    [handleUpload],
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        handleUpload(e.target.files).catch(console.error)
      }
    },
    [handleUpload],
  )

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-6 py-8">
        <h2 className="mb-6 text-xl font-semibold text-ink">Documents</h2>

        {/* Upload area */}
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          className={`mb-8 flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 transition-colors ${
            isDragging
              ? 'border-accent bg-accent/5'
              : 'border-border hover:border-ink-muted hover:bg-surface-raised/50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.csv,.docx,.txt"
            onChange={handleFileInput}
            className="hidden"
          />
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-accent/10 text-accent">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          {uploading ? (
            <p className="text-sm text-ink-muted">Uploading...</p>
          ) : (
            <>
              <p className="text-sm font-medium text-ink">
                Drop files here or click to upload
              </p>
              <p className="mt-1 text-xs text-ink-muted">
                PDF, CSV, DOCX, or TXT files
              </p>
            </>
          )}
        </div>

        {error && (
          <div className="mb-6 rounded-lg bg-danger/10 px-4 py-3 text-sm text-danger">
            {error}
          </div>
        )}

        {/* Document list */}
        {documents.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-sm text-ink-muted">
              No documents uploaded yet. Drop a file above to get started.
            </p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface-raised">
                  <th className="px-4 py-3 text-left font-medium text-ink-muted">
                    Filename
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-ink-muted">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-ink-muted">
                    Stage
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-ink-muted">
                    Uploaded
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {documents.map((doc) => {
                  const style = STATUS_STYLES[doc.status] ?? STATUS_STYLES['queued']!
                  return (
                    <tr key={doc.id} className="transition-colors hover:bg-surface-raised/50">
                      <td className="px-4 py-3 font-medium text-ink">
                        {doc.filename}
                        {doc.error_message && (
                          <p className="mt-0.5 text-xs text-danger">
                            {doc.error_message}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}
                        >
                          {style.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-ink-muted">
                        {doc.status === 'processing' ? (
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 w-20 overflow-hidden rounded-full bg-surface-overlay">
                              <div
                                className="h-full rounded-full bg-accent transition-all"
                                style={{ width: `${(doc.stage / 5) * 100}%` }}
                              />
                            </div>
                            <span className="text-xs">{doc.stage}/5</span>
                          </div>
                        ) : doc.status === 'complete' ? (
                          <span className="text-xs">5/5</span>
                        ) : (
                          <span className="text-xs">{doc.stage}/5</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-ink-muted">
                        {formatDate(doc.created_at)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}
