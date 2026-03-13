import { useEffect, useState } from 'react'

interface FunnelData {
  total_contacts: number
  contacted: number
  replied: number
  stages: Record<string, number>
}

interface CategoryConversion {
  category: string
  total: number
  contacted: number
  replied: number
  contact_rate: number
  reply_rate: number
}

interface ChannelData {
  method: string
  total_sent: number
  replied: number
  response_rate: number
}

interface LagData {
  average_lag_days: number | null
  median_lag_days: number | null
  within_48h_pct: number | null
  sample_size: number
}

interface ActivityWeek {
  week: string
  mentions: number
  outreaches: number
}

export default function Analytics() {
  const [funnel, setFunnel] = useState<FunnelData | null>(null)
  const [categories, setCategories] = useState<CategoryConversion[]>([])
  const [channels, setChannels] = useState<ChannelData[]>([])
  const [lag, setLag] = useState<LagData | null>(null)
  const [activity, setActivity] = useState<ActivityWeek[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const safeFetch = (url: string) =>
      fetch(url).then((r) => {
        if (!r.ok) throw new Error(`${url} returned ${r.status}`)
        return r.json()
      })

    Promise.all([
      safeFetch('/api/analytics/funnel'),
      safeFetch('/api/analytics/conversion'),
      safeFetch('/api/analytics/channel-effectiveness'),
      safeFetch('/api/analytics/mention-lag'),
      safeFetch('/api/analytics/activity?days=90'),
    ])
      .then(([f, conv, ch, l, act]) => {
        setFunnel(f)
        setCategories(conv.categories || [])
        setChannels(ch.channels || [])
        setLag(l)
        setActivity(act.timeline || [])
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-slate-500">Loading analytics...</p>
  if (error) return <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>

  const stageLabels = ['cold', 'warm', 'engaged', 'partner']
  const stageColors: Record<string, string> = { cold: 'bg-slate-400', warm: 'bg-yellow-400', engaged: 'bg-blue-500', partner: 'bg-green-500' }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-slate-800">Analytics</h1>

      {/* Funnel */}
      {funnel && (
        <section className="mb-6 rounded-lg bg-white p-6 shadow">
          <h2 className="mb-4 text-lg font-semibold text-slate-700">Outreach Funnel</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="text-center">
              <p className="text-3xl font-bold text-slate-800">{funnel.total_contacts}</p>
              <p className="text-sm text-slate-500">Total Contacts</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-blue-600">{funnel.contacted}</p>
              <p className="text-sm text-slate-500">Contacted</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-green-600">{funnel.replied}</p>
              <p className="text-sm text-slate-500">Replied</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-purple-600">{funnel.stages?.partner || 0}</p>
              <p className="text-sm text-slate-500">Partners</p>
            </div>
          </div>

          <div className="mt-6">
            <h3 className="mb-2 text-sm font-medium text-slate-600">Relationship Stages</h3>
            <div className="flex h-6 w-full overflow-hidden rounded-full bg-slate-100">
              {stageLabels.map((stage) => {
                const count = funnel.stages?.[stage] || 0
                const pct = funnel.total_contacts ? (count / funnel.total_contacts) * 100 : 0
                return pct > 0 ? (
                  <div key={stage} className={`${stageColors[stage]} transition-all`} style={{ width: `${pct}%` }} title={`${stage}: ${count}`} />
                ) : null
              })}
            </div>
            <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-500">
              {stageLabels.map((stage) => (
                <span key={stage} className="flex items-center gap-1">
                  <span className={`inline-block h-2 w-2 rounded-full ${stageColors[stage]}`} />
                  {stage}: {funnel.stages?.[stage] || 0}
                </span>
              ))}
            </div>
          </div>
        </section>
      )}

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        {/* Channel Effectiveness */}
        <section className="rounded-lg bg-white p-6 shadow">
          <h2 className="mb-4 text-lg font-semibold text-slate-700">Channel Effectiveness</h2>
          {channels.length === 0 ? <p className="text-sm text-slate-500">No outreach data yet.</p> : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="pb-2">Channel</th>
                  <th className="pb-2">Sent</th>
                  <th className="pb-2">Replied</th>
                  <th className="pb-2">Rate</th>
                </tr>
              </thead>
              <tbody>
                {channels.map((ch) => (
                  <tr key={ch.method} className="border-b border-slate-100">
                    <td className="py-2 font-medium text-slate-700">{ch.method}</td>
                    <td className="py-2 text-slate-600">{ch.total_sent}</td>
                    <td className="py-2 text-slate-600">{ch.replied}</td>
                    <td className="py-2 font-medium text-green-600">{ch.response_rate}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        {/* Mention-to-Contact Lag */}
        <section className="rounded-lg bg-white p-6 shadow">
          <h2 className="mb-4 text-lg font-semibold text-slate-700">Mention-to-Contact Lag</h2>
          {!lag || lag.sample_size === 0 ? <p className="text-sm text-slate-500">Not enough data yet. Log outreach after mentions to see lag metrics.</p> : (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-2xl font-bold text-slate-800">{lag.average_lag_days} days</p>
                <p className="text-sm text-slate-500">Average Lag</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">{lag.median_lag_days} days</p>
                <p className="text-sm text-slate-500">Median Lag</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-600">{lag.within_48h_pct}%</p>
                <p className="text-sm text-slate-500">Within 48h</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-600">{lag.sample_size}</p>
                <p className="text-sm text-slate-500">Sample Size</p>
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Conversion by Category */}
      <section className="mb-6 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-700">Conversion by Category</h2>
        {categories.length === 0 ? <p className="text-sm text-slate-500">No category data yet.</p> : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="pb-2">Category</th>
                <th className="pb-2">Total</th>
                <th className="pb-2">Contacted</th>
                <th className="pb-2">Replied</th>
                <th className="pb-2">Contact Rate</th>
                <th className="pb-2">Reply Rate</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((c) => (
                <tr key={c.category} className="border-b border-slate-100">
                  <td className="py-2 font-medium text-slate-700">{c.category}</td>
                  <td className="py-2 text-slate-600">{c.total}</td>
                  <td className="py-2 text-slate-600">{c.contacted}</td>
                  <td className="py-2 text-slate-600">{c.replied}</td>
                  <td className="py-2 text-blue-600">{c.contact_rate}%</td>
                  <td className="py-2 font-medium text-green-600">{c.reply_rate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Activity Timeline */}
      {activity.length > 0 && (
        <section className="rounded-lg bg-white p-6 shadow">
          <h2 className="mb-4 text-lg font-semibold text-slate-700">Weekly Activity (Last 90 Days)</h2>
          <div className="overflow-x-auto">
            <div className="flex items-end gap-1" style={{ minWidth: activity.length * 60 }}>
              {activity.map((w) => {
                const maxVal = Math.max(...activity.map((a) => Math.max(a.mentions, a.outreaches)), 1)
                return (
                  <div key={w.week} className="flex flex-col items-center gap-1" style={{ width: 50 }}>
                    <div className="flex items-end gap-0.5" style={{ height: 80 }}>
                      <div className="w-5 rounded-t bg-blue-400" style={{ height: `${(w.mentions / maxVal) * 80}px` }} title={`${w.mentions} mentions`} />
                      <div className="w-5 rounded-t bg-green-400" style={{ height: `${(w.outreaches / maxVal) * 80}px` }} title={`${w.outreaches} outreaches`} />
                    </div>
                    <span className="text-xs text-slate-400">{w.week.split('-W')[1]}</span>
                  </div>
                )
              })}
            </div>
            <div className="mt-3 flex gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded bg-blue-400" /> Mentions</span>
              <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded bg-green-400" /> Outreaches</span>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
