# Solomon Outreach Application — Capability Description & Design Specification

**Purpose:** A comprehensive description of capabilities for an outreach application supporting Solomon's flywheel strategy — reaching AI engineers, nonprofit funders, and tech leaders interested in "AI for Good," with ultimate goals of funding, partnerships, public awareness, and AI community engagement.

**Context:** Solomon is a system of AI designed to mitigate or check the predictable destruction to social, educational, and civic institutions resulting from the advent of AI. The application supports outreach to 300 individuals on the Solomon Influencer Flywheel List.

---

## 1. Core Capabilities (User-Specified)

### 1.1 Daily Mention Monitoring

- **News reports** — Articles, press coverage, wire services
- **Podcasts** — Episodes, interviews, guest appearances
- **Presentations** — Conference talks, keynotes, webinars
- **Speeches** — Public addresses, congressional testimony, panels
- **Other media** — Blog posts, newsletters, social media posts, academic papers

**Behavior:** Run daily (or configurable) searches across sources for mentions of each of the 300 names. Surface new mentions with source links, date, and relevance scoring.

### 1.2 Contact & Profile Management (Per Mention)

For each person surfaced by the application, record and maintain:

| Field | Description |
|-------|-------------|
| **Contact info** | Email, phone, LinkedIn URL, Twitter/X, other social handles |
| **Bio** | Professional background, current role, affiliations (auto-enriched when possible) |
| **Interconnections** | Links to others on the 300-person list (shared institutions, co-authors, collaborators) |
| **Relevance to Solomon** | Connection to mission (from Names list or user-added notes) |
| **Primary interests/concerns** | Topics they care about (AI safety, labor, education, governance, etc.) |

### 1.3 Outreach Tracking

- **Outreach method** — Email, LinkedIn, social DM, website form, etc.
- **Outreach content** — Copy of message sent, subject line, date/time
- **Response status** — Sent, opened, replied, no response, bounced

### 1.4 First-Time Contact Recommendations

For first-time recipients, recommend contact methods in priority order:

- Email (if available)
- LinkedIn
- Social media (Twitter/X, etc.)
- Website contact form
- Other channels (conference DM, mutual connection intro)

### 1.5 Subsequent Contact & Conversation Notes

For repeat contacts:

- **Conversation log** — Date, channel, summary of exchange
- **Notes** — Key points, commitments, follow-ups
- **Relationship stage** — Cold → Warm → Engaged → Partner/Advocate

---

## 2. Similar Prototypes & Existing Tools

### 2.1 Media & News Monitoring

| Tool | Type | Capabilities | Notes |
|------|------|--------------|-------|
| **Media Cloud** | Open source | 2B+ stories, 60K+ sources, API, Python client | Free at search.mediacloud.org; strong for research |
| **TrackTheNews** | Open source (MIT) | Monitors news for specific words/phrases | Freedom of the Press Foundation; GitHub: freedomofpress/trackthenews |
| **NewsAPI.ai** | Commercial API | Entity detection, event grouping, semantic search | Tracks people, companies in news |
| **NewsCatcher API** | Commercial API | 120K+ sources, real-time, NLP/ML analysis | SOC2, GDPR compliant |
| **NewsWhip API** | Commercial API | Real-time discovery, historical data since 2014 | Used by brands/agencies |
| **SerpApi** | Commercial API | Google News, Bing News; 250 free searches/mo | Good for lightweight monitoring |

### 2.2 Relationship & Outreach CRM

| Tool | Type | Capabilities | Notes |
|------|------|--------------|-------|
| **DARTS** | Open source (Django) | Relationship tracking, leads, activities, auth | GitHub: sid-001/Darts |
| **InfluencerMarketingCRM** | Open source | Influencer relationship management | GitHub: fncischen/InfluencerMarketingCRM |
| **InReach** | Open source | Personalized outreach from YouTube analysis; LangChain | GitHub: taishikato/InReach |
| **Sales-Outreach** | Open source | AI-powered lead research, LinkedIn/website, personalized emails | GitHub: codingaslu/sales-outreach |
| **GrowChief** | Open source | Social automation, workflow, human-like interactions | 3.2K stars; alternative to Phantom Buster |
| **Common Room** | Commercial | GitHub listening, buying signals, outbound templates | B2B developer focus |
| **HaystacksAI** | Commercial | GitHub → LinkedIn matching, technical outreach | "Open Source Qualified Leads" |
| **Octolens** | Commercial | GitHub monitoring, brand mentions, AI relevance | 1K+ SaaS brands |

