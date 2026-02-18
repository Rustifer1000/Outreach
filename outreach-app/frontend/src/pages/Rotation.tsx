import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

const RECOMMENDED = 30

interface RotationContact {
  id: number
  name: string
  category: string | null
}

interface ContactOption {
  id: number
  name: string
  category: string | null
  in_mention_rotation?: boolean
}

export default function Rotation() {
  const [rotation, setRotation] = useState<RotationContact[]>([])
  const [allContacts, setAllContacts] = useState<ContactOption[]>([])
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [addId, setAddId] = useState('')
  const [replacing, setReplacing] = useState(false)

  const loadRotation = () => {
    fetch('/api/contacts/rotation')
      .then((r) => r.json())
      .then((d) => setRotation(d.contacts || []))
      .catch(() => setRotation([]))
  }

  const loadContacts = () => {
    fetch('/api/contacts?limit=400')
      .then((r) => r.json())
      .then((d) => setAllContacts(d.contacts || []))
      .catch(() => setAllContacts([]))
  }

  useEffect(() => {
    setLoading(true)
    loadRotation()
    loadContacts()
    setLoading(false)
  }, [])

  const rotationIds = new Set(rotation.map((c) => c.id))
  const notInRotation = allContacts.filter((c) => !rotationIds.has(c.id))

  const handleRemove = (contactId: number) => {
    fetch(`/api/contacts/${contactId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ in_mention_rotation: false }),
    })
      .then(() => loadRotation())
      .catch((e) => console.error(e))
  }

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    if (!addId) return
    setAdding(true)
    fetch(`/api/contacts/${addId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ in_mention_rotation: true }),
    })
      .then(() => {
        setAddId('')
        loadRotation()
      })
      .catch((e) => console.error(e))
      .finally(() => setAdding(false))
  }

  const handleReplaceRotation = (e: React.FormEvent) => {
    e.preventDefault()
    const ids = (e.currentTarget.querySelector('textarea') as HTMLTextAreaElement)?.value
      .split(/[\n,]+/)
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => !Number.isNaN(n) && n > 0)
    if (ids.length === 0) return
    setReplacing(true)
    fetch('/api/contacts/rotation', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contact_ids: ids }),
    })
      .then((r) => r.json())
      .then(() => {
        loadRotation()
        loadContacts()
      })
      .catch((e) => console.error(e))
      .finally(() => setReplacing(false))
  }

  if (loading) {
    return (
      <div className="py-8">
        <p className="text-slate-500">Loading...</p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold text-slate-800">Mention rotation</h1>
      <p className="mb-6 text-sm text-slate-600">
        Tag a core group (e.g. {RECOMMENDED}+) to focus the daily NewsAPI mention fetch. Only these contacts are searched when the job runs. Change the group each day to maximize coverage across the full list.
      </p>

      <div className="mb-8 rounded-lg border border-slate-200 bg-white p-6 shadow">
        <h2 className="mb-2 text-lg font-semibold text-slate-800">
          In rotation ({rotation.length}) {rotation.length >= RECOMMENDED ? '' : `— recommend ${RECOMMENDED}+`}
        </h2>
        <p className="mb-4 text-xs text-slate-500">
          These contacts will be included in the next mention fetch (dashboard Refresh or scheduled job).
        </p>
        {rotation.length === 0 ? (
          <p className="text-slate-500">No one in rotation. Add contacts below or set from the list.</p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {rotation.map((c) => (
              <li key={c.id} className="flex items-center justify-between py-2">
                <div>
                  <Link to={`/contacts/${c.id}`} className="font-medium text-slate-800 hover:text-slate-600">
                    {c.name}
                  </Link>
                  {c.category && <span className="ml-2 text-sm text-slate-500">{c.category}</span>}
                </div>
                <button
                  type="button"
                  onClick={() => handleRemove(c.id)}
                  className="text-sm text-red-600 hover:text-red-800"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mb-8 rounded-lg border border-slate-200 bg-slate-50 p-6">
        <h2 className="mb-2 text-lg font-semibold text-slate-800">Add to rotation</h2>
        <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-2">
          <div>
            <label className="mb-1 block text-sm text-slate-700">Contact</label>
            <select
              value={addId}
              onChange={(e) => setAddId(e.target.value)}
              className="min-w-[220px] rounded border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">Select...</option>
              {notInRotation.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={adding || !addId}
            className="rounded bg-slate-700 px-4 py-2 text-sm text-white hover:bg-slate-600 disabled:opacity-50"
          >
            {adding ? 'Adding...' : 'Add'}
          </button>
        </form>
      </div>

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-6">
        <h2 className="mb-2 text-lg font-semibold text-slate-800">Set rotation from list (replace all)</h2>
        <p className="mb-3 text-xs text-slate-500">
          Paste contact IDs (one per line or comma-separated) to replace the entire rotation. Use the Contacts page to copy IDs if needed.
        </p>
        <form onSubmit={handleReplaceRotation} className="flex flex-col gap-2">
          <textarea
            name="ids"
            rows={3}
            placeholder="e.g. 1, 2, 3, 5, 8..."
            className="rounded border border-slate-300 bg-white px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={replacing}
            className="w-fit rounded bg-slate-700 px-4 py-2 text-sm text-white hover:bg-slate-600 disabled:opacity-50"
          >
            {replacing ? 'Setting...' : 'Replace rotation with these IDs'}
          </button>
        </form>
      </div>
    </div>
  )
}
