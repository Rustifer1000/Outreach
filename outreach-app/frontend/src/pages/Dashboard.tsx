import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api'

interface Mention {
  id: number
  contact_id: number
  contact_name?: string
  source_type: string
  source_url: string | null
  title: string | null
  snippet: string | null
  published_at: string | null
  created_at: string
  relevance_score: number | null
}

interface HotLead {
  contact_id: number
  contact_name?: string
  mention_count: number
  heat_score: number
  relationship_stage?: string
}

const SOURCE_COLORS: Record<string, string> = {
  news: 'bg-blue-100 text-blue-800',
  podcast: 'bg-purple-100 text-purple-800',
  video: 'bg-red-100 text-red-800',
  speech: 'bg-amber-100 text-amber-800',
}

export default function Dashboard() {
  const [mentions, setMentions] = useState<Mention[]>([])
  const [hotLeads, setHotLeads] = useState<HotLead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadMentions = () =>
    apiFetch<{ mentions: Mention[] }>('/api/mentions?days=7&limit=20')
      .then((data) => { setMentions(data.mentions || []); setError(null) })
      .catch((err) => setError(`Mentions: ${err.message}`))
      .finally(() => setLoading(false))

  const loadHotLeads = () =>
    apiFetch<{ hot_leads: HotLead[] }>('/api/digest/hot-leads?days=7&limit=5')
      .then((data) => setHotLeads(data.hot_leads || []))
      .catch((err) => console.warn('Hot leads unavailable:', err.message))

  useEffect(() => {
    setLoading(true)
    loadMentions()
    loadHotLeads()
  }, [])

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
    }
  }, [])

  const handleRefresh = () => {
    setRefreshing(true)
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
    const beforeCount = mentions.length
    apiFetch('/api/jobs/fetch-mentions', { method: 'POST' })
      .then(() => {
        let attempts = 0
        pollIntervalRef.current = setInterval(() => {
          attempts++
          apiFetch<{ mentions: Mention[] }>('/api/mentions?days=7&limit=20')
            .then((data) => {
              const newMentions = data.mentions || []
              setMentions(newMentions)
              if (newMentions.length !== beforeCount || attempts >= 6) {
                if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
                pollIntervalRef.current = null
                setRefreshing(false)
              }
            })
            .catch(() => {
              if (attempts >= 6) {
                if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
                pollIntervalRef.current = null
                setRefreshing(false)
              }
            })
        }, 10000)
      })
      .catch((err) => {
        setError(`Refresh failed: ${err.message}`)
        setRefreshing(false)
      })
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-slate-800">Dashboard</h1>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <section className="mb-8 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-700">
          Recent Mentions (Last 7 Days)
        </h2>
        {loading ? (
          <p className="text-slate-500">Loading...</p>
        ) : mentions.length === 0 ? (
          <p className="text-slate-500">
            No mentions yet. Run the mention monitoring job to populate.
          </p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {mentions.map((m) => (
              <li key={m.id} className="py-4">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <Link
                        to={`/contacts/${m.contact_id}`}
                        className="font-medium text-slate-800 hover:text-slate-600"
                      >
                        {m.contact_name || `Contact #${m.contact_id}`}
                      </Link>
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${SOURCE_COLORS[m.source_type] || 'bg-slate-100 text-slate-700'}`}>
                        {m.source_type}
                      </span>
                      {m.relevance_score != null && (
                        <span
                          title="Relevance score"
                          className={`inline-flex rounded-full px-1.5 py-0.5 text-xs font-medium ${
                            m.relevance_score >= 0.7 ? 'bg-green-100 text-green-800'
                              : m.relevance_score >= 0.4 ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-red-100 text-red-700'
                          }`}
                        >
                          {Math.round(m.relevance_score * 100)}%
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-600">{m.title || m.snippet?.slice(0, 100)}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {m.published_at ? new Date(m.published_at).toLocaleDateString() : 'Unknown date'}
                    </p>
                  </div>
                  {m.source_url && (
                    <a
                      href={m.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:underline"
                    >
                      View source
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {hotLeads.length > 0 && (
        <section className="mb-8 rounded-lg bg-white p-6 shadow">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-700">Hot Leads</h2>
            <Link to="/digest" className="text-sm text-slate-500 hover:text-slate-700">View full digest →</Link>
          </div>
          <div className="flex flex-wrap gap-3">
            {hotLeads.map((lead) => (
              <Link
                key={lead.contact_id}
                to={`/contacts/${lead.contact_id}`}
                className="flex items-center gap-2 rounded-lg border border-orange-200 bg-orange-50 px-4 py-3 hover:border-orange-300 hover:bg-orange-100"
              >
                <span className="font-medium text-slate-800">{lead.contact_name || `#${lead.contact_id}`}</span>
                <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                  lead.heat_score >= 0.7 ? 'bg-red-100 text-red-800' : lead.heat_score >= 0.4 ? 'bg-orange-100 text-orange-800' : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {Math.round(lead.heat_score * 100)}
                </span>
                <span className="text-xs text-slate-500">{lead.mention_count} mentions</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-700">Quick Actions</h2>
        <div className="flex flex-wrap gap-4">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="rounded-md bg-slate-600 px-4 py-2 text-white hover:bg-slate-500 disabled:opacity-50"
          >
            {refreshing ? 'Fetching... (updates every 10s)' : 'Refresh mentions now'}
          </button>
          <Link
            to="/contacts"
            className="rounded-md bg-slate-800 px-4 py-2 text-white hover:bg-slate-700"
          >
            Browse Contacts
          </Link>
          <Link
            to="/digest"
            className="rounded-md bg-orange-600 px-4 py-2 text-white hover:bg-orange-500"
          >
            Daily Digest
          </Link>
        </div>
      </section>
    </div>
  )
}
