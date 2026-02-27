"""Phase 4: Warm intro path finding and mission alignment scoring.

Warm intros: given a target contact, find existing contacts who
can introduce you (because they have a connection to the target
AND are in an engaged/partner stage with you).

Mission alignment: auto-score contacts 1-10 based on category
keywords, with user override support.
"""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Contact, ContactConnection, ContactTag, OutreachLog


# --- Mission alignment auto-scoring ---

# Category keyword → alignment score (to Solomon's AI safety mission)
CATEGORY_ALIGNMENT: dict[str, float] = {
    "ai safety": 9.5,
    "ai alignment": 9.5,
    "existential risk": 9.0,
    "effective altruism": 8.5,
    "ai governance": 8.5,
    "ai policy": 8.0,
    "ai ethics": 8.0,
    "ai research": 7.5,
    "machine learning": 7.0,
    "philanthropy": 7.0,
    "impact investing": 7.0,
    "science funding": 7.0,
    "technology policy": 6.5,
    "science communication": 6.5,
    "journalism": 6.0,
    "media": 5.5,
    "government": 5.5,
    "academia": 5.0,
    "think tank": 5.0,
    "venture capital": 4.5,
    "business": 4.0,
}


def compute_mission_alignment(contact: Contact) -> float:
    """Compute mission alignment score (1-10) from category and connection_to_solomon.

    Higher = more aligned with Solomon's AI safety mission.
    """
    score = 5.0  # Default middle score

    # Check category
    if contact.category:
        cat_lower = contact.category.lower()
        for keyword, alignment in CATEGORY_ALIGNMENT.items():
            if keyword in cat_lower:
                score = max(score, alignment)
                break

    # Boost if connection_to_solomon field has strong keywords
    if contact.connection_to_solomon:
        conn_lower = contact.connection_to_solomon.lower()
        strong_signals = ["direct", "advisor", "board", "funder", "partner", "collaborat"]
        if any(s in conn_lower for s in strong_signals):
            score = min(10.0, score + 1.0)
        # Mild boost for any documented connection
        elif conn_lower.strip():
            score = min(10.0, score + 0.5)

    # Boost if primary_interests mention relevant topics
    if contact.primary_interests:
        interests_lower = contact.primary_interests.lower()
        relevant = ["ai safety", "alignment", "existential risk", "x-risk", "effective altruism"]
        if any(r in interests_lower for r in relevant):
            score = min(10.0, score + 1.0)

    return round(score, 1)


def score_all_alignments(db: Session, overwrite: bool = False) -> dict:
    """Compute mission alignment for all contacts. Stores in DB.

    Args:
        overwrite: If True, overwrite existing scores. If False, only score unscored contacts.

    Returns: {scored, skipped}
    """
    query = db.query(Contact)
    if not overwrite:
        query = query.filter(Contact.mission_alignment.is_(None))

    contacts = query.all()
    scored = 0
    for c in contacts:
        c.mission_alignment = compute_mission_alignment(c)
        scored += 1

    db.commit()
    return {"scored": scored, "skipped": 0}


# --- Warm intro path finding ---

# Relationship stage priority for intro sources (higher = better intro source)
STAGE_PRIORITY = {
    "Partner-Advocate": 4,
    "Engaged": 3,
    "Warm": 2,
    "Cold": 1,
}


