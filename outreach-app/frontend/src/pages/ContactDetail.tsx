import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'

interface Contact {
  id: number
  list_number: number | null
  name: string
  category: string | null
  role_org: string | null
  connection_to_solomon: string | null
}

interface Mention {
  id: number
  source_type: string
  source_url: string | null
  title: string | null
  snippet: string | null
  published_at: string | null
}

interface OutreachEntry {
  id: number
  method: string
  subject: string | null
  content: string | null
  sent_at: string | null
  response_status: string | null
}

export default function ContactDetail() {
  const { id } = useParams()
  const [contact, setContact] = useState<Contact | null>(null)
  const [mentions, setMentions] = useState<Mention[]>([])
  const [outreach, setOutreach] = useState<OutreachEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const safeFetch = async (url: string) => {
    const res = await fetch(url)
    if (!res.ok) throw new Error(`Server error (${res.status})`)
    return res.json()
  }

  useEffect(() => {
    if (!id) return
    setError(null)
    setLoading(true)

    Promise.allSettled([
      safeFetch(`/api/contacts/${id}`),
      safeFetch(`/api/mentions?contact_id=${id}`),
      safeFetch(`/api/outreach?contact_id=${id}`),
    ])
      .then(([contactResult, mentionsResult, outreachResult]) => {
        if (contactResult.status === 'fulfilled') {
          setContact(contactResult.value)
        } else {
          console.error('Failed to load contact:', contactResult.reason)
          setError('Failed to load contact details.')
        }

        if (mentionsResult.status === 'fulfilled') {
          setMentions(mentionsResult.value.mentions || [])
        } else {
          console.error('Failed to load mentions:', mentionsResult.reason)
        }

        if (outreachResult.status === 'fulfilled') {
          setOutreach(outreachResult.value.entries || [])
        } else {
          console.error('Failed to load outreach:', outreachResult.reason)
        }
      })
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="py-8">
        <p className="text-slate-500">Loading...</p>
      </div>
    )
  }

  if (error || !contact) {
    return (
      <div className="py-8">
        <Link to="/contacts" className="mb-4 inline-block text-sm text-slate-600 hover:text-slate-800">
          &larr; Back to Contacts
        </Link>
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          {error || 'Contact not found.'}
        </div>
      </div>
    )
  }

  return (
    <div>
      <Link to="/contacts" className="mb-4 inline-block text-sm text-slate-600 hover:text-slate-800">
        ← Back to Contacts
      </Link>

      <div className="mb-8 rounded-lg bg-white p-6 shadow">
        <h1 className="text-2xl font-bold text-slate-800">{contact.name}</h1>
        <p className="mt-1 text-slate-600">{contact.role_org}</p>
        <p className="mt-2 text-sm text-slate-500">{contact.category}</p>
        {contact.connection_to_solomon && (
          <div className="mt-4 rounded bg-slate-50 p-4">
            <h3 className="text-sm font-medium text-slate-800">Connection to Solomon</h3>
            <p className="mt-2 text-slate-600">{contact.connection_to_solomon}</p>
          </div>
        )}
      </div>

      <div className="mb-8 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Mentions</h2>
        {mentions.length === 0 ? (
          <p className="text-slate-500">No mentions yet.</p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {mentions.map((m) => (
              <li key={m.id} className="py-4">
                <p className="font-medium text-slate-800">{m.title || m.snippet?.slice(0, 80)}</p>
                <p className="text-sm text-slate-500">
                  {m.source_type} • {m.published_at ? new Date(m.published_at).toLocaleDateString() : 'Unknown'}
                </p>
                {m.source_url && (
                  <a href={m.source_url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">
                    View source
                  </a>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Outreach Log</h2>
        {outreach.length === 0 ? (
          <p className="text-slate-500">No outreach logged yet.</p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {outreach.map((o) => (
              <li key={o.id} className="py-4">
                <p className="font-medium text-slate-800">{o.method}</p>
                {o.subject && <p className="text-sm text-slate-600">{o.subject}</p>}
                <p className="text-xs text-slate-500">
                  {o.sent_at ? new Date(o.sent_at).toLocaleString() : 'Not sent'} • {o.response_status || 'Unknown'}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
