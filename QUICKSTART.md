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

## Start Working

**Option A — One command (recommended)**
```bash
cd outreach-app
npm install
npm start
```
Opens both backend and frontend. Then go to **http://localhost:5173**

**Option B — From Cursor/VS Code UI**
- `Terminal` → `Run Task` → `Start Solomon Outreach`

**Option C — Two terminals**
```bash
# Terminal 1
cd outreach-app/backend && uvicorn app.main:app --reload --port 8000

# Terminal 2
cd outreach-app/frontend && npm run dev
```

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

## Scheduled Fetch

- **Automatic:** When the backend runs, it fetches new mentions daily at **8:00 AM**
- **Manual:** Click "Refresh mentions now" on the dashboard to fetch immediately

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
