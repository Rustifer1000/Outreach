"""Mentions API endpoints."""
import os
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db, SessionLocal
from app.models import Contact, Mention

router = APIRouter()


@router.get("")
def list_mentions(
    days: int = Query(7, ge=1, le=90, description="Mentions from last N days"),
    contact_id: int | None = Query(None, description="Filter by contact"),
    max_per_contact: int = Query(2, ge=1, le=5, description="Max mentions per contact (1-2 typical)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List recent mentions. Limits to max_per_contact per person on dashboard."""
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
    query = (
        db.query(Mention)
        .options(joinedload(Mention.contact))
        .filter(Mention.created_at >= cutoff)
    )
    if contact_id is not None:
        query = query.filter(Mention.contact_id == contact_id)
    mentions = query.order_by(Mention.published_at.desc().nullslast()).limit(1000).all()

    # Limit to max_per_contact per contact on dashboard; contact detail (filtered by contact_id) shows all
    if contact_id:
        flattened = mentions
    else:
        by_contact: dict[int, list] = {}
        for m in mentions:
            cid = m.contact_id
            if cid not in by_contact:
                by_contact[cid] = []
            if len(by_contact[cid]) < max_per_contact:
                by_contact[cid].append(m)
        flattened = [m for ms in by_contact.values() for m in ms]
        flattened.sort(key=lambda m: m.published_at or m.created_at, reverse=True)

    # Apply skip/limit
    total = len(flattened)
    page = flattened[skip : skip + limit]

    result = []
    for m in page:
        result.append({
            "id": m.id,
            "contact_id": m.contact_id,
            "contact_name": m.contact.name if m.contact else None,
            "source_type": m.source_type,
            "source_url": m.source_url,
            "title": m.title,
            "snippet": m.snippet,
            "published_at": m.published_at.isoformat() if m.published_at else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "relevance_score": m.relevance_score,
        })
    return {"total": total, "mentions": result, "skip": skip, "limit": limit}


_fetch_status: dict = {"running": False, "progress": "", "added": 0, "total_contacts": 0, "processed": 0, "error": None}


def _fetch_newsapi(api_key: str, name: str, days: int) -> list[dict]:
    """Fetch articles from NewsAPI.org for a person's name."""
    from_date = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    params = {
        "q": f'"{name}"',
        "from": from_date,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 10,
        "apiKey": api_key,
    }
    try:
        with httpx.Client(timeout=30) as client:
            r = client.get("https://newsapi.org/v2/everything", params=params)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []

    return [
        {
            "source_url": a.get("url"),
            "title": a.get("title"),
            "snippet": a.get("description") or a.get("content", "")[:500],
            "published_at": a.get("publishedAt"),
        }
        for a in data.get("articles", [])
        if a.get("url") and a.get("title")
    ]


def _run_fetch(contact_limit: int | None, days: int, max_per_contact: int):
    """Background task: fetch mentions for contacts via NewsAPI."""
    global _fetch_status
    _fetch_status = {"running": True, "progress": "Starting...", "added": 0, "total_contacts": 0, "processed": 0, "error": None}

    api_key = settings.newsapi_key
    if not api_key:
        _fetch_status.update(running=False, error="No NEWSAPI_KEY configured. Add it to your .env file.")
        return

    db = SessionLocal()
    try:
        query = db.query(Contact).order_by(Contact.list_number)
        if contact_limit:
            query = query.limit(contact_limit)
        contacts = query.all()
        _fetch_status["total_contacts"] = len(contacts)
        _fetch_status["progress"] = f"Fetching mentions for {len(contacts)} contacts..."

        max_per = max(1, min(max_per_contact, 2))
        added = 0

        for i, contact in enumerate(contacts):
            _fetch_status["processed"] = i + 1
            _fetch_status["progress"] = f"Processing {contact.name} ({i+1}/{len(contacts)})"

            articles = _fetch_newsapi(api_key, contact.name, days)
            for a in articles[:max_per]:
                if not a.get("source_url"):
                    continue
                existing = (
                    db.query(Mention)
                    .filter(Mention.contact_id == contact.id, Mention.source_url == a["source_url"])
                    .first()
                )
                if existing:
                    continue
                pub = None
                if a.get("published_at"):
                    try:
                        pub = datetime.fromisoformat(a["published_at"].replace("Z", "+00:00"))
                    except ValueError:
                        pass
                db.add(Mention(
                    contact_id=contact.id,
                    source_type="news",
                    source_url=a["source_url"],
                    title=a["title"],
                    snippet=a["snippet"],
                    published_at=pub,
                ))
                added += 1
            db.commit()

        _fetch_status.update(running=False, added=added, progress=f"Done. Added {added} new mentions.")
    except Exception as e:
        _fetch_status.update(running=False, error=str(e))
    finally:
        db.close()


@router.post("/fetch")
def trigger_fetch(
    background_tasks: BackgroundTasks,
    limit: int | None = Query(None, description="Max contacts to process"),
    days: int = Query(7, ge=1, le=90),
    max_per_contact: int = Query(2, ge=1, le=5),
):
    """Trigger a background fetch of mentions from NewsAPI."""
    if _fetch_status["running"]:
        return {"status": "already_running", "progress": _fetch_status["progress"]}
    background_tasks.add_task(_run_fetch, limit, days, max_per_contact)
    return {"status": "started"}


@router.get("/fetch/status")
def fetch_status():
    """Check progress of the background mention fetch."""
    return _fetch_status


@router.get("/{mention_id}")
def get_mention(mention_id: int, db: Session = Depends(get_db)):
    """Get a single mention by ID."""
    mention = db.query(Mention).filter(Mention.id == mention_id).first()
    if not mention:
        raise HTTPException(status_code=404, detail="Mention not found")
    return mention
