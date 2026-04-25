"""Run once locally: python data/seed.py"""

import os
import sqlite3
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "talantis.db")

COMPANIES = [
    ("Google",     "https://logo.clearbit.com/google.com",     "Tech"),
    ("Meta",       "https://logo.clearbit.com/meta.com",       "Tech"),
    ("Apple",      "https://logo.clearbit.com/apple.com",      "Tech"),
    ("Amazon",     "https://logo.clearbit.com/amazon.com",     "E-Commerce"),
    ("Microsoft",  "https://logo.clearbit.com/microsoft.com",  "Tech"),
    ("Netflix",    "https://logo.clearbit.com/netflix.com",    "Entertainment"),
    ("Uber",       "https://logo.clearbit.com/uber.com",       "Mobility"),
    ("Airbnb",     "https://logo.clearbit.com/airbnb.com",     "Travel"),
    ("Stripe",     "https://logo.clearbit.com/stripe.com",     "Fintech"),
    ("Lyft",       "https://logo.clearbit.com/lyft.com",       "Mobility"),
    ("Salesforce", "https://logo.clearbit.com/salesforce.com", "Enterprise"),
    ("Adobe",      "https://logo.clearbit.com/adobe.com",      "Creative"),
    ("Nvidia",     "https://logo.clearbit.com/nvidia.com",     "Semiconductors"),
    ("LinkedIn",   "https://logo.clearbit.com/linkedin.com",   "Social"),
    ("Figma",      "https://logo.clearbit.com/figma.com",      "Design"),
    ("Notion",     "https://logo.clearbit.com/notion.so",      "Productivity"),
    ("Palantir",   "https://logo.clearbit.com/palantir.com",   "Data"),
    ("SpaceX",     "https://logo.clearbit.com/spacex.com",     "Aerospace"),
    ("Roblox",     "https://logo.clearbit.com/roblox.com",     "Gaming"),
    ("Snap",       "https://logo.clearbit.com/snap.com",       "Social"),
]

UNIVERSITIES = [
    "UCLA",
    "Stanford",
    "UC Berkeley",
    "MIT",
    "Carnegie Mellon",
    "Georgia Tech",
    "UIUC",
    "USC",
    "UT Austin",
    "UW Seattle",
]

# Bias certain school→company pipelines to make the data interesting
PIPELINE_BOOST = {
    ("Stanford",        "Google"):    35,
    ("Stanford",        "Apple"):     28,
    ("UC Berkeley",     "Google"):    30,
    ("UC Berkeley",     "Meta"):      25,
    ("MIT",             "Microsoft"): 30,
    ("MIT",             "Amazon"):    20,
    ("Carnegie Mellon", "Meta"):      22,
    ("Carnegie Mellon", "Nvidia"):    18,
    ("UCLA",            "Amazon"):    15,
    ("UCLA",            "Netflix"):   14,
    ("USC",             "Snap"):      18,
    ("USC",             "Roblox"):    12,
    ("Georgia Tech",    "Microsoft"): 16,
    ("Georgia Tech",    "Palantir"):  12,
    ("UIUC",            "Amazon"):    14,
    ("UIUC",            "Salesforce"):10,
    ("UW Seattle",      "Amazon"):    26,
    ("UW Seattle",      "Microsoft"): 22,
    ("UT Austin",       "SpaceX"):    14,
    ("UT Austin",       "Lyft"):      10,
}

random.seed(42)

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
conn.executescript("""
    CREATE TABLE companies (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        name      TEXT NOT NULL,
        logo_url  TEXT,
        industry  TEXT
    );
    CREATE TABLE internships (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL REFERENCES companies(id),
        university TEXT NOT NULL,
        year       INTEGER NOT NULL,
        count      INTEGER NOT NULL
    );
""")

company_id = {}
for name, logo, industry in COMPANIES:
    cur = conn.execute(
        "INSERT INTO companies (name, logo_url, industry) VALUES (?, ?, ?)",
        (name, logo, industry),
    )
    company_id[name] = cur.lastrowid

for uni in UNIVERSITIES:
    for name, _, _ in COMPANIES:
        base = random.randint(2, 8)
        boost = PIPELINE_BOOST.get((uni, name), 0)
        count = base + boost + random.randint(0, 5)
        conn.execute(
            "INSERT INTO internships (company_id, university, year, count) VALUES (?, ?, ?, ?)",
            (company_id[name], uni, 2024, count),
        )

conn.commit()
conn.close()
print(f"Seeded {len(COMPANIES)} companies × {len(UNIVERSITIES)} universities → {DB_PATH}")
