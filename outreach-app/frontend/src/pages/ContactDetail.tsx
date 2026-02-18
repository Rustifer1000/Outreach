import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'

interface ContactInfo {
  type: string
  value: string
  is_primary: boolean
}

interface ContactRecommendation {
  method: string
  available: boolean
  reason: string
}

interface Contact {
  id: number
  list_number: number | null
  name: string
  category: string | null
  role_org: string | null
  connection_to_solomon: string | null
  contact_info?: ContactInfo[]
  recommended_contact_method?: ContactRecommendation
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

const METHODS = ['email', 'linkedin', 'twitter', 'website', 'other']
const RESPONSE_STATUSES = ['sent', 'replied', 'no_response', 'bounced']

function loadOutreach(contactId: string) {
  return fetch(`/api/outreach?contact_id=${contactId}`).then((r) => r.json())
}

export default function ContactDetail() {
  const { id } = useParams()
  const [contact, setContact] = useState<Contact | null>(null)
  const [mentions, setMentions] = useState<Mention[]>([])
  const [outreach, setOutreach] = useState<OutreachEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ method: 'email', subject: '', content: '', response_status: 'sent' })
  const [contactInfoForm, setContactInfoForm] = useState({ type: 'email', value: '' })
  const [addingInfo, setAddingInfo] = useState(false)

  const refreshOutreach = () => {
    if (id) loadOutreach(id).then((d) => setOutreach(d.entries || []))
  }

  const refreshContact = () => {
    if (id) fetch(`/api/contacts/${id}`).then((r) => r.json()).then(setContact)
  }

  const handleAddContactInfo = (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !contactInfoForm.value.trim()) return
    setAddingInfo(true)
    fetch(`/api/contacts/${id}/info`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: contactInfoForm.type, value: contactInfoForm.value.trim() }),
    })
      .then((r) => r.json())
      .then(() => {
        setContactInfoForm({ type: 'email', value: '' })
        refreshContact()
      })
      .catch((err) => console.error(err))
      .finally(() => setAddingInfo(false))
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  useEffect(() => {
    if (!id) return
    Promise.all([
      fetch(`/api/contacts/${id}`).then((r) => r.json()),
      fetch(`/api/mentions?contact_id=${id}`).then((r) => r.json()),
      loadOutreach(id),
    ])
      .then(([contactData, mentionsData, outreachData]) => {
        setContact(contactData)
        setMentions(mentionsData.mentions || [])
        setOutreach(outreachData.entries || [])
        if (outreachData.entries?.length === 0 && contactData.recommended_contact_method?.method) {
          setForm((f) => ({ ...f, method: contactData.recommended_contact_method.method }))
        }
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false))
  }, [id])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!id) return
    setSubmitting(true)
    const sentAt = new Date().toISOString().slice(0, 19)
    fetch('/api/outreach', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contact_id: parseInt(id),
        method: form.method,
        subject: form.subject || null,
        content: form.content || null,
        sent_at: sentAt,
        response_status: form.response_status,
      }),
    })
      .then((r) => r.json())
      .then(() => {
        setForm({ method: 'email', subject: '', content: '', response_status: 'sent' })
        refreshOutreach()
      })
      .catch((err) => console.error(err))
      .finally(() => setSubmitting(false))
  }

  if (loading || !contact) {
    return (
      <div className="py-8">
        <p className="text-slate-500">Loading...</p>
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

        {contact.recommended_contact_method && (
          <div className={`mt-4 rounded p-4 ${contact.recommended_contact_method.available ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'}`}>
            <h3 className="text-sm font-medium text-slate-800">First-contact recommendation</h3>
            <p className="mt-1 font-medium text-slate-700">
              {contact.recommended_contact_method.reason}
            </p>
          </div>
        )}

        {contact.contact_info && contact.contact_info.length > 0 && (
          <div className="mt-4 rounded bg-slate-50 p-4">
            <h3 className="text-sm font-medium text-slate-800">Contact info</h3>
            <ul className="mt-2 space-y-1">
              {contact.contact_info.map((ci, i) => (
                <li key={i} className="flex items-center gap-2 text-sm">
                  <span className="font-medium text-slate-600">{ci.type}:</span>
                  <span className="text-slate-700">{ci.value}</span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(ci.value)}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    Copy
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <form onSubmit={handleAddContactInfo} className="mt-4 rounded border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-medium text-slate-800">Add contact info</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            <select
              value={contactInfoForm.type}
              onChange={(e) => setContactInfoForm((f) => ({ ...f, type: e.target.value }))}
              className="rounded border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="email">Email</option>
              <option value="linkedin">LinkedIn</option>
              <option value="twitter">Twitter</option>
              <option value="website">Website</option>
              <option value="phone">Phone</option>
              <option value="other">Other</option>
            </select>
            <input
              type="text"
              value={contactInfoForm.value}
              onChange={(e) => setContactInfoForm((f) => ({ ...f, value: e.target.value }))}
              placeholder="e.g. name@example.com or LinkedIn URL"
              className="min-w-[200px] rounded border border-slate-300 px-3 py-2 text-sm"
            />
            <button
              type="submit"
              disabled={addingInfo || !contactInfoForm.value.trim()}
              className="rounded bg-slate-700 px-4 py-2 text-sm text-white hover:bg-slate-600 disabled:opacity-50"
            >
              {addingInfo ? 'Adding...' : 'Add'}
            </button>
          </div>
        </form>
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

        <form onSubmit={handleSubmit} className="mb-6 rounded border border-slate-200 bg-slate-50 p-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Method</label>
              <select
                value={form.method}
                onChange={(e) => setForm((f) => ({ ...f, method: e.target.value }))}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                {METHODS.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Response status</label>
              <select
                value={form.response_status}
                onChange={(e) => setForm((f) => ({ ...f, response_status: e.target.value }))}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
              >
                {RESPONSE_STATUSES.map((s) => (
                  <option key={s} value={s}>{s.replace('_', ' ')}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="mt-4">
            <label className="mb-1 block text-sm font-medium text-slate-700">Subject (optional)</label>
            <input
              type="text"
              value={form.subject}
              onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
              placeholder="Email subject line"
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="mt-4">
            <label className="mb-1 block text-sm font-medium text-slate-700">Content / notes (optional)</label>
            <textarea
              value={form.content}
              onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))}
              placeholder="Brief summary or copy of message"
              rows={3}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="mt-4 rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {submitting ? 'Adding...' : 'Log outreach'}
          </button>
        </form>

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
