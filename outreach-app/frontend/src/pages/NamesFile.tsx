import { useEffect, useState } from 'react'
import { apiFetch } from '../api'

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
  const [editingIdx, setEditingIdx] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [editForm, setEditForm] = useState({
    name: '',
    role_org: '',
    connection: '',
    category: '',
    subcategory: '',
    list_number: '',
  })
  const [newCatName, setNewCatName] = useState('')
  const [addingCat, setAddingCat] = useState(false)
  const [renamingCat, setRenamingCat] = useState<string | null>(null)
  const [renameCatValue, setRenameCatValue] = useState('')
  const [savingCatRename, setSavingCatRename] = useState(false)
  const [deletingCat, setDeletingCat] = useState<string | null>(null)
  const [form, setForm] = useState({
    category: '',
    name: '',
    role_org: '',
    connection: '',
    subcategory: '',
    list_number: '',
  })

  const loadEntries = () => {
    apiFetch<{ entries: NamesEntry[]; path?: string }>('/api/names-file/entries')
      .then((data) => {
        setEntries(data.entries || [])
        setPath(data.path || null)
      })
      .catch((err) => {
        setMessage({ type: 'err', text: `Failed to load Names file entries: ${err.message}` })
      })
      .finally(() => setLoading(false))
  }

  const loadCategories = () => {
    apiFetch<{ categories: string[] }>('/api/names-file/categories')
      .then((data) => setCategories(data.categories || []))
      .catch((err) => {
        setMessage({ type: 'err', text: `Failed to load categories: ${err.message}` })
        setCategories([])
      })
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
    apiFetch('/api/names-file/entries', {
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
    apiFetch(`/api/names-file/entries?${params}`, { method: 'DELETE' })
      .then(() => {
        setMessage({ type: 'ok', text: `Removed ${entry.name}` })
        loadEntries()
      })
      .catch((err) => setMessage({ type: 'err', text: err.message || 'Failed to delete' }))
      .finally(() => setDeleting(null))
  }

  const startEditing = (entry: NamesEntry, idx: number) => {
    setEditingIdx(idx)
    setEditForm({
      name: entry.name,
      role_org: entry.role_org || '',
      connection: entry.connection_to_solomon || '',
      category: entry.category || '',
      subcategory: entry.subcategory || '',
      list_number: entry.list_number != null ? String(entry.list_number) : '',
    })
    setMessage(null)
  }

  const cancelEditing = () => {
    setEditingIdx(null)
  }

  const handleSaveEdit = (originalEntry: NamesEntry) => {
    if (!editForm.name.trim() || !editForm.connection.trim()) return
    setSaving(true)
    setMessage(null)
    apiFetch('/api/names-file/entries', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        original_name: originalEntry.name,
        original_list_number: originalEntry.list_number,
        name: editForm.name.trim(),
        role_org: editForm.role_org.trim(),
        connection: editForm.connection.trim(),
        category: editForm.category.trim() || originalEntry.category,
        subcategory: editForm.subcategory.trim() || null,
        list_number: editForm.list_number.trim() ? parseInt(editForm.list_number, 10) : null,
      }),
    })
      .then(() => {
        setMessage({ type: 'ok', text: `Updated ${editForm.name}` })
        setEditingIdx(null)
        loadEntries()
        loadCategories()
      })
      .catch((err) => setMessage({ type: 'err', text: err.message || 'Failed to save edit' }))
      .finally(() => setSaving(false))
  }

  const handleAddCategory = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newCatName.trim()) return
    setAddingCat(true)
    setMessage(null)
    apiFetch('/api/names-file/categories', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newCatName.trim() }),
    })
      .then(() => {
        setMessage({ type: 'ok', text: `Added category: ${newCatName.trim()}` })
        setNewCatName('')
        loadCategories()
      })
      .catch((err) => setMessage({ type: 'err', text: err.message || 'Failed to add category' }))
      .finally(() => setAddingCat(false))
  }

  const startRenamingCat = (cat: string) => {
    setRenamingCat(cat)
    setRenameCatValue(cat)
    setMessage(null)
  }

  const handleRenameCategory = () => {
    if (!renamingCat || !renameCatValue.trim() || renameCatValue.trim() === renamingCat) {
      setRenamingCat(null)
      return
    }
    setSavingCatRename(true)
    setMessage(null)
    apiFetch('/api/names-file/categories', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_name: renamingCat, new_name: renameCatValue.trim() }),
    })
      .then(() => {
        setMessage({ type: 'ok', text: `Renamed "${renamingCat}" to "${renameCatValue.trim()}"` })
        setRenamingCat(null)
        loadCategories()
        loadEntries()
      })
      .catch((err) => setMessage({ type: 'err', text: err.message || 'Failed to rename category' }))
      .finally(() => setSavingCatRename(false))
  }

  const handleDeleteCategory = (cat: string) => {
    if (!window.confirm(`Remove the "${cat}" category? This only works if the category has no entries.`)) return
    setDeletingCat(cat)
    setMessage(null)
    const params = new URLSearchParams({ name: cat })
    apiFetch(`/api/names-file/categories?${params}`, { method: 'DELETE' })
      .then(() => {
        setMessage({ type: 'ok', text: `Removed category: ${cat}` })
        loadCategories()
      })
      .catch((err) => setMessage({ type: 'err', text: err.message || 'Failed to delete category' }))
      .finally(() => setDeletingCat(null))
  }

  // Count entries per category for the management UI
  const entryCounts: Record<string, number> = {}
  for (const e of entries) {
    entryCounts[e.category] = (entryCounts[e.category] || 0) + 1
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
        Add, edit, or remove names in the source <code className="rounded bg-slate-200 px-1">Names</code> file.
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

      <div className="mb-8 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Categories</h2>
        <div className="mb-4 flex flex-wrap gap-2">
          {categories.map((cat) => (
            <div
              key={cat}
              className="flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 py-1 pl-3 pr-1 text-sm"
            >
              {renamingCat === cat ? (
                <div className="flex items-center gap-1">
                  <input
                    type="text"
                    value={renameCatValue}
                    onChange={(ev) => setRenameCatValue(ev.target.value)}
                    onKeyDown={(ev) => {
                      if (ev.key === 'Enter') handleRenameCategory()
                      if (ev.key === 'Escape') setRenamingCat(null)
                    }}
                    className="w-36 rounded border border-slate-300 px-2 py-0.5 text-sm"
                    autoFocus
                  />
                  <button
                    type="button"
                    onClick={handleRenameCategory}
                    disabled={savingCatRename}
                    className="rounded px-1.5 py-0.5 text-xs font-medium text-green-600 hover:bg-green-50 disabled:opacity-50"
                  >
                    {savingCatRename ? '...' : 'OK'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setRenamingCat(null)}
                    disabled={savingCatRename}
                    className="rounded px-1.5 py-0.5 text-xs text-slate-400 hover:bg-slate-100"
                  >
                    X
                  </button>
                </div>
              ) : (
                <>
                  <span className="text-slate-700">{cat}</span>
                  <span className="ml-1 text-xs text-slate-400">({entryCounts[cat] || 0})</span>
                  <button
                    type="button"
                    onClick={() => startRenamingCat(cat)}
                    className="ml-1 rounded p-0.5 text-xs text-blue-500 hover:bg-blue-50"
                    title="Rename category"
                  >
                    rename
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteCategory(cat)}
                    disabled={deletingCat === cat}
                    className="rounded p-0.5 text-xs text-red-500 hover:bg-red-50 disabled:opacity-50"
                    title={entryCounts[cat] ? 'Remove entries first' : 'Delete category'}
                  >
                    {deletingCat === cat ? '...' : 'x'}
                  </button>
                </>
              )}
            </div>
          ))}
          {categories.length === 0 && (
            <p className="text-sm text-slate-400">No categories found</p>
          )}
        </div>
        <form onSubmit={handleAddCategory} className="flex items-center gap-2">
          <input
            type="text"
            value={newCatName}
            onChange={(ev) => setNewCatName(ev.target.value)}
            placeholder="New category name"
            className="w-64 rounded border border-slate-300 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={addingCat || !newCatName.trim()}
            className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {addingCat ? 'Adding...' : 'Add category'}
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
              {filteredEntries.map((e, idx) => {
                const isEditing = editingIdx === idx
                return (
                  <tr key={`${e.name}-${e.list_number ?? idx}`} className={isEditing ? 'bg-amber-50' : 'hover:bg-slate-50'}>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-500">
                      {isEditing ? (
                        <input
                          type="number"
                          value={editForm.list_number}
                          onChange={(ev) => setEditForm((f) => ({ ...f, list_number: ev.target.value }))}
                          className="w-16 rounded border border-slate-300 px-2 py-1 text-sm"
                          placeholder="#"
                        />
                      ) : (
                        e.list_number ?? '-'
                      )}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 font-medium text-slate-800">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editForm.name}
                          onChange={(ev) => setEditForm((f) => ({ ...f, name: ev.target.value }))}
                          className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
                        />
                      ) : (
                        <span className="cursor-pointer hover:text-blue-600" onClick={() => startEditing(e, idx)} title="Click to edit">
                          {e.name}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">
                      {isEditing ? (
                        <select
                          value={editForm.category}
                          onChange={(ev) => setEditForm((f) => ({ ...f, category: ev.target.value }))}
                          className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
                        >
                          {categories.map((c) => (
                            <option key={c} value={c}>{c}</option>
                          ))}
                        </select>
                      ) : (
                        <span className="cursor-pointer hover:text-blue-600" onClick={() => startEditing(e, idx)} title="Click to edit">
                          {e.category}
                        </span>
                      )}
                    </td>
                    <td className="max-w-[200px] px-6 py-4 text-sm text-slate-600">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editForm.role_org}
                          onChange={(ev) => setEditForm((f) => ({ ...f, role_org: ev.target.value }))}
                          className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
                          placeholder="Role / org"
                        />
                      ) : (
                        <span className="block cursor-pointer truncate hover:text-blue-600" onClick={() => startEditing(e, idx)} title={e.role_org || 'Click to edit'}>
                          {e.role_org || '-'}
                        </span>
                      )}
                    </td>
                    <td className="max-w-[280px] px-6 py-4 text-sm text-slate-500">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editForm.connection}
                          onChange={(ev) => setEditForm((f) => ({ ...f, connection: ev.target.value }))}
                          className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
                          placeholder="Connection"
                        />
                      ) : (
                        <span className="block cursor-pointer truncate hover:text-blue-600" onClick={() => startEditing(e, idx)} title={e.connection_to_solomon || 'Click to edit'}>
                          {e.connection_to_solomon || '-'}
                        </span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-right">
                      {isEditing ? (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => handleSaveEdit(e)}
                            disabled={saving || !editForm.name.trim() || !editForm.connection.trim()}
                            className="text-sm font-medium text-green-600 hover:text-green-800 disabled:opacity-50"
                          >
                            {saving ? 'Saving...' : 'Save'}
                          </button>
                          <button
                            type="button"
                            onClick={cancelEditing}
                            disabled={saving}
                            className="text-sm text-slate-500 hover:text-slate-700 disabled:opacity-50"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-end gap-3">
                          <button
                            type="button"
                            onClick={() => startEditing(e, idx)}
                            className="text-sm text-blue-600 hover:text-blue-800"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(e)}
                            disabled={deleting === e.name}
                            className="text-sm text-red-600 hover:text-red-800 disabled:opacity-50"
                          >
                            {deleting === e.name ? 'Removing...' : 'Remove'}
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
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
