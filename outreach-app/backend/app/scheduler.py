"""Scheduled jobs for mention fetching."""
import subprocess
import sys
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


def run_fetch_mentions():
    """Run the fetch_mentions script as a subprocess."""
    base = Path(__file__).resolve().parent.parent.parent  # outreach-app/
    script = base / "scripts" / "fetch_mentions.py"
    if not script.exists():
        return
    env = {"PYTHONPATH": str(base / "backend")}
    subprocess.run(
        [sys.executable, str(script), "--limit", "50", "--days", "3", "--max-per-contact", "2"],
        cwd=str(base),
        env={**__import__("os").environ, **env},
        capture_output=True,
        timeout=600,  # 10 min max
    )


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
