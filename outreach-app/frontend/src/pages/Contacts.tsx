import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

interface Contact {
  id: number
  list_number: number | null
  name: string
  category: string | null
  role_org: string | null
  in_mention_rotation?: boolean
}

export default function Contacts() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [rotationOnly, setRotationOnly] = useState(false)
  const [togglingId, setTogglingId] = useState<number | null>(null)

  useEffect(() => {
    const params = new URLSearchParams({ limit: '100' })
    if (search) params.set('q', search)
    if (rotationOnly) params.set('in_rotation', '1')
    fetch(`/api/contacts?${params}`)
      .then((res) => res.json())
      .then((data) => {
        setContacts(data.contacts || [])
        setTotal(data.total || 0)
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false))
  }, [search, rotationOnly])

  const toggleRotation = (c: Contact) => {
    setTogglingId(c.id)
    fetch(`/api/contacts/${c.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ in_mention_rotation: !c.in_mention_rotation }),
    })
      .then((r) => r.json())
      .then(() => {
        setContacts((prev) =>
          prev.map((x) => (x.id === c.id ? { ...x, in_mention_rotation: !x.in_mention_rotation } : x)),
        )
      })
      .catch((err) => console.error(err))
      .finally(() => setTogglingId(null))
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-slate-800">Contacts</h1>

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <input
          type="search"
          placeholder="Search by name or category..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-md rounded-md border border-slate-300 px-4 py-2 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
        />
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={rotationOnly}
            onChange={(e) => setRotationOnly(e.target.checked)}
            className="rounded border-slate-300"
          />
          In rotation only
        </label>
        <Link to="/rotation" className="text-sm text-slate-600 hover:text-slate-800">
          Manage rotation →
        </Link>
      </div>

      {loading ? (
        <p className="text-slate-500">Loading...</p>
      ) : (
        <div className="overflow-hidden rounded-lg bg-white shadow">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  #
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  Category
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  Role/Org
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">
                  Rotation
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {contacts.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50">
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-500">
                    {c.list_number ?? '-'}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4">
                    <Link
                      to={`/contacts/${c.id}`}
                      className="font-medium text-slate-800 hover:text-slate-600"
                    >
                      {c.name}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600">
                    {c.category?.replace(/^Category \d+: /, '') ?? '-'}
                  </td>
                  <td className="max-w-xs truncate px-6 py-4 text-sm text-slate-500">
                    {c.role_org ?? '-'}
                  </td>
                  <td className="px-6 py-4">
                    <button
                      type="button"
                      onClick={() => toggleRotation(c)}
                      disabled={togglingId === c.id}
                      title={c.in_mention_rotation ? 'Remove from rotation' : 'Add to rotation'}
                      className={`rounded px-2 py-1 text-xs font-medium ${c.in_mention_rotation ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'} hover:opacity-80 disabled:opacity-50`}
                    >
                      {togglingId === c.id ? '…' : c.in_mention_rotation ? 'In rotation' : 'Add'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-4 text-sm text-slate-500">Showing {contacts.length} of {total} contacts</p>
    </div>
  )
}
