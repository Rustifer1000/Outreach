"""Phase 3: Relevance scoring, hot lead detection, disambiguation, and daily digest.

Scoring factors:
  - Recency:   newer mentions score higher
  - Source type: direct appearances (podcast, video) > news articles > web results
  - Name prominence: name in title > name only in snippet
  - Disambiguation: penalize when contact's role/org doesn't appear in mention text
  - Confidence: low-confidence mentions get flagged for review

Hot lead detection:
  - Activity spike: more mentions than normal in recent window
  - Cross-platform: mentioned in multiple source types
  - High-score mentions: average relevance above threshold
"""
import re
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Contact, ContactConnection, Mention, OutreachLog


# --- Relevance scoring ---

SOURCE_TYPE_WEIGHTS = {
    "podcast": 1.0,   # Direct appearance / interview
    "video": 0.9,     # Video appearance (keynote, panel, interview)
    "speech": 0.8,    # Conference / testimony
    "news": 0.6,      # News article mention
}
DEFAULT_SOURCE_WEIGHT = 0.4

# Hot lead detection thresholds
HOT_LEAD_VOLUME_CAP = 5.0      # 5+ mentions = max volume score
HOT_LEAD_DIVERSITY_CAP = 3.0   # 3+ source types = max diversity score


def _name_in_text(name: str, text: str) -> tuple[bool, float]:
    """Check if a name appears in text. Returns (found, score_boost).

    Full name match = 1.0, last name only = 0.5, not found = 0.0
    """
    if not text:
        return False, 0.0
    text_lower = text.lower()
    name_lower = name.lower().strip()
    # Full name match
    if name_lower in text_lower:
        return True, 1.0
    # Last name only (for "Dr. Smith" type matches)
    parts = name_lower.split()
    if len(parts) >= 2 and parts[-1] in text_lower:
        return True, 0.5
    return False, 0.0


def _disambiguation_score(contact: Contact, title: str | None, snippet: str | None) -> float:
    """Score how likely this mention is about the right person.

    Uses role_org, category, and connection_to_solomon as context clues.
    Returns 0.0 (likely wrong person) to 1.0 (high confidence match).
    """
    text = ((title or "") + " " + (snippet or "")).lower()
    if not text.strip():
        return 0.5  # No text to judge

    clues = 0
    matches = 0

    # Check role/org keywords
    if contact.role_org:
        clues += 1
        org_words = [w.strip().lower() for w in re.split(r'[,;/&]', contact.role_org) if len(w.strip()) > 3]
        if any(w in text for w in org_words):
            matches += 1

    # Check category keywords
    if contact.category:
        clues += 1
        cat_words = [w.strip().lower() for w in contact.category.replace("Category", "").split() if len(w.strip()) > 3]
        if any(w in text for w in cat_words):
            matches += 1

    # Check primary interests
    if contact.primary_interests:
        clues += 1
        interest_words = [w.strip().lower() for w in re.split(r'[,;.]', contact.primary_interests) if len(w.strip()) > 3]
        if any(w in text for w in interest_words[:5]):
            matches += 1

    if clues == 0:
        return 0.5  # No context clues available
    return max(0.2, matches / clues)


def score_mention(mention: Mention, contact: Contact) -> float:
    """Compute relevance score (0.0 - 1.0) for a single mention.

    Components (weighted):
      - recency:       30%  (decays over 30 days)
      - source_type:   20%  (podcast > video > speech > news)
      - name_in_title: 15%  (name found in title)
      - disambiguation: 35% (mention matches contact's domain)
    """
    # Recency (0-1, 1.0 = today, 0.0 = 30+ days ago)
    now = datetime.now(UTC)
    pub = mention.published_at or mention.created_at or now
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=UTC)
    days_old = max(0, (now - pub).total_seconds() / 86400)
    recency = max(0.0, 1.0 - (days_old / 30.0))

    # Source type weight
    source_w = SOURCE_TYPE_WEIGHTS.get(mention.source_type, DEFAULT_SOURCE_WEIGHT)

    # Name prominence in title
    _, title_score = _name_in_text(contact.name, mention.title)

    # Disambiguation
    disambig = _disambiguation_score(contact, mention.title, mention.snippet)

    score = (
        0.30 * recency
        + 0.20 * source_w
        + 0.15 * title_score
        + 0.35 * disambig
    )
    return round(min(1.0, max(0.0, score)), 3)


