"""
Talent Intelligence Core
========================

Six tools that Atlas can call to answer questions about the internship dataset.
Three serve recruiters, three serve students — but they share the same dataset
and the same dispatcher.

The six tools, by audience and complexity:

  RECRUITERS (companies asking about talent pipelines):
    1. filter_internships          — direct factual queries
    2. compare_companies           — head-to-head competitive intel
    3. find_similar_schools        — pipeline gap analysis ("hidden coastlines")

  STUDENTS (asking about their realistic career options):
    4. find_target_companies       — companies tiered by realism for the student
    5. analyze_school_at_company   — school's track record at a specific company
    6. discover_career_paths       — paths students like you take ("hidden pathways")

The two sets mirror each other in shape. Recruiters get pipeline analysis;
students get pathway analysis. Same data, opposite vantage.

Each function:
  - Takes structured arguments (which Claude generates as tool_use JSON)
  - Executes Postgres queries via dedicated tic_* RPC functions
  - Returns a JSON-serializable dict that Claude can reason about

These tools are called BOTH by:
  - The web frontend (via /api/insights)
  - The Fetch.ai uAgent (via Chat Protocol → same FastAPI endpoint)

This is the "one Atlas, two front doors, two audiences" architecture.
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
# Helper: tolerant slug normalization
# ════════════════════════════════════════════════════════════════════════════

def _slugify(s: str) -> str:
    if not s:
        return s
    return s.lower().replace(" ", "-").replace("_", "-")


# ════════════════════════════════════════════════════════════════════════════
# RECRUITER TOOLS (existing — unchanged in shape)
# ════════════════════════════════════════════════════════════════════════════

# ---------------------------------------------------------------------------
# TOOL 1: filter_internships
# ---------------------------------------------------------------------------

def filter_internships(
    university: Optional[str] = None,
    company: Optional[str] = None,
    industry: Optional[str] = None,
    role_category: Optional[str] = None,
    year: int = 2024,
    group_by: str = "company",
    limit: int = 15,
) -> dict:
    """Count internships matching the given filters, grouped by a chosen dimension."""
    valid_group_by = {"company", "university", "industry", "role_category"}
    if group_by not in valid_group_by:
        group_by = "company"

    res = _sb().rpc(
        "tic_filter_internships",
        {
            "p_university":    university,
            "p_company":       company,
            "p_industry":      industry,
            "p_role_category": role_category,
            "p_year":          year,
            "p_group_by":      group_by,
            "p_limit":         limit,
        }
    ).execute()

    rows = res.data or []
    total = sum(r.get("count", 0) for r in rows)

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


# ---------------------------------------------------------------------------
# TOOL 2: compare_companies
# ---------------------------------------------------------------------------

def compare_companies(
    companies: list[str],
    year: int = 2024,
    top_n_universities: int = 10,
) -> dict:
    """Compare two or more companies' top feeder universities side-by-side."""
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


# ---------------------------------------------------------------------------
# TOOL 3: find_similar_schools  ★ recruiter-side magic
# ---------------------------------------------------------------------------

def find_similar_schools(
    reference_company: str,
    peer_companies: list[str],
    year: int = 2024,
    limit: int = 8,
) -> dict:
    """Pipeline gap analysis. Find universities peers recruit from but you don't."""
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
# STUDENT TOOLS (new)
# ════════════════════════════════════════════════════════════════════════════

# ---------------------------------------------------------------------------
# TOOL 4: find_target_companies
# Direct student factual: "what should I apply to?"
# ---------------------------------------------------------------------------

def find_target_companies(
    university: str,
    industry: Optional[str] = None,
    role_category: Optional[str] = None,
    year: int = 2024,
    limit: int = 15,
) -> dict:
    """
    Tier companies by realism for a given student's school + interests.

    Examples Claude might invoke this for:
      - "I'm at UCLA, what AI startups should I apply to?"
        → find_target_companies(university="UCLA", industry="ai-research")
      - "What companies actually hire CS students from my school?"
        → find_target_companies(university="UCSD", role_category="SWE")

    Tiers returned:
      - "strong-fit"  — your school placed 3+ here this year
      - "realistic"   — your school placed 1-2
      - "reach"       — your school placed 0, but comparable schools placed 2+

    Args:
        university:    Student's school (display name or slug). REQUIRED.
        industry:      Optional filter, e.g. "fintech", "ai-research".
        role_category: Optional, e.g. "SWE", "Data".
        year:          Default 2024.
        limit:         Max companies returned. Default 15.

    Returns:
        {
          "university": "UCLA",
          "filters": {...},
          "year": 2024,
          "tiers": {
            "strong-fit": [{"company": "Snap", "intern_count": 8, "reasoning": "..."}],
            "realistic":  [...],
            "reach":      [...]
          },
          "summary": {
            "strong_fit_count": 3,
            "realistic_count": 5,
            "reach_count": 7
          }
        }
    """
    res = _sb().rpc(
        "tic_find_target_companies",
        {
            "p_university":    university,
            "p_industry":      industry,
            "p_role_category": role_category,
            "p_year":          year,
            "p_limit":         limit,
        }
    ).execute()

    rows = res.data or []

    # Bucket rows by tier so Claude can reason about them as groups, not a flat list
    tiers = {"strong-fit": [], "realistic": [], "reach": [], "unmapped": []}
    for r in rows:
        tier = r.get("tier", "unmapped")
        tiers.setdefault(tier, []).append({
            "company":      r.get("company"),
            "industry":     r.get("industry"),
            "intern_count": r.get("intern_count", 0),
            "reasoning":    r.get("reasoning"),
        })

    return {
        "university": university,
        "filters": {
            "industry":      industry,
            "role_category": role_category,
            "year":          year,
        },
        "year": year,
        "tiers": tiers,
        "summary": {
            "strong_fit_count": len(tiers["strong-fit"]),
            "realistic_count":  len(tiers["realistic"]),
            "reach_count":      len(tiers["reach"]),
            "total":            len(rows),
        },
    }


