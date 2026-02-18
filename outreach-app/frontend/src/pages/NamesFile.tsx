import { useEffect, useState } from 'react'

interface NamesEntry {
  name: string
  list_number: number | null
  role_org: string
  connection_to_solomon: string
  category: string
  subcategory: string | null
}

export default function NamesFile() {
  const [entries, setEntries] = useState<NamesEntry[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [path, setPath] = useState<string | null>(null)
  const [message, setMessage] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)
  const [adding, setAdding] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [form, setForm] = useState({
    category: '',
    name: '',
    role_org: '',
    connection: '',
    subcategory: '',
    list_number: '',
  })

  const loadEntries = () => {
    fetch('/api/names-file/entries')
      .then((r) => r.json())
      .then((data) => {
        setEntries(data.entries || [])
        setPath(data.path || null)
      })
      .catch((err) => {
        console.error(err)
        setMessage({ type: 'err', text: 'Failed to load Names file entries' })
      })
      .finally(() => setLoading(false))
  }

  const loadCategories = () => {
    fetch('/api/names-file/categories')
      .then((r) => r.json())
      .then((data) => setCategories(data.categories || []))
      .catch(() => setCategories([]))
  }

  useEffect(() => {
    loadEntries()
    loadCategories()
  }, [])

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim() || !form.connection.trim()) return
    const category = form.category.trim() || (categories[0] ?? 'Uncategorized')
    setAdding(true)
    setMessage(null)
    fetch('/api/names-file/entries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        category,
        name: form.name.trim(),
        role_org: form.role_org.trim(),
        connection: form.connection.trim(),
        subcategory: form.subcategory.trim() || null,
        list_number: form.list_number.trim() ? parseInt(form.list_number, 10) : null,
      }),
    })
      .then((r) => {
        if (!r.ok) return r.json().then((d) => Promise.reject(new Error(d.detail || 'Add failed')))
        return r.json()
      })
      .then(() => {
        setMessage({ type: 'ok', text: `Added ${form.name} to Names file` })
        setForm({ ...form, name: '', role_org: '', connection: '', subcategory: '', list_number: '' })
        loadEntries()
        loadCategories()
      })
      .catch((err) => setMessage({ type: 'err', text: err.message || 'Failed to add entry' }))
      .finally(() => setAdding(false))
  }

  const handleDelete = (entry: NamesEntry) => {
    if (!window.confirm(`Remove "${entry.name}" from the Names file? Re-run parse_names.py and re-seed the DB to sync.`)) return
    setDeleting(entry.name)
    const params = new URLSearchParams({ name: entry.name })
    if (entry.list_number != null) params.set('list_number', String(entry.list_number))
    fetch(`/api/names-file/entries?${params}`, { method: 'DELETE' })
      .then((r) => {
        if (!r.ok) return r.json().then((d) => Promise.reject(new Error(d.detail || 'Delete failed')))
        return r.json()
      })
      .then(() => {
        setMessage({ type: 'ok', text: `Removed ${entry.name}` })
        loadEntries()
      })
      .catch((err) => setMessage({ type: 'err', text: err.message || 'Failed to delete' }))
      .finally(() => setDeleting(null))
  }

  const filteredEntries = search.trim()
    ? entries.filter(
        (e) =>
          e.name.toLowerCase().includes(search.toLowerCase()) ||
          e.category.toLowerCase().includes(search.toLowerCase()) ||
          (e.role_org && e.role_org.toLowerCase().includes(search.toLowerCase())),
      )
    : entries

  if (loading) {
    return (
      <div className="py-8">
        <p className="text-slate-500">Loading Names file...</p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold text-slate-800">Names file</h1>
      <p className="mb-6 text-sm text-slate-500">
        Add or remove names in the source <code className="rounded bg-slate-200 px-1">Names</code> file.
        After changes, run <code className="rounded bg-slate-200 px-1">parse_names.py</code> and re-seed the DB to sync contacts.
      </p>
      {path && <p className="mb-4 text-xs text-slate-400">File: {path}</p>}

      {message && (
        <div
          className={`mb-4 rounded p-3 text-sm ${message.type === 'ok' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}
        >
          {message.text}
        </div>
      )}

      <div className="mb-8 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Add name</h2>
        <form onSubmit={handleAdd} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Category</label>
              <select
                value={form.category}
                onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Select or type below</option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Name *</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="Full name"
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                required
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Role / org</label>
            <input
              type="text"
              value={form.role_org}
              onChange={(e) => setForm((f) => ({ ...f, role_org: e.target.value }))}
              placeholder="e.g. Professor, MIT"
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Connection *</label>
            <textarea
              value={form.connection}
              onChange={(e) => setForm((f) => ({ ...f, connection: e.target.value }))}
              placeholder="Connection to Solomon's mission"
              rows={2}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              required
            />
          </div>
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Subcategory (optional)</label>
              <input
                type="text"
                value={form.subcategory}
                onChange={(e) => setForm((f) => ({ ...f, subcategory: e.target.value }))}
                className="w-48 rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">List number (optional)</label>
              <input
                type="number"
                value={form.list_number}
                onChange={(e) => setForm((f) => ({ ...f, list_number: e.target.value }))}
                placeholder="e.g. 41"
                className="w-24 rounded border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={adding || !form.name.trim() || !form.connection.trim()}
            className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {adding ? 'Adding...' : 'Add to Names file'}
          </button>
        </form>
      </div>

      <div className="rounded-lg bg-white shadow">
        <div className="border-b border-slate-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-slate-800">Entries ({filteredEntries.length})</h2>
          <input
            type="search"
            placeholder="Search by name, category, or role..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="mt-2 w-full max-w-md rounded border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">#</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Category</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Role/Org</th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Connection</th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-500">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {filteredEntries.map((e, idx) => (
                <tr key={`${e.name}-${e.list_number ?? idx}`} className="hover:bg-slate-50">
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-500">{e.list_number ?? '-'}</td>
                  <td className="whitespace-nowrap px-6 py-4 font-medium text-slate-800">{e.name}</td>
                  <td className="px-6 py-4 text-sm text-slate-600">{e.category}</td>
                  <td className="max-w-[200px] truncate px-6 py-4 text-sm text-slate-600" title={e.role_org}>
                    {e.role_org || '-'}
                  </td>
                  <td className="max-w-[280px] truncate px-6 py-4 text-sm text-slate-500" title={e.connection_to_solomon}>
                    {e.connection_to_solomon || '-'}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right">
                    <button
                      type="button"
                      onClick={() => handleDelete(e)}
                      disabled={deleting === e.name}
                      className="text-sm text-red-600 hover:text-red-800 disabled:opacity-50"
                    >
                      {deleting === e.name ? 'Removing...' : 'Remove'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredEntries.length === 0 && (
          <p className="px-6 py-8 text-center text-slate-500">
            {entries.length === 0 ? 'No entries in Names file or file not found.' : 'No entries match your search.'}
          </p>
        )}
      </div>
    </div>
  )
}
