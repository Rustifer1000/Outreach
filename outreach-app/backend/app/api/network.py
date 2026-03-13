"""Network / interconnection API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Contact, Interconnection

router = APIRouter()


class ConnectionCreate(BaseModel):
    contact_a_id: int
    contact_b_id: int
    connection_type: str = Field(..., max_length=100)
    notes: str | None = None


@router.get("")
def list_connections(
    contact_id: int | None = Query(None, description="Show connections for a specific contact"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List interconnections."""
    query = db.query(Interconnection)
    if contact_id is not None:
        query = query.filter(
            (Interconnection.contact_a_id == contact_id) | (Interconnection.contact_b_id == contact_id)
        )
    total = query.count()
    conns = query.order_by(Interconnection.created_at.desc()).offset(skip).limit(limit).all()

    # Resolve names
    contact_ids = set()
    for c in conns:
        contact_ids.add(c.contact_a_id)
        contact_ids.add(c.contact_b_id)
    contacts = {c.id: c.name for c in db.query(Contact).filter(Contact.id.in_(contact_ids)).all()} if contact_ids else {}

    return {
        "total": total,
        "connections": [
            {
                "id": c.id,
                "contact_a_id": c.contact_a_id,
                "contact_a_name": contacts.get(c.contact_a_id),
                "contact_b_id": c.contact_b_id,
                "contact_b_name": contacts.get(c.contact_b_id),
                "connection_type": c.connection_type,
                "notes": c.notes,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in conns
        ],
        "skip": skip,
        "limit": limit,
    }


@router.post("", status_code=201)
def create_connection(body: ConnectionCreate, db: Session = Depends(get_db)):
    """Create an interconnection between two contacts."""
    if body.contact_a_id == body.contact_b_id:
        raise HTTPException(status_code=400, detail="Cannot connect a contact to themselves")
    for cid in [body.contact_a_id, body.contact_b_id]:
        if not db.query(Contact).filter(Contact.id == cid).first():
            raise HTTPException(status_code=404, detail=f"Contact {cid} not found")
    conn = Interconnection(
        contact_a_id=body.contact_a_id,
        contact_b_id=body.contact_b_id,
        connection_type=body.connection_type,
        notes=body.notes,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return conn


@router.delete("/{connection_id}", status_code=204)
def delete_connection(connection_id: int, db: Session = Depends(get_db)):
    """Delete an interconnection."""
    conn = db.query(Interconnection).filter(Interconnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    db.delete(conn)
    db.commit()


@router.get("/warm-intros/{contact_id}")
def find_warm_intros(contact_id: int, db: Session = Depends(get_db)):
    """Find potential warm intro paths to a contact through shared connections."""
    target = db.query(Contact).filter(Contact.id == contact_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Contact not found")

    # Find all contacts connected to the target
    conns = (
        db.query(Interconnection)
        .filter((Interconnection.contact_a_id == contact_id) | (Interconnection.contact_b_id == contact_id))
        .all()
    )

    # Batch-load all connected contacts to avoid N+1 queries
    intro_ids = set()
    for c in conns:
        intro_ids.add(c.contact_b_id if c.contact_a_id == contact_id else c.contact_a_id)
    contacts_map = {ct.id: ct for ct in db.query(Contact).filter(Contact.id.in_(intro_ids)).all()} if intro_ids else {}

    intros = []
    for c in conns:
        intro_id = c.contact_b_id if c.contact_a_id == contact_id else c.contact_a_id
        intro_contact = contacts_map.get(intro_id)
        if intro_contact:
            intros.append({
                "intro_contact_id": intro_contact.id,
                "intro_contact_name": intro_contact.name,
                "relationship_stage": intro_contact.relationship_stage,
                "connection_type": c.connection_type,
                "notes": c.notes,
            })

    # Sort: engaged/partner contacts first (better intro sources)
    stage_order = {"partner": 0, "engaged": 1, "warm": 2, "cold": 3}
    intros.sort(key=lambda x: stage_order.get(x["relationship_stage"] or "cold", 4))

    return {"target": {"id": target.id, "name": target.name}, "intros": intros}
