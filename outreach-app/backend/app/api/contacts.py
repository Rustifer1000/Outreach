"""Contacts API endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Contact

router = APIRouter()


@router.get("")
def list_contacts(
    q: str | None = Query(None, description="Search by name or category"),
    category: str | None = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List contacts with optional search and filter."""
    query = db.query(Contact)
    if q:
        escaped = q.replace("%", r"\%").replace("_", r"\_")
        query = query.filter(
            Contact.name.ilike(f"%{escaped}%", escape="\\")
            | Contact.category.ilike(f"%{escaped}%", escape="\\")
        )
    if category:
        escaped_cat = category.replace("%", r"\%").replace("_", r"\_")
        query = query.filter(Contact.category.ilike(f"%{escaped_cat}%", escape="\\"))
    total = query.count()
    contacts = query.order_by(Contact.list_number).offset(skip).limit(limit).all()
    return {"total": total, "contacts": contacts, "skip": skip, "limit": limit}


@router.get("/summary")
def contacts_summary(db: Session = Depends(get_db)):
    """Get contact count and list_number range for rotation planning."""
    total = db.query(func.count(Contact.id)).scalar()
    min_num = db.query(func.min(Contact.list_number)).scalar()
    max_num = db.query(func.max(Contact.list_number)).scalar()
    return {"total": total, "min_list_number": min_num or 1, "max_list_number": max_num or 0}


@router.get("/{contact_id}")
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    """Get a single contact by ID."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact
