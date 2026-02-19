"""Contact enrichment via Hunter API (email finder)."""
import re
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
    }
