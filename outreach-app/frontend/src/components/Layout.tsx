import { useState } from 'react'
import { Link } from 'react-router-dom'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const [moreOpen, setMoreOpen] = useState(false)

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="bg-slate-800 text-white shadow">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-6">
              <Link to="/" className="text-xl font-semibold">
                Solomon Outreach
              </Link>
              <Link to="/" className="text-slate-300 hover:text-white text-sm">
                Dashboard
              </Link>
              <Link to="/mentions" className="text-slate-300 hover:text-white text-sm">
                Mentions
              </Link>
              <Link to="/rotation" className="text-slate-300 hover:text-white text-sm">
                Rotation
              </Link>
              <Link to="/outreach" className="text-slate-300 hover:text-white text-sm">
                Outreach
              </Link>
              <Link to="/contacts" className="text-slate-300 hover:text-white text-sm">
                Contacts
              </Link>
              <Link to="/analytics" className="text-slate-300 hover:text-white text-sm">
                Analytics
              </Link>
              <div className="relative">
                <button
                  onClick={() => setMoreOpen(!moreOpen)}
                  onBlur={() => setTimeout(() => setMoreOpen(false), 150)}
                  className="text-slate-300 hover:text-white text-sm"
                >
                  More &#9662;
                </button>
                {moreOpen && (
                  <div className="absolute left-0 top-full mt-1 w-44 rounded-md bg-white py-1 shadow-lg z-50">
                    <Link to="/notes" className="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">Notes</Link>
                    <Link to="/network" className="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">Network</Link>
                    <Link to="/enrichment" className="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">Enrichment</Link>
                    <Link to="/templates" className="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">Templates</Link>
                    <Link to="/digest" className="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">Digest</Link>
                    <div className="my-1 border-t border-slate-200" />
                    <Link to="/settings" className="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-100">Settings</Link>
                  </div>
                )}
              </div>
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
