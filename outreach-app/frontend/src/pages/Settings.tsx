import { useEffect, useState } from 'react'

interface AppSettings {
  database_url: string
  environment: string
  debug: boolean
  api_keys: Record<string, string>
  api_key_status: Record<string, boolean>
}

export default function Settings() {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/settings')
      .then((r) => r.ok ? r.json() : Promise.reject(new Error(`Error (${r.status})`)))
      .then(setSettings)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-slate-500">Loading settings...</p>
  if (error) return <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
  if (!settings) return null

  const apiKeys = [
    { key: 'newsapi', label: 'NewsAPI', description: 'News mention monitoring', link: 'https://newsapi.org/register' },
    { key: 'hunter', label: 'Hunter.io', description: 'Contact enrichment (email, LinkedIn)', link: 'https://hunter.io/users/sign_up' },
    { key: 'mediacloud', label: 'MediaCloud', description: 'Academic media research', link: 'https://search.mediacloud.org/' },
  ]

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-slate-800">Settings</h1>

      {/* Environment */}
      <section className="mb-6 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-700">Environment</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-slate-500">Environment:</span>
            <span className="ml-2 font-medium text-slate-700">{settings.environment}</span>
          </div>
          <div>
            <span className="text-slate-500">Debug:</span>
            <span className={`ml-2 font-medium ${settings.debug ? 'text-yellow-600' : 'text-green-600'}`}>
              {settings.debug ? 'On' : 'Off'}
            </span>
          </div>
          <div className="col-span-2">
            <span className="text-slate-500">Database:</span>
            <span className="ml-2 font-mono text-xs text-slate-600">{settings.database_url}</span>
          </div>
        </div>
      </section>

      {/* API Keys */}
      <section className="mb-6 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-700">API Keys</h2>
        <p className="mb-4 text-sm text-slate-500">
          API keys are configured in the <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">.env</code> file in the backend directory.
        </p>
        <div className="space-y-4">
          {apiKeys.map((api) => (
            <div key={api.key} className="flex items-center justify-between rounded-lg border border-slate-200 p-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium text-slate-700">{api.label}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    settings.api_key_status[api.key]
                      ? 'bg-green-100 text-green-700'
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {settings.api_key_status[api.key] ? 'Configured' : 'Not Set'}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-500">{api.description}</p>
                {settings.api_key_status[api.key] && (
                  <p className="mt-1 font-mono text-xs text-slate-400">{settings.api_keys[api.key]}</p>
                )}
              </div>
              {!settings.api_key_status[api.key] && (
                <a
                  href={api.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
                >
                  Get Key
                </a>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Configuration Help */}
      <section className="rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-700">Configuration</h2>
        <div className="rounded bg-slate-50 p-4 font-mono text-sm text-slate-600">
          <p className="mb-2 font-sans text-slate-500">Add keys to <code>outreach-app/backend/.env</code>:</p>
          <pre className="whitespace-pre-wrap">{`DATABASE_URL=sqlite:///./outreach.db
NEWSAPI_KEY=your_newsapi_key_here
HUNTER_API_KEY=your_hunter_key_here
MEDIACLOUD_API_KEY=your_mediacloud_key_here
DEBUG=false
ENVIRONMENT=development`}</pre>
        </div>
      </section>
    </div>
  )
}
