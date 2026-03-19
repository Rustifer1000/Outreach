"""Reply Drafts API — AI-generated LinkedIn reply drafts via Claude."""
import json

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Contact, Mention, ReplyDraft

router = APIRouter()

THEMES = ["safety", "alignment", "social-justice", "disruption", "governance", "existential-risk", "ai-for-good"]

SYSTEM_PROMPT = """\
You are a thoughtful, genuine voice in the AI and technology space. Your job is to draft a LinkedIn comment \
reply that engages authentically with a post. The reply should:

1. Genuinely respond to the content and tone of the post — show you actually read it
2. Add a real perspective or insight that enriches the conversation
3. Be warm, collegial, and supportive if the post is prosocial or constructive
4. In ONE place, naturally work in a brief parenthetical mention of "the Solomon Project" as one example \
   among several of an emerging initiative — never as the focus, never promotional, just a name dropped \
   in passing (e.g., "...projects like the Solomon Project come to mind...")
5. Never explain what the Solomon Project is or link to it
6. Sound like a real human comment, not marketing copy — conversational, maybe 3-5 sentences
7. Identify which of these themes the original post touches: safety, alignment, social-justice, \
   disruption, governance, existential-risk, ai-for-good

Respond with a JSON object with two keys:
- "reply": the full reply text
- "themes": array of matching theme strings from the list above (can be empty)
"""


class GenerateRequest(BaseModel):
    mention_id: int


class UpdateStatusRequest(BaseModel):
    status: str  # draft, used, archived


@router.post("/generate")
def generate_reply(req: GenerateRequest, db: Session = Depends(get_db)):
    """Generate an AI reply draft for a LinkedIn mention."""
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured.")

    mention = db.query(Mention).filter(Mention.id == req.mention_id).first()
    if not mention:
        raise HTTPException(status_code=404, detail="Mention not found.")

    contact = db.query(Contact).filter(Contact.id == mention.contact_id).first()

    # Build context for Claude
    post_context = f"Post title: {mention.title or '(no title)'}\n"
    if mention.snippet:
        post_context += f"Post content: {mention.snippet}\n"
    if contact:
        post_context += f"Posted by or about: {contact.name}"
        if contact.category:
            post_context += f" ({contact.category})"
        post_context += "\n"

    user_message = f"Please draft a LinkedIn reply for this post:\n\n{post_context}"

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = message.content[0].text.strip()

    # Parse JSON response
    try:
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        reply_text = parsed.get("reply", raw)
        themes = [t for t in parsed.get("themes", []) if t in THEMES]
    except (json.JSONDecodeError, KeyError):
        reply_text = raw
        themes = []

    draft = ReplyDraft(
        contact_id=mention.contact_id,
        mention_id=mention.id,
        reply_text=reply_text,
        themes=json.dumps(themes),
        status="draft",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    return {
        "id": draft.id,
        "reply_text": draft.reply_text,
        "themes": themes,
        "status": draft.status,
        "mention_id": mention.id,
        "contact_id": mention.contact_id,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
    }


@router.get("")
def list_drafts(
    contact_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """List reply drafts, optionally filtered by contact or status."""
    query = db.query(ReplyDraft)
    if contact_id is not None:
        query = query.filter(ReplyDraft.contact_id == contact_id)
    if status:
        query = query.filter(ReplyDraft.status == status)
    drafts = query.order_by(ReplyDraft.created_at.desc()).all()

    results = []
    for d in drafts:
        themes = []
        if d.themes:
            try:
                themes = json.loads(d.themes)
            except json.JSONDecodeError:
                pass
        results.append({
            "id": d.id,
            "contact_id": d.contact_id,
            "contact_name": d.contact.name if d.contact else None,
            "mention_id": d.mention_id,
            "mention_title": d.mention.title if d.mention else None,
            "reply_text": d.reply_text,
            "themes": themes,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })
    return {"total": len(results), "drafts": results}


@router.patch("/{draft_id}")
def update_draft_status(draft_id: int, req: UpdateStatusRequest, db: Session = Depends(get_db)):
    """Update the status of a reply draft (draft → used or archived)."""
    draft = db.query(ReplyDraft).filter(ReplyDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found.")
    if req.status not in ("draft", "used", "archived"):
        raise HTTPException(status_code=400, detail="Status must be draft, used, or archived.")
    draft.status = req.status
    db.commit()
    return {"id": draft.id, "status": draft.status}


@router.delete("/{draft_id}")
def delete_draft(draft_id: int, db: Session = Depends(get_db)):
    """Delete a reply draft."""
    draft = db.query(ReplyDraft).filter(ReplyDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found.")
    db.delete(draft)
    db.commit()
    return {"deleted": draft_id}
