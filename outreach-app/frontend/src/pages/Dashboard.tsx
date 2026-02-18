import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

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
}

export default function Dashboard() {
  const [mentions, setMentions] = useState<Mention[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadMentions = () => {
    fetch('/api/mentions?days=7&limit=20')
      .then((res) => res.json())
      .then((data) => setMentions(data.mentions || []))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    setLoading(true)
    loadMentions()
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
    fetch('/api/jobs/fetch-mentions', { method: 'POST' })
      .then((r) => r.json())
      .then(() => {
        let attempts = 0
        pollIntervalRef.current = setInterval(() => {
          attempts++
          loadMentions()
          if (attempts >= 6) {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
            pollIntervalRef.current = null
            setRefreshing(false)
          }
        }, 10000)
      })
      .catch((err) => {
        console.error(err)
        setRefreshing(false)
      })
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-slate-800">Dashboard</h1>

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
                    <Link
                      to={`/contacts/${m.contact_id}`}
                      className="font-medium text-slate-800 hover:text-slate-600"
                    >
                      {m.contact_name || `Contact #${m.contact_id}`}
                    </Link>
                    <p className="text-sm text-slate-600">{m.title || m.snippet?.slice(0, 100)}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {m.source_type} • {m.published_at ? new Date(m.published_at).toLocaleDateString() : 'Unknown date'}
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
        </div>
      </section>
    </div>
  )
}
