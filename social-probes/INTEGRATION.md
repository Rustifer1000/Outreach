# Social Probes — Integration Guide

Standalone prototypes for social media post capture, designed for easy
hookup into the Solomon Outreach app's mention pipeline.

## Probes

| Probe | Platform | API | Port | Auth Required |
|-------|----------|-----|------|---------------|
| `bluesky-probe` | Bluesky | AT Protocol (public) | 8001 | No |
| `linkedin-probe` | LinkedIn (via Google) | Google Custom Search | 8002 | Yes (free tier) |

## Quick Start

```bash
# Bluesky (no setup needed)
cd bluesky-probe
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload

# LinkedIn (needs Google credentials — see /setup in the UI)
cd linkedin-probe
pip install -r requirements.txt
# Edit .env with your GOOGLE_API_KEY and GOOGLE_CSE_ID
uvicorn main:app --port 8002 --reload
```

## Output Schema

Both probes return results in the same schema, compatible with the Outreach
app's `Mention` model:

```json
{
  "source_type": "bluesky|linkedin",
  "source_name": "@handle or LinkedIn — Author Name",
  "source_url": "https://...",
  "title": "Post title or summary",
  "snippet": "Post text or snippet",
  "published_at": "2025-01-15T10:30:00Z"
}
```

## Integrating into Outreach App

When ready, integration requires two changes:

### 1. Add fetch functions to `outreach-app/backend/app/api/mentions.py`

```python
def _fetch_bluesky(name: str, days: int) -> list[dict]:
    """Fetch Bluesky posts mentioning a person."""
    params = {"q": name, "since": since_iso, "sort": "latest", "limit": 25}
    with httpx.Client(timeout=30) as client:
        r = client.get("https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts", params=params)
        r.raise_for_status()
    # ... transform posts to mention dicts (see bluesky-probe/main.py)

def _fetch_linkedin_google(api_key: str, cse_id: str, name: str, days: int) -> list[dict]:
    """Fetch LinkedIn posts via Google Custom Search."""
    params = {"key": api_key, "cx": cse_id, "q": f'"{name}" site:linkedin.com/posts', "dateRestrict": f"d{days}"}
    with httpx.Client(timeout=30) as client:
        r = client.get("https://www.googleapis.com/customsearch/v1", params=params)
        r.raise_for_status()
    # ... transform items to mention dicts (see linkedin-probe/main.py)
```

### 2. Call them from `_run_fetch()` alongside NewsAPI

```python
# In the contact loop inside _run_fetch():
articles = _fetch_newsapi(api_key, contact.name, days)
articles += _fetch_bluesky(contact.name, days)          # add this
articles += _fetch_linkedin_google(g_key, g_cx, contact.name, days)  # add this
```

### 3. Add new env vars to `outreach-app/.env`

```
GOOGLE_API_KEY=your-key
GOOGLE_CSE_ID=your-cx
```

And to `config.py`:
```python
google_api_key: str | None = None
google_cse_id: str | None = None
```

That's it — the Mention model already supports arbitrary `source_type` values,
so `"bluesky"` and `"linkedin"` will just work with existing UI and queries.
