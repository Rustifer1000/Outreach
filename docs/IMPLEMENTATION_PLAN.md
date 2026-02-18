# Solomon Outreach Application — Implementation Plan

**Purpose:** A phased implementation plan that includes core capabilities plus all additional enhancements for maximum effectiveness.

**Prerequisites:** See `OUTREACH_APP_CAPABILITIES.md` for capability descriptions and tool references.

---

## Overview

| Phase | Focus | Duration (Est.) | Key Deliverables |
|-------|-------|-----------------|------------------|
| **1** | Foundation | 3–4 weeks | Mention monitoring, contact DB, basic outreach log, minimal UI |
| **2** | Enrichment & Notes | 2–3 weeks | Contact enrichment, bios, channel recommendations, conversation notes |
| **3** | Quality & Prioritization | 2–3 weeks | Relevance scoring, hot leads, digest, engagement windows |
| **4** | Network & Intelligence | 3–4 weeks | Interconnection mapping, warm intros, mission alignment, custom tags |
| **5** | Outreach Intelligence | 2–3 weeks | Templates, channel effectiveness, follow-up reminders |
| **6** | Relationship Intelligence | 2 weeks | Conversation summarization, relationship health, decay alerts |
| **7** | Analytics & Reporting | 2 weeks | Funnel, conversion by category, mention-to-contact lag |
| **8** | Integrations & Scale | 3–4 weeks | Email, calendar, Slack, additional media sources |
| **9** | Compliance & Polish | 2 weeks | GDPR, opt-out, audit log, production hardening |

**Total estimated duration:** 21–29 weeks (5–7 months) for full implementation.

---

## Phase 1: Foundation (Weeks 1–4)

**Goal:** Working system that monitors mentions, stores contacts, and logs outreach.

### 1.1 Project Setup

| Task | Description | Notes |
|------|-------------|-------|
| Tech stack selection | Python (FastAPI/Flask) or Node.js backend; SQLite/PostgreSQL; React or simple HTML | Prefer Python for Media Cloud/NewsAPI integration |
| Repo structure | `outreach-app/` with `backend/`, `frontend/`, `scripts/`, `data/` | |
| Environment config | `.env` for API keys, DB URL; `config.yaml` for search schedule | |
| Names parser | Parse `Names` file into structured JSON/DB records | Extract: name, category, connection text, org/role |

### 1.2 Data Model (Initial)

**Tables:**

- `contacts` — id, name, category, connection_to_solomon, primary_interests, created_at, updated_at
- `mentions` — id, contact_id, source_type, source_url, title, snippet, published_at, created_at
- `outreach_log` — id, contact_id, method, content, subject, sent_at, response_status
- `contact_info` — id, contact_id, type (email/linkedin/twitter/etc), value, is_primary

### 1.3 Mention Monitoring (News)

| Task | Description | Tool |
|------|-------------|------|
| News ingestion | Daily job: query news sources for each of 300 names | Media Cloud API (free) or NewsAPI.ai |
| Deduplication | Hash URL + contact_id; skip duplicates | |
| Storage | Store mention + link to contact | |
| Scheduling | Cron or scheduler (e.g., APScheduler) for daily run | |

### 1.4 Basic UI

| Task | Description |
|------|-------------|
| Dashboard | List of new mentions (last 7 days) with contact name, source, date, link |
| Contact list | Searchable list of 300 contacts |
| Contact detail | View contact + mentions + outreach log |
| Outreach log form | Add outreach: method, content, date, response status |

### Phase 1 Deliverables

- [ ] Names parsed into `contacts` table
- [ ] Daily news monitoring running
- [ ] Mentions stored and linked to contacts
- [ ] UI to view mentions and log outreach
- [ ] Basic contact detail view

---

## Phase 2: Enrichment & Notes (Weeks 5–7)

**Goal:** Richer contact data, channel recommendations, and conversation notes.

### 2.1 Contact Enrichment

| Task | Description | Tool |
|------|-------------|------|
| Enrichment trigger | On new mention or manual "Enrich" action | |
| Email finder | Look up email by name + org (from mention/bio) | Hunter API |
| LinkedIn finder | Search by name; store LinkedIn URL | Hunter or manual |
| Rate limiting | Queue enrichment requests; respect API limits | |
| Contact info UI | Display email, LinkedIn, etc.; "Copy" buttons | |

### 2.2 Bio Extraction

| Task | Description |
|------|-------------|
| Bio from Names | Use `connection_to_solomon` + role/org from Names as initial bio |
| Bio from mentions | Extract 1–2 sentence summary from mention snippet (LLM optional) |
| Bio from enrichment | If Hunter/Kaspr return job title, company → append to bio |
| Bio field in contact detail | Editable by user | |

### 2.3 First-Contact Channel Recommendations

