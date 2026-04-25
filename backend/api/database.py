import json
import os

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
_sb: Client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def get_universities() -> list[str]:
    res = _sb.rpc("get_universities_list", {}).execute()
    return [r["display_name"] for r in res.data]


def get_intern_data(university: str | None = None) -> list[dict]:
    res = _sb.rpc("get_company_counts", {"p_university": university, "p_year": 2024}).execute()
    return res.data


def get_all_data_summary() -> str:
    res = _sb.rpc("get_data_summary", {"p_year": 2024}).execute()
    return json.dumps(res.data) if res.data else "[]"
