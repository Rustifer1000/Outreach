"""Contacts API endpoints."""
from datetime import UTC, datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.enrichment import enrich_contact_email
from app.models import Contact, ContactInfo, Note, ContactConnection

# Priority order for first-contact recommendations
CONTACT_METHOD_PRIORITY = ["email", "linkedin", "twitter", "website", "other"]


def get_recommended_method(contact_infos: list) -> dict:
    """Return recommended contact method and availability. Priority: email > linkedin > twitter > website > other."""
    types_present = {ci.type.lower() for ci in contact_infos}
    for method in CONTACT_METHOD_PRIORITY:
        if method in types_present:
            return {"method": method, "available": True, "reason": f"{method.capitalize()} (available)"}
    return {
        "method": CONTACT_METHOD_PRIORITY[0],
        "available": False,
        "reason": "Email (not found — add contact info or try LinkedIn)",
    }


router = APIRouter()


@router.get("")
async def list_contacts(
    q: str | None = Query(None, description="Search by name or category"),
    category: str | None = Query(None, description="Filter by category"),
    in_rotation: bool | None = Query(None, description="Filter to contacts in mention rotation"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List contacts with optional search and filter."""
    query = db.query(Contact)
    if q:
        query = query.filter(
            Contact.name.ilike(f"%{q}%") | Contact.category.ilike(f"%{q}%")
        )
    if category:
        query = query.filter(Contact.category.ilike(f"%{category}%"))
    if in_rotation:
        query = query.filter(Contact.in_mention_rotation == 1)
    total = query.count()
    contacts = query.order_by(Contact.list_number).offset(skip).limit(limit).all()
    return {
        "total": total,
        "contacts": [
            {
                "id": c.id,
                "list_number": c.list_number,
                "name": c.name,
                "category": c.category,
                "subcategory": c.subcategory,
                "role_org": c.role_org,
                "connection_to_solomon": c.connection_to_solomon,
                "primary_interests": c.primary_interests,
                "relationship_stage": c.relationship_stage,
                "in_mention_rotation": bool(getattr(c, "in_mention_rotation", 0)),
            }
            for c in contacts
        ],
        "skip": skip,
        "limit": limit,
    }


class RotationSetBody(BaseModel):
    contact_ids: list[int]


@router.put("/rotation")
async def set_mention_rotation(body: RotationSetBody, db: Session = Depends(get_db)):
    """Set the daily mention rotation: only these contact IDs will be included in the next mention fetch. Clears others."""
    # Set all to 0 first
    db.query(Contact).update({Contact.in_mention_rotation: 0}, synchronize_session=False)
    if body.contact_ids:
        # Set only matching IDs to 1 (IDs that don't exist are ignored)
        db.query(Contact).filter(Contact.id.in_(body.contact_ids)).update(
            {Contact.in_mention_rotation: 1}, synchronize_session=False
        )
    db.commit()
    count = db.query(Contact).filter(Contact.in_mention_rotation == 1).count()
    return {"in_rotation": count, "message": f"{count} contacts in today's mention rotation."}


@router.get("/rotation")
async def get_mention_rotation(db: Session = Depends(get_db)):
    """List contact IDs and names currently in the mention rotation."""
    contacts = db.query(Contact).filter(Contact.in_mention_rotation == 1).order_by(Contact.list_number).all()
    return {
        "contacts": [{"id": c.id, "name": c.name, "category": c.category} for c in contacts],
        "count": len(contacts),
    }


@router.get("/{contact_id}")
async def get_contact(contact_id: int, db: Session = Depends(get_db)):
    """Get a single contact by ID with contact info and first-contact recommendation."""
    contact = (
        db.query(Contact)
        .options(joinedload(Contact.contact_info))
        .filter(Contact.id == contact_id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact_infos = list(contact.contact_info) if contact.contact_info else []
    recommendation = get_recommended_method(contact_infos)

    return {
        "id": contact.id,
        "list_number": contact.list_number,
        "name": contact.name,
        "category": contact.category,
        "subcategory": contact.subcategory,
        "role_org": contact.role_org,
        "connection_to_solomon": contact.connection_to_solomon,
        "primary_interests": contact.primary_interests,
        "relationship_stage": contact.relationship_stage,
        "in_mention_rotation": bool(getattr(contact, "in_mention_rotation", 0)),
        "contact_info": [
            {"type": ci.type, "value": ci.value, "is_primary": bool(ci.is_primary)}
            for ci in contact_infos
        ],
        "recommended_contact_method": recommendation,
    }


class ContactPatch(BaseModel):
    relationship_stage: str | None = None
    in_mention_rotation: bool | None = None


@router.patch("/{contact_id}")
async def patch_contact(contact_id: int, data: ContactPatch, db: Session = Depends(get_db)):
    """Update contact (e.g. relationship stage, in_mention_rotation)."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    if data.relationship_stage is not None:
        contact.relationship_stage = data.relationship_stage.strip() or None
    if data.in_mention_rotation is not None:
        contact.in_mention_rotation = 1 if data.in_mention_rotation else 0
    db.commit()
    db.refresh(contact)
    return {
        "id": contact.id,
        "relationship_stage": contact.relationship_stage,
        "in_mention_rotation": bool(contact.in_mention_rotation),
    }


class NoteCreate(BaseModel):
    note_text: str
    note_date: str  # ISO date or datetime
    channel: str | None = None


@router.get("/{contact_id}/notes")
async def list_notes(contact_id: int, db: Session = Depends(get_db)):
    """List notes for a contact, newest first."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    notes = db.query(Note).filter(Note.contact_id == contact_id).order_by(Note.note_date.desc()).all()
    return {
        "notes": [
            {
                "id": n.id,
                "note_text": n.note_text,
                "note_date": n.note_date.isoformat() if n.note_date else None,
                "channel": n.channel,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes
        ],
    }


@router.post("/{contact_id}/notes")
async def create_note(contact_id: int, data: NoteCreate, db: Session = Depends(get_db)):
    """Add a conversation note."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    try:
        note_dt = datetime.fromisoformat(data.note_date.replace("Z", "+00:00"))
    except ValueError:
        note_dt = datetime.now(UTC)
    note = Note(
        contact_id=contact_id,
        note_text=data.note_text.strip(),
        note_date=note_dt,
        channel=data.channel.strip() or None if data.channel else None,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return {
        "id": note.id,
        "note_text": note.note_text,
        "note_date": note.note_date.isoformat(),
        "channel": note.channel,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }


class ConnectionCreate(BaseModel):
    other_contact_id: int
    relationship_type: str  # first_degree, second_degree, same_org, co_author, etc.
    notes: str | None = None


@router.get("/{contact_id}/connections")
async def list_connections(contact_id: int, db: Session = Depends(get_db)):
    """List how this contact is related to others on the list."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    conns = (
        db.query(ContactConnection)
        .options(joinedload(ContactConnection.other_contact))
        .filter(ContactConnection.contact_id == contact_id)
        .all()
    )
    return {
        "connections": [
            {
                "id": c.id,
                "other_contact_id": c.other_contact_id,
                "other_contact_name": c.other_contact.name if c.other_contact else None,
                "relationship_type": c.relationship_type,
                "notes": c.notes,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in conns
        ],
    }


@router.post("/{contact_id}/connections")
async def create_connection(contact_id: int, data: ConnectionCreate, db: Session = Depends(get_db)):
    """Record how this contact is related to another on the list."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    if data.other_contact_id == contact_id:
        raise HTTPException(status_code=400, detail="Cannot link contact to themselves")
    other = db.query(Contact).filter(Contact.id == data.other_contact_id).first()
    if not other:
        raise HTTPException(status_code=404, detail="Other contact not found")
    existing = (
        db.query(ContactConnection)
        .filter(
            ContactConnection.contact_id == contact_id,
            ContactConnection.other_contact_id == data.other_contact_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Connection already exists")
    conn = ContactConnection(
        contact_id=contact_id,
        other_contact_id=data.other_contact_id,
        relationship_type=data.relationship_type.strip(),
        notes=data.notes.strip() or None if data.notes else None,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return {
        "id": conn.id,
        "other_contact_id": conn.other_contact_id,
        "other_contact_name": other.name,
        "relationship_type": conn.relationship_type,
        "notes": conn.notes,
    }


@router.delete("/{contact_id}/connections/{connection_id}")
async def delete_connection(
    contact_id: int, connection_id: int, db: Session = Depends(get_db)
):
    """Remove a connection."""
    conn = (
        db.query(ContactConnection)
        .filter(
            ContactConnection.id == connection_id,
            ContactConnection.contact_id == contact_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    db.delete(conn)
    db.commit()
    return {"ok": True}


class ContactInfoCreate(BaseModel):
    type: str  # email, linkedin, twitter, website, phone, other
    value: str
    is_primary: bool = False


@router.post("/{contact_id}/info")
async def add_contact_info(
    contact_id: int, data: ContactInfoCreate, db: Session = Depends(get_db)
):
    """Add contact info (email, LinkedIn, etc.) for first-contact recommendations."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    info = ContactInfo(
        contact_id=contact_id,
        type=data.type.lower(),
        value=data.value.strip(),
        is_primary=1 if data.is_primary else 0,
    )
    db.add(info)
    db.commit()
    db.refresh(info)
    return {"id": info.id, "type": info.type, "value": info.value, "is_primary": info.is_primary}


@router.post("/{contact_id}/enrich")
async def enrich_contact(contact_id: int, db: Session = Depends(get_db)):
    """Look up email via Hunter API and add to contact_info if found."""
    if not settings.hunter_api_key:
        raise HTTPException(
            status_code=503,
            detail="HUNTER_API_KEY not configured. Add to .env for enrichment.",
        )
    contact = (
        db.query(Contact)
        .options(joinedload(Contact.contact_info))
        .filter(Contact.id == contact_id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Skip if already has email
    existing_emails = {ci.value.lower() for ci in (contact.contact_info or []) if ci.type == "email"}
    if existing_emails:
        return {"found": False, "message": "Contact already has email(s).", "emails": list(existing_emails)}

    result = enrich_contact_email(
        api_key=settings.hunter_api_key,
        full_name=contact.name,
        role_org=contact.role_org,
    )
    if not result:
        return {"found": False, "message": "No email found (check role_org has recognizable org)."}

    # Add email to contact_info
    info = ContactInfo(
        contact_id=contact_id,
        type="email",
        value=result["email"],
        is_primary=1,
    )
    db.add(info)
    db.commit()
    db.refresh(info)
    return {
        "found": True,
        "email": result["email"],
        "score": result.get("score"),
        "position": result.get("position"),
    }
