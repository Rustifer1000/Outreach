"""Additional media source fetchers: podcasts, YouTube, web/speeches.

Each fetcher returns a list of dicts with keys:
  source_type, source_url, title, snippet, published_at (ISO string or None)
"""
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


def fetch_podcasts(
    api_key: str,
    name: str,
    days: int = 30,
    max_results: int = 5,
) -> list[dict]:
    """Search podcast episodes via Listen Notes API.

    Requires LISTENNOTES_API_KEY.
    Free tier: 5 requests/min, 50/month.
    """
    url = "https://listen-api.listennotes.com/api/v2/search"
    headers = {"X-ListenAPI-Key": api_key}
    # published_after is Unix timestamp
    published_after = int((datetime.now(UTC) - timedelta(days=days)).timestamp()) * 1000
    params = {
        "q": f'"{name}"',
        "type": "episode",
        "language": "English",
        "published_after": published_after,
        "sort_by_date": 1,
        "len_min": 5,  # At least 5 min (skip teasers)
    }

    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(url, params=params, headers=headers)
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.debug("ListenNotes search failed for %s: %s", name, exc)
        return []

    results = []
    for ep in data.get("results", [])[:max_results]:
        pub_date = None
        if ep.get("pub_date_ms"):
            pub_date = datetime.fromtimestamp(ep["pub_date_ms"] / 1000, tz=UTC).isoformat()

        results.append({
            "source_type": "podcast",
            "source_url": ep.get("listennotes_url") or ep.get("link"),
            "title": ep.get("title_original", ""),
            "snippet": (ep.get("description_original") or "")[:500],
            "published_at": pub_date,
        })

    return results


def fetch_youtube(
    api_key: str,
    name: str,
    days: int = 30,
    max_results: int = 5,
) -> list[dict]:
    """Search YouTube videos via YouTube Data API v3.

    Requires YOUTUBE_API_KEY.
    Free tier: 10,000 quota units/day (search costs 100 units).
    """
    published_after = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": f'"{name}"',
        "type": "video",
        "order": "date",
        "publishedAfter": published_after,
        "maxResults": max_results,
        "key": api_key,
    }

    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.debug("YouTube search failed for %s: %s", name, exc)
        return []

    results = []
    for item in data.get("items", []):
        snippet = item.get("snippet", {})
        video_id = item.get("id", {}).get("videoId", "")
        video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else None

        results.append({
            "source_type": "video",
            "source_url": video_url,
            "title": snippet.get("title", ""),
            "snippet": (snippet.get("description") or "")[:500],
            "published_at": snippet.get("publishedAt"),
        })

    return results


def fetch_web_speeches(
    api_key: str,
    name: str,
    days: int = 30,
    max_results: int = 5,
) -> list[dict]:
    """Search for speeches, presentations, and conference appearances via SerpApi.

    Requires SERPAPI_KEY.
    Free tier: 100 searches/month.
    """
    # Search for conference/speech appearances
    query = f'"{name}" (speech OR keynote OR presentation OR conference OR testimony OR panel)'
    date_range = f"d{days}"  # SerpApi date range: last N days

    url = "https://serpapi.com/search.json"
    params = {
        "q": query,
        "api_key": api_key,
        "engine": "google",
        "num": max_results,
        "tbs": f"qdr:{date_range}",
    }

    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.debug("SerpApi search failed for %s: %s", name, exc)
        return []

    results = []
    for item in data.get("organic_results", [])[:max_results]:
        results.append({
            "source_type": "speech",
            "source_url": item.get("link"),
            "title": item.get("title", ""),
            "snippet": (item.get("snippet") or "")[:500],
            "published_at": None,  # SerpApi doesn't always return dates
        })

    return results


