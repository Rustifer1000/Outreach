import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

interface NoteEntry {
  id: number
  contact_id: number
  contact_name?: string
  note_text: string
  channel: string | null
  note_date: string | null
  created_at: string
}

const CHANNELS = ['email', 'linkedin', 'phone', 'meeting', 'other']

export default function Notes() {
  const [notes, setNotes] = useState<NoteEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const limit = 50

  // Form
  const [showForm, setShowForm] = useState(false)
  const [contacts, setContacts] = useState<{ id: number; name: string }[]>([])
  const [contactSearch, setContactSearch] = useState('')
  const [formData, setFormData] = useState({ contact_id: '', note_text: '', channel: 'meeting' })

  const loadNotes = useCallback(() => {
    setLoading(true)
    fetch(`/api/notes?limit=${limit}&skip=${page * limit}`)
      .then((r) => r.ok ? r.json() : Promise.reject(new Error(`Error (${r.status})`)))
      .then((data) => { setNotes(data.notes || []); setTotal(data.total || 0) })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [page])

  useEffect(() => { loadNotes() }, [loadNotes])

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

  const submitNote = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.contact_id || !formData.note_text.trim()) return
    fetch('/api/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contact_id: Number(formData.contact_id),
        note_text: formData.note_text,
        channel: formData.channel || null,
        note_date: new Date().toISOString(),
      }),
    })
      .then((r) => { if (!r.ok) throw new Error(`Error (${r.status})`); return r.json() })
      .then(() => {
        setShowForm(false)
        setFormData({ contact_id: '', note_text: '', channel: 'meeting' })
        setContactSearch('')
        loadNotes()
      })
      .catch((err) => setError(err.message))
  }

  const deleteNote = (id: number) => {
    if (!confirm('Delete this note?')) return
    fetch(`/api/notes/${id}`, { method: 'DELETE' })
      .then((r) => { if (r.ok) loadNotes(); else setError(`Delete failed (${r.status})`) })
      .catch((err) => setError(err.message))
  }

  const totalPages = Math.ceil(total / limit)

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Conversation Notes</h1>
        <button onClick={() => setShowForm(!showForm)} className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700">
          {showForm ? 'Cancel' : 'Add Note'}
        </button>
      </div>

      {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}

      {showForm && (
        <section className="mb-6 rounded-lg bg-white p-6 shadow">
          <form onSubmit={submitNote} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-600">Contact</label>
              <input type="text" value={contactSearch} onChange={(e) => setContactSearch(e.target.value)} placeholder="Search..." className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" />
              {contacts.length > 0 && (
                <ul className="mt-1 max-h-40 overflow-y-auto rounded border border-slate-200 bg-white">
                  {contacts.map((c) => (
                    <li key={c.id} onClick={() => { setFormData({ ...formData, contact_id: String(c.id) }); setContactSearch(c.name); setContacts([]) }} className="cursor-pointer px-3 py-2 text-sm hover:bg-slate-50">{c.name}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600">Channel</label>
              <select value={formData.channel} onChange={(e) => setFormData({ ...formData, channel: e.target.value })} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm">
                {CHANNELS.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600">Note</label>
              <textarea value={formData.note_text} onChange={(e) => setFormData({ ...formData, note_text: e.target.value })} rows={4} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <button type="submit" disabled={!formData.contact_id || !formData.note_text.trim()} className="rounded-md bg-slate-800 px-5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50">Save Note</button>
          </form>
        </section>
      )}

      <section className="rounded-lg bg-white shadow">
        {loading ? <p className="p-6 text-slate-500">Loading...</p> : notes.length === 0 ? <p className="p-6 text-slate-500">No notes yet.</p> : (
          <ul className="divide-y divide-slate-200">
            {notes.map((n) => (
              <li key={n.id} className="px-6 py-4">
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <Link to={`/contacts/${n.contact_id}`} className="font-medium text-slate-800 hover:text-slate-600">{n.contact_name || `Contact #${n.contact_id}`}</Link>
                      {n.channel && <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{n.channel}</span>}
                    </div>
                    <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{n.note_text}</p>
                    <p className="mt-1 text-xs text-slate-400">{n.note_date ? new Date(n.note_date).toLocaleDateString() : 'No date'}</p>
                  </div>
                  <button onClick={() => deleteNote(n.id)} className="ml-4 text-xs text-slate-400 hover:text-red-500">delete</button>
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
