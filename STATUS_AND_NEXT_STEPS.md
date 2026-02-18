# Solomon Outreach — Status & Next Steps

**Original goal:** Daily search for mentions of 300 names across news, podcasts, presentations, speeches; record contact info and bios; track outreach; recommend contact methods for first-time recipients; keep conversation notes for follow-ups. Ultimate aim: reach AI engineers, nonprofit funders, and tech leaders interested in "AI for Good" — funding, partnerships, awareness, AI community engagement.

---

## Where We Are

### ✅ Done (Phase 1 + Modifications)

| Original Request | Status | Notes |
|------------------|--------|-------|
| **Daily search for mentions** | ✅ | News via NewsAPI; scheduled 8am + manual "Refresh" button |
| **300 names** | ✅ | 305 contacts from Names file, parsed and seeded |
| **News reports** | ✅ | NewsAPI integration |
| **Record contact info** | ⚠️ Structure only | `contact_info` table exists; no enrichment yet |
| **Record bio** | ⚠️ Partial | `connection_to_solomon` + `role_org` from Names; no auto-enrichment |
| **Interconnections with others on list** | ✅ | `contact_connections` table + UI (first/second degree, same_org, co_author) |
| **Relevance to Solomon** | ⚠️ Partial | `connection_to_solomon` from Names; no scoring |
| **Primary interests/concerns** | ⚠️ Structure only | `primary_interests` field exists; empty |
| **Track outreach method and content** | ✅ | Outreach log with form (method, subject, content, response status) |
| **First-time contact recommendations** | ✅ | Email > LinkedIn > Twitter > website on contact detail |
| **Notes for subsequent contacts** | ✅ | Notes table + form + timeline; relationship stage (Cold/Warm/Engaged/Partner-Advocate) |
| **Podcasts, presentations, speeches** | ❌ | News only |

### Modifications We Made

- **Max 2 mentions per contact** — Avoid overload; focus on most recent
- **Contacts out of rotation once contacted** — Skip fetch for anyone with outreach logged
- **Filter by published date** — Dashboard shows news from last 7 days by publish date
- **URL deduplication** — Normalize URLs to avoid ?utm_ duplicates

---

## Gap Summary

| Capability | Gap |
|------------|-----|
| **Media sources** | News only; no podcasts, presentations, speeches |
| **Contact enrichment** | No email/LinkedIn lookup (Hunter, Kaspr) |
| **First-contact recommendations** | No "use email first" / "LinkedIn (email not found)" logic |
| **Conversation notes** | ✅ Done — notes + timeline + relationship stage |
| **Interconnections** | ✅ Basic — contact_connections (first/second degree, same_org, co_author) |
| **Relevance scoring** | No 0–10 or keyword-based scoring |

---

## Proposed Next Steps (Priority Order)

### 1. **Phase 2A: First-Contact Recommendations** (1–2 days)
*Directly from original request*

- Add logic: if contact has email → recommend "Email"; else LinkedIn; else Twitter; else website
- Show "Recommended: Email (available)" or "Recommended: LinkedIn (email not found)" on contact detail
- Uses existing `contact_info` table; can start with manual entry, then enrich later

### 2. **Phase 2B: Conversation Notes** ✅ Done
*For subsequent contacts / follow-ups*

- `notes` table: contact_id, note_text, note_date, optional channel
- Notes form + timeline on contact detail
- Relationship stage (Cold / Warm / Engaged / Partner-Advocate) on contact
- Contact connections: how this contact is related to others on the list (first_degree, second_degree, same_org, co_author) with add/remove UI

### 3. **Phase 2C: Contact Enrichment** (2–3 days)
*Email, LinkedIn, bio*

- Hunter API (or Kaspr) for email lookup by name + org
- Store in `contact_info`; display with Copy buttons
- Bio: combine `connection_to_solomon` + `role_org`; optional LLM summary from mention snippet

### 4. **Phase 2D: Additional Media Sources** (2–4 days)
*Podcasts, presentations, speeches*

- Podcasts: Listen Notes API or RSS + transcript search
- Presentations: YouTube API, conference sites
- Speeches: SerpApi, C-SPAN, manual
- Depends on API budget and availability

### 5. **Phase 3: Interconnections & Warm Intros** (3–4 days)
*"Person A knows Person B"*

- Parse "works with X," "co-author with Y" from Names
- Manual add: link two contacts
- UI: "You could ask [Person A] for an intro to [Person B]"

---

## Recommended Immediate Next Step

**Phase 2C: Contact Enrichment** — Hunter/Kaspr for email/LinkedIn lookup; or **Phase 2D: Additional Media Sources** (podcasts, presentations).

---

*Last updated: Feb 2025*
