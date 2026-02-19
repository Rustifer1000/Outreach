# Start the Outreach App (New Computer / Next Day)

Use this when opening the project on a different machine or after a fresh clone.

## Prerequisites

- **Python 3.11+** (with pip)
- **Node.js 18+** (with npm)
- **Git** (if cloning)

---

## 1. Get the project

If cloning:
```bash
git clone <your-repo-url>
cd Outreach
```

If you already have the folder (e.g. USB, cloud sync):
```bash
cd path/to/Outreach
```

---

## 2. Backend setup

```bash
cd outreach-app/backend
pip install -r requirements.txt
```

---

## 3. Frontend setup

```bash
cd outreach-app/frontend
npm install
```

---

## 4. Environment variables

Copy the example and add your API keys:

```bash
cd outreach-app
copy .env.example .env
```

Edit `.env` and fill in (at minimum for full features):

| Variable | Purpose |
|----------|---------|
| `NEWSAPI_KEY` | Mention fetch, connection discovery |
| `HUNTER_API_KEY` | Email enrichment |
| `ANTHROPIC_API_KEY` | LLM relationship inference |

---

## 5. Database (first time only)

If the DB doesn't exist yet:

```bash
cd outreach-app
python scripts/seed_contacts.py --db sqlite:///./backend/outreach.db --reset
```

---

## 6. Run the app

From `outreach-app/`:

```bash
npm start
```

This starts both backend (port 8000) and frontend (port 5173).

Open: **http://localhost:5173**

---

## Quick reference

| Command | Where |
|---------|-------|
| `npm start` | `outreach-app/` |
| `pip install -r requirements.txt` | `outreach-app/backend/` |
| `npm install` | `outreach-app/frontend/` |

---

## Troubleshooting

- **Port 5173 not loading** — Run `npm start` from `outreach-app/` (not `npm-start` or `start npm`)
- **"react-force-graph-2d" not found** — Run `npm install` in `outreach-app/frontend/`
- **HUNTER_API_KEY not configured** — Add it to `outreach-app/.env` (not `backend/.env`)
