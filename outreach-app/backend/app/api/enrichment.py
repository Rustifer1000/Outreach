"""Enrichment API endpoints."""
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, SessionLocal
from app.models import Contact, ContactInfo

router = APIRouter()

_enrichment_status: dict = {
    "running": False, "progress": "", "enriched": 0,
    "total_contacts": 0, "processed": 0, "error": None,
}


def _enrich_via_hunter(api_key: str, name: str, domain: str | None = None) -> dict | None:
    """Look up contact info via Hunter.io API."""
    params = {"full_name": name, "api_key": api_key}
    if domain:
        params["domain"] = domain
    try:
        with httpx.Client(timeout=30) as client:
            # Use email finder
            r = client.get("https://api.hunter.io/v2/email-finder", params=params)
            if r.status_code == 200:
                data = r.json().get("data", {})
                return {
                    "email": data.get("email"),
                    "score": data.get("score"),
                    "first_name": data.get("first_name"),
                    "last_name": data.get("last_name"),
                    "position": data.get("position"),
                    "linkedin": data.get("linkedin_url"),
                }
    except Exception:
        pass
    return None


def _run_enrichment(contact_ids: list[int] | None):
    """Background task: enrich contacts via Hunter API."""
    global _enrichment_status
    _enrichment_status = {
        "running": True, "progress": "Starting...", "enriched": 0,
        "total_contacts": 0, "processed": 0, "error": None,
    }

    api_key = settings.hunter_api_key
    if not api_key:
        _enrichment_status.update(running=False, error="No HUNTER_API_KEY configured. Add it to your .env file.")
        return

    db = SessionLocal()
    try:
        query = db.query(Contact).order_by(Contact.list_number)
        if contact_ids:
            query = query.filter(Contact.id.in_(contact_ids))
        else:
            # Only enrich contacts not yet enriched
            query = query.filter((Contact.enrichment_status.is_(None)) | (Contact.enrichment_status == "pending"))
        contacts = query.all()
        _enrichment_status["total_contacts"] = len(contacts)

        enriched = 0
        for i, contact in enumerate(contacts):
            _enrichment_status["processed"] = i + 1
            _enrichment_status["progress"] = f"Enriching {contact.name} ({i+1}/{len(contacts)})"

            # Extract domain from role_org if possible
            domain = None
            if contact.role_org:
                # Simple heuristic: look for common domain patterns
                parts = contact.role_org.lower().split()
                for p in parts:
                    if "." in p and len(p) > 4:
                        domain = p
                        break

            result = _enrich_via_hunter(api_key, contact.name, domain)
            if result:
                if result.get("email"):
                    existing = db.query(ContactInfo).filter(
                        ContactInfo.contact_id == contact.id,
                        ContactInfo.type == "email",
                        ContactInfo.value == result["email"],
                    ).first()
                    if not existing:
                        db.add(ContactInfo(
                            contact_id=contact.id, type="email",
                            value=result["email"], is_primary=1,
                        ))
                if result.get("linkedin"):
                    existing = db.query(ContactInfo).filter(
                        ContactInfo.contact_id == contact.id,
                        ContactInfo.type == "linkedin",
                    ).first()
                    if not existing:
                        db.add(ContactInfo(
                            contact_id=contact.id, type="linkedin",
                            value=result["linkedin"],
                        ))
                contact.enrichment_status = "enriched"
                contact.enriched_at = datetime.now(UTC).replace(tzinfo=None)
                enriched += 1
            else:
                contact.enrichment_status = "failed"
            db.commit()

        _enrichment_status.update(
            running=False, enriched=enriched,
            progress=f"Done. Enriched {enriched} contacts.",
        )
    except Exception as e:
        _enrichment_status.update(running=False, error=str(e))
    finally:
        db.close()


@router.post("/run")
def trigger_enrichment(
    background_tasks: BackgroundTasks,
    contact_ids: str | None = Query(None, description="Comma-separated contact IDs (blank = all unenriched)"),
):
    """Trigger background enrichment via Hunter API."""
    if _enrichment_status["running"]:
        return {"status": "already_running", "progress": _enrichment_status["progress"]}
    ids = [int(x.strip()) for x in contact_ids.split(",") if x.strip().isdigit()] if contact_ids else None
    background_tasks.add_task(_run_enrichment, ids)
    return {"status": "started"}


@router.get("/status")
def enrichment_status():
    """Check enrichment progress."""
    return dict(_enrichment_status)


@router.get("/summary")
def enrichment_summary(db: Session = Depends(get_db)):
    """Get enrichment coverage stats."""
    from sqlalchemy import func
    total = db.query(func.count(Contact.id)).scalar() or 0
    enriched = db.query(func.count(Contact.id)).filter(Contact.enrichment_status == "enriched").scalar() or 0
    failed = db.query(func.count(Contact.id)).filter(Contact.enrichment_status == "failed").scalar() or 0
    with_email = (
        db.query(func.count(func.distinct(ContactInfo.contact_id)))
        .filter(ContactInfo.type == "email")
        .scalar() or 0
    )
    with_linkedin = (
        db.query(func.count(func.distinct(ContactInfo.contact_id)))
        .filter(ContactInfo.type == "linkedin")
        .scalar() or 0
    )
    return {
        "total": total,
        "enriched": enriched,
        "failed": failed,
        "pending": total - enriched - failed,
        "with_email": with_email,
        "with_linkedin": with_linkedin,
    }
