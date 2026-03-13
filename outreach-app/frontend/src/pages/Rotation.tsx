import { useCallback, useEffect, useRef, useState } from 'react'

interface ContactSummary {
  total: number
  min_list_number: number
  max_list_number: number
}

interface Batch {
  start: number
  end: number
  label: string
}

interface FetchStatus {
  running: boolean
  progress: string
  added: number
  total_contacts: number
  processed: number
  error: string | null
}

interface RunRecord {
  batch: Batch
  timestamp: string
  added: number
}

const BATCH_SIZES = [10, 25, 50, 100]

export default function Rotation() {
  const [summary, setSummary] = useState<ContactSummary | null>(null)
  const [batchSize, setBatchSize] = useState(25)
  const [batches, setBatches] = useState<Batch[]>([])
  const [selectedBatch, setSelectedBatch] = useState<number | null>(null)
  const [customStart, setCustomStart] = useState('')
  const [customEnd, setCustomEnd] = useState('')
  const [fetchDays, setFetchDays] = useState(7)
  const [fetchStatus, setFetchStatus] = useState<FetchStatus | null>(null)
  const [runHistory, setRunHistory] = useState<RunRecord[]>(() => {
    try {
      return JSON.parse(localStorage.getItem('rotation_history') || '[]')
    } catch {
      return []
    }
  })
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const activeBatchRef = useRef<Batch | null>(null)

  // Load contact summary
  useEffect(() => {
    fetch('/api/contacts/summary')
      .then((r) => {
        if (!r.ok) throw new Error(`Server error (${r.status})`)
        return r.json()
      })
      .then((data: ContactSummary) => {
        setSummary(data)
      })
      .catch((err) => setError(err.message))
  }, [])

  // Build batches when summary or batchSize changes
  useEffect(() => {
    if (!summary) return
    const built: Batch[] = []
    const min = summary.min_list_number
    const max = summary.max_list_number
    for (let start = min; start <= max; start += batchSize) {
      const end = Math.min(start + batchSize - 1, max)
      built.push({ start, end, label: `#${start} - #${end}` })
    }
    setBatches(built)
    setSelectedBatch(null)
  }, [summary, batchSize])

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const saveHistory = useCallback((record: RunRecord) => {
    setRunHistory((prev) => {
      const updated = [record, ...prev].slice(0, 20)
      localStorage.setItem('rotation_history', JSON.stringify(updated))
      return updated
    })
  }, [])

  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(() => {
      fetch('/api/mentions/fetch/status')
        .then((r) => r.json())
        .then((status: FetchStatus) => {
          setFetchStatus(status)
          if (!status.running) {
            if (pollRef.current) clearInterval(pollRef.current)
            pollRef.current = null
            if (activeBatchRef.current) {
              saveHistory({
                batch: activeBatchRef.current,
                timestamp: new Date().toISOString(),
                added: status.added,
              })
              activeBatchRef.current = null
            }
          }
        })
        .catch(() => {})
    }, 2000)
  }, [saveHistory])

  const runBatch = (batch: Batch) => {
    const params = new URLSearchParams({
      days: String(fetchDays),
      start_list_number: String(batch.start),
      end_list_number: String(batch.end),
    })
    activeBatchRef.current = batch
    fetch(`/api/mentions/fetch?${params}`, { method: 'POST' })
      .then((r) => { if (!r.ok) throw new Error(`Server error (${r.status})`); return r.json() })
      .then((data) => {
        if (data.status === 'already_running') {
          setFetchStatus({
            running: true, progress: data.progress,
            added: 0, total_contacts: 0, processed: 0, error: null,
          })
        } else {
          setFetchStatus({
            running: true, progress: `Starting batch ${batch.label}...`,
            added: 0, total_contacts: 0, processed: 0, error: null,
          })
        }
        startPolling()
      })
      .catch((err) => setError(err.message))
  }

  const runCustomRange = () => {
    const start = parseInt(customStart)
    const end = parseInt(customEnd)
    if (isNaN(start) || isNaN(end) || start > end || start < 1) {
      setError('Enter a valid range (start must be <= end)')
      return
    }
    setError(null)
    runBatch({ start, end, label: `#${start} - #${end}` })
  }

  const runNextBatch = () => {
    if (batches.length === 0) return
    // Find the batch after the most recently run one
    const lastRun = runHistory[0]
    if (!lastRun) {
      runBatch(batches[0])
      return
    }
    const lastIndex = batches.findIndex(
      (b) => b.start === lastRun.batch.start && b.end === lastRun.batch.end
    )
    const nextIndex = (lastIndex + 1) % batches.length
    runBatch(batches[nextIndex])
  }

  const isRunning = fetchStatus?.running ?? false

  // Figure out which batch was last run for highlighting
  const lastRunBatch = runHistory[0]?.batch

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-slate-800">Rotation</h1>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-400 hover:text-red-600">dismiss</button>
        </div>
      )}

      {/* Config row */}
      <section className="mb-6 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-700">Batch Configuration</h2>
        <div className="flex flex-wrap items-end gap-6">
          <div>
            <label className="block text-sm font-medium text-slate-600">Batch size</label>
            <select
              value={batchSize}
              onChange={(e) => setBatchSize(Number(e.target.value))}
              className="mt-1 rounded border border-slate-300 px-3 py-2 text-sm"
            >
              {BATCH_SIZES.map((s) => (
                <option key={s} value={s}>{s} contacts per batch</option>
              ))}
            </select>
          </div>
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
          <button
            onClick={runNextBatch}
            disabled={isRunning || batches.length === 0}
            className="rounded-md bg-slate-800 px-5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isRunning ? 'Running...' : 'Run Next Batch'}
          </button>
          {summary && (
            <span className="text-sm text-slate-400">
              {summary.total} contacts (#{summary.min_list_number} - #{summary.max_list_number})
            </span>
          )}
        </div>
      </section>

      {/* Progress */}
      {fetchStatus && (fetchStatus.running || fetchStatus.error || fetchStatus.added > 0) && (
        <section className="mb-6 rounded-lg bg-white p-6 shadow">
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
        </section>
      )}

      {/* Batch grid */}
      <section className="mb-6 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-700">Select a Batch</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {batches.map((batch, i) => {
            const isSelected = selectedBatch === i
            const wasLastRun = lastRunBatch && lastRunBatch.start === batch.start && lastRunBatch.end === batch.end
            return (
              <button
                key={i}
                onClick={() => setSelectedBatch(isSelected ? null : i)}
                className={`rounded-lg border-2 px-4 py-3 text-sm font-medium transition-colors ${
                  isSelected
                    ? 'border-slate-800 bg-slate-800 text-white'
                    : wasLastRun
                    ? 'border-green-300 bg-green-50 text-green-700 hover:border-green-400'
                    : 'border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-400'
                }`}
              >
                {batch.label}
                {wasLastRun && <span className="mt-1 block text-xs opacity-75">Last run</span>}
              </button>
            )
          })}
        </div>

        {selectedBatch !== null && (
          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={() => runBatch(batches[selectedBatch])}
              disabled={isRunning}
              className="rounded-md bg-slate-800 px-5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isRunning ? 'Running...' : `Fetch Mentions for ${batches[selectedBatch].label}`}
            </button>
          </div>
        )}
      </section>

      {/* Custom range */}
      <section className="mb-6 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-700">Custom Range</h2>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-600">Start #</label>
            <input
              type="number"
              min={1}
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              placeholder="1"
              className="mt-1 w-24 rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600">End #</label>
            <input
              type="number"
              min={1}
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              placeholder="25"
              className="mt-1 w-24 rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <button
            onClick={runCustomRange}
            disabled={isRunning}
            className="rounded-md bg-slate-800 px-5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isRunning ? 'Running...' : 'Fetch Custom Range'}
          </button>
        </div>
      </section>

      {/* Run history */}
      {runHistory.length > 0 && (
        <section className="rounded-lg bg-white p-6 shadow">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-700">Run History</h2>
            <button
              onClick={() => {
                setRunHistory([])
                localStorage.removeItem('rotation_history')
              }}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              Clear
            </button>
          </div>
          <ul className="divide-y divide-slate-200">
            {runHistory.map((record, i) => (
              <li key={i} className="flex items-center justify-between py-3">
                <div>
                  <span className="font-medium text-slate-700">{record.batch.label}</span>
                  <span className="ml-3 text-sm text-slate-400">
                    {new Date(record.timestamp).toLocaleString()}
                  </span>
                </div>
                <span className="text-sm text-green-600">+{record.added} mentions</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
