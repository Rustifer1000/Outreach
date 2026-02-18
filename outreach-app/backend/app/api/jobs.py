"""Background job endpoints."""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.scheduler import run_fetch_mentions
from app.database import SessionLocal
from app.discovery import discover_from_mentions, discover_via_search
from app.config import settings

router = APIRouter()


def _run_discover_from_mentions():
    db = SessionLocal()
    try:
        return discover_from_mentions(db)
    finally:
        db.close()


def _run_discover_via_search(contact_id: int, max_pairs: int = 20):
    db = SessionLocal()
    try:
        api_key = settings.newsapi_key or __import__("os").environ.get("NEWSAPI_KEY")
        if not api_key:
            return {"added": 0, "searched_pairs": 0, "message": "NewsAPI key not configured."}
        return discover_via_search(db, contact_id, api_key, max_pairs=max_pairs)
    finally:
        db.close()


@router.post("/fetch-mentions")
async def trigger_fetch_mentions(background_tasks: BackgroundTasks):
    """Trigger mention fetch now (runs in background)."""
    background_tasks.add_task(run_fetch_mentions)
    return {"status": "started", "message": "Fetching mentions in background. Check dashboard in a few minutes."}


@router.post("/discover-connections-from-mentions")
async def trigger_discover_from_mentions(background_tasks: BackgroundTasks):
    """Scan existing mention snippets for other contact names; add connections when found (same article, podcast, etc.). No extra API calls."""
    background_tasks.add_task(_run_discover_from_mentions)
    return {"status": "started", "message": "Discovering connections from mention text in background. Refresh the map in a minute."}


class DiscoverForContactBody(BaseModel):
    contact_id: int
    max_pairs: int = 20


@router.post("/discover-connections-for-contact")
async def trigger_discover_for_contact(body: DiscoverForContactBody, background_tasks: BackgroundTasks):
    """Run web search (NewsAPI) for this contact vs others: 'Name A' AND 'Name B'. Adds connections when co-mentioned in news. Uses rate limit (1 req/sec)."""
    if body.max_pairs < 1 or body.max_pairs > 50:
        raise HTTPException(status_code=400, detail="max_pairs must be 1–50")
    background_tasks.add_task(_run_discover_via_search, body.contact_id, body.max_pairs)
    return {"status": "started", "message": f"Discovering connections for contact {body.contact_id} via web search (up to {body.max_pairs} pairs). Check back in a few minutes."}
