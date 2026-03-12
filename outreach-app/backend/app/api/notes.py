"""Notes API endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Contact, Note

router = APIRouter()


class NoteCreate(BaseModel):
    contact_id: int
    note_text: str
    channel: str | None = Field(None, max_length=50)
    note_date: datetime | None = None


@router.get("")
def list_notes(
    contact_id: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List notes, optionally filtered by contact."""
    query = db.query(Note).options(joinedload(Note.contact))
    if contact_id is not None:
        query = query.filter(Note.contact_id == contact_id)
    total = query.count()
    notes = query.order_by(Note.note_date.desc().nullslast(), Note.created_at.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "notes": [
            {
                "id": n.id,
                "contact_id": n.contact_id,
                "contact_name": n.contact.name if n.contact else None,
                "note_text": n.note_text,
                "channel": n.channel,
                "note_date": n.note_date.isoformat() if n.note_date else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes
        ],
        "skip": skip,
        "limit": limit,
    }


@router.post("", status_code=201)
def create_note(body: NoteCreate, db: Session = Depends(get_db)):
    """Create a conversation note."""
    contact = db.query(Contact).filter(Contact.id == body.contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    note = Note(
        contact_id=body.contact_id,
        note_text=body.note_text,
        channel=body.channel,
        note_date=body.note_date,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: int, db: Session = Depends(get_db)):
    """Delete a note."""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
