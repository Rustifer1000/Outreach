import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

interface Connection {
  id: number
  contact_a_id: number
  contact_a_name: string
  contact_b_id: number
  contact_b_name: string
  connection_type: string
  notes: string | null
  created_at: string
}

interface WarmIntro {
  intro_contact_id: number
  intro_contact_name: string
  relationship_stage: string | null
  connection_type: string
  notes: string | null
}

const CONNECTION_TYPES = ['shared_org', 'coauthor', 'panel', 'advisor', 'colleague', 'mentor', 'collaborator', 'other']

export default function Network() {
  const [connections, setConnections] = useState<Connection[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Form
  const [showForm, setShowForm] = useState(false)
  const [searchA, setSearchA] = useState('')
  const [searchB, setSearchB] = useState('')
  const [contactsA, setContactsA] = useState<{ id: number; name: string }[]>([])
  const [contactsB, setContactsB] = useState<{ id: number; name: string }[]>([])
  const [formData, setFormData] = useState({ contact_a_id: '', contact_b_id: '', connection_type: 'shared_org', notes: '' })

  // Warm intro
  const [introSearch, setIntroSearch] = useState('')
  const [introContacts, setIntroContacts] = useState<{ id: number; name: string }[]>([])
  const [introTargetId, setIntroTargetId] = useState<number | null>(null)
  const [introTargetName, setIntroTargetName] = useState('')
  const [warmIntros, setWarmIntros] = useState<WarmIntro[]>([])

  const loadConnections = useCallback(() => {
    setLoading(true)
    fetch('/api/network?limit=100')
      .then((r) => r.ok ? r.json() : Promise.reject(new Error(`Error (${r.status})`)))
      .then((data) => { setConnections(data.connections || []); setTotal(data.total || 0) })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { loadConnections() }, [loadConnections])

  const searchContacts = (q: string, setter: (v: { id: number; name: string }[]) => void) => {
    if (!q) { setter([]); return }
    fetch(`/api/contacts?q=${encodeURIComponent(q)}&limit=10`)
      .then((r) => r.json())
      .then((data) => setter(data.contacts?.map((c: { id: number; name: string }) => ({ id: c.id, name: c.name })) || []))
      .catch(() => {})
  }

  useEffect(() => { const t = setTimeout(() => searchContacts(searchA, setContactsA), 300); return () => clearTimeout(t) }, [searchA])
  useEffect(() => { const t = setTimeout(() => searchContacts(searchB, setContactsB), 300); return () => clearTimeout(t) }, [searchB])
  useEffect(() => { const t = setTimeout(() => searchContacts(introSearch, setIntroContacts), 300); return () => clearTimeout(t) }, [introSearch])

  const submitConnection = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.contact_a_id || !formData.contact_b_id) return
    fetch('/api/network', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contact_a_id: Number(formData.contact_a_id),
        contact_b_id: Number(formData.contact_b_id),
        connection_type: formData.connection_type,
        notes: formData.notes || null,
      }),
    })
      .then((r) => { if (!r.ok) throw new Error(`Error (${r.status})`); return r.json() })
      .then(() => {
        setShowForm(false)
        setFormData({ contact_a_id: '', contact_b_id: '', connection_type: 'shared_org', notes: '' })
        setSearchA(''); setSearchB('')
        loadConnections()
      })
      .catch((err) => setError(err.message))
  }

  const deleteConnection = (id: number) => {
    fetch(`/api/network/${id}`, { method: 'DELETE' }).then((r) => { if (r.ok) loadConnections() })
  }

  const findWarmIntros = () => {
    if (!introTargetId) return
    fetch(`/api/network/warm-intros/${introTargetId}`)
      .then((r) => r.ok ? r.json() : Promise.reject(new Error(`Error (${r.status})`)))
      .then((data) => setWarmIntros(data.intros || []))
      .catch((err) => setError(err.message))
  }

  const stageColors: Record<string, string> = { partner: 'text-green-600', engaged: 'text-blue-600', warm: 'text-yellow-600', cold: 'text-slate-400' }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Network</h1>
        <button onClick={() => setShowForm(!showForm)} className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700">
          {showForm ? 'Cancel' : 'Add Connection'}
        </button>
      </div>

      {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}

      {/* Add connection form */}
      {showForm && (
        <section className="mb-6 rounded-lg bg-white p-6 shadow">
          <form onSubmit={submitConnection} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-600">Contact A</label>
                <input type="text" value={searchA} onChange={(e) => setSearchA(e.target.value)} placeholder="Search..." className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" />
                {contactsA.length > 0 && (
                  <ul className="mt-1 max-h-40 overflow-y-auto rounded border border-slate-200 bg-white">
                    {contactsA.map((c) => (
                      <li key={c.id} onClick={() => { setFormData({ ...formData, contact_a_id: String(c.id) }); setSearchA(c.name); setContactsA([]) }} className="cursor-pointer px-3 py-2 text-sm hover:bg-slate-50">{c.name}</li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-600">Contact B</label>
                <input type="text" value={searchB} onChange={(e) => setSearchB(e.target.value)} placeholder="Search..." className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" />
                {contactsB.length > 0 && (
                  <ul className="mt-1 max-h-40 overflow-y-auto rounded border border-slate-200 bg-white">
                    {contactsB.map((c) => (
                      <li key={c.id} onClick={() => { setFormData({ ...formData, contact_b_id: String(c.id) }); setSearchB(c.name); setContactsB([]) }} className="cursor-pointer px-3 py-2 text-sm hover:bg-slate-50">{c.name}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-600">Connection Type</label>
                <select value={formData.connection_type} onChange={(e) => setFormData({ ...formData, connection_type: e.target.value })} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm">
                  {CONNECTION_TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-600">Notes</label>
                <input type="text" value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" />
              </div>
            </div>
            <button type="submit" disabled={!formData.contact_a_id || !formData.contact_b_id} className="rounded-md bg-slate-800 px-5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50">Save Connection</button>
          </form>
        </section>
      )}

      {/* Warm Intro Finder */}
      <section className="mb-6 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-700">Warm Intro Finder</h2>
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-slate-600">Find intros to...</label>
            <input type="text" value={introSearch} onChange={(e) => { setIntroSearch(e.target.value); setIntroTargetId(null) }} placeholder="Search contact..." className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" />
            {introContacts.length > 0 && (
              <ul className="mt-1 max-h-40 overflow-y-auto rounded border border-slate-200 bg-white">
                {introContacts.map((c) => (
                  <li key={c.id} onClick={() => { setIntroTargetId(c.id); setIntroTargetName(c.name); setIntroSearch(c.name); setIntroContacts([]) }} className="cursor-pointer px-3 py-2 text-sm hover:bg-slate-50">{c.name}</li>
                ))}
              </ul>
            )}
          </div>
          <button onClick={findWarmIntros} disabled={!introTargetId} className="rounded-md bg-slate-800 px-5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50">Find Intros</button>
        </div>
        {warmIntros.length > 0 && (
          <div className="mt-4">
            <h3 className="mb-2 text-sm font-medium text-slate-600">Potential intros to {introTargetName}:</h3>
            <ul className="divide-y divide-slate-200">
              {warmIntros.map((intro, i) => (
                <li key={i} className="flex items-center justify-between py-3">
                  <div>
                    <Link to={`/contacts/${intro.intro_contact_id}`} className="font-medium text-slate-800 hover:text-slate-600">{intro.intro_contact_name}</Link>
                    <span className="ml-2 rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{intro.connection_type.replace('_', ' ')}</span>
                    <span className={`ml-2 text-xs font-medium ${stageColors[intro.relationship_stage || 'cold']}`}>{intro.relationship_stage || 'cold'}</span>
                  </div>
                  {intro.notes && <span className="text-xs text-slate-400">{intro.notes}</span>}
                </li>
              ))}
            </ul>
          </div>
        )}
        {introTargetId && warmIntros.length === 0 && (
          <p className="mt-4 text-sm text-slate-500">No warm intro paths found. Add connections to build the network.</p>
        )}
      </section>

      {/* Connection list */}
      <section className="rounded-lg bg-white shadow">
        <div className="border-b border-slate-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-slate-700">All Connections ({total})</h2>
        </div>
        {loading ? <p className="p-6 text-slate-500">Loading...</p> : connections.length === 0 ? <p className="p-6 text-slate-500">No connections yet.</p> : (
          <ul className="divide-y divide-slate-200">
            {connections.map((c) => (
              <li key={c.id} className="flex items-center justify-between px-6 py-3">
                <div className="flex items-center gap-2">
                  <Link to={`/contacts/${c.contact_a_id}`} className="font-medium text-slate-800 hover:text-slate-600">{c.contact_a_name}</Link>
                  <span className="text-slate-400">&harr;</span>
                  <Link to={`/contacts/${c.contact_b_id}`} className="font-medium text-slate-800 hover:text-slate-600">{c.contact_b_name}</Link>
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{c.connection_type.replace('_', ' ')}</span>
                  {c.notes && <span className="text-xs text-slate-400">{c.notes}</span>}
                </div>
                <button onClick={() => deleteConnection(c.id)} className="text-xs text-slate-400 hover:text-red-500">remove</button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
