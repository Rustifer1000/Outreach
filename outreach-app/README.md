# Solomon Outreach Application

Outreach application for the Solomon Influencer Flywheel — monitoring mentions, managing contacts, and tracking outreach to 300 key individuals.

## Quick Start

### 1. Parse the Names file

From the project root (`Outreach/`):

```bash
python scripts/parse_names.py
```

This generates `data/contacts.json` and `data/contacts.csv`.

### 2. Backend setup

```bash
cd outreach-app/backend
pip install -r requirements.txt
cp ../.env.example .env   # Edit .env with API keys if needed
```

### 3. Seed the database

From `outreach-app/` (so the DB is created in `backend/`):

```bash
cd outreach-app
python scripts/seed_contacts.py --db sqlite:///./backend/outreach.db --reset
```

### 4. Run the backend

```bash
cd outreach-app/backend
# Uses sqlite:///./outreach.db by default (same file as seed)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Run the frontend

```bash
cd outreach-app/frontend
npm install
npm run dev
```

Open http://localhost:5173

## Project Structure

```
outreach-app/
├── backend/           # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/       # REST endpoints
│   │   ├── models.py  # DB models
│   │   └── main.py
│   └── requirements.txt
├── frontend/          # React + Vite + Tailwind
│   └── src/
├── scripts/           # Seed, import scripts
├── .env.example
└── config.yaml.example
```

## API Endpoints

- `GET /api/contacts` — List contacts (search, filter by category)
- `GET /api/contacts/:id` — Contact detail
- `GET /api/mentions` — Recent mentions (filter by days, contact)
- `GET /api/outreach` — Outreach log (filter by contact)

## Next Steps (Phase 1)

1. **Mention monitoring job** — Daily cron to query Media Cloud/NewsAPI for each contact
2. **Outreach log form** — Add POST endpoint and UI to log outreach
3. **Contact info display** — Show email, LinkedIn when enriched (Phase 2)

See `IMPLEMENTATION_PLAN.md` in the repo root for the full roadmap.
