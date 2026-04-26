<div align="center">

![Talantis hero banner](https://raw.githubusercontent.com/Talantis/talantis/main/docs/images/hero-banner.png)

# Talantis

**A legendary island of talents.**

*Every company is looking in the same places. We show you the ones no one has mapped yet.*

[![Live App](https://img.shields.io/badge/live%20app-talantis.vercel.app-d4a548?style=for-the-badge)](https://talantis.vercel.app)
[![Agentverse](https://img.shields.io/badge/agentverse-talantis--atlas-3D8BD3?style=for-the-badge)](https://agentverse.ai/agents/details/agent1qw9srfevfplt27z6du7xns4venmtafdezxnujl3ksamz03qwud9yurhc0hv/profile)
[![ASI:One](https://img.shields.io/badge/asi%3Aone-chat%20with%20atlas-5b9eff?style=for-the-badge)](https://asi1.ai)
[![Built for LA Hacks 2026](https://img.shields.io/badge/built%20for-LA%20Hacks%202026-FFD700?style=for-the-badge)](https://lahacks.com)

</div>

---

## What Talantis is

Recruiters at every company chase talent at the same ten universities. The patterns of who *actually* feeds whom — Plaid pulling from UPenn, Citadel from Princeton, Anthropic from Stanford — live in private group chats and LinkedIn scrolling sessions. They've never been mapped.

**Talantis maps them.** Every internship, every pipeline, every hidden coastline.

The product has two faces:

- **The island** — a clean visual surface for browsing university-to-company internship flows
- **Atlas** — an AI guide who walks the data with you, calls the right tools to answer your questions, and surfaces patterns you wouldn't think to ask

You can talk to Atlas anywhere. On the [Talantis web app](https://talantis.vercel.app). On [Agentverse](https://agentverse.ai/agents/details/agent1qw9srfevfplt27z6du7xns4venmtafdezxnujl3ksamz03qwud9yurhc0hv/profile). Through [ASI:One](https://asi1.ai). Same brain, three front doors.

---

## See it move

[IMAGE 2: Atlas chat conversation screenshot — your best multi-turn conversation captured from the FAB chat panel. Ideally shows Question 1 at top → tool indicator badge → Atlas response with specific numbers. Crop tight to just the chat panel, ~480px wide.]

> *"We're Stripe. Where are Plaid, Brex, and Ramp finding talent we're missing?"*

Atlas calls `find_similar_schools`, scans 1,334 placement records across 54 companies and 31 universities, computes the gap between your peers' pipelines and yours, and returns the answer in plain prose:

> *"I see UPenn and NYU feeding heavily to Plaid and Brex — and you have no presence at either. That's the hidden coastline."*

No SQL. No dashboards. No "let me get back to you on that." Just the answer, grounded in real data.

---

## How it works

[IMAGE 3: Architecture diagram — a clean horizontal flow. Left: "Talantis Web App" (Next.js + Vercel logo). Middle: "Talent Intelligence Core" (Python + Claude tool-use loop). Right: "Postgres" (Supabase logo) and "Atlas uAgent" (Fetch.ai logo) branching off. Make in Excalidraw or Figma, export PNG ~1200×400.]

Three layers:

**Frontend** — Next.js 14, Tailwind, deployed on Vercel. The bar chart, the filters, the Atlas FAB chat panel.

**Talent Intelligence Core** — A Python module (`api/atlas.py`) that runs Claude Sonnet 4.5 in an agentic tool-use loop. Three tools defined in `api/tools.py`:

| Tool | Purpose |
|------|---------|
| `filter_internships` | Direct factual queries — counts, lists, rankings by university × company × industry × role × year |
| `compare_companies` | Head-to-head pipeline comparison across multiple companies |
| `find_similar_schools` | The signature insight — pipeline gap analysis. Where do peer companies recruit that you don't? |

Each tool maps to a Postgres function defined in `schema_tools.sql` for indexed performance.

**Atlas uAgent** — A Fetch.ai uAgent (`agent/agent.py`) that bridges ASI:One Chat Protocol to the Talantis backend. Same brain, different transport layer.

---

## The Atlas agent on Agentverse

![Agentverse profile page](https://raw.githubusercontent.com/Talantis/talantis/main/docs/images/agent-profile.png)

Atlas is **registered, active, and discoverable** on Fetch.ai's Agentverse marketplace.

| Property | Value |
|----------|-------|
| Display Name | Talantis Atlas |
| Handle | `@talantis-atlas` |
| Address | `agent1qw9srfevfplt27z6du7xns4venmtafdezxnujl3ksamz03qwud9yurhc0hv` |
| Protocol | AgentChatProtocol v0.3.0 |
| Hosted on | Render (always-on) |
| Status | Active · ASI Available |

→ **[View Atlas's full profile on Agentverse](https://agentverse.ai/agents/details/agent1qw9srfevfplt27z6du7xns4venmtafdezxnujl3ksamz03qwud9yurhc0hv/profile)**

---

## Talk to Atlas through ASI:One

[ASI:One chat session screenshot](https://raw.githubusercontent.com/Talantis/talantis/main/docs/images/asi1-shared-chat.png)

Anyone with an ASI:One account can ask Atlas questions directly:

→ **[Live ASI:One demo conversation](https://asi1.ai/shared-chat/cd572643-48d0-4020-a7ee-679eb37f9e2b)**

Sample questions Atlas handles in stride:

- *"How many UCLA students interned at Stripe last year?"*
- *"Compare Citadel and Jane Street's hiring patterns."*
- *"Which schools feed the most students to OpenAI and Anthropic?"*
- *"We're a fintech startup. Where should we recruit that our competitors don't?"*

Multi-turn works natively — Atlas remembers what you just discussed:

> **You:** *"How many UCLA students interned at Stripe?"*
> **You:** *"What about Berkeley?"*  ← Atlas knows you mean "Berkeley → Stripe"
> **You:** *"Compare those two."*  ← Atlas calls `compare_companies` for UCLA + Berkeley
> **You:** *"Now look at Plaid's hiring."*
> **You:** *"Where do they overlap with Stripe?"*  ← Atlas calls `find_similar_schools`

---

## The data

![Bar chart screenshot](https://raw.githubusercontent.com/Talantis/talantis/main/docs/images/bar-chart.png)

Talantis's dataset covers **1,334 internship placements across 54 companies and 31 universities** for Summer 2024.

It's representative data, modeled on publicly reported placement distributions from:

- [Stanford CS employment report](https://msandecareers.stanford.edu/employment-report/employment-report-bachelor-science-graduates)
- [Berkeley first-destination survey](https://opa.berkeley.edu/campus-surveys/survey-results-reporting-analysis/first-destination-survey)
- CMU SCS career outcomes
- 20+ company hiring patterns from public job postings and LinkedIn

In production, Talantis would ingest data through:

1. Opt-in Chrome extension for verified placements
2. University career center partnerships
3. LinkedIn Talent Solutions API for enterprise customers

The hackathon dataset is realistic enough to demonstrate every Atlas capability without requiring proprietary data.

---

## Architecture

```
┌──────────────────────┐         ┌──────────────────────┐
│  Talantis Web App    │         │  ASI:One / Agentverse │
│  (Next.js · Vercel)  │         │   (Fetch.ai)         │
└──────────┬───────────┘         └──────────┬───────────┘
           │ POST /api/insights              │ ChatMessage
           │ (SSE stream)                    │
           ▼                                 ▼
┌─────────────────────────────────────────────────────────┐
│         Talent Intelligence Core (api/atlas.py)         │
│                                                         │
│   Claude Sonnet 4.5  ←→  3 tools  ←→  Postgres RPCs     │
│   Tool-use loop · Multi-turn history · SSE streaming    │
└─────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────┐
│  Supabase Postgres   │
│  1,334 placements    │
│  54 × 31 grid        │
└──────────────────────┘
```

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14, React, Tailwind CSS, Recharts |
| Backend | Python 3.12, FastAPI, Anthropic SDK 0.49 |
| Database | Supabase (Postgres 15) with custom RPCs |
| Agent | Fetch.ai uAgents 0.24, Chat Protocol v0.3.0 |
| Hosting | Vercel (frontend + API), Render (uAgent) |

---

## The brand

![Brand Grid Ss](https://raw.githubusercontent.com/Talantis/talantis/main/docs/images/brand-grid.png)

Talantis ("tuh-LAN-tis") = **legendary island of talents**. The name does double duty: a play on Atlantis, and a portmanteau of *talent* + *atlantis*.

**The two faces:**
- **Talantis** — the island, the world, the visual product
- **Atlas** — the titan who maps the island, the AI guide

**Voice:** Mythic, not mystical. Curious, not certain. Spare, not sparse. Warm, not casual.

**Palette:** Navy `#0a1628` · Gold `#d4a548` · Cream `#f5ecd7` · Aqua `#4fb3bf` (60/30/8/2)

**Type:** Cormorant Garamond italic for display (the gold "a" in the wordmark is the brand signature), Inter Tight for body.

---

## Repo structure

```
talantis/
├── app/                      Next.js 14 App Router
│   ├── layout.js
│   ├── globals.css
│   ├── page.jsx              Landing
│   ├── explore/page.jsx      Main product page
│   └── submit/page.jsx
│
├── components/
│   ├── Nav.jsx
│   ├── Footer.jsx
│   ├── TalantisLogo.jsx
│   ├── AtlasLogo.jsx
│   ├── chart/                Recharts bar chart + filter
│   └── atlas/                AtlasFAB + AtlasPanel
│
├── api/                      Python serverless functions (Vercel)
│   ├── index.py              FastAPI entrypoint
│   ├── atlas.py              Tool-use loop + SSE streaming
│   ├── tools.py              3 tools, Postgres-backed
│   └── database.py           Supabase client
│
├── agent/                    Fetch.ai uAgent (deployed on Render)
│   ├── agent.py              Chat Protocol implementation
│   ├── requirements.txt
│   ├── render.yaml
│   └── README.md             Published to Agentverse
│
├── public/                   Static assets, favicons, hero images
└── ...                       Tailwind, Next, Vercel config
```

---

## Quick start

```bash
git clone https://github.com/Talantis/talantis
cd talantis

# Frontend
npm install
npm run dev                   # http://localhost:3000

# Backend (in a separate terminal)
cd api
pip install -r requirements.txt
# set SUPABASE_URL, SUPABASE_KEY, ANTHROPIC_API_KEY
uvicorn index:app --reload --port 8000

# uAgent (in another terminal)
cd agent
pip install -r requirements.txt
export AGENT_SEED_PHRASE=$(openssl rand -hex 32)
python agent.py
```

---

## Built with

<div align="center">

![Anthropic](https://img.shields.io/badge/Anthropic-Claude_Sonnet_4.5-d4a548?style=for-the-badge)
![Fetch.ai](https://img.shields.io/badge/Fetch.ai-uAgents_0.24-3D8BD3?style=for-the-badge)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=next.js)
![Vercel](https://img.shields.io/badge/Vercel-deployed-000000?style=for-the-badge&logo=vercel)
![Render](https://img.shields.io/badge/Render-agent-46E3B7?style=for-the-badge&logo=render)
![Supabase](https://img.shields.io/badge/Supabase-Postgres-3FCF8E?style=for-the-badge&logo=supabase)
![Tailwind](https://img.shields.io/badge/Tailwind-CSS-06B6D4?style=for-the-badge&logo=tailwindcss)

</div>

---

## Hackathon submission

Built for **LA Hacks 2026** — Fetch.ai Agentverse: Search & Discovery of Agents track.

**Deliverables:**

1. **ASI:One shared chat session** → [asi1.ai/shared-chat/YOUR_UUID_HERE](https://asi1.ai/shared-chat/cd572643-48d0-4020-a7ee-679eb37f9e2b)
2. **Agentverse profile** → [agentverse.ai/agents/details/agent1qw9srfevfplt27z6du7xns4venmtafdezxnujl3ksamz03qwud9yurhc0hv/profile](https://agentverse.ai/agents/details/agent1qw9srfevfplt27z6du7xns4venmtafdezxnujl3ksamz03qwud9yurhc0hv/profile)
3. **Public repo** → [github.com/Talantis/talantis](https://github.com/Talantis/talantis)
4. **Demo video** → [Devpost submission](https://devpost.com/software/talantis)

---

<div align="center">

*The map exists. It just hasn't been drawn yet.*

</div>