def find_warm_intro_paths(
    db: Session,
    target_contact_id: int,
    limit: int = 10,
) -> list[dict]:
    """Find warm intro paths to a target contact.

    Algorithm:
    1. Find all contacts connected to the target (first-degree)
    2. Among those, rank by:
       - Our relationship stage with the connector (Engaged > Warm > Cold)
       - Whether the connector has replied to outreach
       - Connection strength (relationship type)

    Returns list of intro paths:
      [{connector_id, connector_name, relationship_stage, relationship_to_target,
        has_replied, intro_strength}]
    """
    target = db.query(Contact).filter(Contact.id == target_contact_id).first()
    if not target:
        return []

    # Find all connections where target is involved (either side)
    connections = (
        db.query(ContactConnection)
        .filter(
            or_(
                ContactConnection.contact_id == target_contact_id,
                ContactConnection.other_contact_id == target_contact_id,
            )
        )
        .all()
    )

    if not connections:
        return []

    # Get connector IDs (the other person in each connection)
    connector_map: dict[int, str] = {}  # connector_id -> relationship_type
    for conn in connections:
        if conn.contact_id == target_contact_id:
            connector_map[conn.other_contact_id] = conn.relationship_type
        else:
            connector_map[conn.contact_id] = conn.relationship_type

    # Load connector contacts
    connector_ids = list(connector_map.keys())
    connectors = {
        c.id: c
        for c in db.query(Contact).filter(Contact.id.in_(connector_ids)).all()
    }

    # Check which connectors have replied to our outreach
    replied_ids = set()
    if connector_ids:
        replied = (
            db.query(OutreachLog.contact_id)
            .filter(
                OutreachLog.contact_id.in_(connector_ids),
                OutreachLog.response_status == "replied",
            )
            .distinct()
            .all()
        )
        replied_ids = {r[0] for r in replied}

    # Build ranked intro paths
    paths = []
    for cid, rel_type in connector_map.items():
        connector = connectors.get(cid)
        if not connector:
            continue

        stage = connector.relationship_stage or "Cold"
        stage_score = STAGE_PRIORITY.get(stage, 1)
        has_replied = cid in replied_ids
        reply_bonus = 2 if has_replied else 0

        # Connection type strength
        type_score = {
            "first_degree": 3,
            "co_author": 3,
            "same_org": 2,
            "co_mentioned_news": 1,
            "mentioned_together": 1,
            "same_panel": 2,
            "advisor": 3,
        }.get(rel_type, 1)

        intro_strength = round((stage_score + reply_bonus + type_score) / 9.0, 2)

        paths.append({
            "connector_id": cid,
            "connector_name": connector.name,
            "connector_stage": stage,
            "relationship_to_target": rel_type.replace("_", " "),
            "has_replied": has_replied,
            "intro_strength": min(1.0, intro_strength),
        })

    # Sort by intro strength descending
    paths.sort(key=lambda p: p["intro_strength"], reverse=True)
    return paths[:limit]


# --- Preset tags ---

PRESET_TAGS = [
    "Funding potential",
    "Amplification potential",
    "Technical credibility",
    "Prioritize",
    "Warm intro available",
    "Already engaged",
]


def auto_tag_warm_intro(db: Session) -> dict:
    """Auto-tag contacts that have warm intro paths available.

    Adds "Warm intro available" tag to contacts that have at least one
    connected contact in Engaged or Partner-Advocate stage.
    Returns: {tagged, already_tagged}
    """
    tag_name = "Warm intro available"

    # Find contacts who already have this tag
    existing = (
        db.query(ContactTag.contact_id)
        .filter(ContactTag.tag == tag_name)
        .all()
    )
    already_tagged = {r[0] for r in existing}

    # Find all connections
    all_connections = db.query(ContactConnection).all()

    # Build adjacency: contact_id -> set of connected contact_ids
    adjacency: dict[int, set[int]] = {}
    for conn in all_connections:
        adjacency.setdefault(conn.contact_id, set()).add(conn.other_contact_id)
        adjacency.setdefault(conn.other_contact_id, set()).add(conn.contact_id)

    # Find contacts in Engaged or Partner-Advocate stage
    engaged_ids = {
        c.id
        for c in db.query(Contact)
        .filter(Contact.relationship_stage.in_(["Engaged", "Partner-Advocate"]))
        .all()
    }

    # For each contact, if they're connected to someone engaged with us, tag them
    tagged = 0
    all_contacts = db.query(Contact).all()
    for contact in all_contacts:
        if contact.id in already_tagged:
            continue
        neighbors = adjacency.get(contact.id, set())
        if neighbors & engaged_ids:
            db.add(ContactTag(contact_id=contact.id, tag=tag_name))
            tagged += 1

    db.commit()
    return {"tagged": tagged, "already_tagged": len(already_tagged)}
