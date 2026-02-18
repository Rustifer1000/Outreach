"""Background job endpoints."""
from fastapi import APIRouter, BackgroundTasks

from app.scheduler import run_fetch_mentions

router = APIRouter()


@router.post("/fetch-mentions")
async def trigger_fetch_mentions(background_tasks: BackgroundTasks):
    """Trigger mention fetch now (runs in background)."""
    background_tasks.add_task(run_fetch_mentions)
    return {"status": "started", "message": "Fetching mentions in background. Check dashboard in a few minutes."}