| Task | Description |
|------|-------------|
| Recommendation logic | If email exists → recommend email first; else LinkedIn; else Twitter; else website |
| UI | "Recommended: Email (available)" or "Recommended: LinkedIn (email not found)" |
| Priority order | Email > LinkedIn > Twitter/X > Website form > Other |

### 2.4 Conversation Notes

| Task | Description |
|------|-------------|
| Notes table | id, contact_id, note_text, note_date, channel, created_at |
| Notes UI | Add note form on contact detail; timeline of notes |
| Relationship stage | Dropdown: Cold / Warm / Engaged / Partner-Advocate |
| Stage on contact | Store current stage; show in contact list |

### Phase 2 Deliverables

- [ ] Contact enrichment (email, LinkedIn) via Hunter or Kaspr
- [ ] Bio extraction and display
- [ ] Channel recommendations for first-time contacts
- [ ] Conversation notes and relationship stage

---

## Phase 3: Quality & Prioritization (Weeks 8–10)

**Goal:** Relevance scoring, hot leads, engagement windows, digest.

### 3.1 Relevance Scoring

| Task | Description |
|------|-------------|
| Keyword rules | Score +1 for "AI safety," "AI alignment," "institutional," "governance," etc. |
| Snippet analysis | Optional: LLM call to score 0–10 relevance to Solomon mission |
| Store score | Add `relevance_score` to mentions table |
| Filter/sort | "Show only high-relevance mentions" in UI |

### 3.2 Hot Lead Flag

| Task | Description |
|------|-------------|
| Recency threshold | Mention in last 48 hours → "Hot" badge |
| Engagement window | "Featured in podcast yesterday — good time to reach out" |
| UI | Badge on mention card; sort by "Hot first" |

### 3.3 Batch Digest

| Task | Description |
|------|-------------|
| Digest job | Daily: aggregate new mentions by category |
| Digest format | Email or in-app: "5 new mentions today: 2 AI safety, 2 philanthropy, 1 education" |
| Links | Each item links to mention + contact |
| Config | Toggle digest on/off; email address |

### 3.4 Disambiguation (Basic)

| Task | Description |
|------|-------------|
| Name collision check | If "John Smith" appears, compare org/context from snippet to contact's known org |
| Manual override | "This mention is not about our John Smith" → dismiss |
| Dismissed mentions | Store dismissal; don't show in active list |

### Phase 3 Deliverables

- [ ] Relevance scoring for mentions
- [ ] Hot lead flag and engagement window hints
- [ ] Daily digest (email or in-app)
- [ ] Basic disambiguation and dismiss

---

## Phase 4: Network & Intelligence (Weeks 11–14)

**Goal:** Interconnection mapping, warm intro paths, mission alignment, custom tags.

### 4.1 Interconnection Data Model

| Task | Description |
|------|-------------|
| Interconnections table | id, contact_a_id, contact_b_id, connection_type (shared_org, coauthor, panel, etc.), notes |
| Seed from Names | Parse "works with X," "co-author with Y" from connection text |
| Manual add | UI to add connection between two contacts |
| Display | "Connected to: Person B (shared org), Person C (co-author)" |

### 4.2 Warm Intro Path Discovery

| Task | Description |
|------|-------------|
| Path algorithm | For target T: find contacts C where C has connection to T |
| UI | "You could ask [Person A] for an intro to [Person B]" |
| Sort by strength | Prioritize "Engaged" or "Partner" contacts as intro sources |

### 4.3 Mission Alignment Score

| Task | Description |
|------|-------------|
| Initial score | From category: AI safety = 9, Philanthropy = 8, etc. (configurable) |
| User override | Slider or dropdown: 1–10 alignment |
| Use in prioritization | Sort contacts by alignment when choosing who to reach out to |

### 4.4 Solomon-Specific Tags

| Task | Description |
|------|-------------|
| Tag model | contact_id, tag (string), created_at |
| Preset tags | "Funding potential," "Amplification potential," "Technical credibility," "Prioritize," "Warm intro available," "Already engaged" |
| Custom tags | User can add any tag |
| Filter by tag | "Show contacts with Funding potential" |

### 4.5 Category Clustering

| Task | Description |
|------|-------------|
| Category from Names | Already in data (AI safety, Futurists, Philanthropy, etc.) |
| Filter by category | "Show only AI safety contacts with new mentions" |
| Category in digest | Group digest items by category |

### Phase 4 Deliverables

- [ ] Interconnection mapping (manual + seeded)
- [ ] Warm intro path discovery
- [ ] Mission alignment score
- [ ] Custom and preset tags
- [ ] Category filtering

---

## Phase 5: Outreach Intelligence (Weeks 15–17)

**Goal:** Templates, channel effectiveness, follow-up reminders.

