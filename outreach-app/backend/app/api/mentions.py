"""Mentions API endpoints."""
from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Mention

router = APIRouter()


@router.get("")
async def list_mentions(
    days: int = Query(7, ge=1, le=90, description="Mentions from last N days"),
    contact_id: int | None = Query(None, description="Filter by contact"),
    max_per_contact: int = Query(2, ge=1, le=5, description="Max mentions per contact (1-2 typical)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List recent mentions. Limits to max_per_contact per person on dashboard."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    # Filter by published_at (news date) when available, else created_at (when we added it)
    from sqlalchemy import or_, and_
    query = (
        db.query(Mention)
        .options(joinedload(Mention.contact))
        .filter(
            or_(
                Mention.published_at >= cutoff,
                and_(Mention.published_at.is_(None), Mention.created_at >= cutoff),
            )
        )
    )
    if contact_id:
        query = query.filter(Mention.contact_id == contact_id)
    mentions = query.order_by(Mention.published_at.desc().nullslast()).all()

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


@router.get("/{mention_id}")
async def get_mention(mention_id: int, db: Session = Depends(get_db)):
    """Get a single mention by ID."""
    mention = (
        db.query(Mention)
        .options(joinedload(Mention.contact))
        .filter(Mention.id == mention_id)
        .first()
    )
    if not mention:
        raise HTTPException(status_code=404, detail="Mention not found")
    return {
        "id": mention.id,
        "contact_id": mention.contact_id,
        "contact_name": mention.contact.name if mention.contact else None,
        "source_type": mention.source_type,
        "source_url": mention.source_url,
        "title": mention.title,
        "snippet": mention.snippet,
        "published_at": mention.published_at.isoformat() if mention.published_at else None,
        "created_at": mention.created_at.isoformat() if mention.created_at else None,
        "relevance_score": mention.relevance_score,
    }
