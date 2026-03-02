# Solomon Outreach App - Session Reference

> **Purpose:** Everything needed to get productive immediately from a cold start. Append daily session notes at the bottom.

---

## Quick Start

```bash
cd outreach-app

# First time only:
cp .env.example .env          # then fill in API keys
cd backend && pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..
npm install                    # installs concurrently

# Every time:
npm start                      # starts backend (port 8000) + frontend (port 5173)
```

Backend: http://localhost:8000 (API docs at /docs)
Frontend: http://localhost:5173

---

## What This App Does

Solomon Outreach manages a list of ~300 contacts (the "Solomon Influencer Flywheel") for outreach related to AI safety/governance. It:

1. **Monitors mentions** of contacts across news, podcasts, YouTube, speeches
2. **Scores relevance** of mentions and detects hot leads
3. **Tracks outreach** (emails, LinkedIn, etc.) and conversation notes
4. **Discovers connections** between contacts via co-mentions and LLM inference
5. **Finds warm intro paths** through existing engaged contacts
6. **Generates bios** using Claude from mention data
7. **Produces daily digests** with hot leads and follow-up reminders

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.11+ |
| Database | SQLAlchemy ORM + SQLite (dev) |
| Frontend | React 18 + TypeScript + Vite 5 + Tailwind CSS 3.4 |
| LLM | Anthropic Claude (model: `claude-haiku-4-5-20251001`) |
| External APIs | NewsAPI, Hunter (email), ListenNotes, YouTube Data API, SerpApi |
| Scheduler | APScheduler (daily mention fetch at 8 AM) |
| Testing | pytest + pytest-asyncio |

---

## Project Structure

```
outreach-app/
├── package.json              # npm start runs backend + frontend via concurrently
├── .env                      # API keys (gitignored)
│
├── backend/
│   ├── requirements.txt
│   ├── outreach.db           # SQLite database (auto-created)
│   └── app/
│       ├── main.py           # FastAPI app entry + lifespan (creates tables, runs migrations)
│       ├── config.py         # Pydantic Settings from .env
│       ├── database.py       # SQLAlchemy engine, SessionLocal, Base
│       ├── models.py         # 7 models (see Data Model below)
│       ├── scheduler.py      # APScheduler: daily mention fetch at 8 AM
│       ├── migrate_phase2b.py # Idempotent migration (runs on startup)
│       │
│       ├── api/              # FastAPI routers
│       │   ├── contacts.py   # CRUD, notes, connections, tags, enrichment, warm intros
│       │   ├── mentions.py   # Mention listing with dedup + per-contact limits
│       │   ├── outreach.py   # Outreach log endpoints
│       │   ├── jobs.py       # Background jobs (mention fetch, discovery, enrichment, media, scoring)
│       │   ├── names_file.py # Names file upload/parsing/editing
│       │   ├── relationship_map.py # Graph data for visualization
│       │   └── digest.py     # Daily digest + hot leads
│       │
│       ├── discovery.py      # Connection discovery (from mentions + NewsAPI search)
│       ├── enrichment.py     # Hunter email finder + Claude bio generation
│       ├── llm_extract.py    # LLM relationship inference between contacts
│       ├── media_sources.py  # ListenNotes, YouTube, SerpApi fetchers
│       ├── scoring.py        # Relevance scoring, hot lead detection, daily digest
│       ├── warm_intros.py    # Warm intro path finding + mission alignment scoring
│       └── names_file.py     # Names file parsing logic
│
├── frontend/
│   └── src/
│       ├── App.tsx           # Routes
│       ├── api.ts            # apiFetch wrapper (error handling)
│       ├── components/
│       │   └── Layout.tsx    # Nav + toast notifications
│       └── pages/
│           ├── Dashboard.tsx      # /          - mentions + hot leads
│           ├── Contacts.tsx       # /contacts  - searchable contact list
│           ├── ContactDetail.tsx  # /contacts/:id - full contact view
│           ├── Rotation.tsx       # /rotation  - mention rotation management
│           ├── RelationshipMap.tsx # /map       - force-directed graph
│           ├── Digest.tsx         # /digest    - daily digest view
│           └── NamesFile.tsx      # /names-file - Names file management
│
└── scripts/
    ├── fetch_mentions.py       # NewsAPI mention fetcher (called by scheduler)
    ├── seed_contacts.py        # Seed DB from Names file
    └── seed_sample_mentions.py # Generate sample mention data
```

