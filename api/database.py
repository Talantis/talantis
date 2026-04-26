"""
database.py — frontend data fetchers.

Only handles the bar chart and university dropdown endpoints. Atlas's tool-use
loop pulls its own data via tools.py, so we no longer need get_all_data_summary().

The Supabase client is LAZY — created on first call rather than at module import.
This means a missing env var raises a clean error message instead of crashing
the whole function during cold start (which on Vercel manifests as a useless
500 with no helpful logs because the function never even starts).
"""

import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

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


def get_universities() -> list[str]:
    """Return all university display names, alphabetized. Used by the filter dropdown."""
    res = _sb().rpc("get_universities_list", {}).execute()
    return [r["display_name"] for r in res.data]


CHART_YEARS = [2021, 2022, 2023, 2024, 2025]


def get_intern_data(
    university: str | None = None,
    year: int | None = None,
) -> list[dict]:
    """
    Return intern counts per company for the bar chart.
    Optionally filtered to a single university and/or year.
    When year is None, counts are aggregated across CHART_YEARS.
    """
    if year is not None:
        res = _sb().rpc(
            "get_company_counts",
            {"p_university": university, "p_year": year},
        ).execute()
        return res.data

    aggregated: dict[str, dict] = {}
    for y in CHART_YEARS:
        res = _sb().rpc(
            "get_company_counts",
            {"p_university": university, "p_year": y},
        ).execute()
        for row in res.data or []:
            company = row.get("company")
            if not company:
                continue
            entry = aggregated.get(company)
            if entry is None:
                aggregated[company] = {**row}
            else:
                entry["intern_count"] = (
                    (entry.get("intern_count") or 0)
                    + (row.get("intern_count") or 0)
                )

    return sorted(
        aggregated.values(),
        key=lambda r: r.get("intern_count") or 0,
        reverse=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Submission pipeline
# ──────────────────────────────────────────────────────────────────────────────

OFFER_LETTERS_BUCKET = "offer-letters"


def _lookup_slug(table: str, display_name: str) -> str | None:
    res = _sb().table(table).select("slug").eq("display_name", display_name).execute()
    return res.data[0]["slug"] if res.data else None


def slug_for_university(display_name: str) -> str | None:
    return _lookup_slug("universities", display_name)


def slug_for_company(display_name: str) -> str | None:
    return _lookup_slug("companies", display_name)


def upload_offer_letter(path: str, content: bytes, content_type: str) -> str:
    """Upload to Supabase Storage and return the public URL."""
    sb = _sb()
    sb.storage.from_(OFFER_LETTERS_BUCKET).upload(
        path, content, {"content-type": content_type}
    )
    return sb.storage.from_(OFFER_LETTERS_BUCKET).get_public_url(path)


def insert_internship(row: dict) -> None:
    """Insert a single internship row and refresh materialized views."""
    sb = _sb()
    sb.table("internships").insert(row).execute()
    try:
        sb.rpc("refresh_materialized_views", {}).execute()
    except Exception:
        # If the RPC isn't registered the chart will still pick the row up
        # next time the views are refreshed manually.
        pass
