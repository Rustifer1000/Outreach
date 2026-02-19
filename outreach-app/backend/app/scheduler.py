"""Scheduled jobs for mention fetching and connection discovery."""
import subprocess
import sys
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.discovery import discover_from_mentions


def run_fetch_mentions():
    """Run the fetch_mentions script as a subprocess, then auto-discover connections from new mentions."""
    base = Path(__file__).resolve().parent.parent.parent  # outreach-app/
    script = base / "scripts" / "fetch_mentions.py"
    if script.exists():
        env = {"PYTHONPATH": str(base / "backend")}
        subprocess.run(
            [sys.executable, str(script), "--limit", "50", "--days", "3", "--max-per-contact", "2"],
            cwd=str(base),
            env={**__import__("os").environ, **env},
            capture_output=True,
            timeout=600,  # 10 min max
        )
    # Agentic: auto-discover connections from mention text (no extra API calls)
    db = SessionLocal()
    try:
        result = discover_from_mentions(db)
        if result.get("added", 0) > 0:
            pass  # Logged via discovery
    finally:
        db.close()


def get_scheduler() -> BackgroundScheduler:
    """Create and configure the scheduler."""
    scheduler = BackgroundScheduler()
    # Run daily at 8:00 AM
    scheduler.add_job(
        run_fetch_mentions,
        CronTrigger(hour=8, minute=0),
        id="fetch_mentions",
        replace_existing=True,
    )
    return scheduler
