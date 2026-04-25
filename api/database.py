import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "talantis.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_universities() -> list[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT university FROM internships ORDER BY university"
        ).fetchall()
    return [r["university"] for r in rows]


def get_intern_data(university: str | None = None) -> list[dict]:
    query = """
        SELECT
            c.name        AS company,
            c.logo_url    AS logo_url,
            c.industry    AS industry,
            i.university  AS university,
            SUM(i.count)  AS intern_count
        FROM internships i
        JOIN companies c ON c.id = i.company_id
    """
    params: list = []
    if university:
        query += " WHERE i.university = ?"
        params.append(university)
    query += " GROUP BY c.id, i.university ORDER BY intern_count DESC"

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_all_data_summary() -> str:
    """Return a compact JSON string of all internship counts for AI context."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT c.name AS company, i.university, SUM(i.count) AS total
            FROM internships i JOIN companies c ON c.id = i.company_id
            GROUP BY c.id, i.university
            ORDER BY total DESC
            """
        ).fetchall()
    import json
    return json.dumps([dict(r) for r in rows])
