"""Contact enrichment via Hunter API (email finder) and LLM bio summary."""
import re
import time
from typing import Optional

import httpx

# Common org/company names -> domain for Hunter Email Finder
ORG_TO_DOMAIN = {
    "uc berkeley": "berkeley.edu",
    "berkeley": "berkeley.edu",
    "mit": "mit.edu",
    "stanford": "stanford.edu",
    "anthropic": "anthropic.com",
    "openai": "openai.com",
    "google": "google.com",
    "deepmind": "deepmind.com",
    "microsoft": "microsoft.com",
    "meta": "meta.com",
    "facebook": "meta.com",
    "open philanthropy": "openphilanthropy.org",
    "open phil": "openphilanthropy.org",
    "future of life": "futureoflife.org",
    "future of life institute": "futureoflife.org",
    "miri": "intelligence.org",
    "machine intelligence research institute": "intelligence.org",
    "oxford": "ox.ac.uk",
    "university of oxford": "ox.ac.uk",
    "cambridge": "cam.ac.uk",
    "university of cambridge": "cam.ac.uk",
    "princeton": "princeton.edu",
    "harvard": "harvard.edu",
    "yale": "yale.edu",
    "nyu": "nyu.edu",
    "ucla": "ucla.edu",
    "conjecture": "conjecture.dev",
    "arc": "alignment.org",
    "alignment research center": "alignment.org",
    "rand": "rand.org",
    "rand corporation": "rand.org",
    "georgetown": "georgetown.edu",
    "cset": "cset.georgetown.edu",
    "ford foundation": "fordfoundation.org",
    "rockefeller": "rockefeller.org",
    "khan academy": "khanacademy.org",
    "partnership on ai": "partnershiponai.org",
    "ai now": "ainowinstitute.org",
    "ai now institute": "ainowinstitute.org",
    "dair": "dair-institute.org",
    "distributed ai research": "dair-institute.org",
    "hugging face": "huggingface.co",
    "huggingface": "huggingface.co",
    "mozilla": "mozilla.org",
    "new america": "newamerica.org",
    "brookings": "brookings.edu",
    "brookings institution": "brookings.edu",
    "aei": "aei.org",
    "american enterprise institute": "aei.org",
}


def _parse_name(full_name: str) -> tuple[str, str]:
    """Split full name into first and last. Simple: last word = last name."""
    parts = full_name.strip().split()
    if not parts:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")
    return (" ".join(parts[:-1]), parts[-1])


def _extract_domain(role_org: Optional[str]) -> Optional[str]:
    """Extract company domain from role_org for Hunter lookup."""
    if not role_org:
        return None
    text = role_org.lower()
    # Check for known orgs (substring match)
    for org, domain in ORG_TO_DOMAIN.items():
        if org in text:
            return domain
    # Try "Company" or "Org" pattern
    match = re.search(r"(?:at|@|,)\s*([a-z0-9\s]+?)(?:;|$|\s+author|$)", text, re.I)
    if match:
        org_part = match.group(1).strip()
        for org, domain in ORG_TO_DOMAIN.items():
            if org in org_part:
                return domain
    return None


def enrich_contact_email(
    api_key: str,
    full_name: str,
    role_org: Optional[str],
    company: Optional[str] = None,
) -> Optional[dict]:
    """
    Call Hunter Email Finder. Returns {email, score, position} or None if not found.
    """
    first_name, last_name = _parse_name(full_name)
    if not first_name or not last_name:
        return None

    domain = _extract_domain(role_org) or company
    if not domain:
        return None

    url = "https://api.hunter.io/v2/email-finder"
    params = {
        "domain": domain,
        "first_name": first_name,
        "last_name": last_name,
        "api_key": api_key,
    }

    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return None

    d = data.get("data", {})
    email = d.get("email")
    if not email:
        return None

    return {
        "email": email,
        "score": d.get("score", 0),
        "position": d.get("position"),
        "linkedin_url": d.get("linkedin"),
    }


def enrich_linkedin_url(
    api_key: str,
    full_name: str,
    role_org: Optional[str],
) -> Optional[str]:
    """Use Hunter's people search to find a LinkedIn profile URL.

    Falls back to domain search if available, returning the linkedin field
    from the email finder response.
    """
    first_name, last_name = _parse_name(full_name)
    if not first_name or not last_name:
        return None

    domain = _extract_domain(role_org)
    if not domain:
        return None

    # Hunter email-finder sometimes returns linkedin in the response
    url = "https://api.hunter.io/v2/email-finder"
    params = {
        "domain": domain,
        "first_name": first_name,
        "last_name": last_name,
        "api_key": api_key,
    }

    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return None

    d = data.get("data", {})
    return d.get("linkedin") or None


def enrich_bulk(db, api_key: str, max_contacts: int = 50) -> dict:
    """Enrich all contacts that are missing email. Returns summary stats.

    Rate-limited to 1 request per second to respect Hunter API limits.
    """
    from app.models import Contact, ContactInfo

    contacts = db.query(Contact).all()
    stats = {"attempted": 0, "found": 0, "skipped": 0, "errors": 0, "details": []}

    for contact in contacts:
        if stats["attempted"] >= max_contacts:
            break

        # Skip if already has email
        existing = db.query(ContactInfo).filter(
            ContactInfo.contact_id == contact.id,
            ContactInfo.type == "email",
        ).first()
        if existing:
            stats["skipped"] += 1
            continue

        if not contact.role_org:
            stats["skipped"] += 1
            continue

        stats["attempted"] += 1

        result = enrich_contact_email(
            api_key=api_key,
            full_name=contact.name,
            role_org=contact.role_org,
        )

        if result:
            # Add email
            info = ContactInfo(
                contact_id=contact.id,
                type="email",
                value=result["email"],
                is_primary=1,
            )
            db.add(info)

            # Also add LinkedIn if returned
            if result.get("linkedin_url"):
                existing_li = db.query(ContactInfo).filter(
                    ContactInfo.contact_id == contact.id,
                    ContactInfo.type == "linkedin",
                ).first()
                if not existing_li:
                    li_info = ContactInfo(
                        contact_id=contact.id,
                        type="linkedin",
                        value=result["linkedin_url"],
                        is_primary=0,
                    )
                    db.add(li_info)

            db.commit()
            stats["found"] += 1
            stats["details"].append({"name": contact.name, "email": result["email"]})
        else:
            stats["errors"] += 1

        # Rate limit: 1 request per second
        time.sleep(1)

    return stats


def generate_bio_summary(
    api_key: str,
    contact_name: str,
    role_org: Optional[str],
    connection_to_solomon: Optional[str],
    mention_snippets: list[str],
    model: str = "claude-3-5-haiku-20241022",
) -> Optional[str]:
    """Generate a short bio summary using Claude from mention snippets and existing info.

    Returns a 2-3 sentence bio or None on error.
    """
    if not mention_snippets and not role_org:
        return None

    context_parts = []
    if role_org:
        context_parts.append(f"Role/Org: {role_org}")
    if connection_to_solomon:
        context_parts.append(f"Connection: {connection_to_solomon}")
    for i, snippet in enumerate(mention_snippets[:5]):
        context_parts.append(f"Mention {i + 1}: {snippet[:500]}")

    context = "\n".join(context_parts)

    prompt = f"""Write a concise 2-3 sentence professional bio for {contact_name} based on these sources.
Focus on their role, expertise, and relevance to AI safety/policy. Be factual, no speculation.

{context}

Bio:"""

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        bio = (msg.content[0].text if msg.content else "").strip()
        return bio if bio else None
    except Exception:
        return None
