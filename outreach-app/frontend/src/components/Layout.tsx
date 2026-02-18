import { Link } from 'react-router-dom'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
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