---

## Data Model (7 tables)

```
Contact (contacts)
├── id, list_number, name, category, subcategory
├── role_org, connection_to_solomon, primary_interests
├── relationship_stage: Cold | Warm | Engaged | Partner-Advocate
├── mission_alignment: Float 1-10
├── in_mention_rotation: 0 | 1
│
├──< ContactInfo (contact_info)     # email, linkedin, twitter, phone
├──< Mention (mentions)             # news/podcast/video/speech mentions
│      └── relevance_score: Float   # auto-scored 0-1
├──< OutreachLog (outreach_log)     # method, subject, response_status
├──< Note (notes)                   # conversation notes with channel
├──< ContactConnection (contact_connections)  # relationships to other contacts
│      └── relationship_type: first_degree | second_degree | same_org | co_author | ...
└──< ContactTag (contact_tags)      # custom or preset tags
```

All foreign keys cascade on delete. SQLite has `PRAGMA foreign_keys=ON` enforced per connection.

---

## API Endpoints (prefix: /api)

### Contacts
| Method | Path | Purpose |
|--------|------|---------|
| GET | /contacts | List (search: `?q=`, filter: `?category=`, `?in_rotation=true`) |
| GET | /contacts/{id} | Detail with contact info + recommendation |
| PATCH | /contacts/{id} | Update stage, rotation, alignment |
| POST | /contacts/{id}/enrich | Find email via Hunter API |
| POST | /contacts/{id}/enrich-bio | Generate bio via Claude |
| POST | /contacts/{id}/compute-alignment | Auto-score mission alignment |
| GET/POST | /contacts/{id}/notes | List/add conversation notes |
| GET/POST/DELETE | /contacts/{id}/connections | Manage connections |
| GET/POST/DELETE | /contacts/{id}/tags | Manage tags |
| GET | /contacts/tags/preset | Preset tag list |
| GET | /contacts/{id}/warm-intros | Find warm intro paths |
| PUT | /contacts/rotation | Set rotation list |
| GET | /contacts/rotation | Get rotation list |

### Mentions & Digest
| Method | Path | Purpose |
|--------|------|---------|
| GET | /mentions | List mentions (?days=, ?contact_id=, ?limit=) |
| GET | /digest | Full daily digest |
| GET | /digest/hot-leads | Hot leads only |

### Background Jobs
| Method | Path | Purpose |
|--------|------|---------|
| POST | /jobs/fetch-mentions | Trigger mention fetch |
| POST | /jobs/discover-connections-from-mentions | Scan mentions for co-mentions |
| POST | /jobs/discover-connections-for-contact | NewsAPI search for one contact |
| POST | /jobs/discover-all-connections | Full discovery (mentions + search) |
| POST | /jobs/enrich-all | Bulk email enrichment via Hunter |
| GET | /jobs/enrich-status | Check enrichment progress |
| POST | /jobs/fetch-media | Fetch podcasts/YouTube/speeches |
| GET | /jobs/media-status | Check media fetch progress |
| POST | /jobs/score-alignments | Bulk mission alignment scoring |
| POST | /jobs/auto-tag-warm-intros | Auto-tag warm intro contacts |
| GET | /jobs/media-sources | Which media API keys are configured |

