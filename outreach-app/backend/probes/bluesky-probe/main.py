"""
Bluesky Social Probe — AT Protocol Search API prototype.

Searches Bluesky public posts for contact names.
No authentication required — the AT Protocol search API is fully public.

Output schema matches the Outreach app's Mention model for easy integration.

Usage:
    pip install -r requirements.txt
    uvicorn main:app --port 8001 --reload

Then open http://localhost:8001 for the trial UI, or hit the API directly:
    GET /search?name=Sam+Altman&days=2
"""
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

app = FastAPI(title="Bluesky Social Probe", version="0.1.0")

BSKY_SEARCH_URL = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"


def _parse_bsky_datetime(dt_str: str) -> datetime | None:
    """Parse Bluesky's ISO datetime string."""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _truncate(text: str, length: int = 400) -> str:
    """Truncate text to a max length."""
    if not text or len(text) <= length:
        return text or ""
    return text[:length] + "..."


def _post_to_mention(post: dict) -> dict:
    """Convert a Bluesky post to Outreach Mention-compatible dict."""
    record = post.get("record", {})
    author = post.get("author", {})
    handle = author.get("handle", "")
    display_name = author.get("displayName", handle)
    created_at = record.get("createdAt")
    uri = post.get("uri", "")

    # Build a web URL from the AT URI: at://did/app.bsky.feed.post/rkey
    web_url = ""
    if uri.startswith("at://"):
        parts = uri.replace("at://", "").split("/")
        if len(parts) >= 3:
            web_url = f"https://bsky.app/profile/{handle}/post/{parts[-1]}"

    return {
        "source_type": "bluesky",
        "source_name": f"@{handle}" if handle else "Bluesky",
        "source_url": web_url,
        "title": f"Post by {display_name}",
        "snippet": _truncate(record.get("text", "")),
        "published_at": created_at,
        "author_handle": handle,
        "author_display_name": display_name,
        "author_avatar": author.get("avatar"),
        "like_count": post.get("likeCount", 0),
        "repost_count": post.get("repostCount", 0),
        "reply_count": post.get("replyCount", 0),
    }


@app.get("/search")
async def search_posts(
    name: str = Query(..., description="Person or keyword to search for"),
    days: int = Query(2, ge=1, le=30, description="Search posts from last N days"),
    limit: int = Query(25, ge=1, le=100, description="Max results to return"),
    sort: str = Query("latest", description="Sort order: 'latest' or 'top'"),
):
    """
    Search Bluesky posts mentioning a name.

    Returns results in Outreach Mention-compatible schema.
    """
    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()

    params = {
        "q": name,
        "since": since,
        "sort": sort,
        "limit": min(limit, 100),
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(BSKY_SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"Bluesky API error: {e.response.status_code}", "results": []}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}", "results": []}

    posts = data.get("posts", [])

    # Filter to posts within the date range (belt-and-suspenders)
    cutoff = datetime.now(UTC) - timedelta(days=days)
    results = []
    for post in posts:
        mention = _post_to_mention(post)
        pub = _parse_bsky_datetime(mention.get("published_at", ""))
        if pub and pub.replace(tzinfo=None) < cutoff.replace(tzinfo=None):
            continue
        results.append(mention)

    return {
        "query": name,
        "days": days,
        "total": len(results),
        "results": results,
    }


