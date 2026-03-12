"""Digest API endpoints — mention summaries by category."""
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Contact, Mention

router = APIRouter()


@router.get("")
def get_digest(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Get a digest of recent mentions grouped by contact category."""
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)

    # Get mentions with contacts
    mentions = (
        db.query(Mention, Contact)
        .join(Contact, Mention.contact_id == Contact.id)
        .filter(Mention.created_at >= cutoff)
        .order_by(Mention.published_at.desc().nullslast())
        .all()
    )

    # Group by category
    by_category: dict[str, list] = {}
    for mention, contact in mentions:
        cat = contact.category or "Uncategorized"
        by_category.setdefault(cat, [])
        by_category[cat].append({
            "id": mention.id,
            "contact_id": contact.id,
            "contact_name": contact.name,
            "title": mention.title,
            "snippet": mention.snippet,
            "source_type": mention.source_type,
            "source_url": mention.source_url,
            "published_at": mention.published_at.isoformat() if mention.published_at else None,
        })

    # Build summary
    categories = []
    for cat, items in sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True):
        unique_contacts = len(set(m["contact_id"] for m in items))
        categories.append({
            "category": cat,
            "mention_count": len(items),
            "unique_contacts": unique_contacts,
            "mentions": items[:10],  # Top 10 per category
        })

    total_mentions = sum(c["mention_count"] for c in categories)
    total_contacts = len(set(m["contact_id"] for cat_data in by_category.values() for m in cat_data))

    return {
        "period_days": days,
        "total_mentions": total_mentions,
        "total_contacts": total_contacts,
        "categories": categories,
    }
