import { useEffect, useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import ForceGraph2D from 'react-force-graph-2d'

interface MapNode {
  id: number
  name: string
  category: string | null
  relationship_stage: string | null
}

interface MapLink {
  source_id: number
  target_id: number
  relationship_type: string
}

interface GraphNode extends MapNode {
  x?: number
  y?: number
  __matched?: boolean
}

interface GraphLink {
  source: number
  target: number
  relationship_type?: string
}

function matchesSearch(node: MapNode, q: string): boolean {
  if (!q.trim()) return true
  const lower = q.trim().toLowerCase()
  const name = (node.name ?? '').toLowerCase()
  const category = (node.category ?? '').toLowerCase()
  return name.includes(lower) || category.includes(lower)
}

export default function RelationshipMap() {
  const navigate = useNavigate()
  const [nodes, setNodes] = useState<MapNode[]>([])
  const [links, setLinks] = useState<MapLink[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [discoveringFromMentions, setDiscoveringFromMentions] = useState(false)
  const [discoveringAll, setDiscoveringAll] = useState(false)

  const loadMap = useCallback(() => {
    setLoading(true)
    setError(null)
    fetch('/api/relationship-map')
      .then((r) => r.json())
      .then((data) => {
        setNodes(data.nodes || [])
        setLinks(data.links || [])
      })
      .catch((e) => setError(e.message || 'Failed to load map'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadMap()
  }, [loadMap])

  const { graphData, visibleCount, matchCount, isFiltered } = useMemo(() => {
    const fullLinks = links.map((l) => ({ source: l.source_id, target: l.target_id, relationship_type: l.relationship_type })) as GraphLink[]
    if (!search.trim()) {
      return {
        graphData: {
          nodes: nodes.map((n) => ({ ...n, __matched: true })) as GraphNode[],
          links: fullLinks,
        },
        visibleCount: nodes.length,
        matchCount: nodes.length,
        isFiltered: false,
      }
    }
    const q = search.trim().toLowerCase()
    const matchingIds = new Set(nodes.filter((n) => matchesSearch(n, search)).map((n) => n.id))
    const neighborIds = new Set<number>(matchingIds)
    links.forEach((l) => {
      if (matchingIds.has(l.source_id)) neighborIds.add(l.target_id)
      if (matchingIds.has(l.target_id)) neighborIds.add(l.source_id)
    })
    const visibleIds = neighborIds
    const filteredNodes = nodes.filter((n) => visibleIds.has(n.id)).map((n) => ({
      ...n,
      __matched: matchingIds.has(n.id),
    })) as GraphNode[]
    const filteredLinks = fullLinks.filter(
      (l) => visibleIds.has(l.source) && visibleIds.has(l.target),
    )
    return {
      graphData: { nodes: filteredNodes, links: filteredLinks },
      visibleCount: filteredNodes.length,
      matchCount: matchingIds.size,
      isFiltered: true,
    }
  }, [nodes, links, search])

  const handleNodeClick = (node: GraphNode) => {
    navigate(`/contacts/${node.id}`)
  }

  const handleDiscoverFromMentions = () => {
    setDiscoveringFromMentions(true)
    fetch('/api/jobs/discover-connections-from-mentions', { method: 'POST' })
      .then((r) => r.json())
      .then(() => {
        setTimeout(() => {
          loadMap()
          setDiscoveringFromMentions(false)
        }, 3000)
      })
      .catch(() => setDiscoveringFromMentions(false))
  }

  const handleDiscoverAll = () => {
    setDiscoveringAll(true)
    fetch('/api/jobs/discover-all-connections', { method: 'POST' })
      .then((r) => r.json())
      .then(() => {
        setTimeout(() => {
          loadMap()
          setDiscoveringAll(false)
        }, 5000)
      })
      .catch(() => setDiscoveringAll(false))
  }

  if (loading) {
    return (
      <div className="py-8">
        <p className="text-slate-500">Loading relationship map...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="py-8">
        <p className="text-red-600">{error}</p>
        <button
          type="button"
          onClick={loadMap}
          className="mt-2 rounded bg-slate-700 px-4 py-2 text-sm text-white hover:bg-slate-600"
        >
          Retry
        </button>
      </div>
    )
  }

  const hasConnections = links.length > 0

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Relationship map</h1>
          <p className="mt-1 text-sm text-slate-600">
            How everyone on the list is connected. Search to focus on matching contacts and their connections; the map updates as you type.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="search"
            placeholder="Search by name or category..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="min-w-[200px] rounded border border-slate-300 px-3 py-2 text-sm placeholder:text-slate-400 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
            aria-label="Search contacts to focus map"
          />
          {search.trim() && (
            <button
              type="button"
              onClick={() => setSearch('')}
              className="rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            >
              Clear
            </button>
          )}
          <button
            type="button"
            onClick={loadMap}
            className="rounded bg-slate-700 px-4 py-2 text-sm text-white hover:bg-slate-600"
          >
            Refresh
          </button>
          <button
            type="button"
            onClick={handleDiscoverAll}
            disabled={discoveringAll || discoveringFromMentions}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
            title="Agentic: scan mentions (LLM-enriched when Anthropic key set) + web search. ~2–3 min."
          >
            {discoveringAll ? 'Discovering all…' : 'Discover all connections'}
          </button>
          <button
            type="button"
            onClick={handleDiscoverFromMentions}
            disabled={discoveringAll || discoveringFromMentions}
            className="rounded border border-slate-400 bg-slate-100 px-4 py-2 text-sm text-slate-800 hover:bg-slate-200 disabled:opacity-50"
            title="Scan existing mention snippets only. No extra API calls."
          >
            {discoveringFromMentions ? 'Running…' : 'From mentions only'}
          </button>
        </div>
      </div>

      {!hasConnections && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          No connections yet. Add connections on contact detail pages (“Related to others on the list”) to see the network here.
        </div>
      )}

      <div className="rounded-lg border border-slate-200 bg-white shadow" style={{ height: '70vh', minHeight: 400 }}>
        <ForceGraph2D
          graphData={graphData}
          nodeId="id"
          nodeLabel={(n) => (n as GraphNode).name}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const n = node as GraphNode
            const label = n.name ?? String(n.id)
            const fontSize = 12 / globalScale
            ctx.font = `${fontSize}px Sans-Serif`
            const textWidth = ctx.measureText(label).width
            const bgrPadding = 2
            const bgrWidth = textWidth + bgrPadding * 2
            const bgrHeight = fontSize + bgrPadding * 2
            const isMatch = n.__matched !== false
            ctx.fillStyle = isMatch ? 'rgba(255,255,255,0.95)' : 'rgba(241,245,249,0.9)'
            ctx.strokeStyle = isMatch ? 'rgba(30,41,59,0.4)' : 'rgba(148,163,184,0.4)'
            ctx.lineWidth = (isMatch ? 1.5 : 1) / globalScale
            ctx.beginPath()
            ctx.rect((n.x ?? 0) - bgrWidth / 2, (n.y ?? 0) - bgrHeight / 2, bgrWidth, bgrHeight)
            ctx.fill()
            ctx.stroke()
            ctx.textAlign = 'center'
            ctx.textBaseline = 'middle'
            ctx.fillStyle = isMatch ? 'rgb(30,41,59)' : 'rgb(100,116,139)'
            ctx.fillText(label, n.x ?? 0, n.y ?? 0)
          }}
          linkColor={() => 'rgba(148,163,184,0.6)'}
          linkWidth={1}
          onNodeClick={(node) => handleNodeClick(node as GraphNode)}
          nodePointerAreaPaint={(node, color, ctx) => {
            const n = node as GraphNode
            ctx.fillStyle = color
            ctx.beginPath()
            ctx.arc(n.x ?? 0, n.y ?? 0, 8, 0, 2 * Math.PI)
            ctx.fill()
          }}
        />
      </div>

      <p className="mt-2 text-xs text-slate-500">
        {isFiltered ? (
          <>Showing {visibleCount} contacts ({matchCount} matching "{search.trim()}" + their connections). Clear search to show all.</>
        ) : (
          <>{nodes.length} contacts, {links.length} connections.</>
        )}{' '}
        Click a node to open the contact.
      </p>
    </div>
  )
}