# ---------------------------------------------------------------------------
# TOOL 5: analyze_school_at_company
# Student-side comparison: "how does my school stack up at Stripe?"
# ---------------------------------------------------------------------------

def analyze_school_at_company(
    university: str,
    company: str,
    year: int = 2024,
) -> dict:
    """
    The student's school × specific company analysis.

    Examples Claude might invoke this for:
      - "How does USC do at Stripe?"
        → analyze_school_at_company(university="USC", company="Stripe")
      - "Is my school competitive at Citadel?"
        → analyze_school_at_company(university="Berkeley", company="Citadel")

    Returns:
        {
          "university": "USC",
          "company": "Stripe",
          "year": 2024,
          "school_placements": 2,
          "school_rank": 7,            # rank among all schools placing at Stripe
          "company_total": 38,         # total interns at Stripe this year
          "top_schools_at_company": [
            {"university": "Stanford", "count": 9},
            ...
          ],
          "peer_school_performance": [
            {"university": "UCLA",    "count": 4},
            {"university": "UCSD",    "count": 3},
            ...
          ]
        }
    """
    res = _sb().rpc(
        "tic_analyze_school_at_company",
        {
            "p_university": university,
            "p_company":    company,
            "p_year":       year,
        }
    ).execute()

    return res.data or {"error": "no data"}


# ---------------------------------------------------------------------------
# TOOL 6: discover_career_paths  ★ student-side magic
# Mirror of find_similar_schools — pathway discovery
# ---------------------------------------------------------------------------

def discover_career_paths(
    university: str,
    role_category: Optional[str] = None,
    industry: Optional[str] = None,
    year: int = 2024,
    limit: int = 12,
) -> dict:
    """
    Discover the realistic career paths for students like the user.

    This is the student-side mirror of find_similar_schools. Given a student's
    school + optional interest area, returns:

      - direct_paths: companies the student's own school has placed at
      - peer_paths:   companies that comparable schools place at, but the
                      student's school hasn't (or has placed fewer at)

    Peer paths surface non-obvious "stepping stone" companies — places where
    students from similar schools have built careers, even if the student's
    own school doesn't have a strong precedent.

    Examples Claude might invoke this for:
      - "I'm at UC Davis, where do students like me end up in tech?"
        → discover_career_paths(university="UC Davis", role_category="SWE")
      - "I want to break into AI but my school doesn't have many AI alums.
         Where do students from comparable schools land?"
        → discover_career_paths(university="USC", industry="ai-research")

    Args:
        university:     The student's school. REQUIRED.
        role_category:  Optional, e.g. "SWE".
        industry:       Optional, e.g. "fintech".
        year:           Default 2024.
        limit:          Max companies per category. Default 12.

    Returns:
        {
          "university": "UC Davis",
          "role_category": "SWE",
          "industry": null,
          "year": 2024,
          "direct_paths": [
            {"company": "Apple", "count": 5, "path_type": "direct"},
            ...
          ],
          "peer_paths": [
            {
              "company": "Stripe",
              "count": 12,                 # placements from peers
              "peer_schools": 4,           # how many peer schools placed there
              "your_school": 0,            # your school's count
              "path_type": "peer"
            },
            ...
          ]
        }
    """
    res = _sb().rpc(
        "tic_discover_career_paths",
        {
            "p_university":    university,
            "p_role_category": role_category,
            "p_industry":      industry,
            "p_year":          year,
            "p_limit":         limit,
        }
    ).execute()

    return res.data or {"direct_paths": [], "peer_paths": []}


# ════════════════════════════════════════════════════════════════════════════
# Tool schemas for Claude
# ════════════════════════════════════════════════════════════════════════════

