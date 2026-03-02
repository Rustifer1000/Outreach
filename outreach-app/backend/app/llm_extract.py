"""
LLM-based relationship extraction from mention text.
Uses Claude to infer relationship type and evidence when two people are co-mentioned.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Relationship types we use (aligned with ContactDetail UI)
RELATIONSHIP_TYPES = [
    "co_author",
    "same_org",
    "same_panel",
    "collaborator",
    "first_degree",
    "second_degree",
    "mentioned_together",  # fallback when unclear
]


def infer_relationship(
    api_key: str,
    text: str,
    person_a: str,
    person_b: str,
    model: str | None = None,
) -> Optional[dict]:
    """
    Use Claude to infer how person_a and person_b are related based on the text.
    Returns { "relationship_type": str, "evidence": str } or None on error.
    """
    if not text or not person_a or not person_b:
        return None

    if model is None:
        from app.config import settings
        model = settings.anthropic_model

    # Truncate to stay within context
    text = text[:3000] if len(text) > 3000 else text

    prompt = f"""Analyze this text where two people are mentioned together. Infer their relationship.

Text:
{text}

People: {person_a} and {person_b}

Reply with exactly:
relationship_type: <one of co_author, same_org, same_panel, collaborator, first_degree, second_degree, mentioned_together>
evidence: <short phrase from text or "co-mentioned in same article">

Use mentioned_together only if unclear. Prefer specific types (co_author, same_panel, same_org) when the text implies them."""

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        content = (msg.content[0].text if msg.content else "").strip()
        content_lower = content.lower()
        rel_type = "mentioned_together"
        evidence = "Co-mentioned in same article"

        for rt in RELATIONSHIP_TYPES:
            if rt in content_lower:
                rel_type = rt
                break

        if "evidence:" in content_lower:
            for sep in ["evidence:", "evidence :"]:
                if sep in content_lower:
                    rest = content.split(sep, 1)[-1].strip()
                    evidence = rest.split("\n")[0].strip()[:200] or evidence
                    break

        return {"relationship_type": rel_type, "evidence": evidence}
    except ImportError:
        logger.error("anthropic package is not installed")
        return None
    except Exception as exc:
        logger.debug("LLM relationship inference failed for %s / %s: %s", person_a, person_b, exc)
        return None
