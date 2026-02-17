# Solomon Outreach — Quick Start

**Last updated:** Feb 17, 2025. Use this to pick up where you left off.

---

## What's Done

| Component | Status |
|-----------|--------|
| **Names parser** | `scripts/parse_names.py` → outputs `data/contacts.json` |
| **Database** | SQLite, 305 contacts seeded |
| **Backend** | FastAPI on port 8000, contacts/mentions/outreach APIs |
| **Frontend** | React + Vite + Tailwind on port 5173 |
| **Mention fetch** | `scripts/fetch_mentions.py` — real news via NewsAPI |
| **Sample mentions** | `scripts/seed_sample_mentions.py` — demo data (no API key) |
| **UI limits** | Max 2 mentions per contact on dashboard |

---

## Start Working (2 terminals)

**Terminal 1 — Backend**
```bash
cd outreach-app/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend**
```bash
cd outreach-app/frontend
npm run dev
```

Open **http://localhost:5173**

---

## Key Commands

| Task | Command |
|------|---------|
| Re-parse Names file | `python scripts/parse_names.py` |
| Re-seed contacts | `cd outreach-app && python scripts/seed_contacts.py --db sqlite:///./backend/outreach.db --reset` |
| Add sample mentions | `cd outreach-app && python scripts/seed_sample_mentions.py` |
| Fetch real mentions | `cd outreach-app && python scripts/fetch_mentions.py --limit 50 --max-per-contact 2` |

---

## Config

- **API key:** `NEWSAPI_KEY` in `outreach-app/.env` (get free key at newsapi.org/register)
- **DB:** `outreach-app/backend/outreach.db` (SQLite)

---

## Next Up (Phase 1)

1. **Outreach log form** — Add UI + POST endpoint to log outreach (method, content, date, response)
2. **Scheduled fetch** — Cron or APScheduler to run `fetch_mentions.py` daily
3. **Contact detail polish** — Outreach form on contact page

---

## Project Layout

```
Outreach/
├── Names                    # Source contact list
├── data/contacts.json       # Parsed output
├── scripts/
│   ├── parse_names.py       # Parse Names → JSON/CSV
│   ├── seed_contacts.py     # Seed DB (in outreach-app)
│   ├── seed_sample_mentions.py
│   └── fetch_mentions.py    # NewsAPI → mentions
└── outreach-app/
    ├── backend/             # FastAPI
    ├── frontend/            # React + Vite
    └── .env                 # NEWSAPI_KEY, etc.
```