@app.get("/", response_class=HTMLResponse)
async def trial_ui():
    """Simple HTML UI for testing Bluesky search."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bluesky Probe — Trial UI</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               max-width: 900px; margin: 0 auto; padding: 24px; background: #f0f2f5; color: #1a1a1a; }
        h1 { color: #0085ff; margin-bottom: 4px; font-size: 1.5rem; }
        .subtitle { color: #666; margin-bottom: 20px; font-size: 0.9rem; }
        .search-bar { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
        input, select, button { padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px;
                                 font-size: 0.95rem; }
        input[type="text"] { flex: 1; min-width: 200px; }
        input[type="number"] { width: 80px; }
        button { background: #0085ff; color: white; border: none; cursor: pointer; font-weight: 600; }
        button:hover { background: #0070dd; }
        button:disabled { background: #999; cursor: not-allowed; }
        .status { padding: 12px; margin-bottom: 16px; border-radius: 8px; display: none; }
        .status.error { background: #ffe0e0; color: #c00; display: block; }
        .status.info { background: #e0f0ff; color: #005; display: block; }
        .card { background: white; border-radius: 10px; padding: 16px; margin-bottom: 12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
        .card-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
        .avatar { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; background: #ddd; }
        .author { font-weight: 600; }
        .handle { color: #666; font-size: 0.85rem; }
        .text { line-height: 1.5; margin-bottom: 8px; white-space: pre-wrap; }
        .meta { display: flex; gap: 16px; color: #666; font-size: 0.85rem; }
        .meta a { color: #0085ff; text-decoration: none; }
        .empty { text-align: center; padding: 40px; color: #888; }
    </style>
</head>
<body>
    <h1>&#x1f98b; Bluesky Probe</h1>
    <p class="subtitle">AT Protocol search — test queries before integrating into Outreach</p>

    <div class="search-bar">
        <input type="text" id="query" placeholder="Search name or keyword..." value="">
        <input type="number" id="days" value="2" min="1" max="30" title="Days back">
        <select id="sort">
            <option value="latest">Latest</option>
            <option value="top">Top</option>
        </select>
        <button id="searchBtn" onclick="doSearch()">Search</button>
    </div>

    <div id="status" class="status"></div>
    <div id="results"></div>

    <script>
        async function doSearch() {
            const name = document.getElementById('query').value.trim();
            if (!name) return;
            const days = document.getElementById('days').value;
            const sort = document.getElementById('sort').value;
            const btn = document.getElementById('searchBtn');
            const status = document.getElementById('status');
            const results = document.getElementById('results');

            btn.disabled = true;
            btn.textContent = 'Searching...';
            status.className = 'status info';
            status.style.display = 'block';
            status.textContent = `Searching Bluesky for "${name}"...`;
            results.innerHTML = '';

            try {
                const resp = await fetch(`/search?name=${encodeURIComponent(name)}&days=${days}&sort=${sort}`);
                const data = await resp.json();

                if (data.error) {
                    status.className = 'status error';
                    status.textContent = data.error;
                    return;
                }

                status.className = 'status info';
                status.textContent = `Found ${data.total} post(s) from the last ${data.days} day(s)`;

                if (data.results.length === 0) {
                    results.innerHTML = '<div class="empty">No posts found. Try a broader search or longer time range.</div>';
                    return;
                }

                results.innerHTML = data.results.map(r => `
                    <div class="card">
                        <div class="card-header">
                            ${r.author_avatar ? `<img class="avatar" src="${r.author_avatar}" alt="">` : '<div class="avatar"></div>'}
                            <div>
                                <div class="author">${esc(r.author_display_name || '')}</div>
                                <div class="handle">${esc(r.source_name || '')}</div>
                            </div>
                        </div>
                        <div class="text">${esc(r.snippet || '')}</div>
                        <div class="meta">
                            <span>&#x2764; ${r.like_count || 0}</span>
                            <span>&#x1f501; ${r.repost_count || 0}</span>
                            <span>&#x1f4ac; ${r.reply_count || 0}</span>
                            <span>${r.published_at ? new Date(r.published_at).toLocaleString() : ''}</span>
                            ${r.source_url ? `<a href="${r.source_url}" target="_blank">View on Bluesky</a>` : ''}
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                status.className = 'status error';
                status.textContent = 'Request failed: ' + e.message;
            } finally {
                btn.disabled = false;
                btn.textContent = 'Search';
            }
        }

        function esc(s) {
            const d = document.createElement('div');
            d.textContent = s;
            return d.innerHTML;
        }

        document.getElementById('query').addEventListener('keydown', e => {
            if (e.key === 'Enter') doSearch();
        });
    </script>
</body>
</html>"""


@app.get("/health")
async def health():
    return {"status": "ok", "service": "bluesky-probe"}
