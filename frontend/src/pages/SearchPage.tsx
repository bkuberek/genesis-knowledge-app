import { useState, useCallback, useRef } from 'react'
import { api } from '../lib/api'
import type { EntityResponse } from '../lib/types'

const ENTITY_TYPE_COLORS: Record<string, string> = {
  company: 'bg-blue-500/15 text-blue-400',
  person: 'bg-purple-500/15 text-purple-400',
  technology: 'bg-emerald-500/15 text-emerald-400',
  industry: 'bg-amber-500/15 text-amber-400',
  location: 'bg-rose-500/15 text-rose-400',
}

const DEFAULT_TYPE_COLOR = 'bg-slate-500/15 text-slate-400'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [results, setResults] = useState<EntityResponse[]>([])
  const [total, setTotal] = useState(0)
  const [searched, setSearched] = useState(false)
  const [loading, setLoading] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const doSearch = useCallback(
    async (q: string, entityType: string) => {
      if (!q.trim()) {
        setResults([])
        setTotal(0)
        setSearched(false)
        return
      }
      setLoading(true)
      try {
        const data = await api.searchEntities(q, entityType || undefined)
        setResults(data.entities)
        setTotal(data.total)
        setSearched(true)
      } catch (err) {
        console.error('Search failed:', err)
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  const handleQueryChange = useCallback(
    (value: string) => {
      setQuery(value)
      if (debounceRef.current) clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(() => {
        doSearch(value, typeFilter).catch(console.error)
      }, 300)
    },
    [doSearch, typeFilter],
  )

  const handleTypeChange = useCallback(
    (value: string) => {
      setTypeFilter(value)
      if (query.trim()) {
        doSearch(query, value).catch(console.error)
      }
    },
    [doSearch, query],
  )

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault()
      doSearch(query, typeFilter).catch(console.error)
    },
    [doSearch, query, typeFilter],
  )

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-6 py-8">
        <h2 className="mb-6 text-xl font-semibold text-ink">Search Entities</h2>

        {/* Search form */}
        <form onSubmit={handleSubmit} className="mb-8 flex gap-3">
          <div className="relative flex-1">
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-muted"
            >
              <circle cx="7" cy="7" r="4" />
              <path d="M14 14l-3-3" />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => handleQueryChange(e.target.value)}
              placeholder="Search by name, type, or properties..."
              className="w-full rounded-xl border border-border bg-surface py-3 pl-10 pr-4 text-sm text-ink placeholder:text-ink-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>
          <select
            value={typeFilter}
            onChange={(e) => handleTypeChange(e.target.value)}
            className="rounded-xl border border-border bg-surface px-4 py-3 text-sm text-ink focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          >
            <option value="">All types</option>
            <option value="company">Company</option>
            <option value="person">Person</option>
            <option value="technology">Technology</option>
            <option value="industry">Industry</option>
            <option value="location">Location</option>
          </select>
          <button
            type="submit"
            className="rounded-xl bg-accent px-6 py-3 text-sm font-medium text-surface transition-colors hover:bg-accent-hover"
          >
            Search
          </button>
        </form>

        {/* Loading */}
        {loading && (
          <div className="flex justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          </div>
        )}

        {/* Results */}
        {!loading && searched && results.length === 0 && (
          <div className="py-12 text-center">
            <p className="text-sm text-ink-muted">
              No entities found matching &ldquo;{query}&rdquo;
            </p>
          </div>
        )}

        {!loading && results.length > 0 && (
          <>
            <p className="mb-4 text-xs text-ink-muted">
              {total} {total === 1 ? 'result' : 'results'} found
            </p>
            <div className="space-y-3">
              {results.map((entity) => {
                const colorClass =
                  ENTITY_TYPE_COLORS[entity.type.toLowerCase()] ?? DEFAULT_TYPE_COLOR
                const isExpanded = expandedId === entity.id
                const propertyEntries = Object.entries(entity.properties)

                return (
                  <div
                    key={entity.id}
                    className="rounded-xl border border-border bg-surface-raised transition-colors hover:border-ink-muted/30"
                  >
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : entity.id)}
                      className="flex w-full items-center gap-4 px-5 py-4 text-left"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-semibold text-ink">
                            {entity.name}
                          </span>
                          <span
                            className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${colorClass}`}
                          >
                            {entity.type}
                          </span>
                        </div>
                        {propertyEntries.length > 0 && !isExpanded && (
                          <p className="mt-1 truncate text-xs text-ink-muted">
                            {propertyEntries
                              .slice(0, 3)
                              .map(([k, v]) => `${k}: ${String(v)}`)
                              .join(' / ')}
                          </p>
                        )}
                      </div>
                      <span className="text-xs text-ink-muted">
                        {entity.source_count} source{entity.source_count !== 1 ? 's' : ''}
                      </span>
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 16 16"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        className={`shrink-0 text-ink-muted transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                      >
                        <path d="M4 6l4 4 4-4" />
                      </svg>
                    </button>

                    {isExpanded && propertyEntries.length > 0 && (
                      <div className="border-t border-border px-5 py-4">
                        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                          {propertyEntries.map(([key, value]) => (
                            <div key={key} className="flex gap-2">
                              <dt className="font-medium text-ink-muted">{key}:</dt>
                              <dd className="text-ink">{String(value)}</dd>
                            </div>
                          ))}
                        </dl>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </>
        )}

        {/* Empty state */}
        {!searched && !loading && (
          <div className="flex flex-col items-center py-16 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-accent/10 text-accent">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </div>
            <h3 className="mb-2 font-semibold text-ink">Explore your knowledge graph</h3>
            <p className="max-w-sm text-sm text-ink-muted">
              Search for entities extracted from your documents by name, type, or
              properties.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
