"""
Generate Carnegie Mellon internship rows by modeling on MIT's existing
distribution (peer-tier CS school) with ±15% jitter so the data isn't an
identical clone. Appends rows to internships.csv in place.

Usage:
    python data/add_cmu_data.py

After running, re-seed Supabase to push the new rows:
    python data/seed_from_csv.py
"""
import csv
import hashlib
import random
from collections import defaultdict
from pathlib import Path

CSV_PATH = Path(__file__).parent / "internships.csv"
SOURCE_UNI = "mit"
TARGET_UNI = "carnegie-mellon"
JITTER_LO = 0.80
JITTER_HI = 1.15
SEED = 1729

rng = random.Random(SEED)


def main():
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if any(r["university_slug"] == TARGET_UNI for r in rows):
        print(f"⚠  {TARGET_UNI} rows already present in {CSV_PATH.name}. Aborting.")
        return

    # Group MIT rows by (company, year, season) so we can scale per-cohort
    mit_groups = defaultdict(list)
    for r in rows:
        if r["university_slug"] == SOURCE_UNI:
            mit_groups[(r["company_slug"], r["year"], r["season"])].append(r)

    new_rows = []
    counter = 0
    for (company, year, season), templates in mit_groups.items():
        scaled = max(1, int(len(templates) * rng.uniform(JITTER_LO, JITTER_HI)))
        for _ in range(scaled):
            template = rng.choice(templates)
            row = template.copy()
            row["university_slug"] = TARGET_UNI
            key = f"talantis-{TARGET_UNI}-{company}-{counter}-{year}"
            row["student_hash"] = hashlib.sha256(key.encode()).hexdigest()[:16]
            row["source"] = "synthetic"
            new_rows.append(row)
            counter += 1

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerows(new_rows)

    by_year = defaultdict(int)
    by_company = defaultdict(int)
    for r in new_rows:
        by_year[r["year"]] += 1
        by_company[r["company_slug"]] += 1

    print(f"✓ Appended {len(new_rows)} {TARGET_UNI} rows to {CSV_PATH.name}")
    print("\nBy year:")
    for y in sorted(by_year):
        print(f"  {y}  {by_year[y]:>4}")
    print(f"\nTop 10 companies:")
    for c, n in sorted(by_company.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {c:<20} {n:>3}")


if __name__ == "__main__":
    main()
