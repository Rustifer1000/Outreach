import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { apiFetch } from '../api'

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
  primary_interests: string | null
  relationship_stage?: string | null
  mission_alignment?: number | null
  tags?: string[]
  contact_info?: ContactInfo[]
  recommended_contact_method?: ContactRecommendation
}

interface WarmIntroPath {
  connector_id: number
  connector_name: string
  connector_stage: string
  relationship_to_target: string
  has_replied: boolean
  intro_strength: number
}

interface Mention {
  id: number
  source_type: string
  source_url: string | null
  title: string | null
  snippet: string | null
  published_at: string | null
}

interface ReplyDraft {
  id: number
  reply_text: string
  themes: string[]
  status: string
  mention_id: number
  contact_id: number
  created_at: string | null
}

interface OutreachEntry {
  id: number
  method: string
  subject: string | null
  content: string | null
  sent_at: string | null
  response_status: string | null
}

interface NoteEntry {
  id: number
  note_text: string
  note_date: string | null
  channel: string | null
  created_at: string | null
}

interface ConnectionEntry {
  id: number
  other_contact_id: number
  other_contact_name: string | null
  relationship_type: string
  notes: string | null
  created_at: string | null
}

const METHODS = ['email', 'linkedin', 'twitter', 'website', 'other']
const RESPONSE_STATUSES = ['sent', 'replied', 'no_response', 'bounced']
const RELATIONSHIP_STAGES = ['Cold', 'Warm', 'Engaged', 'Partner-Advocate']
const NOTE_CHANNELS = ['', 'email', 'call', 'meeting', 'linkedin', 'other']
const CONNECTION_TYPES = ['first_degree', 'second_degree', 'same_org', 'co_author', 'other']

