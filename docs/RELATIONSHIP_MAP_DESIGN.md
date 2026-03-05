# Relationship Map — Design

**Goal:** A single view that shows how everyone on the list is connected, and stays correct as names and connections are added or removed.

---

## Data we already have

- **Nodes:** All contacts (from `contacts` table). When you add/remove names in the Names file and re-run parse + seed, the contact list changes.
- **Edges:** `contact_connections` (contact_id → other_contact_id, relationship_type, notes). Edges are added/removed from the contact detail page (“Related to others on the list”).

So the map is **always derived from current DB state**: no separate “map” store.

---

## How it stays updateable

| Change | How it’s reflected on the map |
|--------|-------------------------------|
| **Add a name** | Add in Names file → run parse_names.py → re-seed (or future “sync” that adds new contacts). Next time the map loads, it fetches nodes/edges from the API; the new contact appears as a node (no edges until you add connections). |
| **Remove a name** | Remove from Names file → re-seed with `--reset`. That recreates tables from contacts.json, so the contact and any edges involving them disappear. If we later add “delete one contact” without full reset, we should delete their connection rows (or use FK `ON DELETE CASCADE` on `contact_connections`). |
| **Add/remove a connection** | Done on contact detail (“Related to others on the list”). Map fetches data on load (and can refetch); new or removed edges show up. |

So: **one source of truth** (contacts + contact_connections). Map is a read-only view over that. No special “map update” logic beyond normal add/remove of names and connections.

---

## API

**`GET /api/relationship-map`**

Returns:

- **nodes:** `[{ id, name, category?, relationship_stage? }]` — all contacts (optionally limit/filter for very large lists later).
- **links:** `[{ source_id, target_id, relationship_type? }]` — all rows from `contact_connections` (source_id = contact_id, target_id = other_contact_id).

Frontend builds a graph from this. Refetch after navigating back to the map (or add a “Refresh” button) so new names and connection changes are visible.

---

## Frontend

- **Route:** e.g. `/map` or `/relationship-map`.
- **Graph:** 2D force-directed (react-force-graph-2d): nodes = contacts, links = connections. Click node → go to contact detail.
- **Search (self-implementing):** Search by name or category; the map updates as you type. Shows matching contacts + everyone connected to them; matching nodes highlighted, neighbors dimmed. Clear search to show full graph. Client-side only.
- **Empty state:** If there are no connections yet, show all nodes with a message: “Add connections on contact detail pages to see the network.”

---

## Connection discovery (automatic from web / mentions)

The system can **discover** connections so the map builds itself from real-world co-occurrence:

1. **From mention snippets (no extra API):** **"Discover from mentions"** (Map page) scans every stored mention's title + snippet for other contact names. When person B's name appears in an article about person A, it adds a connection `mentioned_together` with the source URL in notes. Use after fetching mentions.
2. **Via web search (NewsAPI):** **"Discover connections (web search)"** (contact detail) runs NewsAPI for this contact vs others (same category, up to 20 pairs). When news co-mentions both, it adds `co_mentioned_news` with the article URL. Requires NEWSAPI_KEY.

---

## Optional later

- **Filter:** Only show nodes with at least one connection; or filter by category.
- **Sync from Names file:** After editing the Names file, a “Sync contacts” action that adds new contacts and optionally marks or removes contacts no longer in the file (instead of full `--reset`), so the map updates without wiping the DB.
- **FK cascade:** On `contact_connections.contact_id` and `other_contact_id`, set `ON DELETE CASCADE` so deleting a contact (if we add that) automatically removes their edges.

---

*Design for the Solomon Outreach relationship map. Keeps the map updateable by deriving it from the same data that add/remove of names and connections already update.*
