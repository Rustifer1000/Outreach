"""Outreach log API endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Contact, OutreachLog


class OutreachCreate(BaseModel):
    contact_id: int
    method: str = Field(..., max_length=50)
    subject: str | None = Field(None, max_length=500)
    content: str | None = None
    sent_at: datetime | None = None
    response_status: str | None = Field(None, max_length=50)


class OutreachStatusUpdate(BaseModel):
    response_status: str = Field(..., max_length=50)

router = APIRouter()


@router.get("")
def list_outreach(
    contact_id: int | None = Query(None, description="Filter by contact"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List outreach log entries."""
    query = db.query(OutreachLog).options(joinedload(OutreachLog.contact))
    if contact_id is not None:
        query = query.filter(OutreachLog.contact_id == contact_id)
    total = query.count()
    entries = query.order_by(OutreachLog.sent_at.desc().nullslast()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "entries": [
            {
                "id": e.id,
                "contact_id": e.contact_id,
                "contact_name": e.contact.name if e.contact else None,
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


@router.post("", status_code=201)
def create_outreach(body: OutreachCreate, db: Session = Depends(get_db)):
    """Create a new outreach log entry.

    TODO: Add authentication before deployment - this endpoint is currently unprotected.
    """
    contact = db.query(Contact).filter(Contact.id == body.contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    entry = OutreachLog(
        contact_id=body.contact_id,
        method=body.method,
        subject=body.subject,
        content=body.content,
        sent_at=body.sent_at,
        response_status=body.response_status,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/{outreach_id}")
def update_outreach_status(outreach_id: int, body: OutreachStatusUpdate, db: Session = Depends(get_db)):
    """Update response status of an outreach entry."""
    entry = db.query(OutreachLog).filter(OutreachLog.id == outreach_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Outreach entry not found")
    entry.response_status = body.response_status
    db.commit()
    db.refresh(entry)
    return entry
