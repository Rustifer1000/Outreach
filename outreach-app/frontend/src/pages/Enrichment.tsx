import { useCallback, useEffect, useRef, useState } from 'react'

interface EnrichmentSummary {
  total: number
  enriched: number
  failed: number
  pending: number
  with_email: number
  with_linkedin: number
}

interface EnrichmentStatus {
  running: boolean
  progress: string
  enriched: number
  total_contacts: number
  processed: number
  error: string | null
}

export default function Enrichment() {
  const [summary, setSummary] = useState<EnrichmentSummary | null>(null)
  const [status, setStatus] = useState<EnrichmentStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadSummary = useCallback(() => {
    fetch('/api/enrichment/summary')
      .then((r) => r.ok ? r.json() : Promise.reject(new Error(`Error (${r.status})`)))
      .then(setSummary)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { loadSummary() }, [loadSummary])
  useEffect(() => { return () => { if (pollRef.current) clearInterval(pollRef.current) } }, [])

  const startPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(() => {
      fetch('/api/enrichment/status')
        .then((r) => r.json())
        .then((s: EnrichmentStatus) => {
          setStatus(s)
          if (!s.running) {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            loadSummary()
          }
        })
        .catch(() => {})
    }, 2000)
  }

  const triggerEnrichment = () => {
    fetch('/api/enrichment/run', { method: 'POST' })
      .then((r) => r.json())
      .then((data) => {
        if (data.status === 'already_running') {
          setStatus({ running: true, progress: data.progress, enriched: 0, total_contacts: 0, processed: 0, error: null })
        } else {
          setStatus({ running: true, progress: 'Starting...', enriched: 0, total_contacts: 0, processed: 0, error: null })
        }
        startPolling()
      })
      .catch((err) => setError(err.message))
  }

  const isRunning = status?.running ?? false

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-slate-800">Contact Enrichment</h1>

      {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}

      {/* Summary cards */}
      {loading ? <p className="text-slate-500">Loading...</p> : summary && (
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {[
            { label: 'Total Contacts', value: summary.total, color: 'text-slate-800' },
            { label: 'Enriched', value: summary.enriched, color: 'text-green-600' },
            { label: 'Failed', value: summary.failed, color: 'text-red-600' },
            { label: 'Pending', value: summary.pending, color: 'text-yellow-600' },
            { label: 'With Email', value: summary.with_email, color: 'text-blue-600' },
            { label: 'With LinkedIn', value: summary.with_linkedin, color: 'text-blue-600' },
          ].map((card) => (
            <div key={card.label} className="rounded-lg bg-white p-4 shadow">
              <p className="text-sm text-slate-500">{card.label}</p>
              <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Coverage bar */}
      {summary && summary.total > 0 && (
        <section className="mb-6 rounded-lg bg-white p-6 shadow">
          <h2 className="mb-3 text-lg font-semibold text-slate-700">Enrichment Coverage</h2>
          <div className="h-4 w-full rounded-full bg-slate-200">
            <div
              className="h-4 rounded-full bg-green-500 transition-all"
              style={{ width: `${(summary.enriched / summary.total) * 100}%` }}
            />
          </div>
          <p className="mt-2 text-sm text-slate-500">
            {Math.round((summary.enriched / summary.total) * 100)}% of contacts enriched
          </p>
        </section>
      )}

      {/* Action */}
      <section className="mb-6 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-700">Run Enrichment</h2>
        <p className="mb-4 text-sm text-slate-500">
          Enrichment uses the Hunter.io API to find email addresses and LinkedIn profiles for contacts that haven't been enriched yet.
        </p>
        <button
          onClick={triggerEnrichment}
          disabled={isRunning}
          className="rounded-md bg-slate-800 px-5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isRunning ? 'Enriching...' : 'Enrich All Pending Contacts'}
        </button>

        {status && (
          <div className="mt-4">
            {status.error ? (
              <p className="text-sm text-red-600">{status.error}</p>
            ) : (
              <div>
                <p className="text-sm text-slate-600">{status.progress}</p>
                {status.running && status.total_contacts > 0 && (
                  <div className="mt-2 h-2 w-full rounded-full bg-slate-200">
                    <div className="h-2 rounded-full bg-slate-600 transition-all" style={{ width: `${(status.processed / status.total_contacts) * 100}%` }} />
                  </div>
                )}
                {!status.running && status.enriched > 0 && (
                  <p className="mt-1 text-sm font-medium text-green-600">Enriched {status.enriched} contacts</p>
                )}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  )
}
