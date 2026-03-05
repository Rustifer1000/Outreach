"""Outreach log API endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Contact, OutreachLog


class OutreachCreate(BaseModel):
    contact_id: int
    method: str
    subject: str | None = None
    content: str | None = None
    sent_at: datetime | None = None
    response_status: str | None = None

router = APIRouter()


@router.get("")
def list_outreach(
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


@router.post("", status_code=201)
def create_outreach(body: OutreachCreate, db: Session = Depends(get_db)):
    """Create a new outreach log entry."""
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
