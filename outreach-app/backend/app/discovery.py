"""
Connection discovery: find how contacts are related using existing mention text or web search.

- From mentions: scan each mention's title + snippet for other contact names (same article, podcast, conference).
- Via search: NewsAPI query "Name A" AND "Name B" to find co-mentions in news.
- LLM: when Anthropic key is set, infer relationship type from context (co_author, same_panel, etc.).
"""
import time
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
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


def discover_from_mentions(db: Session, max_llm_calls: int = 10) -> dict:
    """
    Scan existing mentions: for each mention, look for other contact names in title + snippet.
    When found, add contact_connection. If Anthropic key is set, use LLM to infer relationship type.
    Returns { "added": N, "scanned_mentions": M, "llm_enriched": K }.
    """
    from app.llm_extract import infer_relationship

    mentions = db.query(Mention).all()
    contacts = db.query(Contact).all()
    contact_ids = {c.id for c in contacts}
    name_by_id = {c.id: c.name for c in contacts}
    existing = {
        (r.contact_id, r.other_contact_id)
        for r in db.query(ContactConnection).all()
    }
    added = 0
    llm_enriched = 0
    api_key = settings.anthropic_api_key

    for m in mentions:
        text = " ".join(filter(None, [m.title, m.snippet]))
        text_lower = text.lower()
        if not text:
            continue
        contact_id = m.contact_id
        source_note = (m.source_url or m.title or "mention")[:500]
        person_a = name_by_id.get(contact_id)

        for other_id in contact_ids:
            if other_id == contact_id:
                continue
            if (contact_id, other_id) in existing:
                continue
            name = name_by_id.get(other_id)
            if not name or len(name) < 4:
                continue
            if name.lower() not in text_lower:
                continue

            rel_type = "mentioned_together"
            notes = f"Co-mentioned in: {source_note}"

            if api_key and llm_enriched < max_llm_calls and person_a:
                result = infer_relationship(api_key, text, person_a, name)
                if result:
                    rel_type = result.get("relationship_type", rel_type)
                    evidence = result.get("evidence", "")
                    notes = f"{evidence}. Source: {source_note}"[:500]
                    llm_enriched += 1
                    time.sleep(0.3)  # Rate limit

            conn = ContactConnection(
                contact_id=contact_id,
                other_contact_id=other_id,
                relationship_type=rel_type,
                notes=notes,
            )
            db.add(conn)
            existing.add((contact_id, other_id))
            added += 1

    if added:
        db.commit()
    return {"added": added, "scanned_mentions": len(mentions), "llm_enriched": llm_enriched}


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


def discover_all(
    db: Session,
    api_key: str | None,
    max_contacts: int = 15,
    max_pairs_per_contact: int = 5,
) -> dict:
    """
    Agentic discovery: run from-mentions (all) then via-search for N contacts.
    Prioritizes contacts in rotation, then by list_number.
    """
    mentions_result = discover_from_mentions(db)
    total_added = mentions_result.get("added", 0)

    if not api_key:
        return {
            "from_mentions": total_added,
            "from_search": 0,
            "contacts_searched": 0,
            "message": f"From mentions: {total_added} connections. NewsAPI key not configured for search.",
        }

    # Prioritize in-rotation contacts, then others by list_number
    in_rotation = (
        db.query(Contact)
        .filter(Contact.in_mention_rotation == 1)
        .order_by(Contact.list_number)
        .limit(max_contacts)
        .all()
    )
    if len(in_rotation) < max_contacts:
        others = (
            db.query(Contact)
            .filter(or_(Contact.in_mention_rotation == 0, Contact.in_mention_rotation.is_(None)))
            .order_by(Contact.list_number)
            .limit(max_contacts - len(in_rotation))
            .all()
        )
        to_search = in_rotation + others
    else:
        to_search = in_rotation

    search_added = 0
    for c in to_search:
        r = discover_via_search(
            db, c.id, api_key,
            max_pairs=max_pairs_per_contact,
            same_category_only=False,  # Broader discovery across categories
            delay_seconds=1.2,
        )
        search_added += r.get("added", 0)

    llm_enriched = mentions_result.get("llm_enriched", 0)
    msg = f"From mentions: {total_added}"
    if llm_enriched:
        msg += f" ({llm_enriched} LLM-enriched)"
    msg += f". From search ({len(to_search)} contacts): {search_added}."

    return {
        "from_mentions": total_added,
        "from_search": search_added,
        "contacts_searched": len(to_search),
        "llm_enriched": llm_enriched,
        "message": msg,
    }
