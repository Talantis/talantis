"""
Talent Intelligence Core
========================

Three tools that Atlas can call to answer recruiter questions about the
internship dataset. Each tool is a plain Python function that hits Supabase
via the existing client.

The three tools, ordered by complexity:

    1. filter_internships()    — direct factual queries ("how many UCLA at Stripe?")
    2. compare_companies()     — head-to-head competitive intel
    3. find_similar_schools()  — the magic. Pipeline gap analysis.

Each function:
  - Takes structured arguments (which Claude generates as tool_use JSON)
  - Executes Postgres queries against the existing schema
  - Returns a JSON-serializable dict that Claude can reason about

These tools are called BOTH by:
  - The web frontend (via /api/insights)
  - The Fetch.ai uAgent (via Chat Protocol → same FastAPI endpoint)

This is the "one Atlas, two front doors" architecture.
"""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

# LAZY Supabase client. We initialize on first use rather than at import time,
# so that:
#   1. A missing env var doesn't crash the whole module import — which on
#      Vercel manifests as a useless 500 with no logs (the function fails
#      to even start up).
#   2. Vercel's serverless cold start is faster (no DNS or TCP handshake
#      at module load).
# The client is cached for the lifetime of the warm container.
_sb_client: Client | None = None


def _sb() -> Client:
    """Return a cached Supabase client, creating it on first call."""
    global _sb_client
    if _sb_client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError(
                "Missing SUPABASE_URL or SUPABASE_KEY env var. "
                "Set both in Vercel → Project Settings → Environment Variables."
            )
        _sb_client = create_client(url, key)
    return _sb_client


# ════════════════════════════════════════════════════════════════════════════
# TOOL 1: filter_internships
# Direct factual queries. The workhorse.
# ════════════════════════════════════════════════════════════════════════════

def filter_internships(
    university: Optional[str] = None,
    company: Optional[str] = None,
    industry: Optional[str] = None,
    role_category: Optional[str] = None,
    year: int = 2024,
    group_by: str = "company",
    limit: int = 15,
) -> dict:
    """
    Count internships matching the given filters, grouped by a chosen dimension.

    Examples Claude might invoke this for:
      - "How many UCLA students interned at Stripe?"
        → filter_internships(university="UCLA", company="Stripe")
      - "Show me Snap's top feeder schools"
        → filter_internships(company="Snap", group_by="university")
      - "Where do fintech firms hire from?"
        → filter_internships(industry="fintech", group_by="university")

    Args:
        university:    Display name (e.g. "UCLA") or slug. Optional.
        company:       Display name (e.g. "Stripe") or slug. Optional.
        industry:      Industry slug (e.g. "fintech"). Optional.
        role_category: One of SWE / PM / Data / Design / Research / Business / Other.
        year:          Year to filter on. Default 2024.
        group_by:      "company" | "university" | "industry" | "role_category".
        limit:         Max rows in the result. Default 15.

    Returns:
        {
          "filters": {...},                  # what we filtered on (echoed back)
          "group_by": "company",
          "total_internships": 187,          # total matching rows
          "rows": [
            {"key": "Google", "count": 18},
            {"key": "Meta",   "count": 14},
            ...
          ]
        }
    """
    # Build the WHERE clause as a Postgres JOIN through the dimension tables.
    # We use a SQL string here because Supabase's Python query builder gets
    # awkward with multi-table joins and group_by. The string is fully
    # parameterized — no injection risk.
    valid_group_by = {"company", "university", "industry", "role_category"}
    if group_by not in valid_group_by:
        group_by = "company"

    # Map the group_by to the actual column expression
    group_col = {
        "company":       "c.display_name",
        "university":    "u.display_name",
        "industry":      "c.industry_slug",
        "role_category": "i.role_category",
    }[group_by]

    # Build filter clauses
    filters = []
    params = {"p_year": year, "p_limit": limit}

    if university:
        filters.append("(u.display_name ilike :p_university or u.slug = :p_university_slug)")
        params["p_university"] = university
        params["p_university_slug"] = _slugify(university)

    if company:
        filters.append("(c.display_name ilike :p_company or c.slug = :p_company_slug)")
        params["p_company"] = company
        params["p_company_slug"] = _slugify(company)

    if industry:
        filters.append("c.industry_slug = :p_industry")
        params["p_industry"] = industry

    if role_category:
        filters.append("i.role_category = :p_role")
        params["p_role"] = role_category

    where_clause = " and ".join(["i.year = :p_year"] + filters)

    # Use the dedicated RPC `tic_filter_internships` defined in schema.sql
    # (we'll add this RPC below). RPC keeps logic in Postgres so the network
    # round-trip is one call, and lets us define indexes on the underlying joins.
    res = _sb().rpc(
        "tic_filter_internships",
        {
            "p_university":    params.get("p_university"),
            "p_company":       params.get("p_company"),
            "p_industry":      params.get("p_industry"),
            "p_role_category": params.get("p_role"),
            "p_year":          year,
            "p_group_by":      group_by,
            "p_limit":         limit,
        }
    ).execute()

    rows = res.data or []
    total = sum(r["count"] for r in rows)

    return {
        "filters": {
            "university":    university,
            "company":       company,
            "industry":      industry,
            "role_category": role_category,
            "year":          year,
        },
        "group_by": group_by,
        "total_internships": total,
        "rows": rows,
    }


