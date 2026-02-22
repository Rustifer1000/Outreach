# Codebase Review — Bugs & Inefficiencies

*Review date: Feb 2025*

---

## Critical / High

### 1. **Names file: newlines in add-entry fields** — FIXED
- **Issue:** If the user enters newlines in Name, Role/org, or Connection, the written block would span multiple "lines" and break the file format (next parse would misread).
- **Fix:** Sanitize by replacing newlines with spaces (or stripping) in `add_entry()` before writing.

### 2. **Names file: path safety (NAMES_FILE_PATH)** — DOCUMENTED
- **Issue:** If `NAMES_FILE_PATH` is set to something like `../../../etc/passwd`, the app could read/write outside the project. Low risk for a single-user/local app.
- **Recommendation:** Document that the path should point to a dedicated Names file; optionally validate that the path is under a configured project root.

### 3. **Dashboard: refresh interval not cleared on unmount** — FIXED
- **Issue:** After clicking "Refresh mentions now", a 10s polling interval runs. If the user navigates away before it finishes, the interval keeps running (memory/leak and stale updates).
- **Fix:** Store the interval id in a ref and clear it in a `useEffect` cleanup (and when `attempts >= 6`).

### 4. **API: explicit JSON serialization for list endpoints** — FIXED
- **Issue:** `list_contacts` and `list_outreach` return raw SQLAlchemy objects. FastAPI’s `jsonable_encoder` can handle them, but datetimes and relations can be inconsistent; explicit dicts are clearer and safer.
- **Fix:** Build response dicts with explicit `.isoformat()` for datetime fields in both endpoints.

---

## Medium

### 5. **Mentions API: load-then-filter in Python** — FIXED
- **Issue:** `list_mentions` loaded all mentions in the date range, then limited to `max_per_contact` per contact in Python. Inefficient for large datasets.
- **Fix:** Use `ROW_NUMBER() OVER (PARTITION BY contact_id ORDER BY published_at DESC NULLS LAST)` in a subquery; filter `rn <= max_per_contact` in SQL. Single contact filter unchanged (no limit).

### 6. **fetch_mentions.py: N+1 dedupe query** — FIXED
- **Issue:** For each contact, we ran `session.query(Mention).filter(Mention.contact_id == contact.id).all()` to check URL dedupe. One query per contact (~300).
- **Fix:** Load all mentions for the contact set once with `contact_id.in_(contact_ids)`, build a set of `(contact_id, normalized_url)`, and check dedupe in memory. Also add newly inserted URLs to the set within the same run.

### 7. **ContactDetail: no user feedback on copy**
- **Issue:** `copyToClipboard()` is called with no toast or message; user doesn’t know the copy succeeded.
- **Improvement:** Brief “Copied!” feedback (state + timeout or toast).

### 8. **ContactDetail / NamesFile: API errors not always surfaced**
- **Issue:** Some `.catch()` only `console.error`; user sees no inline error message.
- **Improvement:** Set error state and show a small message in the UI where appropriate.

---

## Low / Nice-to-have

### 9. **seed_contacts.py: --data path when run from different cwd**
- **Issue:** Default `--data` is `Path(__file__).parent.parent.parent / "data" / "contacts.json"`. Correct when run from `outreach-app/`; if run from elsewhere, path is still absolute from `__file__`, so it’s fine.
- **Note:** No change needed.

### 10. **Scheduler: fetch_mentions subprocess DB path**
- **Issue:** `run_fetch_mentions()` runs the script with `cwd=base` (outreach-app). The script default is `--db sqlite:///./backend/outreach.db`, so the DB path is relative to outreach-app. Correct.
- **Note:** No change needed.

### 11. **Outreach create: sent_at timezone**
- **Issue:** `datetime.fromisoformat(data.sent_at.replace("Z", "+00:00"))` is correct for ISO with Z. If the frontend sends local time without Z, it could be interpreted as UTC. Acceptable for now; document if needed.

### 12. **Names file: duplicate names**
- **Issue:** Delete uses first match when only `name` is given. If two entries share the same name, only one is removed unless `list_number` is provided. Documented in API; UI could show list_number in the table (already shown) and pass it when deleting. No bug.

---

## Summary

- **Fixed in this pass:** Newline sanitization in Names add_entry, Dashboard interval cleanup, explicit serialization for contacts and outreach list endpoints.
- **Documented / optional:** NAMES_FILE_PATH path safety.
- **Left for later:** Mentions per-contact limit in SQL, fetch_mentions N+1, copy feedback, broader error UI.

---

## From previous CODE_REVIEW.md (merged)

- **seed_sample_mentions:** Uses `name_fragment in name`; if you add more samples, keep fragments unique or match by `list_number`.
- **CORS:** `allow_origins` is localhost only; add production origin before deploy.
- **Security:** No rate limiting on API — consider for production. SQL and .env are fine.
- **Deprecations:** `datetime.utcnow()` already replaced with `datetime.now(UTC)`; modern type hints in use.

---

## Since last review (Phase 2B, Map, Discovery)

### Fixed in this pass

- **Discovery from mentions: N² DB queries** — Previously `_connection_exists(db, …)` was called inside a double loop (mentions × contacts), causing tens of thousands of queries. Now we preload all existing connections into a set and check in memory; single query for contacts and single query for connections.

### New code reviewed (no critical bugs)

- **Notes API** — create_note uses `note_date` with fallback to now() on parse error; channel handles None.
- **Relationship map** — useMemo for filtered graph; search filters client-side; no extra API on search.
- **Discovery via search** — commit once at end; rate limit delay; connection existence check per pair (acceptable for max 20–50 pairs).
- **Migration** — Phase 2B migration ignores "no such table" so it’s safe before first seed.

### Optional follow-ups

- **Discovery: name matching** — Full-name substring can false-positive (e.g. "Bengio" in "Yoshua Bengio"). We skip names under 4 chars; could add word-boundary or prefer exact phrase.
- **Discovery jobs: error feedback** — Background tasks don’t return result to client; user only sees "started". Could add a small "job status" endpoint or poll for last-run result.
- **ContactDetail discover button** — On failure we set `discovering` false but don’t show an error message; could set error state.

---

## Recent session (Feb 2025)

### Fixed
- **GET /api/contacts limit** — Raised max from 100 to 500; Rotation page was requesting 400 and getting 422, causing empty dropdown.
- **Rotation page loading** — `loadRotation` and `loadContacts` now awaited before clearing loading state; Refresh button fixed.
- **Missing DB tables on startup** — Added `Base.metadata.create_all(engine)` in main.py lifespan so mentions/other tables are created if missing.

### Known issue (low priority)
- **Replace rotation (Set rotation from list)** — Sometimes does not update count; Add-to-rotation dropdown and one-by-one add work. Possible cause: API or frontend parsing; leave unfixed for now to avoid regressions.
