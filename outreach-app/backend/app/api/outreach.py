"""Outreach log API endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OutreachLog

router = APIRouter()


@router.get("")
async def list_outreach(
    contact_id: int | None = Query(None, description="Filter by contact"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List outreach log entries."""
    query = db.query(OutreachLog)
    if contact_id:
        query = query.filter(OutreachLog.contact_id == contact_id)
    total = query.count()
    entries = query.order_by(OutreachLog.sent_at.desc().nullslast()).offset(skip).limit(limit).all()
    return {"total": total, "entries": entries, "skip": skip, "limit": limit}
