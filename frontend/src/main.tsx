import { StrictMode, useState, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { initKeycloak } from './lib/keycloak'
import App from './App'
import './index.css'

function Bootstrap() {
  const [ready, setReady] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    initKeycloak()
      .then((authenticated) => {
        if (authenticated) {
          setReady(true)
        } else {
          setError('Authentication failed. Please try again.')
        }
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : 'Unknown error'
        setError(`Failed to initialize authentication: ${message}`)
      })
  }, [])

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <div className="max-w-md rounded-xl bg-surface-raised p-8 text-center shadow-xl">
          <div className="mb-4 text-4xl">!</div>
          <h1 className="mb-2 text-lg font-semibold text-ink">Authentication Error</h1>
          <p className="text-sm text-ink-muted">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 rounded-lg bg-accent px-6 py-2 text-sm font-medium text-surface transition-colors hover:bg-accent-hover"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <div className="text-center">
          <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          <p className="text-sm text-ink-muted">Connecting...</p>
        </div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <App />
    </BrowserRouter>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Bootstrap />
  </StrictMode>,
)
