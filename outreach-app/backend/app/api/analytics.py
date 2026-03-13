"""Analytics API endpoints."""
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Contact, Mention, OutreachLog

router = APIRouter()


@router.get("/funnel")
def outreach_funnel(db: Session = Depends(get_db)):
    """Get outreach funnel counts by relationship stage."""
    stages = ["cold", "warm", "engaged", "partner"]
    counts = {}
    for stage in stages:
        counts[stage] = db.query(func.count(Contact.id)).filter(Contact.relationship_stage == stage).scalar() or 0
    # Count contacts with at least one outreach as "contacted"
    contacted = (
        db.query(func.count(func.distinct(OutreachLog.contact_id))).scalar() or 0
    )
    # Count contacts that got a reply
    replied = (
        db.query(func.count(func.distinct(OutreachLog.contact_id)))
        .filter(OutreachLog.response_status == "replied")
        .scalar() or 0
    )
    total = db.query(func.count(Contact.id)).scalar() or 0
    return {
        "total_contacts": total,
        "contacted": contacted,
        "replied": replied,
        "stages": counts,
    }


@router.get("/conversion")
def conversion_by_category(db: Session = Depends(get_db)):
    """Get outreach conversion rates by contact category."""
    categories = (
        db.query(Contact.category)
        .filter(Contact.category.isnot(None))
        .distinct()
        .all()
    )
    results = []
    for (cat,) in categories:
        contact_ids = [c.id for c in db.query(Contact.id).filter(Contact.category == cat).all()]
        if not contact_ids:
            continue
        total = len(contact_ids)
        contacted = (
            db.query(func.count(func.distinct(OutreachLog.contact_id)))
            .filter(OutreachLog.contact_id.in_(contact_ids))
            .scalar() or 0
        )
        replied = (
            db.query(func.count(func.distinct(OutreachLog.contact_id)))
            .filter(OutreachLog.contact_id.in_(contact_ids), OutreachLog.response_status == "replied")
            .scalar() or 0
        )
        results.append({
            "category": cat,
            "total": total,
            "contacted": contacted,
            "replied": replied,
            "contact_rate": round(contacted / total * 100, 1) if total else 0,
            "reply_rate": round(replied / contacted * 100, 1) if contacted else 0,
        })
    results.sort(key=lambda x: x["reply_rate"], reverse=True)
    return {"categories": results}


@router.get("/mention-lag")
def mention_to_contact_lag(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Calculate average time between mention and first outreach."""
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
    mentions = (
        db.query(Mention.contact_id, func.min(Mention.published_at).label("first_mention"))
        .filter(Mention.published_at >= cutoff)
        .group_by(Mention.contact_id)
        .all()
    )

    lags = []
    for contact_id, first_mention in mentions:
        if not first_mention:
            continue
        first_outreach = (
            db.query(func.min(OutreachLog.sent_at))
            .filter(OutreachLog.contact_id == contact_id, OutreachLog.sent_at >= first_mention)
            .scalar()
        )
        if first_outreach:
            lag_days = (first_outreach - first_mention).total_seconds() / 86400
            lags.append(lag_days)

    if not lags:
        return {"average_lag_days": None, "median_lag_days": None, "within_48h_pct": None, "sample_size": 0}

    lags.sort()
    avg = round(sum(lags) / len(lags), 1)
    n = len(lags)
    if n % 2 == 1:
        median = round(lags[n // 2], 1)
    else:
        median = round((lags[n // 2 - 1] + lags[n // 2]) / 2, 1)
    within_48h = round(sum(1 for l in lags if l <= 2) / len(lags) * 100, 1)
    return {
        "average_lag_days": avg,
        "median_lag_days": median,
        "within_48h_pct": within_48h,
        "sample_size": len(lags),
    }


@router.get("/channel-effectiveness")
def channel_effectiveness(db: Session = Depends(get_db)):
    """Get response rates by outreach channel."""
    methods = db.query(OutreachLog.method).distinct().all()
    results = []
    for (method,) in methods:
        total = db.query(func.count(OutreachLog.id)).filter(OutreachLog.method == method).scalar() or 0
        replied = (
            db.query(func.count(OutreachLog.id))
            .filter(OutreachLog.method == method, OutreachLog.response_status == "replied")
            .scalar() or 0
        )
        results.append({
            "method": method,
            "total_sent": total,
            "replied": replied,
            "response_rate": round(replied / total * 100, 1) if total else 0,
        })
    results.sort(key=lambda x: x["response_rate"], reverse=True)
    return {"channels": results}


@router.get("/activity")
def activity_over_time(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
):
    """Get mention and outreach counts per week."""
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
    mention_dates = (
        db.query(Mention.created_at)
        .filter(Mention.created_at >= cutoff, Mention.created_at.isnot(None))
        .all()
    )
    outreach_dates = (
        db.query(OutreachLog.created_at)
        .filter(OutreachLog.created_at >= cutoff, OutreachLog.created_at.isnot(None))
        .all()
    )

    # Group by ISO week
    weeks: dict[str, dict] = {}
    for (dt,) in mention_dates:
        week = dt.strftime("%Y-W%W")
        weeks.setdefault(week, {"mentions": 0, "outreaches": 0})
        weeks[week]["mentions"] += 1
    for (dt,) in outreach_dates:
        week = dt.strftime("%Y-W%W")
        weeks.setdefault(week, {"mentions": 0, "outreaches": 0})
        weeks[week]["outreaches"] += 1

    timeline = [{"week": w, **data} for w, data in sorted(weeks.items())]
    return {"timeline": timeline}
