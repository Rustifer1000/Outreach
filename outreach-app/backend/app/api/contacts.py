"""Contacts API endpoints."""
from collections import Counter
from datetime import UTC, datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.enrichment import enrich_contact_email
from app.models import Contact, ContactInfo, Note, ContactConnection, OutreachLog

# Priority order for first-contact recommendations
CONTACT_METHOD_PRIORITY = ["email", "linkedin", "twitter", "website", "other"]

# Stage-specific priority adjustments
STAGE_PRIORITY = {
    "Cold": ["email", "linkedin", "twitter", "website", "other"],
    "Warm": ["linkedin", "email", "twitter", "website", "other"],
    "Engaged": None,  # Use outreach history to determine
    "Partner-Advocate": ["email", "linkedin", "twitter", "website", "other"],
}


def get_recommended_method(
    contact_infos: list,
    outreach_logs: list | None = None,
    relationship_stage: str | None = None,
) -> dict:
    """Return recommended contact method factoring in availability, outreach history, and relationship stage.

    Priority logic:
    - Cold contacts: email first (formal, low-pressure)
    - Warm contacts: LinkedIn preferred (more personal)
    - Engaged contacts: use whatever method got replies; fall back to most-used
    - Partner-Advocate: email first (established relationship)
    - If a method was tried and got a reply, boost it
    - If a method was tried with no response, deprioritize it
    """
    types_present = {ci.type.lower() for ci in contact_infos}
    outreach_logs = outreach_logs or []

    # Analyze outreach history
    replied_methods: set[str] = set()
    no_response_methods: set[str] = set()
    method_counts: Counter[str] = Counter()
    for log in outreach_logs:
        m = (log.method or "").lower()
        method_counts[m] += 1
        if log.response_status == "replied":
            replied_methods.add(m)
        elif log.response_status in ("no_response", "bounced"):
            no_response_methods.add(m)

    # Determine base priority order from relationship stage
    stage = (relationship_stage or "").strip()
    if stage == "Engaged" and replied_methods:
        # For engaged contacts, prefer whatever method got replies
        priority = list(replied_methods) + [m for m in CONTACT_METHOD_PRIORITY if m not in replied_methods]
    elif stage in STAGE_PRIORITY and STAGE_PRIORITY[stage] is not None:
        priority = STAGE_PRIORITY[stage]
    else:
        priority = list(CONTACT_METHOD_PRIORITY)

    # Boost methods that got replies to the front
    if replied_methods:
        boosted = [m for m in priority if m in replied_methods]
        rest = [m for m in priority if m not in replied_methods]
        priority = boosted + rest

    # Deprioritize methods that got no response (push to end, but keep available)
    if no_response_methods and not replied_methods:
        good = [m for m in priority if m not in no_response_methods]
        bad = [m for m in priority if m in no_response_methods]
        priority = good + bad

    # Find the best available method
    for method in priority:
        if method in types_present:
            reason = _build_reason(method, stage, replied_methods, no_response_methods, method_counts)
            return {"method": method, "available": True, "reason": reason}

    # Nothing available — suggest based on stage
    if stage in ("Warm", "Engaged"):
        return {
            "method": "linkedin",
            "available": False,
            "reason": "LinkedIn (not found — add LinkedIn URL to contact info)",
        }
    return {
        "method": "email",
        "available": False,
        "reason": "Email (not found — add contact info or try enrichment)",
    }


def _build_reason(
    method: str,
    stage: str,
    replied_methods: set[str],
    no_response_methods: set[str],
    method_counts: Counter,
) -> str:
    """Build a human-readable reason string for the recommendation."""
    label = method.capitalize()
    parts: list[str] = []

    if method in replied_methods:
        parts.append("previously got a reply")
    elif method_counts.get(method, 0) > 0 and method not in no_response_methods:
        parts.append(f"used {method_counts[method]}x")

    if stage == "Cold":
        parts.append("good for cold outreach")
    elif stage == "Warm" and method == "linkedin":
        parts.append("personal touch for warm contacts")
    elif stage == "Engaged" and method in replied_methods:
        parts.append("proven channel")
    elif stage == "Partner-Advocate":
        parts.append("established relationship")

    # Note if other methods were tried without success
    tried_no_reply = no_response_methods - {method}
    if tried_no_reply:
        tried_label = ", ".join(m.capitalize() for m in sorted(tried_no_reply))
        parts.append(f"{tried_label} tried without reply")

    if parts:
        return f"{label} ({'; '.join(parts)})"
    return f"{label} (available)"


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
    query = db.query(Contact).options(joinedload(Contact.contact_info))
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

    # Batch-load outreach logs for all contacts in one query
    contact_ids = [c.id for c in contacts]
    all_outreach = db.query(OutreachLog).filter(OutreachLog.contact_id.in_(contact_ids)).all() if contact_ids else []
    outreach_by_contact: dict[int, list] = {}
    for log in all_outreach:
        outreach_by_contact.setdefault(log.contact_id, []).append(log)

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
                "recommended_contact_method": get_recommended_method(
                    list(c.contact_info) if c.contact_info else [],
                    outreach_by_contact.get(c.id),
                    c.relationship_stage,
                ),
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
    outreach_logs = db.query(OutreachLog).filter(OutreachLog.contact_id == contact_id).all()
    recommendation = get_recommended_method(contact_infos, outreach_logs, contact.relationship_stage)

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
        channel=(data.channel.strip() or None) if data.channel else None,
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
        notes=(data.notes.strip() or None) if data.notes else None,
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
    """Look up email (and LinkedIn if available) via Hunter API and add to contact_info."""
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

    # Also add LinkedIn if returned and not already present
    linkedin_url = result.get("linkedin_url")
    if linkedin_url:
        existing_li = any(ci.type == "linkedin" for ci in (contact.contact_info or []))
        if not existing_li:
            li_info = ContactInfo(
                contact_id=contact_id,
                type="linkedin",
                value=linkedin_url,
                is_primary=0,
            )
            db.add(li_info)

    db.commit()
    db.refresh(info)
    return {
        "found": True,
        "email": result["email"],
        "score": result.get("score"),
        "position": result.get("position"),
        "linkedin_url": linkedin_url,
    }


@router.post("/{contact_id}/enrich-bio")
async def enrich_bio(contact_id: int, db: Session = Depends(get_db)):
    """Generate a short bio summary from mention snippets using Claude."""
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY not configured. Add to .env for bio enrichment.",
        )

    from app.enrichment import generate_bio_summary
    from app.models import Mention

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    mentions = (
        db.query(Mention)
        .filter(Mention.contact_id == contact_id)
        .order_by(Mention.published_at.desc())
        .limit(5)
        .all()
    )
    snippets = [m.snippet for m in mentions if m.snippet]

    bio = generate_bio_summary(
        api_key=settings.anthropic_api_key,
        contact_name=contact.name,
        role_org=contact.role_org,
        connection_to_solomon=contact.connection_to_solomon,
        mention_snippets=snippets,
    )

    if not bio:
        return {"generated": False, "message": "Could not generate bio (not enough data or API error)."}

    # Store in primary_interests field (used for bio/interests)
    contact.primary_interests = bio
    db.commit()
    return {"generated": True, "bio": bio}
