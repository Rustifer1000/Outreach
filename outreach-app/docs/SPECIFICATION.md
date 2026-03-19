# Solomon Outreach App — Product Specification

**Version:** 1.0
**Last Updated:** March 2026

---

## 1. Purpose & Overview

The Solomon Outreach App is a private relationship intelligence and engagement platform built to support the Solomon Project's mission in the AI safety and governance space. Its purpose is to help a small team manage strategic outreach to approximately 300 key individuals — researchers, funders, policymakers, journalists, technologists, and advocates — who are positioned to amplify, fund, or advance the Solomon Project's goals.

The application is designed for one primary operator (the user) and works as a personal command center for:

- **Monitoring** what the 300 contacts are saying and publishing across news and LinkedIn
- **Drafting** thoughtful, AI-assisted replies to LinkedIn posts that organically build awareness of the Solomon Project
- **Tracking** all outreach attempts, responses, and conversation history
- **Managing** contact profiles, notes, and enrichment data
- **Analyzing** the health and progress of the outreach effort over time

The system is intentionally private — it does not expose any public-facing interface and is not a mass-marketing tool. All outreach is human-reviewed before sending.

---

## 2. The Contact List

The foundation of the application is a curated list of approximately 300 individuals referred to as the **Solomon Influencer Flywheel List**. This list is stored in a file called `Names` at the project root and is organized into named categories and subcategories (e.g., AI Safety Researchers, Funders, Journalists, Policymakers).

Each contact record stores:

| Field | Description |
|-------|-------------|
| Name | Full name |
| List Number | Sequential position in the master list |
| Category / Subcategory | Thematic grouping from the Names file |
| Role / Organization | Job title and employer |
| Connection to Solomon | How this person relates to the Solomon Project's mission |
| Primary Interests | Topics this person is known for |
| Bio | Free-text biography |
| Relationship Stage | Current status: `cold`, `warm`, `engaged`, or `partner` |
| Mission Alignment | Score from 1–10 indicating alignment with Solomon's goals |
| Enrichment Status | Whether contact info has been looked up: `pending`, `enriched`, or `failed` |

---

## 3. Core Features

### 3.1 Mention Monitoring

The app automatically fetches recent mentions of each contact across two sources:

**News (via NewsAPI.org)**
Searches for news articles mentioning each contact by name from the past N days. Results are stored with title, source name, URL, snippet, and publish date.

**LinkedIn Posts (via Serper.dev)**
Searches Google (via Serper) for recent LinkedIn posts by or about each contact, filtered to `site:linkedin.com/posts`. Results are stored in the same mention schema as news articles with `source_type = "linkedin"`.

Fetching is triggered manually from the Mentions page. It runs as a background job so the UI remains responsive. Progress is shown in real time (e.g., "Processing contact 47 of 300"). Duplicate URLs are automatically skipped on re-fetch.

Each mention is linked to a contact and stored with:
- Source type (`news` or `linkedin`)
- Source name (e.g., "The Atlantic", "LinkedIn — Rose Luckin")
- URL
- Title
- Snippet or excerpt
- Publish date

### 3.2 AI-Generated LinkedIn Reply Drafts

On any contact's detail page, LinkedIn mentions display a **"Draft Reply"** button. Clicking it opens a modal that:

1. Calls the Claude AI (Anthropic) API with the post content and contact context
2. Generates a genuine, thoughtful reply draft that:
   - Engages authentically with the post's topic and tone
   - Adds real perspective or insight
   - Drops the name "The Solomon Project" **once**, briefly and parenthetically — as one example among others (e.g., *"...projects like the Solomon Project come to mind..."*) — with no promotion, no explanation, and no link
3. Automatically tags the reply with relevant themes it detects in the post (see Section 5)
4. Saves the draft to the database linked to the contact and the specific post
5. Allows the user to edit the text before use
6. Provides a **Copy to Clipboard** button for pasting directly into LinkedIn
7. Allows marking the draft as **Used** or **Archived**

**Important design principle:** The Solomon Project mention is always incidental, parenthetical, and non-promotional. Phase 1 goal is name-only awareness. Future phases will gradually introduce purpose.

### 3.3 Contact Enrichment

The app integrates with the Hunter.io API to automatically look up email addresses and LinkedIn profile URLs for contacts. Enrichment runs as a background job and updates each contact's `ContactInfo` records. The Enrichment page shows coverage statistics and allows triggering the enrichment process.

### 3.4 Outreach Logging

Every outreach attempt is recorded manually, including:
- Contact
- Method (email, LinkedIn, phone, etc.)
- Subject and message content
- Date sent
- Response status (sent, replied, no response, bounced)

### 3.5 Conversation Notes

Free-text notes can be added to any contact to record the substance of conversations, key insights, or follow-up reminders. Notes include the channel (email, LinkedIn, phone, meeting) and date.

### 3.6 Message Templates

Reusable message templates can be created and categorized (e.g., by theme or contact type) and referenced when drafting outreach.