# ════════════════════════════════════════════════════════════════════════════
# TOOL 2: compare_companies
# Head-to-head pipeline comparison.
# ════════════════════════════════════════════════════════════════════════════

def compare_companies(
    companies: list[str],
    year: int = 2024,
    top_n_universities: int = 10,
) -> dict:
    """
    Compare two or more companies' top feeder universities side-by-side.

    Examples Claude might invoke this for:
      - "Compare Stripe and Plaid's hiring"
        → compare_companies(["Stripe", "Plaid"])
      - "Where does Citadel hire from that Two Sigma doesn't?"
        → compare_companies(["Citadel", "Two Sigma"])

    Args:
        companies:           List of company display names or slugs (2+).
        year:                Year to compare. Default 2024.
        top_n_universities:  How many universities per company to include.

    Returns:
        {
          "year": 2024,
          "companies": ["Stripe", "Plaid"],
          "comparison": [
            {
              "university": "Stanford",
              "Stripe": 9,
              "Plaid": 5
            },
            {
              "university": "MIT",
              "Stripe": 7,
              "Plaid": 4
            },
            ...
          ],
          "summary": {
            "Stripe": {"total": 39, "unique_universities": 7},
            "Plaid":  {"total": 20, "unique_universities": 5}
          }
        }
    """
    if len(companies) < 2:
        return {"error": "compare_companies requires at least 2 companies"}

    res = _sb().rpc(
        "tic_compare_companies",
        {
            "p_companies": companies,
            "p_year":      year,
            "p_top_n":     top_n_universities,
        }
    ).execute()

    return res.data or {"comparison": [], "summary": {}}


# ════════════════════════════════════════════════════════════════════════════
# TOOL 3: find_similar_schools  ★ the magic
# Pipeline gap analysis — Talantis's signature insight.
# ════════════════════════════════════════════════════════════════════════════

def find_similar_schools(
    reference_company: str,
    peer_companies: list[str],
    year: int = 2024,
    limit: int = 8,
) -> dict:
    """
    The "Pipeline Intelligence" tool. Find universities that peer companies
    recruit heavily from, but the reference company recruits less from.
    These are the "hidden coastlines" Atlas can guide the user toward.

    Algorithm (in plain English):
      1. For each peer, count interns per university.
      2. Sum those counts across all peers — call this `peer_signal`.
      3. For the reference, count interns per university — call this `ref_signal`.
      4. Compute `gap = peer_signal - ref_signal` (clamped at 0).
      5. Sort by gap descending. Return the top N.

    A high gap means: peers are recruiting heavily from this school, but the
    reference company is not. That's a "hidden island."

    Examples Claude might invoke this for:
      - "We're Stripe — where are Plaid and Brex finding talent we're missing?"
        → find_similar_schools("Stripe", ["Plaid", "Brex", "Ramp"])
      - "Which schools should an AI startup recruit from that we don't already?"
        → find_similar_schools("Anthropic", ["OpenAI", "Scale AI"])

    Args:
        reference_company:  The company asking the question.
        peer_companies:     Companies whose hiring patterns we use as a benchmark.
        year:               Year to analyze. Default 2024.
        limit:              How many "hidden" schools to return. Default 8.

    Returns:
        {
          "reference_company": "Stripe",
          "peer_companies": ["Plaid", "Brex", "Ramp"],
          "year": 2024,
          "hidden_pipelines": [
            {
              "university": "UPenn",
              "peer_intern_count": 9,
              "reference_intern_count": 0,
              "gap": 9,
              "interpretation": "Peers hire heavily; you don't recruit here."
            },
            ...
          ]
        }
    """
    res = _sb().rpc(
        "tic_find_similar_schools",
        {
            "p_reference_company": reference_company,
            "p_peer_companies":    peer_companies,
            "p_year":              year,
            "p_limit":             limit,
        }
    ).execute()

    return res.data or {"hidden_pipelines": []}