def score_all_mentions(db: Session, contact_id: int | None = None, rescore: bool = False) -> dict:
    """Score all mentions (or just for one contact). Stores in DB.

    Args:
        contact_id: If set, only score for this contact
        rescore: If True, re-score even if already scored

    Returns: {scored, skipped}
    """
    query = db.query(Mention)
    if contact_id:
        query = query.filter(Mention.contact_id == contact_id)
    if not rescore:
        query = query.filter(Mention.relevance_score.is_(None))

    mentions = query.all()
    # Pre-load contacts
    contact_ids = {m.contact_id for m in mentions}
    contacts = {c.id: c for c in db.query(Contact).filter(Contact.id.in_(contact_ids)).all()}

    scored = 0
    for m in mentions:
        contact = contacts.get(m.contact_id)
        if not contact:
            continue
        m.relevance_score = score_mention(m, contact)
        scored += 1

    db.commit()
    return {"scored": scored, "skipped": len(mentions) - scored}


# --- Hot lead detection ---

def get_hot_leads(
    db: Session,
    days: int = 7,
    min_mentions: int = 2,
    min_avg_score: float = 0.4,
    limit: int = 10,
) -> list[dict]:
    """Identify contacts with unusual recent activity (hot leads).

    Criteria (any of):
      - >= min_mentions in the last `days` days
      - Average relevance_score >= min_avg_score
      - Mentions across 2+ source types (cross-platform visibility)

    Returns list sorted by heat_score (composite).
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Aggregate mention stats per contact
    stats = (
        db.query(
            Mention.contact_id,
            func.count(Mention.id).label("mention_count"),
            func.avg(Mention.relevance_score).label("avg_score"),
            func.count(func.distinct(Mention.source_type)).label("source_types"),
        )
        .filter(
            Mention.published_at >= cutoff
        )
        .group_by(Mention.contact_id)
        .all()
    )

    hot = []
    for row in stats:
        cid, count, avg_sc, src_types = row
        avg_sc = avg_sc or 0.0

        # Heat score: weighted combination
        volume_score = min(1.0, count / HOT_LEAD_VOLUME_CAP)
        quality_score = avg_sc
        diversity_score = min(1.0, src_types / HOT_LEAD_DIVERSITY_CAP)

        heat = round(
            0.40 * volume_score + 0.35 * quality_score + 0.25 * diversity_score,
            3,
        )

        # Only flag if meaningful activity
        is_hot = count >= min_mentions or avg_sc >= min_avg_score or src_types >= 2
        if is_hot:
            hot.append({
                "contact_id": cid,
                "mention_count": count,
                "avg_relevance": round(avg_sc, 3),
                "source_type_count": src_types,
                "heat_score": heat,
            })

    # Sort by heat score descending
    hot.sort(key=lambda x: x["heat_score"], reverse=True)

    # Enrich with contact info
    if hot:
        cids = [h["contact_id"] for h in hot[:limit]]
        contacts = {c.id: c for c in db.query(Contact).filter(Contact.id.in_(cids)).all()}
        for h in hot[:limit]:
            c = contacts.get(h["contact_id"])
            if c:
                h["contact_name"] = c.name
                h["category"] = c.category
                h["relationship_stage"] = c.relationship_stage

    return hot[:limit]


# --- Daily digest ---

def generate_daily_digest(db: Session, hours: int = 24) -> dict:
    """Generate a daily digest of activity and recommendations.

    Returns:
      - new_mentions: count + breakdown by source type
      - hot_leads: top contacts by heat score
      - follow_up_due: contacts with outreach > 7 days ago and no reply
      - low_confidence_mentions: mentions with poor disambiguation scores
      - summary: human-readable text
    """
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    # --- New mentions ---
    new_mentions = (
        db.query(Mention)
        .filter(Mention.created_at >= cutoff)
        .all()
    )
    by_source: dict[str, int] = {}
    by_contact: dict[int, int] = {}
    for m in new_mentions:
        by_source[m.source_type] = by_source.get(m.source_type, 0) + 1
        by_contact[m.contact_id] = by_contact.get(m.contact_id, 0) + 1

    # --- Hot leads ---
    hot_leads = get_hot_leads(db, days=7, limit=5)

    # --- Follow-up due ---
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    stale_outreach = (
        db.query(OutreachLog)
        .filter(
            OutreachLog.response_status.in_(["sent", "no_response"]),
            OutreachLog.sent_at <= seven_days_ago,
        )
        .all()
    )
    # Group by contact, find most recent per contact
    latest_per_contact: dict[int, OutreachLog] = {}
    for o in stale_outreach:
        if o.contact_id not in latest_per_contact or (o.sent_at and o.sent_at > (latest_per_contact[o.contact_id].sent_at or cutoff)):
            latest_per_contact[o.contact_id] = o

    # Only include if no more recent outreach or reply
    replied_ids = {
        r.contact_id
        for r in db.query(OutreachLog)
        .filter(OutreachLog.response_status == "replied")
        .all()
    }
    follow_ups = []
    if latest_per_contact:
        cids = list(latest_per_contact.keys())
        contacts = {c.id: c for c in db.query(Contact).filter(Contact.id.in_(cids)).all()}
        for cid, outreach in latest_per_contact.items():
            if cid in replied_ids:
                continue
            c = contacts.get(cid)
            sent = outreach.sent_at
            if sent is None:
                sent = datetime.now(UTC)
            elif sent.tzinfo is None:
                sent = sent.replace(tzinfo=UTC)
            days_since = (datetime.now(UTC) - sent).days
            follow_ups.append({
                "contact_id": cid,
                "contact_name": c.name if c else f"Contact #{cid}",
                "last_method": outreach.method,
                "last_sent": outreach.sent_at.isoformat() if outreach.sent_at else None,
                "days_since": days_since,
            })
    follow_ups.sort(key=lambda x: x["days_since"], reverse=True)

    # --- Low confidence mentions (disambiguation < 0.3) ---
    low_conf = (
        db.query(Mention)
        .filter(
            Mention.relevance_score.isnot(None),
            Mention.relevance_score < 0.3,
            Mention.created_at >= cutoff,
        )
        .all()
    )
    low_confidence = []
    if low_conf:
        cids = [m.contact_id for m in low_conf]
        contacts = {c.id: c for c in db.query(Contact).filter(Contact.id.in_(cids)).all()}
        for m in low_conf:
            c = contacts.get(m.contact_id)
            low_confidence.append({
                "mention_id": m.id,
                "contact_name": c.name if c else f"Contact #{m.contact_id}",
                "title": m.title,
                "relevance_score": m.relevance_score,
                "source_type": m.source_type,
            })

    # --- Summary text ---
    parts = []
    if new_mentions:
        parts.append(f"{len(new_mentions)} new mentions ({', '.join(f'{v} {k}' for k, v in by_source.items())})")
    else:
        parts.append("No new mentions")

    if hot_leads:
        names = ", ".join(h["contact_name"] for h in hot_leads[:3] if "contact_name" in h)
        parts.append(f"{len(hot_leads)} hot leads: {names}")

    if follow_ups:
        parts.append(f"{len(follow_ups)} contacts due for follow-up")

    if low_confidence:
        parts.append(f"{len(low_confidence)} low-confidence mentions to review")

    return {
        "period_hours": hours,
        "generated_at": datetime.now(UTC).isoformat(),
        "new_mentions": {
            "total": len(new_mentions),
            "by_source_type": by_source,
            "contacts_mentioned": len(by_contact),
        },
        "hot_leads": hot_leads,
        "follow_up_due": follow_ups[:10],
        "low_confidence_mentions": low_confidence,
        "summary": ". ".join(parts) + ".",
    }
