import { useCallback, useEffect, useState } from 'react'

interface Template {
  id: number
  name: string
  category: string | null
  subject: string | null
  body: string
  created_at: string
  updated_at: string
}

const CATEGORIES = ['general', 'ai_safety', 'philanthropy', 'education', 'futurists', 'governance', 'media']
const PLACEHOLDERS = ['{{name}}', '{{recent_mention}}', '{{connection}}', '{{role}}', '{{organization}}']

export default function Templates() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Form
  const [editing, setEditing] = useState<number | 'new' | null>(null)
  const [formData, setFormData] = useState({ name: '', category: 'general', subject: '', body: '' })

  const loadTemplates = useCallback(() => {
    setLoading(true)
    fetch('/api/templates')
      .then((r) => r.ok ? r.json() : Promise.reject(new Error(`Error (${r.status})`)))
      .then((data) => setTemplates(data.templates || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { loadTemplates() }, [loadTemplates])

  const startEdit = (t: Template) => {
    setEditing(t.id)
    setFormData({ name: t.name, category: t.category || 'general', subject: t.subject || '', body: t.body })
  }

  const startNew = () => {
    setEditing('new')
    setFormData({ name: '', category: 'general', subject: '', body: '' })
  }

  const cancelEdit = () => {
    setEditing(null)
    setFormData({ name: '', category: 'general', subject: '', body: '' })
  }

  const save = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name.trim() || !formData.body.trim()) return
    const payload = {
      name: formData.name,
      category: formData.category,
      subject: formData.subject || null,
      body: formData.body,
    }
    const isNew = editing === 'new'
    const url = isNew ? '/api/templates' : `/api/templates/${editing}`
    const method = isNew ? 'POST' : 'PUT'
    fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      .then((r) => { if (!r.ok) throw new Error(`Error (${r.status})`); return r.json() })
      .then(() => { cancelEdit(); loadTemplates() })
      .catch((err) => setError(err.message))
  }

  const deleteTemplate = (id: number) => {
    if (!confirm('Delete this template?')) return
    fetch(`/api/templates/${id}`, { method: 'DELETE' })
      .then((r) => { if (r.ok) loadTemplates(); else setError(`Delete failed (${r.status})`) })
      .catch((err) => setError(err.message))
  }

  const insertPlaceholder = (ph: string) => {
    setFormData({ ...formData, body: formData.body + ph })
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Message Templates</h1>
        {editing === null && (
          <button onClick={startNew} className="rounded-md bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700">New Template</button>
        )}
      </div>

      {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}

      {/* Editor */}
      {editing !== null && (
        <section className="mb-6 rounded-lg bg-white p-6 shadow">
          <h2 className="mb-4 text-lg font-semibold text-slate-700">{editing === 'new' ? 'New Template' : 'Edit Template'}</h2>
          <form onSubmit={save} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-600">Name</label>
                <input type="text" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-600">Category</label>
                <select value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value })} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm">
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace('_', ' ')}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600">Subject Line</label>
              <input type="text" value={formData.subject} onChange={(e) => setFormData({ ...formData, subject: e.target.value })} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" placeholder="Optional subject for email" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600">Body</label>
              <div className="mb-2 flex flex-wrap gap-1">
                {PLACEHOLDERS.map((ph) => (
                  <button key={ph} type="button" onClick={() => insertPlaceholder(ph)} className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600 hover:bg-slate-200">{ph}</button>
                ))}
              </div>
              <textarea value={formData.body} onChange={(e) => setFormData({ ...formData, body: e.target.value })} rows={8} className="w-full rounded border border-slate-300 px-3 py-2 text-sm font-mono" />
            </div>
            <div className="flex gap-2">
              <button type="submit" disabled={!formData.name.trim() || !formData.body.trim()} className="rounded-md bg-slate-800 px-5 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50">Save</button>
              <button type="button" onClick={cancelEdit} className="rounded-md border border-slate-300 px-5 py-2 text-sm text-slate-600 hover:bg-slate-50">Cancel</button>
            </div>
          </form>
        </section>
      )}

      {/* Template list */}
      <section className="rounded-lg bg-white shadow">
        {loading ? <p className="p-6 text-slate-500">Loading...</p> : templates.length === 0 ? <p className="p-6 text-slate-500">No templates yet. Create one to get started.</p> : (
          <ul className="divide-y divide-slate-200">
            {templates.map((t) => (
              <li key={t.id} className="px-6 py-4">
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-800">{t.name}</span>
                      {t.category && <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">{t.category.replace('_', ' ')}</span>}
                    </div>
                    {t.subject && <p className="mt-1 text-sm text-slate-600">Subject: {t.subject}</p>}
                    <p className="mt-1 whitespace-pre-wrap text-sm text-slate-500 line-clamp-3">{t.body}</p>
                  </div>
                  <div className="ml-4 flex gap-2">
                    <button onClick={() => startEdit(t)} className="text-xs text-slate-500 hover:text-slate-700">edit</button>
                    <button onClick={() => deleteTemplate(t.id)} className="text-xs text-slate-400 hover:text-red-500">delete</button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
