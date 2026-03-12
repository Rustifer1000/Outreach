import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

interface DigestMention {
  id: number
  contact_id: number
  contact_name: string
  title: string | null
  snippet: string | null
  source_type: string
  source_url: string | null
  published_at: string | null
}

interface DigestCategory {
  category: string
  mention_count: number
  unique_contacts: number
  mentions: DigestMention[]
}

interface DigestData {
  period_days: number
  total_mentions: number
  total_contacts: number
  categories: DigestCategory[]
}

export default function Digest() {
  const [digest, setDigest] = useState<DigestData | null>(null)
  const [days, setDays] = useState(7)
  const [loading, setLoading] = useState(true)
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set())

  useEffect(() => {
    setLoading(true)
    fetch(`/api/digest?days=${days}`)
      .then((r) => r.ok ? r.json() : Promise.reject(new Error(`Error (${r.status})`)))
      .then(setDigest)
      .finally(() => setLoading(false))
  }, [days])

  const toggleCategory = (cat: string) => {
    setExpandedCats((prev) => {
      const next = new Set(prev)
      if (next.has(cat)) next.delete(cat); else next.add(cat)
      return next
    })
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-slate-800">Digest</h1>

      <div className="mb-6 flex items-center gap-4">
        <label className="text-sm font-medium text-slate-600">Period:</label>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="rounded border border-slate-300 px-3 py-1.5 text-sm">
          <option value={1}>Last 24 hours</option>
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
        </select>
      </div>

      {loading ? <p className="text-slate-500">Loading digest...</p> : !digest ? <p className="text-slate-500">Failed to load.</p> : (
        <>
          {/* Summary cards */}
          <div className="mb-6 grid grid-cols-3 gap-4">
            <div className="rounded-lg bg-white p-4 shadow text-center">
              <p className="text-3xl font-bold text-slate-800">{digest.total_mentions}</p>
              <p className="text-sm text-slate-500">Total Mentions</p>
            </div>
            <div className="rounded-lg bg-white p-4 shadow text-center">
              <p className="text-3xl font-bold text-blue-600">{digest.total_contacts}</p>
              <p className="text-sm text-slate-500">Contacts Mentioned</p>
            </div>
            <div className="rounded-lg bg-white p-4 shadow text-center">
              <p className="text-3xl font-bold text-green-600">{digest.categories.length}</p>
              <p className="text-sm text-slate-500">Categories</p>
            </div>
          </div>

          {/* Category breakdown */}
          {digest.categories.length === 0 ? (
            <p className="rounded-lg bg-white p-6 text-slate-500 shadow">No mentions in this period.</p>
          ) : (
            <div className="space-y-4">
              {digest.categories.map((cat) => (
                <section key={cat.category} className="rounded-lg bg-white shadow">
                  <button
                    onClick={() => toggleCategory(cat.category)}
                    className="flex w-full items-center justify-between px-6 py-4 text-left hover:bg-slate-50"
                  >
                    <div>
                      <span className="text-lg font-semibold text-slate-700">{cat.category}</span>
                      <span className="ml-3 text-sm text-slate-400">
                        {cat.mention_count} mentions from {cat.unique_contacts} contacts
                      </span>
                    </div>
                    <span className="text-slate-400">{expandedCats.has(cat.category) ? '\u25B2' : '\u25BC'}</span>
                  </button>
                  {expandedCats.has(cat.category) && (
                    <ul className="divide-y divide-slate-200 border-t border-slate-200">
                      {cat.mentions.map((m) => (
                        <li key={m.id} className="px-6 py-3">
                          <div className="flex items-start justify-between">
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2">
                                <Link to={`/contacts/${m.contact_id}`} className="font-medium text-slate-800 hover:text-slate-600">{m.contact_name}</Link>
                                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{m.source_type}</span>
                              </div>
                              <p className="mt-1 text-sm text-slate-700">{m.title || 'Untitled'}</p>
                              <p className="mt-1 text-xs text-slate-400">{m.published_at ? new Date(m.published_at).toLocaleDateString() : 'Unknown date'}</p>
                            </div>
                            {m.source_url && /^https?:\/\//i.test(m.source_url) && (
                              <a href={m.source_url} target="_blank" rel="noopener noreferrer" className="ml-4 shrink-0 text-xs text-blue-600 hover:underline">View</a>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