### 2.3 Contact Enrichment

| Tool | Type | Capabilities | Notes |
|------|------|--------------|-------|
| **Hunter** | API | Lead enrichment, email finder, 100+ attributes | Industry standard |
| **Clado** | API | LinkedIn → email/phone from profile URL | Specialized |
| **Kaspr** | API | LinkedIn enrichment, GDPR aligned | Starter plan+ |
| **ContactOut** | API | Full LinkedIn enrichment, work/personal email | Comprehensive |

### 2.4 Relationship Intelligence & Network Mapping

| Tool | Type | Capabilities | Notes |
|------|------|--------------|-------|
| **Affinity** | Commercial | Relationship mapping, warm intro paths, CRM integration | VC/deal sourcing focus |
| **The Swarm** | Commercial | Relationship data, intro paths | Network analysis |
| **Neos** | Commercial | Relationship strength scoring, decay detection | "Customer Relationship Intuition" |

---

## 3. Additional Capabilities to Enhance Effectiveness

### 3.1 Mention Quality & Relevance

- **Relevance scoring** — AI/rule-based scoring of how relevant a mention is to Solomon (e.g., AI safety vs. unrelated topic)
- **Context extraction** — Pull quote or summary of what was said about the person or topic
- **Sentiment** — Positive/neutral/negative toward AI governance, safety, or institutions
- **Disambiguation** — Handle name collisions (e.g., "John Smith" in different contexts)

### 3.2 Timing & Prioritization

- **Mention recency** — Prioritize very recent mentions (e.g., last 24–48 hours) for timely outreach
- **Engagement windows** — After a podcast or speech, person may be more receptive
- **"Hot lead" flag** — Surfaces who was just quoted or featured and might be easier to reach
- **Batch digest** — Daily/weekly summary email of new mentions by category

### 3.3 Contact Discovery & Enrichment

- **Auto-enrichment** — When a new mention appears, trigger enrichment APIs (Hunter, Kaspr, etc.) to find email/LinkedIn
- **Bio extraction** — Use LLM or structured data to build short bios from articles, LinkedIn, institutional pages
- **Availability signals** — Job changes, new roles, recent funding — moments when people are more open to new connections

### 3.4 Network & Interconnection Mapping

- **Shared institutions** — Same university, lab, foundation, company
- **Co-authorship / collaboration** — Papers, projects, panels
- **Warm intro paths** — "Person A on your list knows Person B; ask A for an intro"
- **Influence graph** — Who influences whom (podcast guest → host, advisor → founder)
- **Category clustering** — Group by AI safety, philanthropy, education, etc., for targeted messaging

### 3.5 Outreach Intelligence

- **Channel effectiveness** — Track which channels (email vs. LinkedIn vs. Twitter) get the best response rates
- **Message templates** — Per category (e.g., AI safety researcher vs. foundation leader) with personalization placeholders
- **A/B testing** — Test subject lines, opening lines, call-to-action
- **Optimal send time** — Suggest send windows based on past engagement
- **Follow-up sequences** — Automated reminder to follow up if no response after N days

### 3.6 Solomon-Specific Relevance

- **Mission alignment score** — How closely their work aligns with Solomon (from Names list + user feedback)
- **Funding potential** — Flag foundation leaders, impact investors, major donors
- **Amplification potential** — Podcast hosts, journalists, conference organizers
- **Technical credibility** — AI researchers, lab leads for technical validation
- **Custom tags** — User-defined tags (e.g., "prioritize," "warm intro available," "already engaged")

### 3.7 Conversation & Relationship Intelligence

- **Conversation summarization** — LLM summaries of long email threads or meeting notes
- **Action items** — Extract commitments, next steps, follow-ups
- **Relationship health** — Score based on recency, response rate, depth of engagement
- **Decay alerts** — "Haven't contacted X in 6 months; relationship may be cooling"

### 3.8 Reporting & Analytics

- **Outreach funnel** — Cold → Contacted → Replied → Meeting → Engaged
- **Conversion by category** — Which categories (AI safety, philanthropy, etc.) convert best
- **Mention-to-contact lag** — How quickly you reach out after a mention (faster = better?)
- **Pipeline value** — Estimated impact of engaged contacts (funding, partnerships, awareness)