### 3.7 Network & Warm Introductions

Connections between contacts can be recorded (e.g., co-authors, shared organization, panelists together). The app can suggest **warm introduction paths** — finding contacts who know both you and a target person.

### 3.8 Analytics

The Analytics page provides:
- **Funnel view** — how many contacts are at each relationship stage
- **Conversion rates** — by category
- **Mention-to-contact lag** — how quickly mentions are leading to outreach
- **Channel effectiveness** — which outreach methods generate responses
- **Activity over time** — outreach volume trends

### 3.9 Digest

A digest view groups recent mentions by category, providing a weekly or monthly summary of what the target community is talking about — useful for identifying themes, hot topics, and outreach timing.

### 3.10 Adding New Contacts

The Contacts page includes an **"Add contacts"** input at the top. The user can type multiple names separated by commas and click Add. Each name is added to the end of the contact list with an auto-incremented list number and a default relationship stage of `cold`. Duplicate names (case-insensitive) are automatically skipped with a notification.

---

## 4. Data Architecture

### Database

The application uses **SQLite** for development (a single file: `outreach-app/backend/outreach.db`). It is designed to migrate to **PostgreSQL** for production use by changing one environment variable.

### Tables

| Table | Purpose |
|-------|---------|
| `contacts` | The 300 target individuals and their profile data |
| `contact_info` | Email addresses, LinkedIn URLs, phone numbers per contact |
| `mentions` | News and LinkedIn posts mentioning contacts |
| `reply_drafts` | AI-generated LinkedIn reply drafts, linked to mentions |
| `outreach_log` | Record of every outreach attempt |
| `notes` | Freeform conversation notes per contact |
| `templates` | Reusable message templates |
| `interconnections` | Relationships between contacts (for warm intro mapping) |

### Reply Drafts Table (detail)

| Field | Description |
|-------|-------------|
| contact_id | Which contact this reply is for |
| mention_id | Which specific LinkedIn post is being replied to |
| reply_text | The full text of the generated reply |
| themes | JSON array of detected themes (see Section 5) |
| status | `draft`, `used`, or `archived` |
| created_at | Timestamp |

---

## 5. Theme Classification

When generating reply drafts, the AI automatically identifies which of the following themes the original post touches. These tags are stored with each draft and will be used in future versions for pattern analysis and campaign targeting.

| Theme | Description |
|-------|-------------|
| `safety` | AI safety — preventing harm from AI systems |
| `alignment` | AI alignment — ensuring AI systems behave as intended |
| `social-justice` | Equity, fairness, and societal impact of technology |
| `disruption` | Economic and social disruption caused by AI and automation |
| `governance` | Policy, regulation, and institutional oversight of AI |
| `existential-risk` | Long-term and catastrophic risks from advanced AI |
| `ai-for-good` | Using AI to address humanitarian and social challenges |

---

## 6. External Integrations

| Service | Purpose | Required? |
|---------|---------|-----------|
| **NewsAPI.org** | Fetches news articles mentioning contacts | Yes (for news mentions) |
| **Serper.dev** | Fetches LinkedIn posts via Google search | Yes (for LinkedIn mentions) |
| **Hunter.io** | Looks up email and LinkedIn URLs for contacts | Optional |
| **Anthropic (Claude)** | Generates LinkedIn reply drafts | Yes (for reply drafts) |

All API keys are stored in the `.env` file and never exposed to the frontend or committed to source control.

---

## 7. Application Structure

### Backend

Built with **Python** using the **FastAPI** framework. Runs on port **8000**.

```
outreach-app/backend/
├── app/
│   ├── main.py          — App entry point, middleware, route registration
│   ├── config.py        — Environment variable loading and validation
│   ├── database.py      — Database connection and session management
│   ├── models.py        — Database table definitions
│   └── api/
│       ├── contacts.py       — Contact CRUD and search
│       ├── mentions.py       — Mention fetching and listing
│       ├── reply_drafts.py   — AI reply draft generation and management
│       ├── outreach.py       — Outreach log
│       ├── notes.py          — Conversation notes
│       ├── templates.py      — Message templates
│       ├── network.py        — Interconnections and warm intros
│       ├── analytics.py      — Reporting endpoints
│       ├── enrichment.py     — Hunter.io enrichment
│       ├── digest.py         — Mention digest
│       └── settings_api.py   — API key status
```

### Frontend

Built with **React** and **TypeScript** using **Vite** and **Tailwind CSS**. Runs on port **5173**.

