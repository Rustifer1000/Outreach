#!/usr/bin/env python3
"""
Fetch news mentions for contacts using NewsAPI.org or Media Cloud.

Requires API key in .env:
  NEWSAPI_KEY=your_key     # from newsapi.org (free: 100 req/day)
  MEDIACLOUD_API_KEY=key   # from search.mediacloud.org

Usage:
    python fetch_mentions.py [--limit 50] [--days 7]
"""
import argparse
import hashlib
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Contact, Mention


def fetch_newsapi(api_key: str, name: str, days: int) -> list[dict]:
    """Fetch articles from NewsAPI.org for a person's name."""
    import httpx

    from_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": f'"{name}"',
        "from": from_date,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 10,
        "apiKey": api_key,
    }

    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        print(f"  NewsAPI error for '{name}': {e}")
        return []

    articles = data.get("articles", [])
    return [
        {
            "source_url": a.get("url"),
            "title": a.get("title"),
            "snippet": a.get("description") or a.get("content", "")[:500],
            "published_at": a.get("publishedAt"),
        }
        for a in articles
        if a.get("url") and a.get("title")
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=str, default="sqlite:///./backend/outreach.db")
    parser.add_argument("--limit", type=int, default=None, help="Max contacts to process (for rate limits)")
    parser.add_argument("--days", type=int, default=7, help="Look back days")
    parser.add_argument("--max-per-contact", type=int, default=2, help="Max mentions to store per contact (1 or 2)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between API calls")
    args = parser.parse_args()

    # Load API key from env (check outreach-app/.env or backend/.env)
    base = Path(__file__).parent.parent
    for env_path in [base / ".env", base / "backend" / ".env"]:
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
        break

    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        print("No NEWSAPI_KEY in .env. Add to outreach-app/backend/.env")
        print("Get a free key at https://newsapi.org/register")
        return 1

    engine = create_engine(args.db, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    session = Session()

    contacts = session.query(Contact).order_by(Contact.list_number).all()
    if args.limit:
        contacts = contacts[: args.limit]

    max_per = max(1, min(args.max_per_contact, 2))  # Clamp to 1 or 2
    print(f"Fetching mentions for {len(contacts)} contacts (last {args.days} days, max {max_per} per contact)...")

    added = 0
    for i, contact in enumerate(contacts):
        articles = fetch_newsapi(api_key, contact.name, args.days)
        for a in articles[:max_per]:  # Only take first 1-2 (most recent)
            if not a.get("source_url"):
                continue
            # Dedupe: check if we already have this URL for this contact
            existing = (
                session.query(Mention)
                .filter(
                    Mention.contact_id == contact.id,
                    Mention.source_url == a["source_url"],
                )
                .first()
            )
            if existing:
                continue

            pub = None
            if a.get("published_at"):
                try:
                    pub = datetime.fromisoformat(a["published_at"].replace("Z", "+00:00"))
                except Exception:
                    pass

            mention = Mention(
                contact_id=contact.id,
                source_type="news",
                source_url=a["source_url"],
                title=a["title"],
                snippet=a["snippet"],
                published_at=pub,
            )
            session.add(mention)
            added += 1

        session.commit()
        if articles:
            print(f"  [{i+1}/{len(contacts)}] {contact.name}: +{len(articles)} articles")
        time.sleep(args.delay)

    session.close()
    print(f"Done. Added {added} new mentions.")
    return 0


if __name__ == "__main__":
    exit(main())