export default function ContactDetail() {
  const { id } = useParams()
  const [contact, setContact] = useState<Contact | null>(null)
  const [mentions, setMentions] = useState<Mention[]>([])
  const [outreach, setOutreach] = useState<OutreachEntry[]>([])
  const [notes, setNotes] = useState<NoteEntry[]>([])
  const [connections, setConnections] = useState<ConnectionEntry[]>([])
  const [contactList, setContactList] = useState<{ id: number; name: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ method: 'email', subject: '', content: '', response_status: 'sent' })
  const [contactInfoForm, setContactInfoForm] = useState({ type: 'email', value: '' })
  const [addingInfo, setAddingInfo] = useState(false)
  const [noteForm, setNoteForm] = useState({ note_text: '', note_date: new Date().toISOString().slice(0, 10), channel: '' })
  const [addingNote, setAddingNote] = useState(false)
  const [connectionForm, setConnectionForm] = useState({ other_contact_id: '', relationship_type: 'first_degree', notes: '' })
  const [addingConnection, setAddingConnection] = useState(false)
  const [savingStage, setSavingStage] = useState(false)
  const [discovering, setDiscovering] = useState(false)
  const [enriching, setEnriching] = useState(false)
  const [enrichMessage, setEnrichMessage] = useState<string | null>(null)
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null)
  const [enrichingBio, setEnrichingBio] = useState(false)
  const [bioMessage, setBioMessage] = useState<string | null>(null)
  const [fetchingMedia, setFetchingMedia] = useState(false)
  const [mediaMessage, setMediaMessage] = useState<string | null>(null)
  const [tags, setTags] = useState<{ id: number; tag: string }[]>([])
  const [presetTags, setPresetTags] = useState<string[]>([])
  const [customTag, setCustomTag] = useState('')
  const [warmIntros, setWarmIntros] = useState<WarmIntroPath[]>([])
  const [error, setError] = useState<string | null>(null)
  const [draftModal, setDraftModal] = useState<{ mentionId: number; draft: ReplyDraft | null; generating: boolean; editText: string } | null>(null)
  const mediaPollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (mediaPollRef.current) clearInterval(mediaPollRef.current)
    }
  }, [])

  const refreshOutreach = () => {
    if (id) apiFetch<{ entries: OutreachEntry[] }>(`/api/outreach?contact_id=${id}`)
      .then((d) => setOutreach(d.entries || []))
      .catch((err) => setError(`Failed to refresh outreach: ${err.message}`))
  }
  const refreshNotes = () => {
    if (id) apiFetch<{ notes: NoteEntry[] }>(`/api/contacts/${id}/notes`)
      .then((d) => setNotes(d.notes || []))
      .catch((err) => setError(`Failed to refresh notes: ${err.message}`))
  }
  const refreshContact = () => {
    if (id) apiFetch<Contact>(`/api/contacts/${id}`)
      .then(setContact)
      .catch((err) => setError(`Failed to refresh contact: ${err.message}`))
  }
  const refreshTags = () => {
    if (id) apiFetch<{ tags: { id: number; tag: string }[] }>(`/api/contacts/${id}/tags`)
      .then((d) => setTags(d.tags || []))
      .catch((err) => console.warn('Tags refresh failed:', err.message))
  }
  const refreshWarmIntros = () => {
    if (id) apiFetch<{ intro_paths: WarmIntroPath[] }>(`/api/contacts/${id}/warm-intros`)
      .then((d) => setWarmIntros(d.intro_paths || []))
      .catch((err) => console.warn('Warm intros refresh failed:', err.message))
  }
  const refreshConnections = () => {
    if (id) {
      apiFetch<{ connections: ConnectionEntry[] }>(`/api/contacts/${id}/connections`)
        .then((d) => setConnections(d.connections || []))
        .catch((err) => setError(`Failed to refresh connections: ${err.message}`))
      refreshWarmIntros()
    }
  }
  const handleAddTag = (tagName: string) => {
    if (!id || !tagName.trim()) return
    apiFetch(`/api/contacts/${id}/tags`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tag: tagName.trim() }),
    })
      .then(() => { refreshTags(); setCustomTag('') })
      .catch((err) => setError(`Failed to add tag: ${err.message}`))
  }
  const handleRemoveTag = (tagId: number) => {
    if (!id) return
    apiFetch(`/api/contacts/${id}/tags/${tagId}`, { method: 'DELETE' })
      .then(() => refreshTags())
      .catch((err) => setError(`Failed to remove tag: ${err.message}`))
  }
  const handleAlignmentChange = (value: number) => {
    if (!id) return
    apiFetch<{ mission_alignment: number }>(`/api/contacts/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mission_alignment: value }),
    })
      .then((d) => setContact((c) => (c ? { ...c, mission_alignment: d.mission_alignment } : c)))
      .catch((err) => setError(`Failed to save alignment: ${err.message}`))
  }
  const handleAutoAlignment = () => {
    if (!id) return
    apiFetch<{ mission_alignment: number }>(`/api/contacts/${id}/compute-alignment`, { method: 'POST' })
      .then((d) => setContact((c) => (c ? { ...c, mission_alignment: d.mission_alignment } : c)))
      .catch((err) => setError(`Failed to compute alignment: ${err.message}`))
  }

  const handleGenerateDraft = (mentionId: number) => {
    setDraftModal({ mentionId, draft: null, generating: true, editText: '' })
    apiFetch<ReplyDraft>('/api/reply-drafts/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mention_id: mentionId }),
    })
      .then((d) => setDraftModal({ mentionId, draft: d, generating: false, editText: d.reply_text }))
      .catch((err) => {
        setError(`Failed to generate draft: ${err.message}`)
        setDraftModal(null)
      })
  }

  const handleUpdateDraftStatus = (status: string) => {
    if (!draftModal?.draft) return
    apiFetch(`/api/reply-drafts/${draftModal.draft.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
      .then(() => setDraftModal((d) => d ? { ...d, draft: d.draft ? { ...d.draft, status } : null } : null))
      .catch((err) => setError(`Failed to update draft: ${err.message}`))
  }

  const handleDeleteDraft = () => {
    if (!draftModal?.draft) return
    apiFetch(`/api/reply-drafts/${draftModal.draft.id}`, { method: 'DELETE' })
      .then(() => setDraftModal(null))
      .catch((err) => setError(`Failed to delete draft: ${err.message}`))
  }

  const handleStageChange = (stage: string) => {
    if (!id) return
    setSavingStage(true)
    apiFetch<{ relationship_stage: string | null }>(`/api/contacts/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ relationship_stage: stage || null }),
    })
      .then((d) => {
        setContact((c) => (c ? { ...c, relationship_stage: d.relationship_stage } : c))
      })
      .catch((err) => setError(`Failed to save relationship stage: ${err.message}`))
      .finally(() => setSavingStage(false))
  }

  const handleAddNote = (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !noteForm.note_text.trim()) return
    setAddingNote(true)
    apiFetch(`/api/contacts/${id}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        note_text: noteForm.note_text.trim(),
        note_date: noteForm.note_date ? `${noteForm.note_date}T12:00:00` : new Date().toISOString(),
        channel: noteForm.channel.trim() || null,
      }),
    })
      .then(() => {
        setNoteForm({ note_text: '', note_date: new Date().toISOString().slice(0, 10), channel: '' })
        refreshNotes()
      })
      .catch((err) => setError(`Failed to add note: ${err.message}`))
      .finally(() => setAddingNote(false))
  }

  const handleAddConnection = (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !connectionForm.other_contact_id) return
    setAddingConnection(true)
    apiFetch(`/api/contacts/${id}/connections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        other_contact_id: parseInt(connectionForm.other_contact_id),
        relationship_type: connectionForm.relationship_type,
        notes: connectionForm.notes.trim() || null,
      }),
    })
      .then(() => {
        setConnectionForm({ other_contact_id: '', relationship_type: 'first_degree', notes: '' })
        refreshConnections()
      })
      .catch((err) => setError(`Failed to add connection: ${err.message}`))
      .finally(() => setAddingConnection(false))
  }

  const handleDeleteConnection = (connectionId: number) => {
    if (!id || !window.confirm('Remove this connection?')) return
    apiFetch(`/api/contacts/${id}/connections/${connectionId}`, { method: 'DELETE' })
      .then(() => refreshConnections())
      .catch((err) => setError(`Failed to remove connection: ${err.message}`))
  }

  const discoverTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      if (discoverTimeoutRef.current) clearTimeout(discoverTimeoutRef.current)
    }
  }, [])

  const handleDiscoverConnections = () => {
    if (!id) return
    setDiscovering(true)
    apiFetch('/api/jobs/discover-connections-for-contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contact_id: parseInt(id), max_pairs: 20 }),
    })
      .then(() => {
        discoverTimeoutRef.current = setTimeout(() => {
          discoverTimeoutRef.current = null
          refreshConnections()
          setDiscovering(false)
        }, 2000)
      })
      .catch((err) => {
        setDiscovering(false)
        setError(`Connection discovery failed: ${err.message}`)
      })
  }

  const hasEmail = contact?.contact_info?.some((ci) => ci.type === 'email') ?? false

  const handleEnrich = () => {
    if (!id) return
    setEnriching(true)
    setEnrichMessage(null)
    apiFetch<{ detail?: string; found?: boolean; email?: string; linkedin_url?: string; message?: string }>(`/api/contacts/${id}/enrich`, { method: 'POST' })
      .then((d) => {
        if (d.detail) {
          setEnrichMessage(d.detail)
        } else if (d.found) {
          const parts = [`Found: ${d.email}`]
          if (d.linkedin_url) parts.push(`+ LinkedIn`)
          setEnrichMessage(parts.join(' '))
          refreshContact()
        } else {
          setEnrichMessage(d.message ?? 'No email found')
        }
      })
      .catch((err) => setEnrichMessage(`Enrichment failed: ${err.message}`))
      .finally(() => setEnriching(false))
  }

  const handleEnrichBio = () => {
    if (!id) return
    setEnrichingBio(true)
    setBioMessage(null)
    apiFetch<{ detail?: string; generated?: boolean; message?: string }>(`/api/contacts/${id}/enrich-bio`, { method: 'POST' })
      .then((d) => {
        if (d.detail) {
          setBioMessage(d.detail)
        } else if (d.generated) {
          setBioMessage('Bio generated')
          refreshContact()
        } else {
          setBioMessage(d.message ?? 'Could not generate bio')
        }
      })
      .catch((err) => setBioMessage(`Bio enrichment failed: ${err.message}`))
      .finally(() => setEnrichingBio(false))
  }

  const handleFetchMedia = () => {
    if (!id) return
    setFetchingMedia(true)
    setMediaMessage(null)
    if (mediaPollRef.current) {
      clearInterval(mediaPollRef.current)
      mediaPollRef.current = null
    }
    apiFetch<{ detail?: string; sources?: string[] }>('/api/jobs/fetch-media', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contact_ids: [parseInt(id)], days: 30, max_per_source: 3 }),
    })
      .then((d) => {
        if (d.detail) {
          setMediaMessage(d.detail)
          setFetchingMedia(false)
        } else {
          setMediaMessage(`Searching ${d.sources?.join(', ') || 'media'}...`)
          mediaPollRef.current = setInterval(() => {
            apiFetch<{ status: string; added?: number }>('/api/jobs/media-status')
              .then((s) => {
                if (s.status === 'complete') {
                  if (mediaPollRef.current) clearInterval(mediaPollRef.current)
                  mediaPollRef.current = null
                  setMediaMessage(`Done: ${s.added} new mentions found`)
                  setFetchingMedia(false)
                  apiFetch<{ mentions: Mention[] }>(`/api/mentions?contact_id=${id}`)
                    .then((data) => setMentions(data.mentions || []))
                    .catch((err) => setError(`Failed to refresh mentions: ${err.message}`))
                }
              })
              .catch((err) => {
                if (mediaPollRef.current) clearInterval(mediaPollRef.current)
                mediaPollRef.current = null
                setMediaMessage(`Media status check failed: ${err.message}`)
                setFetchingMedia(false)
              })
          }, 3000)
        }
      })
      .catch((err) => {
        setMediaMessage(`Media fetch failed: ${err.message}`)
        setFetchingMedia(false)
      })
  }

  const handleAddContactInfo = (e: React.FormEvent) => {
    e.preventDefault()
    if (!id || !contactInfoForm.value.trim()) return
    setAddingInfo(true)
    apiFetch(`/api/contacts/${id}/info`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: contactInfoForm.type, value: contactInfoForm.value.trim() }),
    })
      .then(() => {
        setContactInfoForm({ type: 'email', value: '' })
        refreshContact()
      })
      .catch((err) => setError(`Failed to add contact info: ${err.message}`))
      .finally(() => setAddingInfo(false))
  }

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedIndex(key)
      setTimeout(() => setCopiedIndex(null), 1500)
    }).catch(() => {
      setError('Failed to copy to clipboard')
    })
  }

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      apiFetch<Contact>(`/api/contacts/${id}`),
      apiFetch<{ mentions: Mention[] }>(`/api/mentions?contact_id=${id}`),
      apiFetch<{ entries: OutreachEntry[] }>(`/api/outreach?contact_id=${id}`),
      apiFetch<{ notes: NoteEntry[] }>(`/api/contacts/${id}/notes`),
      apiFetch<{ connections: ConnectionEntry[] }>(`/api/contacts/${id}/connections`),
      apiFetch<{ tags: { id: number; tag: string }[] }>(`/api/contacts/${id}/tags`),
      apiFetch<{ intro_paths: WarmIntroPath[] }>(`/api/contacts/${id}/warm-intros`),
    ])
      .then(([contactData, mentionsData, outreachData, notesData, connectionsData, tagsData, warmData]) => {
        setContact(contactData)
        setMentions(mentionsData.mentions || [])
        setOutreach(outreachData.entries || [])
        setNotes(notesData.notes || [])
        setConnections(connectionsData.connections || [])
        setTags(tagsData.tags || [])
        setWarmIntros(warmData.intro_paths || [])
        setError(null)
        if (outreachData.entries?.length === 0 && contactData.recommended_contact_method?.method) {
          setForm((f) => ({ ...f, method: contactData.recommended_contact_method!.method }))
        }
      })
      .catch((err) => setError(`Failed to load contact data: ${err.message}`))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    apiFetch<{ contacts: { id: number; name: string }[] }>('/api/contacts?limit=500')
      .then((d) => setContactList(d.contacts?.map((c) => ({ id: c.id, name: c.name })) || []))
      .catch((err) => console.warn('Failed to load contact list:', err.message))
    apiFetch<{ tags: string[] }>('/api/contacts/tags/preset')
      .then((d) => setPresetTags(d.tags || []))
      .catch((err) => console.warn('Failed to load preset tags:', err.message))
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!id) return
    setSubmitting(true)
    const sentAt = new Date().toISOString().slice(0, 19)
    apiFetch('/api/outreach', {
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
      .then(() => {
        setForm({ method: 'email', subject: '', content: '', response_status: 'sent' })
        refreshOutreach()
      })
      .catch((err) => setError(`Failed to log outreach: ${err.message}`))
      .finally(() => setSubmitting(false))
  }

  if (loading || !contact) {
    return (
      <div className="py-8">
        {error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : (
          <p className="text-slate-500">Loading...</p>
        )}
      </div>
    )
  }

  return (
    <div>
      <Link to="/contacts" className="mb-4 inline-block text-sm text-slate-600 hover:text-slate-800">
        &larr; Back to Contacts
      </Link>

      {error && (
        <div className="mb-4 flex items-center justify-between rounded bg-red-50 px-4 py-3 text-sm text-red-800">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)} className="ml-4 font-medium text-red-600 hover:text-red-800">Dismiss</button>
        </div>
      )}

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

        <div className="mt-4 rounded bg-slate-50 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-800">Bio / Interests</h3>
            <button type="button" onClick={handleEnrichBio} disabled={enrichingBio} className="rounded border border-blue-400 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50">
              {enrichingBio ? 'Generating...' : contact.primary_interests ? 'Regenerate bio' : 'Generate bio (AI)'}
            </button>
          </div>
          {contact.primary_interests ? (
            <p className="mt-2 text-slate-600">{contact.primary_interests}</p>
          ) : (
            <p className="mt-2 text-sm text-slate-400">No bio yet. Click &quot;Generate bio&quot; to create one from mentions and role info.</p>
          )}
          {bioMessage && <p className="mt-2 text-xs text-slate-500">{bioMessage}</p>}
        </div>

        {contact.recommended_contact_method && (
          <div className={`mt-4 rounded p-4 ${contact.recommended_contact_method.available ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'}`}>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-slate-800">First-contact recommendation</h3>
              {contact.relationship_stage && (
                <span className="rounded-full bg-slate-200 px-2.5 py-0.5 text-xs font-medium text-slate-700">
                  {contact.relationship_stage}
                </span>
              )}
            </div>
            <p className="mt-1 font-medium text-slate-700">{contact.recommended_contact_method.reason}</p>
            {!contact.recommended_contact_method.available && (
              <p className="mt-2 text-xs text-slate-500">Try adding contact info below or use enrichment to find their email.</p>
            )}
          </div>
        )}

        <div className="mt-4 rounded bg-slate-50 p-4">
          <h3 className="text-sm font-medium text-slate-800">Relationship stage</h3>
          <select value={contact.relationship_stage ?? ''} onChange={(e) => handleStageChange(e.target.value)} disabled={savingStage} className="mt-2 rounded border border-slate-300 bg-white px-3 py-2 text-sm">
            <option value="">—</option>
            {RELATIONSHIP_STAGES.map((s) => (<option key={s} value={s}>{s}</option>))}
          </select>
          {savingStage && <span className="ml-2 text-xs text-slate-500">Saving...</span>}
        </div>

        <div className="mt-4 rounded bg-slate-50 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-800">Mission Alignment</h3>
            <button type="button" onClick={handleAutoAlignment} className="text-xs text-blue-600 hover:underline">Auto-compute</button>
          </div>
          <div className="mt-2 flex items-center gap-3">
            <input type="range" min={1} max={10} step={0.5} value={contact.mission_alignment ?? 5} onChange={(e) => handleAlignmentChange(parseFloat(e.target.value))} className="w-48" />
            <span className={`rounded-full px-2.5 py-0.5 text-sm font-semibold ${
              (contact.mission_alignment ?? 5) >= 8 ? 'bg-green-100 text-green-800' :
              (contact.mission_alignment ?? 5) >= 5 ? 'bg-yellow-100 text-yellow-800' :
              'bg-red-100 text-red-700'
            }`}>
              {contact.mission_alignment ?? '—'} / 10
            </span>
          </div>
        </div>

        <div className="mt-4 rounded bg-slate-50 p-4">
          <h3 className="text-sm font-medium text-slate-800">Tags</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {tags.map((t) => (
              <span key={t.id} className="inline-flex items-center gap-1 rounded-full bg-slate-200 px-3 py-1 text-xs font-medium text-slate-700">
                {t.tag}
                <button type="button" onClick={() => handleRemoveTag(t.id)} className="ml-1 text-slate-500 hover:text-red-600">x</button>
              </span>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap gap-1">
            {presetTags.filter((pt) => !tags.some((t) => t.tag === pt)).map((pt) => (
              <button key={pt} type="button" onClick={() => handleAddTag(pt)} className="rounded-full border border-dashed border-slate-400 px-2.5 py-1 text-xs text-slate-600 hover:border-slate-600 hover:bg-slate-100">
                + {pt}
              </button>
            ))}
          </div>
          <div className="mt-2 flex gap-2">
            <input type="text" value={customTag} onChange={(e) => setCustomTag(e.target.value)} placeholder="Custom tag..." className="rounded border border-slate-300 px-2 py-1 text-xs" onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddTag(customTag) } }} />
            <button type="button" onClick={() => handleAddTag(customTag)} disabled={!customTag.trim()} className="rounded bg-slate-600 px-2 py-1 text-xs text-white hover:bg-slate-500 disabled:opacity-50">Add</button>
          </div>
        </div>

        {contact.contact_info && contact.contact_info.length > 0 && (
          <div className="mt-4 rounded bg-slate-50 p-4">
            <h3 className="text-sm font-medium text-slate-800">Contact info</h3>
            <ul className="mt-2 space-y-1">
              {contact.contact_info.map((ci) => {
                const ciKey = `${ci.type}-${ci.value}`
                return (
                <li key={ciKey} className="flex items-center gap-2 text-sm">
                  <span className="font-medium text-slate-600">{ci.type}:</span>
                  <span className="text-slate-700">{ci.value}</span>
                  <button type="button" onClick={() => copyToClipboard(ci.value, ciKey)} className={`text-xs ${copiedIndex === ciKey ? 'text-green-600 font-medium' : 'text-blue-600 hover:underline'}`}>
                    {copiedIndex === ciKey ? 'Copied!' : 'Copy'}
                  </button>
                </li>
                )
              })}
            </ul>
          </div>
        )}

        {!hasEmail && contact.role_org && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button type="button" onClick={handleEnrich} disabled={enriching} className="rounded border border-emerald-500 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-50">
              {enriching ? 'Looking up...' : 'Enrich (find email via Hunter)'}
            </button>
            {enrichMessage && <span className="text-sm text-slate-600">{enrichMessage}</span>}
          </div>
        )}

        <form onSubmit={handleAddContactInfo} className="mt-4 rounded border border-slate-200 bg-white p-4">
          <h3 className="text-sm font-medium text-slate-800">Add contact info</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            <select value={contactInfoForm.type} onChange={(e) => setContactInfoForm((f) => ({ ...f, type: e.target.value }))} className="rounded border border-slate-300 px-3 py-2 text-sm">
              <option value="email">Email</option>
              <option value="linkedin">LinkedIn</option>
              <option value="twitter">Twitter</option>
              <option value="website">Website</option>
              <option value="phone">Phone</option>
              <option value="other">Other</option>
            </select>
            <input type="text" value={contactInfoForm.value} onChange={(e) => setContactInfoForm((f) => ({ ...f, value: e.target.value }))} placeholder="e.g. name@example.com or LinkedIn URL" className="min-w-[200px] rounded border border-slate-300 px-3 py-2 text-sm" />
            <button type="submit" disabled={addingInfo || !contactInfoForm.value.trim()} className="rounded bg-slate-700 px-4 py-2 text-sm text-white hover:bg-slate-600 disabled:opacity-50">
              {addingInfo ? 'Adding...' : 'Add'}
            </button>
          </div>
        </form>
      </div>

      <div className="mb-8 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Conversation notes</h2>
        <form onSubmit={handleAddNote} className="mb-6 rounded border border-slate-200 bg-slate-50 p-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm font-medium text-slate-700">Note</label>
              <textarea value={noteForm.note_text} onChange={(e) => setNoteForm((f) => ({ ...f, note_text: e.target.value }))} placeholder="Call summary, follow-up, key points..." rows={2} className="w-full rounded border border-slate-300 px-3 py-2 text-sm" required />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Date</label>
              <input type="date" value={noteForm.note_date} onChange={(e) => setNoteForm((f) => ({ ...f, note_date: e.target.value }))} className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Channel (optional)</label>
              <select value={noteForm.channel} onChange={(e) => setNoteForm((f) => ({ ...f, channel: e.target.value }))} className="w-full rounded border border-slate-300 px-3 py-2 text-sm">
                {NOTE_CHANNELS.map((ch) => (<option key={ch || 'none'} value={ch}>{ch || '—'}</option>))}
              </select>
            </div>
          </div>
          <button type="submit" disabled={addingNote || !noteForm.note_text.trim()} className="mt-4 rounded bg-slate-700 px-4 py-2 text-sm text-white hover:bg-slate-600 disabled:opacity-50">
            {addingNote ? 'Adding...' : 'Add note'}
          </button>
        </form>
        {notes.length === 0 ? (
          <p className="text-slate-500">No notes yet.</p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {notes.map((n) => (
              <li key={n.id} className="py-4">
                <p className="text-slate-800">{n.note_text}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {n.note_date ? new Date(n.note_date).toLocaleDateString() : ''}
                  {n.channel ? ` • ${n.channel}` : ''}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mb-8 rounded-lg bg-white p-6 shadow">
        <h2 className="mb-4 text-lg font-semibold text-slate-800">Related to others on the list</h2>
        <p className="mb-4 text-sm text-slate-600">First/second degree: how this contact is connected to others on the list. Add manually below, or run discovery to find co-mentions in news (same conference, article, podcast).</p>
        <div className="mb-4 flex flex-wrap gap-2">
          <button type="button" onClick={handleDiscoverConnections} disabled={discovering} className="rounded border border-slate-400 bg-slate-100 px-4 py-2 text-sm text-slate-800 hover:bg-slate-200 disabled:opacity-50">
            {discovering ? 'Discovering… (check back in a minute)' : 'Discover connections (web search)'}
          </button>
        </div>
        <form onSubmit={handleAddConnection} className="mb-6 rounded border border-slate-200 bg-slate-50 p-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Other contact</label>
              <select value={connectionForm.other_contact_id} onChange={(e) => setConnectionForm((f) => ({ ...f, other_contact_id: e.target.value }))} className="w-full rounded border border-slate-300 px-3 py-2 text-sm" required>
                <option value="">Select...</option>
                {contactList.filter((c) => c.id !== contact?.id).map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Relationship type</label>
              <select value={connectionForm.relationship_type} onChange={(e) => setConnectionForm((f) => ({ ...f, relationship_type: e.target.value }))} className="w-full rounded border border-slate-300 px-3 py-2 text-sm">
                {CONNECTION_TYPES.map((t) => (<option key={t} value={t}>{t.replace('_', ' ')}</option>))}
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm font-medium text-slate-700">Notes (optional)</label>
              <input type="text" value={connectionForm.notes} onChange={(e) => setConnectionForm((f) => ({ ...f, notes: e.target.value }))} placeholder="e.g. co-author on X paper, same lab 2020" className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
            </div>
          </div>
          <button type="submit" disabled={addingConnection || !connectionForm.other_contact_id} className="mt-4 rounded bg-slate-700 px-4 py-2 text-sm text-white hover:bg-slate-600 disabled:opacity-50">
            {addingConnection ? 'Adding...' : 'Add connection'}
          </button>
        </form>
        {connections.length === 0 ? (
          <p className="text-slate-500">No connections recorded yet.</p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {connections.map((conn) => (
              <li key={conn.id} className="flex items-start justify-between py-4">
                <div>
                  <Link to={`/contacts/${conn.other_contact_id}`} className="font-medium text-slate-800 hover:text-slate-600">
                    {conn.other_contact_name ?? `Contact #${conn.other_contact_id}`}
                  </Link>
                  <p className="text-sm text-slate-600">{conn.relationship_type.replace('_', ' ')}</p>
                  {conn.notes && <p className="mt-1 text-xs text-slate-500">{conn.notes}</p>}
                </div>
                <button type="button" onClick={() => handleDeleteConnection(conn.id)} className="text-sm text-red-600 hover:text-red-800">Remove</button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {warmIntros.length > 0 && (
        <div className="mb-8 rounded-lg bg-white p-6 shadow">
          <h2 className="mb-4 text-lg font-semibold text-slate-800">Warm Intro Paths</h2>
          <p className="mb-3 text-sm text-slate-500">People who could introduce you to {contact.name}, ranked by intro strength.</p>
          <ul className="divide-y divide-slate-200">
            {warmIntros.map((path) => (
              <li key={path.connector_id} className="flex items-center justify-between py-3">
                <div>
                  <Link to={`/contacts/${path.connector_id}`} className="font-medium text-slate-800 hover:text-slate-600">{path.connector_name}</Link>
                  <p className="text-xs text-slate-500">
                    {path.relationship_to_target} with {contact.name}
                    {path.connector_stage && ` — Your stage: ${path.connector_stage}`}
                    {path.has_replied && ' — Has replied to you'}
                  </p>
                </div>
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                  path.intro_strength >= 0.7 ? 'bg-green-100 text-green-800' :
                  path.intro_strength >= 0.4 ? 'bg-yellow-100 text-yellow-800' :
                  'bg-slate-100 text-slate-600'
                }`}>
                  {Math.round(path.intro_strength * 100)}% strength
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mb-8 rounded-lg bg-white p-6 shadow">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">Mentions</h2>
          <div className="flex items-center gap-2">
            <button type="button" onClick={handleFetchMedia} disabled={fetchingMedia} className="rounded border border-purple-400 bg-purple-50 px-3 py-1 text-xs font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-50">
              {fetchingMedia ? 'Searching...' : 'Fetch podcasts, videos, speeches'}
            </button>
            {mediaMessage && <span className="text-xs text-slate-500">{mediaMessage}</span>}
          </div>
        </div>
        {mentions.length === 0 ? (
          <p className="text-slate-500">No mentions yet.</p>
        ) : (
          <ul className="divide-y divide-slate-200">
            {mentions.map((m) => (
              <li key={m.id} className="py-4">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                    m.source_type === 'news' ? 'bg-blue-100 text-blue-800' :
                    m.source_type === 'podcast' ? 'bg-purple-100 text-purple-800' :
                    m.source_type === 'video' ? 'bg-red-100 text-red-800' :
                    m.source_type === 'speech' ? 'bg-amber-100 text-amber-800' :
                    'bg-slate-100 text-slate-700'
                  }`}>
                    {m.source_type}
                  </span>
                  <p className="font-medium text-slate-800">{m.title || m.snippet?.slice(0, 80)}</p>
                </div>
                <p className="mt-1 text-sm text-slate-500">{m.published_at ? new Date(m.published_at).toLocaleDateString() : 'Unknown date'}</p>
                {m.source_url && (
                  <a href={m.source_url} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">View source</a>
                )}
                {m.source_type === 'linkedin' && (
                  <button type="button" onClick={() => handleGenerateDraft(m.id)} className="mt-2 rounded border border-indigo-400 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100">
                    Draft Reply
                  </button>
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
              <select value={form.method} onChange={(e) => setForm((f) => ({ ...f, method: e.target.value }))} className="w-full rounded border border-slate-300 px-3 py-2 text-sm">
                {METHODS.map((m) => (<option key={m} value={m}>{m}</option>))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Response status</label>
              <select value={form.response_status} onChange={(e) => setForm((f) => ({ ...f, response_status: e.target.value }))} className="w-full rounded border border-slate-300 px-3 py-2 text-sm">
                {RESPONSE_STATUSES.map((s) => (<option key={s} value={s}>{s.replace('_', ' ')}</option>))}
              </select>
            </div>
          </div>
          <div className="mt-4">
            <label className="mb-1 block text-sm font-medium text-slate-700">Subject (optional)</label>
            <input type="text" value={form.subject} onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))} placeholder="Email subject line" className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div className="mt-4">
            <label className="mb-1 block text-sm font-medium text-slate-700">Content / notes (optional)</label>
            <textarea value={form.content} onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))} placeholder="Brief summary or copy of message" rows={3} className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <button type="submit" disabled={submitting} className="mt-4 rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50">
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
      {draftModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-800">LinkedIn Reply Draft</h2>
              <button type="button" onClick={() => setDraftModal(null)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>

            {draftModal.generating ? (
              <p className="py-8 text-center text-slate-500">Generating draft via Claude...</p>
            ) : (
              <>
                {draftModal.draft?.themes && draftModal.draft.themes.length > 0 && (
                  <div className="mb-3 flex flex-wrap gap-1">
                    {draftModal.draft.themes.map((t) => (
                      <span key={t} className="rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-700">{t}</span>
                    ))}
                  </div>
                )}
                <textarea
                  value={draftModal.editText}
                  onChange={(e) => setDraftModal((d) => d ? { ...d, editText: e.target.value } : null)}
                  rows={6}
                  className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                />
                {draftModal.draft && (
                  <p className="mt-1 text-xs text-slate-400">
                    Status: <span className="font-medium">{draftModal.draft.status}</span>
                  </p>
                )}
                <div className="mt-4 flex flex-wrap gap-2">
                  <button type="button" onClick={() => copyToClipboard(draftModal.editText, 'draft')} className={`rounded border px-3 py-1.5 text-sm font-medium ${copiedIndex === 'draft' ? 'border-green-400 bg-green-50 text-green-700' : 'border-slate-400 bg-slate-50 text-slate-700 hover:bg-slate-100'}`}>
                    {copiedIndex === 'draft' ? 'Copied!' : 'Copy to clipboard'}
                  </button>
                  {draftModal.draft && draftModal.draft.status !== 'used' && (
                    <button type="button" onClick={() => handleUpdateDraftStatus('used')} className="rounded border border-green-500 bg-green-50 px-3 py-1.5 text-sm font-medium text-green-700 hover:bg-green-100">
                      Mark as Used
                    </button>
                  )}
                  {draftModal.draft && draftModal.draft.status !== 'archived' && (
                    <button type="button" onClick={() => handleUpdateDraftStatus('archived')} className="rounded border border-amber-400 bg-amber-50 px-3 py-1.5 text-sm font-medium text-amber-700 hover:bg-amber-100">
                      Archive
                    </button>
                  )}
                  {draftModal.draft && (
                    <button type="button" onClick={handleDeleteDraft} className="rounded border border-red-400 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100">
                      Delete
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