```
outreach-app/frontend/src/
├── App.tsx              — Route definitions
├── components/
│   └── Layout.tsx       — Navigation sidebar
└── pages/
    ├── Dashboard.tsx    — Recent mentions overview
    ├── Contacts.tsx     — Contact list with search and add
    ├── ContactDetail.tsx — Contact profile with mentions and Draft Reply
    ├── Mentions.tsx     — All mentions with fetch trigger
    ├── Outreach.tsx     — Outreach log
    ├── Notes.tsx        — Notes browser
    ├── Enrichment.tsx   — Hunter.io enrichment controls
    ├── Analytics.tsx    — Funnel and conversion charts
    ├── Network.tsx      — Interconnections and warm intros
    ├── Templates.tsx    — Message template library
    ├── Digest.tsx       — Mention digest by category
    └── Settings.tsx     — API key status
```

### Social Probes (Standalone)

Two standalone FastAPI microservices used for development and testing of search sources before integration:

| Probe | Port | Purpose |
|-------|------|---------|
| `bluesky-probe` | 8001 | Search Bluesky posts via AT Protocol (currently inactive — auth required) |
| `linkedin-probe` | 8002 | Search LinkedIn posts via Serper.dev (active) |

Each probe has its own trial UI accessible in a browser for manual testing.

---

## 8. API Endpoints Summary

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/contacts` | List/search contacts |
| POST | `/api/contacts` | Add new contacts by name |
| GET | `/api/contacts/{id}` | Get single contact |
| PATCH | `/api/contacts/{id}` | Update contact fields |
| GET | `/api/mentions` | List mentions (filterable by contact, days) |
| POST | `/api/mentions/fetch` | Trigger background mention fetch |
| GET | `/api/mentions/fetch/status` | Check fetch progress |
| POST | `/api/reply-drafts/generate` | Generate AI reply draft for a mention |
| GET | `/api/reply-drafts` | List saved drafts |
| PATCH | `/api/reply-drafts/{id}` | Update draft status |
| DELETE | `/api/reply-drafts/{id}` | Delete a draft |
| GET | `/api/outreach` | List outreach log entries |
| POST | `/api/outreach` | Log a new outreach attempt |
| PATCH | `/api/outreach/{id}` | Update outreach status |
| GET | `/api/notes` | List notes |
| POST | `/api/notes` | Add a note |
| DELETE | `/api/notes/{id}` | Delete a note |
| GET | `/api/templates` | List templates |
| POST | `/api/templates` | Create template |
| PUT | `/api/templates/{id}` | Update template |
| DELETE | `/api/templates/{id}` | Delete template |
| GET | `/api/network` | List interconnections |
| POST | `/api/network` | Add connection |
| GET | `/api/network/warm-intros/{id}` | Find warm intro paths |
| POST | `/api/enrichment/run` | Trigger Hunter.io enrichment |
| GET | `/api/enrichment/status` | Check enrichment progress |
| GET | `/api/analytics/funnel` | Relationship stage funnel |
| GET | `/api/analytics/conversion` | Conversion by category |
| GET | `/api/digest` | Mention digest by category |
| GET | `/api/settings` | API key configuration status |

---

## 9. Environment Configuration

All secrets and configuration live in `outreach-app/.env`. This file is never committed to source control.

```
DATABASE_URL=sqlite:///./outreach.db
NEWSAPI_KEY=...
SERPER_API_KEY=...
HUNTER_API_KEY=...
ANTHROPIC_API_KEY=...
DEBUG=false
ENVIRONMENT=development
```

---

## 10. Running the Application

### Prerequisites
- Python 3.11+
- Node.js 18+

### First-time Setup

```bash
# 1. Parse the Names file into JSON/CSV
python scripts/parse_names.py

# 2. Install backend dependencies
cd outreach-app/backend
pip install -r requirements.txt

# 3. Seed the database with contacts
cd outreach-app
python scripts/seed_contacts.py --db sqlite:///./backend/outreach.db --reset

# 4. Install frontend dependencies
cd outreach-app/frontend
npm install
```

### Running

```bash
cd outreach-app
npm run start
```

This starts both the backend (port 8000) and frontend (port 5173) concurrently.
Open `http://localhost:5173` in your browser.

---

## 11. Planned Future Phases

| Phase | Description |
|-------|-------------|
| **Phase 2 (Reply)** | Begin injecting subtle purpose messaging into reply drafts, not just name-dropping |
| **Phase 3 (Scheduling)** | Automated scheduled mention fetches via APScheduler |
| **Phase 4 (Email)** | Email integration for outreach directly from the app |
| **Phase 5 (Auth)** | User authentication for multi-user or remote deployment |
| **Phase 6 (Bluesky)** | Re-enable Bluesky probe once auth flow is implemented |
| **Phase 7 (Production)** | Migrate to PostgreSQL, Alembic migrations, cloud deployment |

---

## 12. Design Principles

1. **Human in the loop** — No automated sending. Every reply, email, or outreach is reviewed and sent manually by the operator.
2. **Ambient awareness, not promotion** — The Solomon Project is introduced organically through genuine engagement, never through pitches or promotional copy.
3. **Quality over volume** — The contact list is curated and small. The goal is meaningful relationships, not mass outreach.
4. **Privacy by default** — The app is local-only. No data leaves the machine except via explicit API calls to external services.
