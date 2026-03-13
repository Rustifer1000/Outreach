import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

interface Mention {
  id: number
  contact_id: number
  contact_name?: string
  source_type: string
  source_name: string | null
  source_url: string | null
  title: string | null
  snippet: string | null
  published_at: string | null
  created_at: string
}

interface FetchStatus {
  running: boolean
  progress: string
  added: number
  total_contacts: number
  processed: number
  error: string | null
}

function escapeHtml(str: string) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function highlightName(snippet: string, name: string): string {
  const safe = escapeHtml(snippet)
  if (!name) return safe
  // Highlight full name, then last name
  const names = [name]
  const parts = name.split(' ')
  if (parts.length > 1) names.push(parts[parts.length - 1])
  let result = safe
  for (const n of names) {
    const escaped = n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const re = new RegExp(`(${escaped})`, 'gi')
    if (re.test(result)) {
      result = result.replace(re, '<mark class="bg-yellow-200 rounded px-0.5">$1</mark>')
      break
    }
  }
  return result
}

export default function Mentions() {
  const [mentions, setMentions] = useState<Mention[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(0)
  const [days, setDays] = useState(30)
  const limit = 50

  // Fetch trigger state
  const [fetchStatus, setFetchStatus] = useState<FetchStatus | null>(null)
  const [fetchDays, setFetchDays] = useState(7)
  const [fetchLimit, setFetchLimit] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadMentions = useCallback(() => {
    setLoading(true)
    setError(null)
    fetch(`/api/mentions?days=${days}&limit=${limit}&skip=${page * limit}&max_per_contact=5`)
      .then((res) => {
        if (!res.ok) throw new Error(`Server error (${res.status})`)
        return res.json()
      })
      .then((data) => {
        setMentions(data.mentions || [])
        setTotal(data.total || 0)
      })
      .catch((err) => {
        setError(err.message)
      })
      .finally(() => setLoading(false))
  }, [days, page])

  useEffect(() => {
    loadMentions()
  }, [loadMentions])

  // Poll for fetch status while running
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const startPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(() => {
      fetch('/api/mentions/fetch/status')
        .then((r) => r.json())
        .then((status: FetchStatus) => {
          setFetchStatus(status)
          if (!status.running) {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            loadMentions()
          }
        })
        .catch(() => {})
    }, 2000)
  }

  const triggerFetch = () => {
    const params = new URLSearchParams({ days: String(fetchDays) })
    if (fetchLimit) params.set('limit', fetchLimit)
    fetch(`/api/mentions/fetch?${params}`, { method: 'POST' })
      .then((r) => { if (!r.ok) throw new Error(`Server error (${r.status})`); return r.json() })
      .then((data) => {
        if (data.status === 'already_running') {
          setFetchStatus({ running: true, progress: data.progress, added: 0, total_contacts: 0, processed: 0, error: null })
        } else {
          setFetchStatus({ running: true, progress: 'Starting...', added: 0, total_contacts: 0, processed: 0, error: null })
        }
        startPolling()
      })
      .catch((err) => setError(err.message))
  }

  const totalPages = Math.ceil(total / limit)

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-slate-800">Mentions</h1>

      {/* Fetch Controls */}
      <section className="mb-6 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-700">Fetch New Mentions</h2>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-600">Look-back days</label>
            <input
              type="number"
              min={1}
              max={90}
              value={fetchDays}
              onChange={(e) => setFetchDays(Number(e.target.value))}
              className="mt-1 w-24 rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600">
              Contact limit <span className="text-slate-400">(blank = all)</span>
            </label>
            <input
              type="number"
              min={1}
              value={fetchLimit}
              onChange={(e) => setFetchLimit(e.target.value)}
              placeholder="All"
              className="mt-1 w-24 rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <button
            onClick={triggerFetch}
            disabled={fetchStatus?.running}
            className="rounded-md bg-slate-800 px-5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {fetchStatus?.running ? 'Fetching...' : 'Fetch Mentions'}
          </button>
        </div>

        {/* Status bar */}
        {fetchStatus && (
          <div className="mt-4">
            {fetchStatus.error ? (
              <p className="text-sm text-red-600">{fetchStatus.error}</p>
            ) : (
              <div>
                <p className="text-sm text-slate-600">{fetchStatus.progress}</p>
                {fetchStatus.running && fetchStatus.total_contacts > 0 && (
                  <div className="mt-2 h-2 w-full rounded-full bg-slate-200">
                    <div
                      className="h-2 rounded-full bg-slate-600 transition-all"
                      style={{ width: `${(fetchStatus.processed / fetchStatus.total_contacts) * 100}%` }}
                    />
                  </div>
                )}
                {!fetchStatus.running && fetchStatus.added > 0 && (
                  <p className="mt-1 text-sm font-medium text-green-600">
                    Added {fetchStatus.added} new mentions
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </section>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {error}
        </div>
      )}

      {/* Filter */}
      <div className="mb-4 flex items-center gap-4">
        <label className="text-sm font-medium text-slate-600">Show mentions from last</label>
        <select
          value={days}
          onChange={(e) => { setDays(Number(e.target.value)); setPage(0) }}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm"
        >
          <option value={7}>7 days</option>
          <option value={14}>14 days</option>
          <option value={30}>30 days</option>
          <option value={60}>60 days</option>
          <option value={90}>90 days</option>
        </select>
        <span className="text-sm text-slate-400">{total} mentions</span>
      </div>

      {/* Mentions List */}
      <section className="rounded-lg bg-white shadow">
        {loading ? (
          <p className="p-6 text-slate-500">Loading...</p>
        ) : mentions.length === 0 ? (
          <p className="p-6 text-slate-500">
            No mentions found. Use the button above to fetch mentions from NewsAPI.
          </p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {mentions.map((m) => (
              <li key={m.id} className="px-6 py-4">
                {/* Row 1: Contact name + media badge + date */}
                <div className="flex items-center gap-2">
                  <Link
                    to={`/contacts/${m.contact_id}`}
                    className="font-medium text-slate-800 hover:text-slate-600"
                  >
                    {m.contact_name || `Contact #${m.contact_id}`}
                  </Link>
                  {m.source_name && (
                    <span className="rounded bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                      {m.source_name}
                    </span>
                  )}
                  {!m.source_name && (
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                      {m.source_type}
                    </span>
                  )}
                  <span className="text-xs text-slate-400">
                    {m.published_at
                      ? new Date(m.published_at).toLocaleDateString()
                      : 'Unknown date'}
                  </span>
                </div>

                {/* Row 2: Headline as link to source */}
                <p className="mt-1 text-sm font-semibold text-slate-700">
                  {m.source_url && /^https?:\/\//i.test(m.source_url) ? (
                    <a
                      href={m.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-blue-600 hover:underline"
                    >
                      {m.title || 'Untitled'}
                    </a>
                  ) : (
                    m.title || 'Untitled'
                  )}
                </p>

                {/* Row 3: Mention excerpt with contact name highlighted */}
                {m.snippet && (
                  <p
                    className="mt-1.5 rounded bg-slate-50 px-3 py-2 text-sm text-slate-600 line-clamp-3"
                    dangerouslySetInnerHTML={{
                      __html: highlightName(m.snippet, m.contact_name || ''),
                    }}
                  />
                )}
              </li>
            ))}
          </ul>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-200 px-6 py-3">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded border border-slate-300 px-3 py-1 text-sm disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-sm text-slate-500">
              Page {page + 1} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="rounded border border-slate-300 px-3 py-1 text-sm disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </section>
    </div>
  )
}