### Other
| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | /names-file/* | Names file parsing/editing |
| GET | /relationship-map/graph | Graph data for visualization |

---

## Environment Variables (.env)

| Variable | Required | Purpose |
|----------|----------|---------|
| DATABASE_URL | No (defaults to sqlite) | Database connection string |
| NEWSAPI_KEY | For mentions | News article monitoring |
| HUNTER_API_KEY | For enrichment | Email/LinkedIn lookup |
| ANTHROPIC_API_KEY | For AI features | Bio generation, relationship inference |
| LISTENNOTES_API_KEY | For podcasts | Podcast episode search |
| YOUTUBE_API_KEY | For videos | YouTube video search |
| SERPAPI_KEY | For speeches | Speech/presentation search |

---

## Key Patterns & Conventions

- **DB sessions**: FastAPI `Depends(get_db)` in route handlers; `SessionLocal()` with try/finally in background jobs
- **Background jobs**: FastAPI `BackgroundTasks`; results stored in thread-safe `_job_results` dict with `threading.Lock`
- **API errors**: Use `HTTPException` with descriptive `detail`; validate inputs (relationship stages, dates, ranges)
- **Frontend API calls**: All go through `apiFetch()` in `api.ts` which throws on non-2xx
- **Frontend errors**: Display via `setError()` state + dismissable red banner; never use `.catch(() => {})`
- **Relationship stages**: `Cold`, `Warm`, `Engaged`, `Partner-Advocate` (validated server-side)
- **Mention rotation**: Contacts with `in_mention_rotation=1` get daily mention fetches
- **Scoring**: Relevance 0-1 (recency 30%, source type 20%, name prominence 15%, disambiguation 35%)
- **Hot leads**: Heat score = 0.40 * volume + 0.35 * quality + 0.25 * diversity

---

## Running Tests

```bash
cd outreach-app/backend
python -m pytest tests/ -v
```

Test files: `test_contacts_api.py`, `test_mentions_api.py`, `test_scoring.py`, `test_tags_api.py`, `test_warm_intros.py`, `test_digest_api.py`

---

## Common Tasks

**Seed the database from the Names file:**
```bash
cd outreach-app
python scripts/seed_contacts.py
```

**Reset the database:**
```bash
rm outreach-app/backend/outreach.db
# Restart the app — tables auto-create on startup
```

**Add a new API endpoint:**
1. Add route in the appropriate `backend/app/api/*.py` file
2. Register router in `main.py` if it's a new module
3. Add frontend call using `apiFetch()` in the relevant page component

**Add a new DB model/column:**
1. Update `models.py`
2. If needed, add migration logic in `migrate_phase2b.py` (idempotent pattern)
3. Tables auto-create on startup; columns added via migrations

---

## Known Limitations

- SQLite only (no concurrent write safety in production)
- No authentication/authorization
- CORS is dev-only (localhost:3000, localhost:5173)
- Scheduler runs in-process (no distributed job queue)
- Names file path is assumed local to the server

---

## Repository Info

- **Main repo**: `C:\Users\russe\Outreach`
- **Remote**: `https://github.com/Rustifer1000/Outreach.git`
- **Main branch**: `main`

---

## Session Log

> Append notes at the end of each session. Format: `### YYYY-MM-DD — Summary`

### 2026-02-28 — Codebase review and fixes

**Repo sync:** Merged 12 commits from remote into local `main`. Deleted stale branches (`claude/agitated-tesla`, `claude/angry-wing`). Cleaned up junk artifact files in `backend/`.

**Code review findings and fixes (10 files, 12 issues):**

Backend:
- Replaced all bare `except Exception:` clauses with specific types + logging across `enrichment.py`, `discovery.py`, `media_sources.py`, `llm_extract.py`, `main.py`
- Fixed hardcoded LLM model in `llm_extract.py` — now uses `settings.anthropic_model`
- Removed `__import__("os")` env var hack in `jobs.py` — relies on Pydantic settings
- Added `threading.Lock` for thread-safe background job result storage in `jobs.py`
- Added `VALID_RELATIONSHIP_STAGES` validation in `contacts.py` PATCH endpoint
- Invalid dates now return HTTP 400 instead of silently defaulting (`contacts.py`, `outreach.py`)
- Replaced `getattr(c, "in_mention_rotation", 0)` with direct `c.in_mention_rotation` access
- Extracted `HOT_LEAD_VOLUME_CAP`/`HOT_LEAD_DIVERSITY_CAP` constants in `scoring.py`
- Simplified complex timezone one-liner in `scoring.py` digest generation
- Fixed `len(contacts) - len(contacts)` always-zero bug in `media_sources.py`

Frontend:
- Replaced 3 silent `.catch(() => {})` with proper error handling in `ContactDetail.tsx`
- Changed array index React key to `type-value` composite key for contact info list
- Added `discoverTimeoutRef` with cleanup on unmount to prevent stale closure
- Dashboard: hot leads error clears state gracefully; polling error surfaces to user
