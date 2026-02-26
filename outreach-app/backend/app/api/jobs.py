"""Background job endpoints."""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.scheduler import run_fetch_mentions
from app.database import SessionLocal
from app.discovery import discover_from_mentions, discover_via_search, discover_all
from app.enrichment import enrich_bulk
from app.media_sources import fetch_media_for_contacts
from app.warm_intros import score_all_alignments, auto_tag_warm_intro
from app.config import settings

router = APIRouter()

# Store latest bulk enrichment results (simple in-memory; replaced each run)
_bulk_enrich_result: dict | None = None
_media_fetch_result: dict | None = None


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


def _run_discover_all():
    db = SessionLocal()
    try:
        api_key = settings.newsapi_key or __import__("os").environ.get("NEWSAPI_KEY")
        return discover_all(db, api_key, max_contacts=15, max_pairs_per_contact=5)
    finally:
        db.close()


@router.post("/discover-all-connections")
async def trigger_discover_all(background_tasks: BackgroundTasks):
    """Agentic: run from-mentions (all) + via-search for up to 15 contacts (rotation first). ~2–3 min."""
    background_tasks.add_task(_run_discover_all)
    return {"status": "started", "message": "Discovering all connections (mentions + web search). Refresh the map in 2–3 minutes."}


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


class BulkEnrichBody(BaseModel):
    max_contacts: int = 50


def _run_bulk_enrich(max_contacts: int):
    global _bulk_enrich_result
    db = SessionLocal()
    try:
        api_key = settings.hunter_api_key
        if not api_key:
            _bulk_enrich_result = {"attempted": 0, "found": 0, "skipped": 0, "errors": 0, "message": "HUNTER_API_KEY not configured."}
            return
        _bulk_enrich_result = enrich_bulk(db, api_key, max_contacts=max_contacts)
    finally:
        db.close()


@router.post("/enrich-all")
async def trigger_bulk_enrich(body: BulkEnrichBody, background_tasks: BackgroundTasks):
    """Enrich all contacts missing email via Hunter API. Rate-limited to 1 req/sec."""
    if not settings.hunter_api_key:
        raise HTTPException(status_code=503, detail="HUNTER_API_KEY not configured. Add to .env for enrichment.")
    if body.max_contacts < 1 or body.max_contacts > 200:
        raise HTTPException(status_code=400, detail="max_contacts must be 1–200")
    global _bulk_enrich_result
    _bulk_enrich_result = None
    background_tasks.add_task(_run_bulk_enrich, body.max_contacts)
    return {"status": "started", "message": f"Enriching up to {body.max_contacts} contacts in background (1/sec). Check status with GET /api/jobs/enrich-status."}


@router.get("/enrich-status")
async def get_enrich_status():
    """Check the result of the latest bulk enrichment run."""
    if _bulk_enrich_result is None:
        return {"status": "running", "message": "Enrichment in progress or not started yet."}
    return {"status": "complete", **_bulk_enrich_result}


# --- Media source fetching (podcasts, YouTube, speeches) ---

class MediaFetchBody(BaseModel):
    days: int = 30
    max_contacts: int = 25
    max_per_source: int = 2
    contact_ids: list[int] | None = None  # None = use rotation or all


def _run_media_fetch(days: int, max_contacts: int, max_per_source: int, contact_ids: list[int] | None):
    global _media_fetch_result
    db = SessionLocal()
    try:
        _media_fetch_result = fetch_media_for_contacts(
            db,
            contact_ids=contact_ids,
            days=days,
            listennotes_key=settings.listennotes_api_key,
            youtube_key=settings.youtube_api_key,
            serpapi_key=settings.serpapi_key,
            max_per_source=max_per_source,
            max_contacts=max_contacts,
        )
    finally:
        db.close()


@router.post("/fetch-media")
async def trigger_fetch_media(body: MediaFetchBody, background_tasks: BackgroundTasks):
    """Fetch podcasts, YouTube videos, and speech/presentation mentions.

    Requires at least one of: LISTENNOTES_API_KEY, YOUTUBE_API_KEY, SERPAPI_KEY in .env.
    """
    has_keys = any([settings.listennotes_api_key, settings.youtube_api_key, settings.serpapi_key])
    if not has_keys:
        raise HTTPException(
            status_code=503,
            detail="No media API keys configured. Add LISTENNOTES_API_KEY, YOUTUBE_API_KEY, or SERPAPI_KEY to .env.",
        )
    global _media_fetch_result
    _media_fetch_result = None
    background_tasks.add_task(_run_media_fetch, body.days, body.max_contacts, body.max_per_source, body.contact_ids)
    sources = []
    if settings.listennotes_api_key:
        sources.append("podcasts")
    if settings.youtube_api_key:
        sources.append("YouTube")
    if settings.serpapi_key:
        sources.append("speeches")
    return {
        "status": "started",
        "sources": sources,
        "message": f"Fetching {', '.join(sources)} for up to {body.max_contacts} contacts. Check status with GET /api/jobs/media-status.",
    }


@router.get("/media-status")
async def get_media_status():
    """Check the result of the latest media fetch run."""
    if _media_fetch_result is None:
        return {"status": "running", "message": "Media fetch in progress or not started yet."}
    return {"status": "complete", **_media_fetch_result}


@router.get("/media-sources")
async def get_available_media_sources():
    """Return which media source API keys are configured."""
    return {
        "news": bool(settings.newsapi_key),
        "podcast": bool(settings.listennotes_api_key),
        "video": bool(settings.youtube_api_key),
        "speech": bool(settings.serpapi_key),
    }


# --- Mission alignment bulk scoring ---

@router.post("/score-alignments")
async def trigger_score_alignments(background_tasks: BackgroundTasks):
    """Auto-compute mission alignment scores for all unscored contacts."""
    def _run():
        db = SessionLocal()
        try:
            return score_all_alignments(db)
        finally:
            db.close()
    background_tasks.add_task(_run)
    return {"status": "started", "message": "Computing mission alignment scores in background."}


@router.post("/auto-tag-warm-intros")
async def trigger_auto_tag_warm_intros(background_tasks: BackgroundTasks):
    """Auto-tag contacts with 'Warm intro available' when they're connected to an Engaged/Partner contact."""
    def _run():
        db = SessionLocal()
        try:
            return auto_tag_warm_intro(db)
        finally:
            db.close()
    background_tasks.add_task(_run)
    return {"status": "started", "message": "Auto-tagging warm intro contacts in background."}
