"""
LinkedIn Social Probe — Google Custom Search API prototype.

Searches for recent LinkedIn posts via Google Custom Search,
filtered to site:linkedin.com/posts.

Output schema matches the Outreach app's Mention model for easy integration.

Setup:
    1. Go to https://console.cloud.google.com/apis/credentials
       → Create an API key (or use an existing one)
    2. Go to https://programmablesearchengine.google.com/controlpanel/create
       → Create a search engine with "Search the entire web" enabled
       → Copy the Search Engine ID (cx)
    3. Add both to your .env file

Usage:
    pip install -r requirements.txt
    uvicorn main:app --port 8002 --reload

Then open http://localhost:8002 for the trial UI, or hit the API directly:
    GET /search?name=Sam+Altman&days=2
"""
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

# Load .env from this directory, then fall back to outreach-app/.env
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent.parent / "outreach-app" / ".env")

app = FastAPI(title="LinkedIn Social Probe", version="0.1.0")

GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"


def _get_credentials() -> tuple[str | None, str | None]:
    """Get Google API key and Custom Search Engine ID from env."""
    return os.getenv("GOOGLE_API_KEY"), os.getenv("GOOGLE_CSE_ID")


def _result_to_mention(item: dict) -> dict:
    """Convert a Google CSE result to Outreach Mention-compatible dict."""
    # Google sometimes returns a "pagemap" with extra metadata
    pagemap = item.get("pagemap", {})
    metatags = pagemap.get("metatags", [{}])[0] if pagemap.get("metatags") else {}

    # Try to extract the author/poster from the title or metatags
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    link = item.get("link", "")

    # LinkedIn post titles often follow: "FirstName LastName on LinkedIn: ..."
    author_name = ""
    post_title = title
    if " on LinkedIn:" in title:
        parts = title.split(" on LinkedIn:", 1)
        author_name = parts[0].strip()
        post_title = parts[1].strip() if len(parts) > 1 else title
    elif " | LinkedIn" in title:
        post_title = title.replace(" | LinkedIn", "").strip()

    # Try to get published date from metatags
    published = metatags.get("article:published_time") or metatags.get("og:updated_time") or ""

    return {
        "source_type": "linkedin",
        "source_name": f"LinkedIn — {author_name}" if author_name else "LinkedIn",
        "source_url": link,
        "title": post_title,
        "snippet": snippet,
        "published_at": published or None,
        "author_name": author_name,
        "thumbnail": metatags.get("og:image"),
    }


@app.get("/search")
async def search_posts(
    name: str = Query(..., description="Person or keyword to search for"),
    days: int = Query(2, ge=1, le=30, description="Search posts from last N days"),
    limit: int = Query(10, ge=1, le=10, description="Max results (Google free tier caps at 10 per query)"),
):
    """
    Search LinkedIn posts via Google Custom Search.

    Returns results in Outreach Mention-compatible schema.
    Free tier: 100 queries/day, 10 results per query.
    """
    api_key, cse_id = _get_credentials()

    if not api_key or not cse_id:
        return {
            "error": "Missing GOOGLE_API_KEY or GOOGLE_CSE_ID. See setup instructions at /setup",
            "results": [],
        }

    # Build date-restricted query
    # Google CSE dateRestrict format: d[N] = last N days
    query_str = f'"{name}" site:linkedin.com/posts'

    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query_str,
        "dateRestrict": f"d{days}",
        "num": min(limit, 10),
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(GOOGLE_CSE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        error_body = {}
        try:
            error_body = e.response.json()
        except Exception:
            pass
        error_msg = error_body.get("error", {}).get("message", str(e))
        return {"error": f"Google CSE error: {error_msg}", "results": []}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}", "results": []}

    items = data.get("items", [])
    total_results = int(data.get("searchInformation", {}).get("totalResults", 0))

    results = [_result_to_mention(item) for item in items]

    return {
        "query": name,
        "days": days,
        "total": len(results),
        "total_available": total_results,
        "results": results,
        "quota_note": "Free tier: 100 queries/day, 10 results/query",
    }


