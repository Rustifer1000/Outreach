"""
Connection discovery: find how contacts are related using existing mention text or web search.

- From mentions: scan each mention's title + snippet for other contact names (same article, podcast, conference).
- Via search: NewsAPI query "Name A" AND "Name B" to find co-mentions in news.
"""
import time
from sqlalchemy.orm import Session

from app.models import Contact, Mention, ContactConnection


def _connection_exists(db: Session, contact_id: int, other_contact_id: int) -> bool:
    if contact_id == other_contact_id:
        return True
    return (
        db.query(ContactConnection)
        .filter(
            ContactConnection.contact_id == contact_id,
            ContactConnection.other_contact_id == other_contact_id,
        )
        .first()
        is not None
    )


def discover_from_mentions(db: Session) -> dict:
    """
    Scan existing mentions: for each mention, look for other contact names in title + snippet.
    When found, add contact_connection (mentioned_together) with source URL in notes.
    Returns { "added": N, "scanned_mentions": M }.
    """
    mentions = db.query(Mention).all()
    contacts = db.query(Contact).all()
    contact_ids = {c.id for c in contacts}
    name_by_id = {c.id: c.name for c in contacts}
    existing = {
        (r.contact_id, r.other_contact_id)
        for r in db.query(ContactConnection).all()
    }
    added = 0
    for m in mentions:
        text = " ".join(filter(None, [m.title, m.snippet])).lower()
        if not text:
            continue
        contact_id = m.contact_id
        source_note = (m.source_url or m.title or "mention")[:500]
        for other_id in contact_ids:
            if other_id == contact_id:
                continue
            if (contact_id, other_id) in existing:
                continue
            name = name_by_id.get(other_id)
            if not name or len(name) < 4:
                continue
            if name.lower() not in text:
                continue
            conn = ContactConnection(
                contact_id=contact_id,
                other_contact_id=other_id,
                relationship_type="mentioned_together",
                notes=f"Co-mentioned in: {source_note}",
            )
            db.add(conn)
            existing.add((contact_id, other_id))
            added += 1
    if added:
        db.commit()
    return {"added": added, "scanned_mentions": len(mentions)}


def discover_via_search(
    db: Session,
    contact_id: int,
    api_key: str,
    max_pairs: int = 20,
    same_category_only: bool = True,
    delay_seconds: float = 1.0,
) -> dict:
    """
    For one contact, run NewsAPI search "Name A" AND "Name B" for up to max_pairs other contacts.
    When articles are found, add contact_connection (co_mentioned_news) with first article URL.
    Returns { "added": N, "searched_pairs": M, "message": str }.
    """
    import httpx
    from datetime import UTC, datetime, timedelta

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        return {"added": 0, "searched_pairs": 0, "message": "Contact not found"}
    others = db.query(Contact).filter(Contact.id != contact_id)
    if same_category_only and contact.category:
        others = others.filter(Contact.category.ilike(f"%{contact.category}%"))
    others = others.limit(max_pairs * 2).all()
    from_date = (datetime.now(UTC) - timedelta(days=90)).strftime("%Y-%m-%d")
    added = 0
    searched = 0
    for other in others:
        if searched >= max_pairs:
            break
        if _connection_exists(db, contact_id, other.id):
            continue
        searched += 1
        q = f'"{contact.name}" "{other.name}"'
        try:
            with httpx.Client(timeout=15) as client:
                r = client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": q,
                        "from": from_date,
                        "language": "en",
                        "pageSize": 1,
                        "apiKey": api_key,
                    },
                )
                r.raise_for_status()
                data = r.json()
        except Exception:
            time.sleep(delay_seconds)
            continue
        total = data.get("totalResults", 0)
        articles = data.get("articles", [])
        if total and articles and articles[0].get("url"):
            source_url = articles[0].get("url", "")[:500]
            conn = ContactConnection(
                contact_id=contact_id,
                other_contact_id=other.id,
                relationship_type="co_mentioned_news",
                notes=f"News search: {source_url}",
            )
            db.add(conn)
            added += 1
        time.sleep(delay_seconds)
    if added:
        db.commit()
    return {
        "added": added,
        "searched_pairs": searched,
        "message": f"Searched {searched} pairs, added {added} connections.",
    }
