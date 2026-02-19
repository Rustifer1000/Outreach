@echo off
REM Start Solomon Outreach App - run from outreach-app/ folder
REM Prerequisites: pip install -r backend/requirements.txt, npm install in frontend

cd /d "%~dp0"

if not exist "backend\outreach.db" (
    echo Database not found. Seeding...
    python scripts/seed_contacts.py --db sqlite:///./backend/outreach.db --reset
)

echo Starting backend + frontend...
npm start