### 5.1 Message Templates

| Task | Description |
|------|-------------|
| Template model | id, name, category (or "general"), body, subject (for email), placeholders |
| Placeholders | `{{name}}`, `{{recent_mention}}`, `{{connection}}` |
| Preset templates | One per category (AI safety, philanthropy, education, etc.) |
| Template picker | When composing outreach, select template → fill placeholders → edit |

### 5.2 Channel Effectiveness Tracking

| Task | Description |
|------|-------------|
| Aggregate by channel | Count: sent, replied, no response per channel (email, LinkedIn, etc.) |
| Response rate | replied / sent per channel |
| UI | "Email: 23% response rate; LinkedIn: 12%" in settings or analytics |

### 5.3 Follow-Up Reminders

| Task | Description |
|------|-------------|
| Reminder rule | If outreach sent, no reply, N days ago → create reminder |
| Default N | 7 days (configurable) |
| Reminder list | "Follow up with: [5 contacts]" on dashboard |
| Snooze | "Remind me in 3 days" |

### 5.4 Optimal Send Time (Basic)

| Task | Description |
|------|-------------|
| Track send time | Store hour/day of week when outreach was sent |
| Correlate with reply | If we have reply data, suggest "Best response rate: Tue–Thu, 9–11am" |
| Defer to Phase 7 | Full analytics in reporting phase |

### Phase 5 Deliverables

- [ ] Message templates with placeholders
- [ ] Channel effectiveness metrics
- [ ] Follow-up reminders
- [ ] Basic send-time insight (if data available)

---

## Phase 6: Relationship Intelligence (Weeks 18–19)

**Goal:** Conversation summarization, relationship health, decay alerts.

### 6.1 Conversation Summarization (Optional LLM)

| Task | Description |
|------|-------------|
| Summarize long notes | If note > 500 chars, offer "Summarize" → LLM call |
| Action items | "Extract action items" → bullet list of commitments, next steps |
| Store summary | Append to note or store separately |

### 6.2 Relationship Health Score

| Task | Description |
|------|-------------|
| Factors | Recency of last contact, response rate, number of exchanges, stage |
| Formula | e.g., health = 0.3*recency + 0.3*response_rate + 0.4*stage_score |
| Display | "Relationship health: 7/10" on contact card |
| Sort | "Show contacts with cooling relationships first" |

### 6.3 Decay Alerts

| Task | Description |
|------|-------------|
| Threshold | No contact in 90 days (configurable) → "Relationship may be cooling" |
| Alert list | Dashboard: "Consider re-engaging: [10 contacts]" |
| Config | Per-category or global threshold |

### Phase 6 Deliverables

- [ ] Conversation summarization (if LLM available)
- [ ] Relationship health score
- [ ] Decay alerts

---

## Phase 7: Analytics & Reporting (Weeks 20–21)

**Goal:** Funnel, conversion by category, mention-to-contact lag, pipeline value.

### 7.1 Outreach Funnel

| Task | Description |
|------|-------------|
| Stages | Cold → Contacted → Replied → Meeting → Engaged |
| Count per stage | Dashboard: "120 Cold, 80 Contacted, 25 Replied, 10 Meeting, 5 Engaged" |
| Funnel viz | Simple bar or funnel chart |

### 7.2 Conversion by Category

| Task | Description |
|------|-------------|
| Metric | Contacted → Replied rate per category |
| Table | "AI safety: 28%; Philanthropy: 18%; Education: 22%" |
| Insight | "AI safety converts best — prioritize" |

### 7.3 Mention-to-Contact Lag

| Task | Description |
|------|-------------|
| Metric | Days between mention date and first outreach |
| Average | "Average lag: 4.2 days" |
| Distribution | "60% contacted within 48 hours" |
| Goal | Track over time; aim to reduce lag |

### 7.4 Pipeline Value (Qualitative)

| Task | Description |
|------|-------------|
| Tag-based | Contacts tagged "Funding potential" + "Engaged" = pipeline value |
| Simple count | "5 high-value engaged contacts" |
| Optional | Add manual "estimated value" field per contact |

### Phase 7 Deliverables

- [ ] Outreach funnel visualization
- [ ] Conversion by category
- [ ] Mention-to-contact lag metrics
- [ ] Pipeline value summary

---

## Phase 8: Integrations & Scale (Weeks 22–25)

**Goal:** Email, calendar, Slack, additional media sources.

### 8.1 Additional Media Sources

| Task | Description | Tool |
|------|-------------|------|
| Podcasts | RSS + transcript search (if available) or podcast APIs | Spotify Podcast API, Listen Notes, or transcript APIs |
| Presentations | Conference sites, YouTube (talks) | YouTube API, manual RSS |
| Speeches | C-SPAN, congressional records, event sites | SerpApi, manual |
| Web | Broader web search for names | SerpApi, Google Custom Search |