TOOL_DEFINITIONS = [
    # ── Recruiter tools ─────────────────────────────────────────────────────
    {
        "name": "filter_internships",
        "description": (
            "Count internships matching given filters, grouped by a dimension. "
            "Use for direct factual questions like 'how many UCLA students interned at Stripe?' "
            "or 'show me Snap's top feeder schools'. Works for both recruiter and student "
            "framings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "university":    {"type": "string", "description": "University display name or slug."},
                "company":       {"type": "string", "description": "Company display name or slug."},
                "industry":      {"type": "string", "description": "Industry slug, e.g. 'fintech'."},
                "role_category": {"type": "string", "enum": ["SWE", "PM", "Data", "Design", "Research", "Business", "Other"]},
                "year":          {"type": "integer", "description": "Year. Default 2024."},
                "group_by":      {"type": "string", "enum": ["company", "university", "industry", "role_category"]},
                "limit":         {"type": "integer", "description": "Max rows. Default 15."},
            },
        },
    },
    {
        "name": "compare_companies",
        "description": (
            "Compare 2+ companies' top feeder universities side-by-side. Recruiter-oriented. "
            "Use when someone wants a head-to-head view, e.g. 'compare Stripe and Plaid' or "
            "'where does Citadel pull from that Two Sigma doesn't?'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "companies":          {"type": "array", "items": {"type": "string"}, "description": "Company names. At least 2."},
                "year":               {"type": "integer", "description": "Year. Default 2024."},
                "top_n_universities": {"type": "integer", "description": "Max universities. Default 10."},
            },
            "required": ["companies"],
        },
    },
    {
        "name": "find_similar_schools",
        "description": (
            "★ RECRUITER-SIDE MAGIC. Find universities that PEER companies recruit from but the "
            "REFERENCE company doesn't. Use when a recruiter asks about hidden pipelines, "
            "e.g. 'where are competitors finding talent we're missing?'. NOT for student questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reference_company": {"type": "string", "description": "The company asking."},
                "peer_companies":    {"type": "array", "items": {"type": "string"}, "description": "Competitor companies."},
                "year":              {"type": "integer", "description": "Year. Default 2024."},
                "limit":             {"type": "integer", "description": "Max hidden schools. Default 8."},
            },
            "required": ["reference_company", "peer_companies"],
        },
    },
    # ── Student tools ───────────────────────────────────────────────────────
    {
        "name": "find_target_companies",
        "description": (
            "Tier companies by realism for a student. Use when a student asks 'where should I "
            "apply?' or 'what companies hire from my school?'. Returns companies bucketed into "
            "strong-fit / realistic / reach based on their school's actual placement history."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "university":    {"type": "string", "description": "The student's school. REQUIRED."},
                "industry":      {"type": "string", "description": "Optional filter, e.g. 'fintech'."},
                "role_category": {"type": "string", "enum": ["SWE", "PM", "Data", "Design", "Research", "Business", "Other"]},
                "year":          {"type": "integer", "description": "Year. Default 2024."},
                "limit":         {"type": "integer", "description": "Max companies. Default 15."},
            },
            "required": ["university"],
        },
    },
    {
        "name": "analyze_school_at_company",
        "description": (
            "Analyze how a student's school stacks up at a specific company. Use when a student "
            "asks 'is my school competitive at Stripe?' or 'how does USC do at Citadel?'. Returns "
            "the school's placement count, rank, and how comparable peer schools fared at the "
            "same company."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "university": {"type": "string", "description": "Student's school. REQUIRED."},
                "company":    {"type": "string", "description": "Target company. REQUIRED."},
                "year":       {"type": "integer", "description": "Year. Default 2024."},
            },
            "required": ["university", "company"],
        },
    },
    {
        "name": "discover_career_paths",
        "description": (
            "★ STUDENT-SIDE MAGIC. Discover where students like the user typically end up. "
            "Returns 'direct paths' (companies your school has placed at) AND 'peer paths' "
            "(non-obvious companies that comparable schools have placed at but yours hasn't yet). "
            "Use when a student asks 'where do students like me end up?' or 'I want to break into "
            "<industry> but my school doesn't have many alums there — where else should I look?'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "university":    {"type": "string", "description": "The student's school. REQUIRED."},
                "role_category": {"type": "string", "enum": ["SWE", "PM", "Data", "Design", "Research", "Business", "Other"]},
                "industry":      {"type": "string", "description": "Optional, e.g. 'ai-research'."},
                "year":          {"type": "integer", "description": "Year. Default 2024."},
                "limit":         {"type": "integer", "description": "Max companies per category. Default 12."},
            },
            "required": ["university"],
        },
    },
]


# ════════════════════════════════════════════════════════════════════════════
# Dispatch
# ════════════════════════════════════════════════════════════════════════════

TOOL_REGISTRY = {
    # recruiter
    "filter_internships":         filter_internships,
    "compare_companies":          compare_companies,
    "find_similar_schools":       find_similar_schools,
    # student
    "find_target_companies":      find_target_companies,
    "analyze_school_at_company":  analyze_school_at_company,
    "discover_career_paths":      discover_career_paths,
}


def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Look up a tool by name and execute it with the provided arguments."""
    fn = TOOL_REGISTRY.get(tool_name)
    if fn is None:
        return {"error": f"Unknown tool: {tool_name}"}
    try:
        return fn(**tool_input)
    except TypeError as e:
        return {"error": f"Bad arguments for {tool_name}: {e}"}
    except Exception as e:
        return {"error": f"{tool_name} failed: {e}"}
