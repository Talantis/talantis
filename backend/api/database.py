"""
database.py — frontend data fetchers.

Only handles the bar chart and university dropdown endpoints. Atlas's tool-use
loop pulls its own data via tools.py, so we no longer need get_all_data_summary().
"""

import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()
_sb: Client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def get_universities() -> list[str]:
    """Return all university display names, alphabetized. Used by the filter dropdown."""
    res = _sb.rpc("get_universities_list", {}).execute()
    return [r["display_name"] for r in res.data]


def get_intern_data(university: str | None = None) -> list[dict]:
    """
    Return intern counts per company for the bar chart.
    Optionally filtered to a single university.
    """
    res = _sb.rpc(
        "get_company_counts",
        {"p_university": university, "p_year": 2024}
    ).execute()
    return res.data