# ════════════════════════════════════════════════════════════════════════════
# Helper: tolerant slug normalization
# Accepts "UC Berkeley", "uc-berkeley", "UC-Berkeley" → "uc-berkeley"
# ════════════════════════════════════════════════════════════════════════════

def _slugify(s: str) -> str:
    if not s:
        return s
    return s.lower().replace(" ", "-").replace("_", "-")


# ════════════════════════════════════════════════════════════════════════════
# Tool schemas — fed to Claude via the messages.create(tools=[...]) parameter.
# Claude reads these descriptions to decide which tool to call and with what
# arguments. Write the descriptions clearly — they are essentially documentation
# Claude reads at inference time.
# ════════════════════════════════════════════════════════════════════════════

TOOL_DEFINITIONS = [
    {
        "name": "filter_internships",
        "description": (
            "Count internships matching given filters, grouped by a dimension. "
            "Use this for direct factual questions like 'how many UCLA students interned at Stripe?' "
            "or 'show me Snap's top feeder schools'. This is the right tool whenever the user "
            "wants a count, list, or ranking of internships filtered on a specific axis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "university":    {"type": "string", "description": "University display name or slug, e.g. 'UCLA' or 'uc-berkeley'."},
                "company":       {"type": "string", "description": "Company display name or slug, e.g. 'Stripe'."},
                "industry":      {"type": "string", "description": "Industry slug, e.g. 'fintech', 'big-tech', 'ai-research'."},
                "role_category": {"type": "string", "enum": ["SWE", "PM", "Data", "Design", "Research", "Business", "Other"]},
                "year":          {"type": "integer", "description": "Year. Default 2024."},
                "group_by":      {"type": "string", "enum": ["company", "university", "industry", "role_category"], "description": "Dimension to group results by. Default 'company'."},
                "limit":         {"type": "integer", "description": "Max rows. Default 15."}
            },
        },
    },
    {
        "name": "compare_companies",
        "description": (
            "Compare 2+ companies' top feeder universities side-by-side. Use this when the user "
            "wants a head-to-head view, e.g. 'compare Stripe and Plaid's hiring' or 'where does "
            "Citadel pull from that Two Sigma doesn't?'. Returns a unified table with one row per "
            "university and one column per company."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "companies":          {"type": "array", "items": {"type": "string"}, "description": "Company display names or slugs. At least 2."},
                "year":               {"type": "integer", "description": "Year. Default 2024."},
                "top_n_universities": {"type": "integer", "description": "Max universities per company. Default 10."}
            },
            "required": ["companies"],
        },
    },
    {
        "name": "find_similar_schools",
        "description": (
            "★ Talantis's signature insight. Find universities that PEER companies recruit heavily "
            "from but the REFERENCE company does not. Use this when the user asks 'where are my "
            "competitors finding talent that I'm missing?' or 'what hidden pipelines should I tap?'. "
            "Returns universities ranked by 'gap' = peer_signal - reference_signal."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reference_company": {"type": "string", "description": "The company asking. E.g. 'Stripe'."},
                "peer_companies":    {"type": "array", "items": {"type": "string"}, "description": "Competitor companies. E.g. ['Plaid', 'Brex', 'Ramp']."},
                "year":              {"type": "integer", "description": "Year. Default 2024."},
                "limit":             {"type": "integer", "description": "Max hidden schools to return. Default 8."}
            },
            "required": ["reference_company", "peer_companies"],
        },
    },
]


# ════════════════════════════════════════════════════════════════════════════
# Dispatch — called by the Atlas orchestrator when Claude returns a tool_use
# ════════════════════════════════════════════════════════════════════════════

TOOL_REGISTRY = {
    "filter_internships":   filter_internships,
    "compare_companies":    compare_companies,
    "find_similar_schools": find_similar_schools,
}


def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Look up a tool by name and execute it with the provided arguments."""
    fn = TOOL_REGISTRY.get(tool_name)
    if fn is None:
        return {"error": f"Unknown tool: {tool_name}"}
    try:
        return fn(**tool_input)
    except TypeError as e:
        # Bad argument shape — Claude usually self-corrects on the next turn
        return {"error": f"Bad arguments for {tool_name}: {e}"}
    except Exception as e:
        return {"error": f"{tool_name} failed: {e}"}
