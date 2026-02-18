"""Contacts API endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Contact, ContactInfo

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
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
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
    total = query.count()
    contacts = query.order_by(Contact.list_number).offset(skip).limit(limit).all()
    return {"total": total, "contacts": contacts, "skip": skip, "limit": limit}


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
        "contact_info": [
            {"type": ci.type, "value": ci.value, "is_primary": bool(ci.is_primary)}
            for ci in contact_infos
        ],
        "recommended_contact_method": recommendation,
    }


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
