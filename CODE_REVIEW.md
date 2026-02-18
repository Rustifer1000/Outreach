# Code Review — Solomon Outreach

**Date:** Feb 2025

---

## Fixes Applied

| Issue | Location | Fix |
|-------|----------|-----|
| Unused import | `fetch_mentions.py` | Removed `hashlib` |
| Inefficient commits | `fetch_mentions.py` | Single `commit()` at end instead of per-contact |
| Unused variable | `parse_names.py` | Removed `category_pattern`, `entry_pattern` |
| Raw model return | `mentions.py` get_mention | Return explicit dict with `contact_name`, use `joinedload` |

---

## Remaining Notes (No Changes)

### API serialization
- **contacts.py** / **outreach.py** return raw SQLAlchemy models. FastAPI serializes them; if you add more relationships later, consider Pydantic response models to avoid N+1 or recursion.

### seed_sample_mentions contact matching
- Uses `name_fragment in name` (e.g. "Russell" in "Stuart Russell"). Works for the 8 samples; if you add more, ensure fragments are unique or switch to explicit `list_number` matching.

### CORS
- `allow_origins` is `["http://localhost:3000", "http://localhost:5173"]`. Add your production URL before deploying.

### Frontend error handling
- API failures are logged to console but not shown in the UI. Consider adding error state and user feedback.

---

## Deprecations Checked

- ✅ `datetime.utcnow()` — Already replaced with `datetime.now(UTC)` (PR #1)
- ✅ Python 3.11+ type hints (`list[Contact]`) — In use
- ✅ No deprecated SQLAlchemy patterns

---

## Security

- ✅ SQL injection: Safe — SQLAlchemy parameterized queries
- ✅ `.env` in `.gitignore` — API keys not committed
- ⚠️ No rate limiting on API — Consider for production