### 3.9 Integrations & Automation

- **Calendar** — Schedule follow-ups, sync meetings
- **Email** — Send from app or log sent emails (Gmail/Outlook)
- **LinkedIn** — Log connection requests, DMs (manual or via integration if available)
- **Slack/Discord** — Notifications for high-priority mentions
- **RSS/Newsletter** — Subscribe to key sources, ingest into system

### 3.10 Compliance & Ethics

- **GDPR/CCPA** — Consent tracking, data retention, right to deletion
- **CAN-SPAM** — Unsubscribe handling for email
- **Audit log** — Who accessed what contact data, when
- **Opt-out list** — Respect requests to not be contacted

---

## 4. Target Outcomes (Solomon Mission)

| Outcome | How the App Supports It |
|---------|--------------------------|
| **Funding** | Identify and track foundation leaders, impact investors, major donors; prioritize warm intro paths; track grant cycles and RFPs |
| **Partnerships** | Map interconnections; surface orgs (AI labs, nonprofits, universities) for partnership; track conversation depth |
| **Public awareness** | Prioritize journalists, podcast hosts, conference organizers; track media mentions and amplification |
| **AI community engagement** | Focus on AI researchers, lab leads, safety advocates; use technical credibility tags; track conference/podcast appearances |
| **"AI for Good" alignment** | Relevance scoring for AI-for-good, institutional protection, civic tech; category filters for targeted outreach |

---

## 5. Suggested Architecture (High-Level)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        OUTREACH APPLICATION                              │
├─────────────────────────────────────────────────────────────────────────┤
│  INGESTION LAYER                                                        │
│  • Media Cloud / NewsAPI / TrackTheNews (news)                          │
│  • Podcast RSS / transcript APIs (podcasts)                              │
│  • Conference/event APIs (presentations, speeches)                       │
│  • Google Alerts / SerpApi (web)                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  MATCHING & SCORING                                                     │
│  • Name matching (with disambiguation)                                   │
│  • Relevance scoring (Solomon alignment)                                 │
│  • Deduplication                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  CONTACT & PROFILE LAYER                                                 │
│  • Contact DB (from Names + enriched)                                    │
│  • Hunter / Kaspr / ContactOut (enrichment)                              │
│  • Bio extraction (LLM or structured)                                    │
│  • Interconnection graph (manual + inferred)                             │
├─────────────────────────────────────────────────────────────────────────┤
│  OUTREACH & TRACKING                                                     │
│  • Outreach log (method, content, date)                                   │
│  • Conversation notes                                                    │
│  • Channel recommendations                                               │
│  • Template library                                                      │
├─────────────────────────────────────────────────────────────────────────┤
│  UI & WORKFLOW                                                           │
│  • Daily digest / dashboard                                               │
│  • Contact detail view                                                   │
│  • Outreach composer                                                     │
│  • Notes & relationship timeline                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Implementation Priorities

**Phase 1 — Core**
1. Daily mention monitoring (news, podcasts) using Media Cloud or NewsAPI
2. Contact DB seeded from Names list
3. Basic outreach log (method, content, date)
4. Simple UI for viewing mentions and logging outreach

**Phase 2 — Enrichment**
5. Contact enrichment (email, LinkedIn) via Hunter or Kaspr
6. Bio extraction
7. First-contact channel recommendations
8. Conversation notes

**Phase 3 — Intelligence**
9. Interconnection mapping
10. Relevance scoring
11. Warm intro path discovery
12. Analytics and reporting

**Phase 4 — Scale**
13. Additional media sources (presentations, speeches)
14. Template library and A/B testing
15. Integrations (email, calendar, Slack)
16. Compliance (GDPR, opt-out)

---

## 7. Open Questions

- **Data sources:** Which news/podcast APIs are in budget? Media Cloud is free; NewsAPI.ai and NewsCatcher have paid tiers.
- **Enrichment:** Hunter/Kaspr/ContactOut have rate limits and costs; need volume estimates.
- **Podcasts:** Transcript APIs (e.g., Deepgram, AssemblyAI) can search podcast content but add cost.
- **Self-hosted vs. SaaS:** Balance of control (self-hosted) vs. speed (SaaS components).
- **Names format:** Parse existing `Names` file into structured records (name, category, connection, org) for DB seeding.

---

*Document created for the Solomon Outreach project. Last updated: February 2025.*
