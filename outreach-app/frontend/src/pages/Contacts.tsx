import { useEffect, useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api'

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
  in_mention_rotation?: boolean
  recommended_contact_method?: ContactRecommendation
}

export default function Contacts() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [rotationOnly, setRotationOnly] = useState(false)
  const [togglingId, setTogglingId] = useState<number | null>(null)
  const [bulkEnriching, setBulkEnriching] = useState(false)
  const [enrichStatus, setEnrichStatus] = useState<string | null>(null)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<{
    created: number
    updated: number
    info_added: number
    info_skipped_duplicates: number
    skipped_rows: { row: number; reason: string }[]
    created_names: string[]
    updated_names: string[]
  } | null>(null)
  const [importError, setImportError] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const enrichPollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (enrichPollRef.current) clearInterval(enrichPollRef.current)
    }
  }, [])

  // Debounce search input by 300ms
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => setDebouncedSearch(search), 300)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [search])

  const loadContacts = () => {
    const params = new URLSearchParams({ limit: '100' })
    if (debouncedSearch) params.set('q', debouncedSearch)
    if (rotationOnly) params.set('in_rotation', '1')
    return apiFetch<{ contacts: Contact[]; total: number }>(`/api/contacts?${params}`)
      .then((data) => {
        setContacts(data.contacts || [])
        setTotal(data.total || 0)
        setError(null)
      })
      .catch((err) => setError(`Failed to load contacts: ${err.message}`))
  }

  useEffect(() => {
    setLoading(true)
    loadContacts().finally(() => setLoading(false))
  }, [debouncedSearch, rotationOnly])

  const toggleRotation = (c: Contact) => {
    setTogglingId(c.id)
    apiFetch(`/api/contacts/${c.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ in_mention_rotation: !c.in_mention_rotation }),
    })
      .then(() => {
        setContacts((prev) =>
          prev.map((x) => (x.id === c.id ? { ...x, in_mention_rotation: !x.in_mention_rotation } : x)),
        )
      })
      .catch((err) => setError(`Toggle failed: ${err.message}`))
      .finally(() => setTogglingId(null))
  }

  const handleBulkEnrich = () => {
    setBulkEnriching(true)
    setEnrichStatus('Starting bulk enrichment...')
    if (enrichPollRef.current) {
      clearInterval(enrichPollRef.current)
      enrichPollRef.current = null
    }
    apiFetch<{ detail?: string; message?: string }>('/api/jobs/enrich-all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ max_contacts: 50 }),
    })
      .then((d) => {
        if (d.detail) {
          setEnrichStatus(d.detail)
          setBulkEnriching(false)
        } else {
          setEnrichStatus(d.message || 'Running...')
          enrichPollRef.current = setInterval(() => {
            apiFetch<{ status: string; found?: number; attempted?: number; skipped?: number }>('/api/jobs/enrich-status')
              .then((s) => {
                if (s.status === 'complete') {
                  if (enrichPollRef.current) clearInterval(enrichPollRef.current)
                  enrichPollRef.current = null
                  setEnrichStatus(`Done: ${s.found} emails found, ${s.attempted} attempted, ${s.skipped} skipped`)
                  setBulkEnriching(false)
                  loadContacts()
                }
              })
              .catch((err) => {
                if (enrichPollRef.current) clearInterval(enrichPollRef.current)
                enrichPollRef.current = null
                setEnrichStatus(`Enrichment status check failed: ${err.message}`)
                setBulkEnriching(false)
              })
          }, 5000)
        }
      })
      .catch((err) => {
        setEnrichStatus(`Bulk enrichment failed: ${err.message}`)
        setBulkEnriching(false)
      })
  }

  const [addNames, setAddNames] = useState('')
  const [addingContacts, setAddingContacts] = useState(false)
  const [addResult, setAddResult] = useState<string | null>(null)

  const handleAddContacts = () => {
    if (!addNames.trim()) return
    setAddingContacts(true)
    setAddResult(null)
    apiFetch<{ added: string[]; skipped: string[]; message: string }>('/api/contacts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ names: addNames }),
    })
      .then((d) => {
        setAddResult(d.message)
        setAddNames('')
        loadContacts()
      })
      .catch((err) => setAddResult(`Failed: ${err.message}`))
      .finally(() => setAddingContacts(false))
  }

  const handleImportCSV = () => fileInputRef.current?.click()

  const handleFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setImporting(true)
    setImportResult(null)
    setImportError(null)

    const formData = new FormData()
    formData.append('file', file)

    fetch('/api/contacts/import-csv', { method: 'POST', body: formData })
      .then(async (res) => {
        if (!res.ok) {
          let detail = res.statusText
          try {
            const body = await res.json()
            detail = body.detail || body.message || JSON.stringify(body)
          } catch { /* keep statusText */ }
          throw new Error(`${res.status}: ${detail}`)
        }
        return res.json()
      })
      .then((data) => {
        setImportResult(data)
        loadContacts()
      })
      .catch((err) => setImportError(err.message || 'Import failed'))
      .finally(() => {
        setImporting(false)
        if (fileInputRef.current) fileInputRef.current.value = ''
      })
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-slate-800">Contacts</h1>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          type="text"
          placeholder="Add contacts by name (comma-separated)..."
          value={addNames}
          onChange={(e) => setAddNames(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleAddContacts() }}
          className="w-full max-w-md rounded-md border border-slate-300 px-4 py-2 text-sm focus:border-slate-500 focus:outline-none"
        />
        <button
          type="button"
          onClick={handleAddContacts}
          disabled={addingContacts || !addNames.trim()}
          className="rounded-md bg-slate-700 px-4 py-2 text-sm text-white hover:bg-slate-600 disabled:opacity-50"
        >
          {addingContacts ? 'Adding...' : 'Add'}
        </button>
        {addResult && <span className="text-sm text-slate-600">{addResult}</span>}
      </div>

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
        <button
          type="button"
          onClick={handleBulkEnrich}
          disabled={bulkEnriching}
          className="rounded border border-emerald-500 bg-emerald-50 px-3 py-1.5 text-sm font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
        >
          {bulkEnriching ? 'Enriching...' : 'Bulk enrich emails'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileSelected}
          className="hidden"
        />
        <button
          type="button"
          onClick={handleImportCSV}
          disabled={importing}
          className="rounded border border-blue-500 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50"
        >
          {importing ? 'Importing...' : 'Import CSV'}
        </button>
        {enrichStatus && (
          <span className="text-sm text-slate-600">{enrichStatus}</span>
        )}
      </div>

      {importError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <div className="flex items-center justify-between">
            <span>CSV import failed: {importError}</span>
            <button type="button" onClick={() => setImportError(null)}
              className="ml-4 text-xs font-medium text-red-600 hover:text-red-800">Dismiss</button>
          </div>
        </div>
      )}

      {importResult && (
        <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-4 text-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-green-800">CSV Import Complete</h3>
            <button type="button" onClick={() => setImportResult(null)}
              className="text-xs text-green-600 hover:text-green-800">Dismiss</button>
          </div>
          <div className="mt-2 flex flex-wrap gap-4 text-green-700">
            <span>{importResult.created} created</span>
            <span>{importResult.updated} updated</span>
            <span>{importResult.info_added} info entries added</span>
            {importResult.info_skipped_duplicates > 0 && (
              <span className="text-slate-500">{importResult.info_skipped_duplicates} duplicates skipped</span>
            )}
          </div>
          {importResult.created_names.length > 0 && (
            <p className="mt-2 text-xs text-green-600">
              New contacts: {importResult.created_names.join(', ')}
            </p>
          )}
          {importResult.skipped_rows.length > 0 && (
            <div className="mt-2 text-xs text-amber-700">
              Skipped rows: {importResult.skipped_rows.map(
                (s) => `Row ${s.row}: ${s.reason}`
              ).join('; ')}
            </div>
          )}
        </div>
      )}

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
                  Recommended
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
                    {c.recommended_contact_method ? (
                      <span
                        title={c.recommended_contact_method.reason}
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          c.recommended_contact_method.available
                            ? 'bg-green-100 text-green-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {c.recommended_contact_method.method}
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400">-</span>
                    )}
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
