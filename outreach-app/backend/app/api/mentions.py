"""Mentions API endpoints."""
from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Mention

router = APIRouter()


@router.get("/fetch/status")
def get_fetch_status():
    """Return the status of the current or last mention fetch job."""
    from app.api.jobs import get_fetch_status as _get
    return _get()


@router.get("")
def list_mentions(
    days: int = Query(7, ge=1, le=90, description="Mentions from last N days"),
    contact_id: int | None = Query(None, description="Filter by contact"),
    max_per_contact: int = Query(2, ge=1, le=5, description="Max mentions per contact (1-2 typical)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List recent mentions. Limits to max_per_contact per person on dashboard (SQL)."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    date_filter = or_(
        Mention.published_at >= cutoff,
        and_(Mention.published_at.is_(None), Mention.created_at >= cutoff),
    )

    if contact_id:
        # Single contact: no per-contact limit, fetch all for that contact
        query = (
            db.query(Mention)
            .options(joinedload(Mention.contact))
            .filter(date_filter, Mention.contact_id == contact_id, Mention.dismissed == 0)
            .order_by(Mention.published_at.desc().nullslast())
        )
        total = query.count()
        mentions = query.offset(skip).limit(limit).all()
    else:
        # Dashboard: limit per contact in SQL using ROW_NUMBER
        rn = func.row_number().over(
            partition_by=Mention.contact_id,
            order_by=Mention.published_at.desc().nullslast(),
        ).label("rn")
        subq = db.query(Mention, rn).filter(date_filter, Mention.dismissed == 0).subquery()
        mention_alias = db.query(Mention).join(
            subq, Mention.id == subq.c.id
        ).filter(subq.c.rn <= max_per_contact)
        total = db.query(func.count()).select_from(subq).filter(
            subq.c.rn <= max_per_contact
        ).scalar() or 0
        mentions = (
            mention_alias.options(joinedload(Mention.contact))
            .order_by(Mention.published_at.desc().nullslast())
            .offset(skip)
            .limit(limit)
            .all()
        )

    result = []
    for m in mentions:
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


class DismissMentionRequest(BaseModel):
    dismissed: bool
    reason: str | None = None


@router.patch("/{mention_id}")
def update_mention(mention_id: int, req: DismissMentionRequest, db: Session = Depends(get_db)):
    """Dismiss a mention as 'not this person' (or un-dismiss)."""
    mention = db.query(Mention).filter(Mention.id == mention_id).first()
    if not mention:
        raise HTTPException(status_code=404, detail="Mention not found")
    mention.dismissed = 1 if req.dismissed else 0
    mention.dismissed_reason = req.reason if req.dismissed else None
    db.commit()
    return {"id": mention.id, "dismissed": bool(mention.dismissed), "dismissed_reason": mention.dismissed_reason}


@router.get("/{mention_id}")
def get_mention(mention_id: int, db: Session = Depends(get_db)):
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
