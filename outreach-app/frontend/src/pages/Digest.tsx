import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api'

interface HotLead {
  contact_id: number
  contact_name?: string
  category?: string
  relationship_stage?: string
  mention_count: number
  avg_relevance: number
  source_type_count: number
  heat_score: number
}

interface FollowUp {
  contact_id: number
  contact_name: string
  last_method: string
  last_sent: string | null
  days_since: number
}

interface LowConfidence {
  mention_id: number
  contact_name: string
  title: string | null
  relevance_score: number
  source_type: string
}

interface DigestData {
  period_hours: number
  generated_at: string
  new_mentions: {
    total: number
    by_source_type: Record<string, number>
    by_category: Record<string, number>
    contacts_mentioned: number
  }
  hot_leads: HotLead[]
  follow_up_due: FollowUp[]
  low_confidence_mentions: LowConfidence[]
  summary: string
}

function HeatBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color =
    pct >= 70
      ? 'bg-red-100 text-red-800'
      : pct >= 40
        ? 'bg-orange-100 text-orange-800'
        : 'bg-yellow-100 text-yellow-800'
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${color}`}>{pct}</span>
}

function SourceBadge({ type }: { type: string }) {
  const color =
    type === 'news'
      ? 'bg-blue-100 text-blue-800'
      : type === 'podcast'
        ? 'bg-purple-100 text-purple-800'
        : type === 'video'
          ? 'bg-red-100 text-red-800'
          : type === 'speech'
            ? 'bg-amber-100 text-amber-800'
            : 'bg-slate-100 text-slate-700'
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>{type}</span>
}

export default function Digest() {
  const [digest, setDigest] = useState<DigestData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [scoring, setScoring] = useState(false)
  const [scoreMsg, setScoreMsg] = useState<string | null>(null)
  const [hours, setHours] = useState(24)
  const scorePollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (scorePollRef.current) clearInterval(scorePollRef.current)
    }
  }, [])

  const loadDigest = (h: number) => {
    setLoading(true)
    setError(null)
    apiFetch<DigestData>(`/api/digest/daily?hours=${h}`)
      .then((d) => setDigest(d))
      .catch((err) => {
        setDigest(null)
        setError(`Failed to load digest: ${err.message}`)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadDigest(hours)
  }, [hours])

  const handleScoreMentions = () => {
    setScoring(true)
    setScoreMsg(null)
    if (scorePollRef.current) {
      clearInterval(scorePollRef.current)
      scorePollRef.current = null
    }
    apiFetch('/api/digest/score-mentions', { method: 'POST' })
      .then(() => {
        setScoreMsg('Scoring...')
        scorePollRef.current = setInterval(() => {
          apiFetch<{ status: string; scored?: number }>('/api/digest/score-status')
            .then((s) => {
              if (s.status === 'complete') {
                if (scorePollRef.current) clearInterval(scorePollRef.current)
                scorePollRef.current = null
                setScoreMsg(`Done: ${s.scored} mentions scored`)
                setScoring(false)
                loadDigest(hours)
              }
            })
            .catch((err) => {
              if (scorePollRef.current) clearInterval(scorePollRef.current)
              scorePollRef.current = null
              setScoreMsg(`Score status check failed: ${err.message}`)
              setScoring(false)
            })
        }, 2000)
      })
      .catch((err) => {
        setScoreMsg(`Scoring failed: ${err.message}`)
        setScoring(false)
      })
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Daily Digest</h1>
        <div className="flex items-center gap-3">
          <select
            value={hours}
            onChange={(e) => setHours(parseInt(e.target.value))}
            className="rounded border border-slate-300 px-2 py-1 text-sm"
          >
            <option value={24}>Last 24 hours</option>
            <option value={48}>Last 48 hours</option>
            <option value={168}>Last 7 days</option>
          </select>
          <button
            type="button"
            onClick={handleScoreMentions}
            disabled={scoring}
            className="rounded border border-slate-400 bg-slate-50 px-3 py-1 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
          >
            {scoring ? 'Scoring...' : 'Re-score mentions'}
          </button>
          {scoreMsg && <span className="text-xs text-slate-500">{scoreMsg}</span>}
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-slate-500">Loading digest...</p>
      ) : !digest ? (
        <p className="text-slate-500">{error ? 'Could not load digest — see error above.' : 'No digest data available.'}</p>
      ) : (
        <div className="space-y-6">
          {/* Summary */}
          <div className="rounded-lg bg-gradient-to-r from-slate-700 to-slate-800 p-6 text-white shadow">
            <p className="text-lg font-medium">{digest.summary}</p>
            <p className="mt-1 text-sm text-slate-300">
              Generated {new Date(digest.generated_at).toLocaleString()}
            </p>
          </div>

          {/* New mentions breakdown */}
          <div className="rounded-lg bg-white p-6 shadow">
            <h2 className="mb-3 text-lg font-semibold text-slate-800">New Mentions</h2>
            {digest.new_mentions.total === 0 ? (
              <p className="text-slate-500">No new mentions in this period.</p>
            ) : (
              <div className="flex flex-wrap gap-4">
                <div className="rounded-lg border border-slate-200 px-4 py-3">
                  <p className="text-2xl font-bold text-slate-800">{digest.new_mentions.total}</p>
                  <p className="text-xs text-slate-500">Total mentions</p>
                </div>
                <div className="rounded-lg border border-slate-200 px-4 py-3">
                  <p className="text-2xl font-bold text-slate-800">{digest.new_mentions.contacts_mentioned}</p>
                  <p className="text-xs text-slate-500">Contacts mentioned</p>
                </div>
                {Object.entries(digest.new_mentions.by_source_type).map(([type, count]) => (
                  <div key={type} className="rounded-lg border border-slate-200 px-4 py-3">
                    <div className="flex items-center gap-2">
                      <p className="text-2xl font-bold text-slate-800">{count}</p>
                      <SourceBadge type={type} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* By Category */}
          {digest.new_mentions.total > 0 && Object.keys(digest.new_mentions.by_category).length > 0 && (
            <div className="rounded-lg bg-white p-6 shadow">
              <h2 className="mb-3 text-lg font-semibold text-slate-800">Mentions by Category</h2>
              <div className="flex flex-wrap gap-3">
                {Object.entries(digest.new_mentions.by_category).map(([cat, count]) => (
                  <div key={cat} className="rounded-lg border border-slate-200 px-4 py-3">
                    <p className="text-xl font-bold text-slate-800">{count}</p>
                    <p className="mt-0.5 text-xs text-slate-500">{cat.replace(/^Category \d+: /, '')}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Hot Leads */}
          <div className="rounded-lg bg-white p-6 shadow">
            <h2 className="mb-3 text-lg font-semibold text-slate-800">Hot Leads</h2>
            {digest.hot_leads.length === 0 ? (
              <p className="text-slate-500">No hot leads right now. Mentions need scoring first — use the button above.</p>
            ) : (
              <div className="overflow-hidden rounded border border-slate-200">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Contact</th>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Heat</th>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Mentions</th>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Avg Score</th>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Sources</th>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-slate-500">Stage</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {digest.hot_leads.map((lead) => (
                      <tr key={lead.contact_id} className="hover:bg-slate-50">
                        <td className="px-4 py-3">
                          <Link to={`/contacts/${lead.contact_id}`} className="font-medium text-slate-800 hover:text-slate-600">
                            {lead.contact_name || `#${lead.contact_id}`}
                          </Link>
                          {lead.category && (
                            <p className="text-xs text-slate-500">{lead.category.replace(/^Category \d+: /, '')}</p>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <HeatBadge score={lead.heat_score} />
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-700">{lead.mention_count}</td>
                        <td className="px-4 py-3 text-sm text-slate-700">{Math.round(lead.avg_relevance * 100)}%</td>
                        <td className="px-4 py-3 text-sm text-slate-700">{lead.source_type_count} types</td>
                        <td className="px-4 py-3">
                          {lead.relationship_stage ? (
                            <span className="text-xs text-slate-600">{lead.relationship_stage}</span>
                          ) : (
                            <span className="text-xs text-slate-400">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Follow-ups Due */}
          <div className="rounded-lg bg-white p-6 shadow">
            <h2 className="mb-3 text-lg font-semibold text-slate-800">Follow-ups Due</h2>
            {digest.follow_up_due.length === 0 ? (
              <p className="text-slate-500">No follow-ups due. All caught up!</p>
            ) : (
              <ul className="divide-y divide-slate-200">
                {digest.follow_up_due.map((f) => (
                  <li key={f.contact_id} className="flex items-center justify-between py-3">
                    <div>
                      <Link to={`/contacts/${f.contact_id}`} className="font-medium text-slate-800 hover:text-slate-600">
                        {f.contact_name}
                      </Link>
                      <p className="text-sm text-slate-500">
                        Last: {f.last_method} {f.last_sent ? `on ${new Date(f.last_sent).toLocaleDateString()}` : ''}
                      </p>
                    </div>
                    <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
                      {f.days_since}d ago
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Low Confidence Mentions */}
          {digest.low_confidence_mentions.length > 0 && (
            <div className="rounded-lg bg-white p-6 shadow">
              <h2 className="mb-3 text-lg font-semibold text-slate-800">Low-Confidence Mentions (Review)</h2>
              <p className="mb-3 text-sm text-slate-500">
                These mentions scored low on disambiguation — they may be about a different person with the same name.
              </p>
              <ul className="divide-y divide-slate-200">
                {digest.low_confidence_mentions.map((m) => (
                  <li key={m.mention_id} className="flex items-center justify-between py-3">
                    <div>
                      <p className="text-sm font-medium text-slate-700">{m.title || 'Untitled'}</p>
                      <p className="text-xs text-slate-500">
                        {m.contact_name} — <SourceBadge type={m.source_type} />
                      </p>
                    </div>
                    <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                      {Math.round(m.relevance_score * 100)}%
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