@app.get("/setup", response_class=HTMLResponse)
async def setup_guide():
    """Setup instructions for Google Custom Search."""
    api_key, cse_id = _get_credentials()
    key_status = "configured" if api_key else "MISSING"
    cse_status = "configured" if cse_id else "MISSING"

    return f"""<!DOCTYPE html>
<html><head><title>LinkedIn Probe — Setup</title>
<style>
    body {{ font-family: -apple-system, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px;
           line-height: 1.6; color: #1a1a1a; }}
    h1 {{ color: #0a66c2; }}
    code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
    pre {{ background: #f4f4f4; padding: 16px; border-radius: 8px; overflow-x: auto; }}
    .status {{ padding: 12px; border-radius: 8px; margin: 16px 0; }}
    .ok {{ background: #e6f9e6; color: #060; }}
    .missing {{ background: #ffe0e0; color: #c00; }}
    ol li {{ margin-bottom: 12px; }}
    a {{ color: #0a66c2; }}
</style></head>
<body>
    <h1>LinkedIn Probe — Setup Guide</h1>

    <div class="status {'ok' if api_key else 'missing'}">
        GOOGLE_API_KEY: <strong>{key_status}</strong>
    </div>
    <div class="status {'ok' if cse_id else 'missing'}">
        GOOGLE_CSE_ID: <strong>{cse_status}</strong>
    </div>

    <h2>Step 1: Get a Google API Key</h2>
    <ol>
        <li>Go to <a href="https://console.cloud.google.com/apis/credentials" target="_blank">
            Google Cloud Console → Credentials</a></li>
        <li>Click <strong>"Create Credentials" → "API Key"</strong></li>
        <li>Copy the key</li>
        <li>Enable the <strong>Custom Search API</strong> at
            <a href="https://console.cloud.google.com/apis/library/customsearch.googleapis.com" target="_blank">
            APIs & Services → Library</a></li>
    </ol>

    <h2>Step 2: Create a Custom Search Engine</h2>
    <ol>
        <li>Go to <a href="https://programmablesearchengine.google.com/controlpanel/create" target="_blank">
            Programmable Search Engine</a></li>
        <li>Name it something like "LinkedIn Posts Search"</li>
        <li>Select <strong>"Search the entire web"</strong></li>
        <li>After creation, copy the <strong>Search Engine ID</strong> (cx value)</li>
    </ol>

    <h2>Step 3: Add to .env</h2>
    <pre>
# In social-probes/linkedin-probe/.env
GOOGLE_API_KEY=your-api-key-here
GOOGLE_CSE_ID=your-search-engine-id-here</pre>

    <h2>Step 4: Test</h2>
    <p>Restart the server, then go to <a href="/">the trial UI</a> and search for a name.</p>

    <p><strong>Free tier limits:</strong> 100 queries/day, 10 results per query.
    For higher volume, enable billing ($5 per 1,000 queries).</p>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
async def trial_ui():
    """Simple HTML UI for testing LinkedIn search via Google CSE."""
    api_key, cse_id = _get_credentials()
    if not api_key or not cse_id:
        return """<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0;url=/setup"></head>
        <body>Redirecting to setup...</body></html>"""

    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkedIn Probe — Trial UI</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               max-width: 900px; margin: 0 auto; padding: 24px; background: #f3f2ef; color: #1a1a1a; }
        h1 { color: #0a66c2; margin-bottom: 4px; font-size: 1.5rem; }
        .subtitle { color: #666; margin-bottom: 20px; font-size: 0.9rem; }
        .search-bar { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
        input, button { padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px;
                        font-size: 0.95rem; }
        input[type="text"] { flex: 1; min-width: 200px; }
        input[type="number"] { width: 80px; }
        button { background: #0a66c2; color: white; border: none; cursor: pointer; font-weight: 600; }
        button:hover { background: #004182; }
        button:disabled { background: #999; cursor: not-allowed; }
        .status { padding: 12px; margin-bottom: 16px; border-radius: 8px; display: none; }
        .status.error { background: #ffe0e0; color: #c00; display: block; }
        .status.info { background: #e0f0ff; color: #005; display: block; }
        .card { background: white; border-radius: 10px; padding: 16px; margin-bottom: 12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
        .card-title { font-weight: 600; margin-bottom: 6px; }
        .card-title a { color: #0a66c2; text-decoration: none; }
        .card-title a:hover { text-decoration: underline; }
        .card-source { color: #666; font-size: 0.85rem; margin-bottom: 6px; }
        .card-snippet { line-height: 1.5; color: #333; }
        .quota { text-align: right; color: #888; font-size: 0.8rem; margin-top: 8px; }
        .empty { text-align: center; padding: 40px; color: #888; }
        a.setup { color: #0a66c2; font-size: 0.85rem; }
    </style>
</head>
<body>
    <h1>LinkedIn Probe</h1>
    <p class="subtitle">Google Custom Search for LinkedIn posts — <a class="setup" href="/setup">Setup & Config</a></p>

    <div class="search-bar">
        <input type="text" id="query" placeholder="Search name or keyword..." value="">
        <input type="number" id="days" value="2" min="1" max="30" title="Days back">
        <button id="searchBtn" onclick="doSearch()">Search</button>
    </div>

    <div id="status" class="status"></div>
    <div id="results"></div>

    <script>
        async function doSearch() {
            const name = document.getElementById('query').value.trim();
            if (!name) return;
            const days = document.getElementById('days').value;
            const btn = document.getElementById('searchBtn');
            const status = document.getElementById('status');
            const results = document.getElementById('results');

            btn.disabled = true;
            btn.textContent = 'Searching...';
            status.className = 'status info';
            status.style.display = 'block';
            status.textContent = `Searching LinkedIn posts for "${name}"...`;
            results.innerHTML = '';

            try {
                const resp = await fetch(`/search?name=${encodeURIComponent(name)}&days=${days}`);
                const data = await resp.json();

                if (data.error) {
                    status.className = 'status error';
                    status.textContent = data.error;
                    return;
                }

                status.className = 'status info';
                status.textContent = `Found ${data.total} result(s) from the last ${data.days} day(s) (${data.total_available} total available)`;

                if (data.results.length === 0) {
                    results.innerHTML = '<div class="empty">No LinkedIn posts found. Try a broader search or longer time range.</div>';
                    return;
                }

                let html = data.results.map(r => `
                    <div class="card">
                        <div class="card-title">
                            <a href="${r.source_url || '#'}" target="_blank">${esc(r.title || 'Untitled')}</a>
                        </div>
                        <div class="card-source">${esc(r.source_name || 'LinkedIn')}${r.published_at ? ' · ' + new Date(r.published_at).toLocaleDateString() : ''}</div>
                        <div class="card-snippet">${esc(r.snippet || '')}</div>
                    </div>
                `).join('');
                html += `<div class="quota">${data.quota_note || ''}</div>`;
                results.innerHTML = html;
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
    api_key, cse_id = _get_credentials()
    return {
        "status": "ok",
        "service": "linkedin-probe",
        "google_api_key": "configured" if api_key else "missing",
        "google_cse_id": "configured" if cse_id else "missing",
    }
