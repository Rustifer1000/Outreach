import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

interface OutreachEntry {
  id: number
  contact_id: number
  contact_name?: string
  method: string
  subject: string | null
  content: string | null
  sent_at: string | null
  response_status: string | null
  created_at: string
}

interface ContactOption {
  id: number
  name: string
}

const METHODS = ['email', 'linkedin', 'twitter', 'phone', 'website', 'other']
const STATUSES = ['sent', 'replied', 'no_response', 'bounced']

export default function Outreach() {
  const [entries, setEntries] = useState<OutreachEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const limit = 50

  // Form state
  const [showForm, setShowForm] = useState(false)
  const [contacts, setContacts] = useState<ContactOption[]>([])
  const [contactSearch, setContactSearch] = useState('')
  const [formData, setFormData] = useState({
    contact_id: '',
    method: 'email',
    subject: '',
    content: '',
    response_status: 'sent',
  })

  const loadEntries = useCallback(() => {
    setLoading(true)
    fetch(`/api/outreach?limit=${limit}&skip=${page * limit}`)
      .then((r) => r.ok ? r.json() : Promise.reject(new Error(`Server error (${r.status})`)))
      .then((data) => {
        setEntries(data.entries || [])
        setTotal(data.total || 0)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [page])

  useEffect(() => { loadEntries() }, [loadEntries])

  // Search contacts for the form
  useEffect(() => {
    if (!contactSearch) { setContacts([]); return }
    const timer = setTimeout(() => {
      fetch(`/api/contacts?q=${encodeURIComponent(contactSearch)}&limit=10`)
        .then((r) => r.json())
        .then((data) => setContacts(data.contacts?.map((c: { id: number; name: string }) => ({ id: c.id, name: c.name })) || []))
        .catch(() => {})
    }, 300)
    return () => clearTimeout(timer)
  }, [contactSearch])

  const submitOutreach = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.contact_id) return
    fetch('/api/outreach', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contact_id: Number(formData.contact_id),
        method: formData.method,
        subject: formData.subject || null,
        content: formData.content || null,
        sent_at: new Date().toISOString(),
        response_status: formData.response_status,
      }),
    })
      .then((r) => {
        if (!r.ok) throw new Error(`Error (${r.status})`)
        return r.json()
      })
      .then(() => {
        setShowForm(false)
        setFormData({ contact_id: '', method: 'email', subject: '', content: '', response_status: 'sent' })
        setContactSearch('')
        loadEntries()
      })
      .catch((err) => setError(err.message))
  }

  const updateStatus = (id: number, status: string) => {
    fetch(`/api/outreach/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ response_status: status }),
    })
      .then((r) => { if (r.ok) loadEntries() })
      .catch(() => {})
  }

  const totalPages = Math.ceil(total / limit)

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Outreach Log</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          {showForm ? 'Cancel' : 'Log Outreach'}
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
      )}

      {/* Compose Form */}
      {showForm && (
        <section className="mb-6 rounded-lg bg-white p-6 shadow">
          <h2 className="mb-4 text-lg font-semibold text-slate-700">New Outreach Entry</h2>
          <form onSubmit={submitOutreach} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-600">Contact</label>
              <input
                type="text"
                value={contactSearch}
                onChange={(e) => setContactSearch(e.target.value)}
                placeholder="Search by name..."
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
              {contacts.length > 0 && (
                <ul className="mt-1 max-h-40 overflow-y-auto rounded border border-slate-200 bg-white">
                  {contacts.map((c) => (
                    <li
                      key={c.id}
                      onClick={() => {
                        setFormData({ ...formData, contact_id: String(c.id) })
                        setContactSearch(c.name)
                        setContacts([])
                      }}
                      className="cursor-pointer px-3 py-2 text-sm hover:bg-slate-50"
                    >
                      {c.name}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-600">Method</label>
                <select
                  value={formData.method}
                  onChange={(e) => setFormData({ ...formData, method: e.target.value })}
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                >
                  {METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-600">Status</label>
                <select
                  value={formData.response_status}
                  onChange={(e) => setFormData({ ...formData, response_status: e.target.value })}
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
                >
                  {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600">Subject</label>
              <input
                type="text"
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600">Content</label>
              <textarea
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                rows={4}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={!formData.contact_id}
              className="rounded-md bg-slate-800 px-5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              Save Entry
            </button>
          </form>
        </section>
      )}

      {/* Entries list */}
      <section className="rounded-lg bg-white shadow">
        {loading ? (
          <p className="p-6 text-slate-500">Loading...</p>
        ) : entries.length === 0 ? (
          <p className="p-6 text-slate-500">No outreach logged yet.</p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {entries.map((e) => (
              <li key={e.id} className="px-6 py-4">
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <Link
                        to={`/contacts/${e.contact_id}`}
                        className="font-medium text-slate-800 hover:text-slate-600"
                      >
                        {e.contact_name || `Contact #${e.contact_id}`}
                      </Link>
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{e.method}</span>
                      <select
                        value={e.response_status || 'sent'}
                        onChange={(ev) => updateStatus(e.id, ev.target.value)}
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          e.response_status === 'replied' ? 'bg-green-100 text-green-700' :
                          e.response_status === 'bounced' ? 'bg-red-100 text-red-700' :
                          e.response_status === 'no_response' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-blue-100 text-blue-700'
                        }`}
                      >
                        {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </div>
                    {e.subject && <p className="mt-1 text-sm text-slate-700">{e.subject}</p>}
                    {e.content && <p className="mt-1 text-sm text-slate-500 line-clamp-2">{e.content}</p>}
                    <p className="mt-1 text-xs text-slate-400">
                      {e.sent_at ? new Date(e.sent_at).toLocaleDateString() : 'No date'}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-200 px-6 py-3">
            <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} className="rounded border border-slate-300 px-3 py-1 text-sm disabled:opacity-50">Previous</button>
            <span className="text-sm text-slate-500">Page {page + 1} of {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1} className="rounded border border-slate-300 px-3 py-1 text-sm disabled:opacity-50">Next</button>
          </div>
        )}
      </section>
    </div>
  )
}
