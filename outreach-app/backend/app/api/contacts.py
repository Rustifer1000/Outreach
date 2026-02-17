"""Contacts API endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Contact

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
    """Get a single contact by ID."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact
