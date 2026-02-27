import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const [refreshing, setRefreshing] = useState(false)
  const [discovering, setDiscovering] = useState(false)
  const [toast, setToast] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  const showToast = (type: 'ok' | 'err', text: string) => {
    setToast({ type, text })
    setTimeout(() => setToast(null), 5000)
  }

  const handleRefreshMentions = () => {
    if (refreshing) return
    setRefreshing(true)
    apiFetch('/api/jobs/fetch-mentions', { method: 'POST' })
      .then(() => showToast('ok', 'Mention fetch started. Check Dashboard in a few minutes.'))
      .catch((err) => showToast('err', `Refresh failed: ${err.message}`))
      .finally(() => setRefreshing(false))
  }

  const handleDiscoverConnections = () => {
    if (discovering) return
    setDiscovering(true)
    apiFetch('/api/jobs/discover-all-connections', { method: 'POST' })
      .then(() => showToast('ok', 'Discovering all connections. Check Map in 2–3 min.'))
      .catch((err) => showToast('err', `Discovery failed: ${err.message}`))
      .finally(() => setDiscovering(false))
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="bg-slate-800 text-white shadow">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-8">
              <Link to="/" className="text-xl font-semibold">
                Solomon Outreach
              </Link>
              <Link to="/" className="text-slate-300 hover:text-white">
                Dashboard
              </Link>
              <Link to="/contacts" className="text-slate-300 hover:text-white">
                Contacts
              </Link>
              <Link to="/rotation" className="text-slate-300 hover:text-white">
                Rotation
              </Link>
              <Link to="/map" className="text-slate-300 hover:text-white">
                Map
              </Link>
              <Link to="/digest" className="text-slate-300 hover:text-white">
                Digest
              </Link>
              <Link to="/names-file" className="text-slate-300 hover:text-white">
                Names file
              </Link>
              <button
                type="button"
                onClick={handleRefreshMentions}
                disabled={refreshing}
                className="rounded bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
              >
                {refreshing ? 'Starting…' : 'Refresh mentions'}
              </button>
              <button
                type="button"
                onClick={handleDiscoverConnections}
                disabled={discovering}
                className="rounded bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-50"
              >
                {discovering ? 'Starting…' : 'Discover connections'}
              </button>
            </div>
          </div>
        </div>
      </nav>

      {toast && (
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div
            className={`mt-2 rounded-lg px-4 py-3 text-sm shadow ${
              toast.type === 'ok'
                ? 'bg-green-50 text-green-800 border border-green-200'
                : 'bg-red-50 text-red-800 border border-red-200'
            }`}
          >
            <div className="flex items-center justify-between">
              <span>{toast.text}</span>
              <button type="button" onClick={() => setToast(null)} className="ml-4 text-xs opacity-60 hover:opacity-100">
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  )
}
