"""Relationship map: all contacts as nodes, all contact_connections as edges."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Contact, ContactConnection

router = APIRouter()


@router.get("")
async def get_relationship_map(db: Session = Depends(get_db)):
    """
    Return the full graph for the relationship map.
    Nodes = all contacts; links = all contact_connections.
    Stays in sync: add/remove names (Names file + seed) or connections (contact detail) and refetch.
    """
    contacts = db.query(Contact).order_by(Contact.list_number).all()
    connections = db.query(ContactConnection).all()

    nodes = [
        {
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "relationship_stage": c.relationship_stage,
        }
        for c in contacts
    ]
    links = [
        {
            "source_id": c.contact_id,
            "target_id": c.other_contact_id,
            "relationship_type": c.relationship_type,
        }
        for c in connections
    ]
    return {"nodes": nodes, "links": links}