def fetch_all_media(
    contact_name: str,
    days: int = 30,
    listennotes_key: Optional[str] = None,
    youtube_key: Optional[str] = None,
    serpapi_key: Optional[str] = None,
    max_per_source: int = 3,
) -> list[dict]:
    """Fetch from all available media sources for a contact.

    Only calls APIs where keys are configured. Returns combined results.
    """
    all_results: list[dict] = []

    if listennotes_key:
        try:
            all_results.extend(
                fetch_podcasts(listennotes_key, contact_name, days=days, max_results=max_per_source)
            )
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Podcast fetch failed for %s: %s", contact_name, exc)

    if youtube_key:
        try:
            all_results.extend(
                fetch_youtube(youtube_key, contact_name, days=days, max_results=max_per_source)
            )
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("YouTube fetch failed for %s: %s", contact_name, exc)

    if serpapi_key:
        try:
            all_results.extend(
                fetch_web_speeches(serpapi_key, contact_name, days=days, max_results=max_per_source)
            )
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Speech fetch failed for %s: %s", contact_name, exc)

    return all_results


def fetch_media_for_contacts(
    db,
    contact_ids: list[int] | None = None,
    days: int = 30,
    listennotes_key: Optional[str] = None,
    youtube_key: Optional[str] = None,
    serpapi_key: Optional[str] = None,
    max_per_source: int = 2,
    max_contacts: int = 25,
) -> dict:
    """Batch-fetch media mentions for multiple contacts. Stores in DB.

    Returns stats: {attempted, added, skipped, sources_used}
    """
    from urllib.parse import urlparse, urlunparse

    from app.models import Contact, Mention

    if not any([listennotes_key, youtube_key, serpapi_key]):
        return {"attempted": 0, "added": 0, "skipped": 0, "sources_used": [], "message": "No media API keys configured."}

    sources_used = []
    if listennotes_key:
        sources_used.append("podcast")
    if youtube_key:
        sources_used.append("video")
    if serpapi_key:
        sources_used.append("speech")

    # Get contacts
    query = db.query(Contact)
    if contact_ids:
        query = query.filter(Contact.id.in_(contact_ids))
    else:
        # Default: rotation contacts, then by list_number
        has_rotation = db.query(Contact).filter(Contact.in_mention_rotation == 1).first()
        if has_rotation:
            query = query.filter(Contact.in_mention_rotation == 1)
    contacts = query.order_by(Contact.list_number).limit(max_contacts).all()

    # Build existing URL set for dedup
    all_contact_ids = [c.id for c in contacts]
    existing = db.query(Mention).filter(Mention.contact_id.in_(all_contact_ids)).all()
    seen_urls: set[tuple[int, str]] = set()
    for m in existing:
        if m.source_url:
            try:
                p = urlparse(m.source_url.strip())
                norm = urlunparse((p.scheme, p.netloc, p.path, "", "", ""))
                seen_urls.add((m.contact_id, norm))
            except ValueError:
                pass

    stats = {"attempted": 0, "added": 0, "skipped": 0, "sources_used": sources_used}

    for contact in contacts:
        stats["attempted"] += 1
        results = fetch_all_media(
            contact_name=contact.name,
            days=days,
            listennotes_key=listennotes_key,
            youtube_key=youtube_key,
            serpapi_key=serpapi_key,
            max_per_source=max_per_source,
        )

        for item in results:
            raw_url = item.get("source_url")
            if not raw_url:
                continue
            try:
                p = urlparse(raw_url.strip())
                norm = urlunparse((p.scheme, p.netloc, p.path, "", "", ""))
            except ValueError:
                continue
            if (contact.id, norm) in seen_urls:
                continue
            seen_urls.add((contact.id, norm))

            pub = None
            if item.get("published_at"):
                try:
                    pub = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            mention = Mention(
                contact_id=contact.id,
                source_type=item["source_type"],
                source_url=raw_url,
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
                published_at=pub,
            )
            db.add(mention)
            stats["added"] += 1

        # Rate limit between contacts
        time.sleep(1)

    db.commit()
    return stats
