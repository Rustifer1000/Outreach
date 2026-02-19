@echo off
REM Full setup + start for Solomon Outreach App
REM Run from outreach-app/ folder (or Outreach/ to cd first)

cd /d "%~dp0"
if exist "outreach-app" cd outreach-app

echo Installing backend dependencies...
cd backend
pip install -r requirements.txt
cd ..

echo Installing frontend dependencies...
cd frontend
npm install
cd ..

if not exist ".env" (
    echo.
    echo .env not found. Copy .env.example to .env and add your API keys.
    copy .env.example .env
    echo Created .env - edit it with your keys, then run this script again.
    pause
    exit /b 1
)

if not exist "backend\outreach.db" (
    echo Seeding database...
    python scripts/seed_contacts.py --db sqlite:///./backend/outreach.db --reset
)

echo.
echo Starting app...
npm start
