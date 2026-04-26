![tag:talant](https://img.shields.io/badge/talant-FFD700)
![tag:recruiting](https://img.shields.io/badge/recruiting-blue)
![tag:university](https://img.shields.io/badge/university-green)
![tag:internships](https://img.shields.io/badge/internships-purple)
![domain:innovation-lab](https://img.shields.io/badge/innovation--lab-3D8BD3)

# Atlas — The Talent Intelligence Guide

Atlas is the AI guide for **Talantis**, a platform that maps where top university talent flows across companies. Ask Atlas natural-language questions about university-to-company internship pipelines, and it answers with grounded, data-backed analysis.

## What Atlas can do

Atlas has three tools it calls automatically based on your question:

- **`filter_internships`** — direct factual queries
  *"How many UCLA students interned at Stripe last year?"*
- **`compare_companies`** — head-to-head pipeline comparison
  *"Compare Citadel and Jane Street's hiring patterns."*
- **`find_similar_schools`** — pipeline gap analysis (the magic)
  *"We're Stripe. Where are Plaid, Brex, and Ramp finding talent we're missing?"*

Atlas reasons across multi-turn conversations. You can follow up:

> *User:* How many UCLA students interned at Stripe?
> *User:* What about Berkeley?
> *User:* Compare those two universities.
> *User:* Now look at Plaid's hiring.
> *User:* Where do they overlap with Stripe's pipeline?

Each turn calls the right tool with the right arguments and remembers prior context.

## Sample questions

- *Where do top universities place their CS interns?*
- *Which schools feed the most students to OpenAI and Anthropic?*
- *Show me Snap's top feeder universities.*
- *Compare Google and Meta's hiring patterns by university.*
- *We're an AI startup. Which schools should we recruit from that our competitors don't already?*
- *Where does Citadel hire from that Two Sigma doesn't?*

## Use cases

- **Recruiters & talent leads** — discover under-tapped universities; benchmark your pipeline against competitors
- **University career centers** — see how your placements compare across companies and industries
- **Founders & startup operators** — find hidden talent pools your peer companies are recruiting from

## How it works

Atlas is a thin **uAgent** that bridges ASI:One Chat Protocol to a Python backend hosted at [talantis.vercel.app](https://talantis.vercel.app). The backend runs Atlas's tool-use loop with Claude (Anthropic's model), executes Postgres queries via three SQL functions, and streams the answer back.

The dataset covers Summer 2024 internship placements across 54 companies × 31 universities (1,334 records), modeled on publicly reported placement distributions from Stanford CS, CMU SCS, Berkeley EECS career reports, and 20+ company hiring patterns.

## Project links

- Web app: https://talantis.vercel.app
- GitHub: (replace with your repo URL when published)

## Built for the Fetch.ai Innovation Lab hackathon track

Talantis · LA Hacks 2026