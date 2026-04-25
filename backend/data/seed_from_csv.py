"""
Talantis · Supabase Seeder
==========================

Loads the generated CSV files into Supabase Postgres, in the correct order:
  1. industries     (no dependencies)
  2. universities   (no dependencies)
  3. companies      (depends on industries)
  4. internships    (depends on companies + universities)
  5. refresh materialized views

Usage:
  Make sure backend/.env has SUPABASE_URL and SUPABASE_KEY set.
  Then run from the project root:

    python backend/data/seed_from_csv.py

Notes:
  - Idempotent: clears existing data before re-inserting.
  - Skips materialized view refresh if the RPC isn't available (won't crash).
  - Inserts internships in batches of 200 to stay within Supabase request limits.
"""
import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent  # CSVs live alongside this script
BATCH_SIZE = 200

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")

client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def read_csv(filename):
    """Read a CSV file from DATA_DIR and return a list of dicts."""
    path = DATA_DIR / filename
    if not path.exists():
        sys.exit(f"ERROR: missing {path}. Run build_dataset.py first.")
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def insert_batch(table, rows, batch_size=BATCH_SIZE):
    """Insert rows in batches to stay within Supabase's request size limits."""
    total = len(rows)
    for start in range(0, total, batch_size):
        batch = rows[start : start + batch_size]
        client.table(table).insert(batch).execute()
        end = min(start + batch_size, total)
        print(f"    {end}/{total}")


def coerce_internship(row):
    """Convert string CSV values into the right Postgres types."""
    return {
        "student_hash":    row["student_hash"],
        "company_slug":    row["company_slug"],
        "university_slug": row["university_slug"],
        "role_title":      row["role_title"],
        "role_category":   row["role_category"],
        "year":            int(row["year"]),
        "season":          row["season"],
        "source":          row["source"],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Main flow
# ──────────────────────────────────────────────────────────────────────────────

def clear_existing():
    print("Clearing existing data...")
    # Order matters: delete child tables first to satisfy FK constraints
    client.table("internships").delete().gte("id", 0).execute()
    client.table("companies").delete().neq("slug", "").execute()
    client.table("universities").delete().neq("slug", "").execute()
    client.table("industries").delete().neq("slug", "").execute()


def seed_industries():
    rows = read_csv("industries.csv")
    print(f"Seeding industries... ({len(rows)} rows)")
    client.table("industries").insert(rows).execute()


def seed_universities():
    rows = read_csv("universities.csv")
    print(f"Seeding universities... ({len(rows)} rows)")
    client.table("universities").insert(rows).execute()


def seed_companies():
    rows = read_csv("companies.csv")
    print(f"Seeding companies... ({len(rows)} rows)")
    client.table("companies").insert(rows).execute()


def seed_internships():
    rows = [coerce_internship(r) for r in read_csv("internships.csv")]
    print(f"Seeding internships... ({len(rows)} rows in batches of {BATCH_SIZE})")
    insert_batch("internships", rows)


def refresh_views():
    """Refresh materialized views. Skips silently if RPC isn't set up."""
    print("Refreshing materialized views...")
    try:
        client.rpc("refresh_materialized_views", {}).execute()
        print("  ✓ refreshed")
    except Exception as e:
        print(f"  ⚠  skipped (RPC not registered): {e}")
        print("     If you have materialized views, run this SQL manually in Supabase:")
        print("       refresh materialized view mv_company_counts_by_uni;")
        print("       refresh materialized view mv_university_counts_by_company;")


def main():
    print("─" * 60)
    print("Talantis · Supabase Seeder")
    print("─" * 60)
    clear_existing()
    seed_industries()
    seed_universities()
    seed_companies()
    seed_internships()
    refresh_views()
    print("─" * 60)
    print("Done.")


if __name__ == "__main__":
    main()
