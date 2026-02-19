import { Link } from 'react-router-dom'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const handleRefreshMentions = () => {
    fetch('/api/jobs/fetch-mentions', { method: 'POST' })
      .then((r) => r.json())
      .then(() => alert('Mention fetch started. Check Dashboard in a few minutes.'))
      .catch((err) => {
        console.error(err)
        alert('Refresh failed. Check console.')
      })
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
              <Link to="/names-file" className="text-slate-300 hover:text-white">
                Names file
              </Link>
              <button
                type="button"
                onClick={handleRefreshMentions}
                className="rounded bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500"
              >
                Refresh mentions
              </button>
              <button
                type="button"
                onClick={() => {
                  fetch('/api/jobs/discover-all-connections', { method: 'POST' })
                    .then((r) => r.json())
                    .then(() => alert('Discovering all connections. Check Map in 2–3 min.'))
                    .catch((err) => { console.error(err); alert('Failed.') })
                }}
                className="rounded bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-500"
              >
                Discover connections
              </button>
            </div>
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  )
}
