"""Outreach log API endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OutreachLog, Contact

router = APIRouter()


class OutreachCreate(BaseModel):
    contact_id: int
    method: str
    subject: str | None = None
    content: str | None = None
    sent_at: str | None = None  # ISO datetime string
    response_status: str | None = None  # sent, replied, no_response, bounced


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
    return {
        "total": total,
        "entries": [
            {
                "id": e.id,
                "contact_id": e.contact_id,
                "method": e.method,
                "subject": e.subject,
                "content": e.content,
                "sent_at": e.sent_at.isoformat() if e.sent_at else None,
                "response_status": e.response_status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
        "skip": skip,
        "limit": limit,
    }


@router.post("")
async def create_outreach(data: OutreachCreate, db: Session = Depends(get_db)):
    """Add a new outreach log entry."""
    contact = db.query(Contact).filter(Contact.id == data.contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    sent_at = None
    if data.sent_at:
        from datetime import datetime, UTC
        try:
            sent_at = datetime.fromisoformat(data.sent_at.replace("Z", "+00:00"))
        except ValueError:
            pass

    entry = OutreachLog(
        contact_id=data.contact_id,
        method=data.method,
        subject=data.subject,
        content=data.content,
        sent_at=sent_at,
        response_status=data.response_status or "sent",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {
        "id": entry.id,
        "contact_id": entry.contact_id,
        "method": entry.method,
        "subject": entry.subject,
        "content": entry.content,
        "sent_at": entry.sent_at.isoformat() if entry.sent_at else None,
        "response_status": entry.response_status,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }
