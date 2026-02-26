"""Relevance scoring, hot leads, and daily digest endpoints."""
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.scoring import generate_daily_digest, get_hot_leads, score_all_mentions

router = APIRouter()


# In-memory store for async scoring results
_scoring_result: dict | None = None


def _run_score_all(contact_id: int | None, rescore: bool):
    global _scoring_result
    db = SessionLocal()
    try:
        _scoring_result = score_all_mentions(db, contact_id=contact_id, rescore=rescore)
    finally:
        db.close()


@router.post("/score-mentions")
async def trigger_score_mentions(
    background_tasks: BackgroundTasks,
    contact_id: int | None = Query(None, description="Score only this contact's mentions"),
    rescore: bool = Query(False, description="Re-score already-scored mentions"),
):
    """Score all unscored mentions (or re-score all). Runs in background."""
    global _scoring_result
    _scoring_result = None
    background_tasks.add_task(_run_score_all, contact_id, rescore)
    return {"status": "started", "message": "Scoring mentions in background. Check GET /api/digest/score-status."}


@router.get("/score-status")
async def get_score_status():
    """Check the result of the latest scoring run."""
    if _scoring_result is None:
        return {"status": "running", "message": "Scoring in progress or not started yet."}
    return {"status": "complete", **_scoring_result}


@router.get("/hot-leads")
async def api_hot_leads(
    days: int = Query(7, ge=1, le=90),
    min_mentions: int = Query(2, ge=1, le=20),
    min_avg_score: float = Query(0.4, ge=0.0, le=1.0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get contacts with unusual recent activity (hot leads).

    Returns contacts ranked by heat_score based on mention volume,
    relevance quality, and cross-platform visibility.
    """
    leads = get_hot_leads(
        db,
        days=days,
        min_mentions=min_mentions,
        min_avg_score=min_avg_score,
        limit=limit,
    )
    return {"hot_leads": leads, "count": len(leads), "period_days": days}


@router.get("/daily")
async def api_daily_digest(
    hours: int = Query(24, ge=1, le=168, description="Look-back window in hours"),
    db: Session = Depends(get_db),
):
    """Daily digest: new mentions, hot leads, follow-ups due, low-confidence flags.

    Call this once per day (or on demand) to get a summary of activity
    and recommended actions.
    """
    return generate_daily_digest(db, hours=hours)