### 8.2 Email Integration

| Task | Description |
|------|-------------|
| Log sent emails | Manual paste or OAuth read (Gmail API) to log sent |
| Send from app | Optional: integrate with SendGrid/Mailgun for sending |
| Thread linking | Link outreach log entry to email thread ID if available |

### 8.3 Calendar Integration

| Task | Description |
|------|-------------|
| Schedule follow-up | "Add to calendar" for follow-up reminder |
| Sync meetings | OAuth calendar read to detect meetings with contacts |
| Log meetings | "Met with X on [date]" from calendar |

### 8.4 Slack/Discord Notifications

| Task | Description |
|------|-------------|
| Webhook | On high-priority mention (relevance > 8, hot lead) → post to Slack |
| Config | Webhook URL, which channels to notify |
| Digest option | Daily digest to Slack instead of/in addition to email |

### Phase 8 Deliverables

- [ ] Podcast and/or presentation ingestion
- [ ] Email integration (log or send)
- [ ] Calendar integration
- [ ] Slack/Discord notifications

---

## Phase 9: Compliance & Polish (Weeks 26–27)

**Goal:** GDPR, opt-out, audit log, production readiness.

### 9.1 Compliance

| Task | Description |
|------|-------------|
| Opt-out list | Table: email/contact_id, opted_out_at, reason |
| Opt-out check | Before any outreach: "Is this contact opted out?" |
| Data retention | Configurable retention for mentions, notes (e.g., 2 years) |
| Right to deletion | "Delete my data" flow: anonymize or remove contact + related data |
| CAN-SPAM | Unsubscribe link in emails if sending from app |

### 9.2 Audit Log

| Task | Description |
|------|-------------|
| Log table | user_id, action, resource_type, resource_id, timestamp, ip |
| Actions | view_contact, export_contact, add_outreach, delete_contact |
| UI | Admin view of audit log (optional) |

### 9.3 Production Hardening

| Task | Description |
|------|-------------|
| Auth | User login (if multi-user) or single-user with password |
| Backups | Daily DB backup |
| Error handling | Graceful failure of external APIs; retry logic |
| Rate limiting | Protect enrichment and mention jobs from overload |

### Phase 9 Deliverables

- [ ] Opt-out list and check
- [ ] Data retention and deletion
- [ ] Audit log
- [ ] Production-ready deployment

---

## Dependency Graph

```
Phase 1 (Foundation)
    ↓
Phase 2 (Enrichment & Notes) — depends on Phase 1
    ↓
Phase 3 (Quality & Prioritization) — depends on Phase 1
    ↓
Phase 4 (Network & Intelligence) — depends on Phase 1, 2
    ↓
Phase 5 (Outreach Intelligence) — depends on Phase 1, 2
    ↓
Phase 6 (Relationship Intelligence) — depends on Phase 2
    ↓
Phase 7 (Analytics) — depends on Phases 1–6
    ↓
Phase 8 (Integrations) — can run parallel to 5–7 after Phase 4
    ↓
Phase 9 (Compliance) — depends on all
```

**Parallelization:** Phases 5, 6, 7 can be developed in parallel once Phase 4 is done. Phase 8 can start after Phase 4.

---

## Technology Recommendations

| Component | Recommendation | Alternatives |
|-----------|----------------|--------------|
| Backend | Python + FastAPI | Flask, Node.js + Express |
| Database | PostgreSQL | SQLite (dev), Supabase |
| Frontend | React + Tailwind | Vue, Svelte, or server-rendered (Jinja) |
| Task queue | Celery + Redis | APScheduler (simpler), Dramatiq |
| News API | Media Cloud (free) | NewsAPI.ai, SerpApi |
| Enrichment | Hunter | Kaspr, ContactOut |
| Hosting | Railway, Render, Fly.io | AWS, GCP, self-hosted |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| API rate limits | Queue jobs; cache enrichment results; batch requests |
| API costs | Start with free tiers (Media Cloud, SerpApi free); monitor usage |
| Name disambiguation | Manual override; improve over time with feedback |
| LLM costs | Make summarization/scoring optional; use cheaper models |
| Scope creep | Stick to phase boundaries; defer "nice-to-haves" to later phases |

---

## Success Metrics

| Metric | Target (Example) |
|--------|------------------|
| Mention coverage | 95%+ of 300 names searched daily |
| Enrichment rate | 50%+ of mentioned contacts have email or LinkedIn |
| Outreach velocity | 10+ first-time outreaches per week |
| Response rate | Track baseline; aim to improve with templates and timing |
| Warm intro usage | 5+ warm intros facilitated per quarter |

---

*Implementation plan for Solomon Outreach. Last updated: February 2025.*
