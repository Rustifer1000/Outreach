"""Message template API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Template

router = APIRouter()


class TemplateCreate(BaseModel):
    name: str = Field(..., max_length=255)
    category: str | None = Field(None, max_length=255)
    subject: str | None = Field(None, max_length=500)
    body: str


class TemplateUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    category: str | None = Field(None, max_length=255)
    subject: str | None = Field(None, max_length=500)
    body: str | None = None


@router.get("")
def list_templates(
    category: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List message templates."""
    query = db.query(Template)
    if category:
        query = query.filter(Template.category == category)
    total = query.count()
    templates = query.order_by(Template.name).offset(skip).limit(limit).all()
    return {"total": total, "templates": templates, "skip": skip, "limit": limit}


@router.post("", status_code=201)
def create_template(body: TemplateCreate, db: Session = Depends(get_db)):
    """Create a message template."""
    t = Template(name=body.name, category=body.category, subject=body.subject, body=body.body)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/{template_id}")
def update_template(template_id: int, body: TemplateUpdate, db: Session = Depends(get_db)):
    """Update a template."""
    t = db.query(Template).filter(Template.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    if body.name is not None:
        t.name = body.name
    if body.category is not None:
        t.category = body.category
    if body.subject is not None:
        t.subject = body.subject
    if body.body is not None:
        t.body = body.body
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a template."""
    t = db.query(Template).filter(Template.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(t)
    db.commit()
