"""Run once locally: python backend/data/seed.py"""

import hashlib
import os
import random

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

# ── Dimension data ─────────────────────────────────────────────────────────────

INDUSTRIES = [
    ("tech",          "Tech",          "Technology companies"),
    ("e-commerce",    "E-Commerce",    "Online retail and marketplace"),
    ("entertainment", "Entertainment", "Media and streaming"),
    ("mobility",      "Mobility",      "Transportation technology"),
    ("travel",        "Travel",        "Travel and hospitality"),
    ("fintech",       "Fintech",       "Financial technology"),
    ("enterprise",    "Enterprise",    "Enterprise software"),
    ("creative",      "Creative",      "Design and creative tools"),
    ("semiconductors","Semiconductors","Chip design and hardware"),
    ("social",        "Social",        "Social media and networking"),
    ("design",        "Design",        "Design tools"),
    ("productivity",  "Productivity",  "Productivity software"),
    ("data",          "Data",          "Data and analytics"),
    ("aerospace",     "Aerospace",     "Space and aviation"),
    ("gaming",        "Gaming",        "Games and entertainment"),
]

# (slug, display_name, industry_slug, logo_url, hq_location, size_bucket)
COMPANIES = [
    ("google",     "Google",     "tech",          "https://logo.clearbit.com/google.com",     "Mountain View, CA",  "big-tech"),
    ("meta",       "Meta",       "tech",          "https://logo.clearbit.com/meta.com",        "Menlo Park, CA",     "big-tech"),
    ("apple",      "Apple",      "tech",          "https://logo.clearbit.com/apple.com",       "Cupertino, CA",      "big-tech"),
    ("amazon",     "Amazon",     "e-commerce",    "https://logo.clearbit.com/amazon.com",      "Seattle, WA",        "big-tech"),
    ("microsoft",  "Microsoft",  "tech",          "https://logo.clearbit.com/microsoft.com",   "Redmond, WA",        "big-tech"),
    ("netflix",    "Netflix",    "entertainment", "https://logo.clearbit.com/netflix.com",     "Los Gatos, CA",      "big-tech"),
    ("uber",       "Uber",       "mobility",      "https://logo.clearbit.com/uber.com",        "San Francisco, CA",  "enterprise"),
    ("airbnb",     "Airbnb",     "travel",        "https://logo.clearbit.com/airbnb.com",      "San Francisco, CA",  "enterprise"),
    ("stripe",     "Stripe",     "fintech",       "https://logo.clearbit.com/stripe.com",      "San Francisco, CA",  "mid-market"),
    ("lyft",       "Lyft",       "mobility",      "https://logo.clearbit.com/lyft.com",        "San Francisco, CA",  "mid-market"),
    ("salesforce", "Salesforce", "enterprise",    "https://logo.clearbit.com/salesforce.com",  "San Francisco, CA",  "big-tech"),
    ("adobe",      "Adobe",      "creative",      "https://logo.clearbit.com/adobe.com",       "San Jose, CA",       "big-tech"),
    ("nvidia",     "Nvidia",     "semiconductors","https://logo.clearbit.com/nvidia.com",      "Santa Clara, CA",    "big-tech"),
    ("linkedin",   "LinkedIn",   "social",        "https://logo.clearbit.com/linkedin.com",    "Sunnyvale, CA",      "big-tech"),
    ("figma",      "Figma",      "design",        "https://logo.clearbit.com/figma.com",       "San Francisco, CA",  "mid-market"),
    ("notion",     "Notion",     "productivity",  "https://logo.clearbit.com/notion.so",       "San Francisco, CA",  "startup"),
    ("palantir",   "Palantir",   "data",          "https://logo.clearbit.com/palantir.com",    "Denver, CO",         "enterprise"),
    ("spacex",     "SpaceX",     "aerospace",     "https://logo.clearbit.com/spacex.com",      "Hawthorne, CA",      "enterprise"),
    ("roblox",     "Roblox",     "gaming",        "https://logo.clearbit.com/roblox.com",      "San Mateo, CA",      "mid-market"),
    ("snap",       "Snap",       "social",        "https://logo.clearbit.com/snap.com",        "Santa Monica, CA",   "mid-market"),
]

# (slug, display_name, region, tier)
UNIVERSITIES = [
    ("ucla",            "UCLA",            "West Coast",       "top-tier"),
    ("stanford",        "Stanford",        "West Coast",       "top-tier"),
    ("uc-berkeley",     "UC Berkeley",     "West Coast",       "top-tier"),
    ("mit",             "MIT",             "East Coast",       "top-tier"),
    ("carnegie-mellon", "Carnegie Mellon", "East Coast",       "top-tier"),
    ("georgia-tech",    "Georgia Tech",    "Southeast",        "strong"),
    ("uiuc",            "UIUC",            "Midwest",          "strong"),
    ("usc",             "USC",             "West Coast",       "strong"),
    ("ut-austin",       "UT Austin",       "South",            "strong"),
    ("uw-seattle",      "UW Seattle",      "Pacific Northwest", "strong"),
]

PIPELINE_BOOST = {
    ("stanford",        "google"):     35,
    ("stanford",        "apple"):      28,
    ("uc-berkeley",     "google"):     30,
    ("uc-berkeley",     "meta"):       25,
    ("mit",             "microsoft"):  30,
    ("mit",             "amazon"):     20,
    ("carnegie-mellon", "meta"):       22,
    ("carnegie-mellon", "nvidia"):     18,
    ("ucla",            "amazon"):     15,
    ("ucla",            "netflix"):    14,
    ("usc",             "snap"):       18,
    ("usc",             "roblox"):     12,
    ("georgia-tech",    "microsoft"):  16,
    ("georgia-tech",    "palantir"):   12,
    ("uiuc",            "amazon"):     14,
    ("uiuc",            "salesforce"): 10,
    ("uw-seattle",      "amazon"):     26,
    ("uw-seattle",      "microsoft"):  22,
    ("ut-austin",       "spacex"):     14,
    ("ut-austin",       "lyft"):       10,
}

# Role distribution per industry (category → weight)
ROLE_MIX: dict[str, list[tuple[str, float]]] = {
    "tech":          [("SWE", 0.70), ("PM", 0.15), ("Data", 0.15)],
    "e-commerce":    [("SWE", 0.60), ("PM", 0.20), ("Data", 0.20)],
    "entertainment": [("SWE", 0.60), ("PM", 0.20), ("Data", 0.20)],
    "mobility":      [("SWE", 0.70), ("PM", 0.20), ("Data", 0.10)],
    "travel":        [("SWE", 0.60), ("PM", 0.25), ("Data", 0.15)],
    "fintech":       [("SWE", 0.60), ("Data", 0.25), ("Business", 0.15)],
    "enterprise":    [("SWE", 0.60), ("PM", 0.25), ("Business", 0.15)],
    "creative":      [("SWE", 0.50), ("Design", 0.35), ("PM", 0.15)],
    "semiconductors":[("SWE", 0.50), ("Research", 0.35), ("Data", 0.15)],
    "social":        [("SWE", 0.50), ("PM", 0.30), ("Data", 0.20)],
    "design":        [("SWE", 0.50), ("Design", 0.40), ("PM", 0.10)],
    "productivity":  [("SWE", 0.65), ("PM", 0.25), ("Design", 0.10)],
    "data":          [("SWE", 0.40), ("Data", 0.35), ("Research", 0.25)],
    "aerospace":     [("SWE", 0.50), ("Research", 0.40), ("Other", 0.10)],
    "gaming":        [("SWE", 0.60), ("Design", 0.25), ("PM", 0.15)],
}

ROLE_TITLES = {
    "SWE":      "Software Engineer Intern",
    "PM":       "Product Manager Intern",
    "Data":     "Data Scientist Intern",
    "Design":   "Product Design Intern",
    "Research": "Research Intern",
    "Business": "Business Analyst Intern",
    "Other":    "Operations Intern",
}


def student_hash(uni_slug: str, company_slug: str, i: int) -> str:
    key = f"talantis-{uni_slug}-{company_slug}-{i}-2024"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def pick_role(industry_slug: str, rng: random.Random) -> tuple[str, str]:
    mix = ROLE_MIX.get(industry_slug, [("SWE", 1.0)])
    categories = [m[0] for m in mix]
    weights = [m[1] for m in mix]
    cat = rng.choices(categories, weights=weights)[0]
    return cat, ROLE_TITLES[cat]


# ── Seed ───────────────────────────────────────────────────────────────────────

rng = random.Random(42)

print("Clearing existing data...")
client.table("internships").delete().gte("id", 0).execute()
client.table("companies").delete().neq("slug", "").execute()
client.table("universities").delete().neq("slug", "").execute()
client.table("industries").delete().neq("slug", "").execute()

print("Inserting industries...")
client.table("industries").insert(
    [{"slug": s, "display_name": d, "description": desc} for s, d, desc in INDUSTRIES]
).execute()

print("Inserting universities...")
client.table("universities").insert(
    [{"slug": s, "display_name": d, "region": r, "tier": t} for s, d, r, t in UNIVERSITIES]
).execute()

print("Inserting companies...")
client.table("companies").insert([
    {"slug": s, "display_name": d, "industry_slug": ind, "logo_url": logo,
     "hq_location": hq, "size_bucket": size}
    for s, d, ind, logo, hq, size in COMPANIES
]).execute()

print("Building internship rows...")
industry_map = {s: ind for s, d, ind, logo, hq, size in COMPANIES}

rows: list[dict] = []
for uni_slug, uni_name, *_ in UNIVERSITIES:
    for co_slug, co_name, industry_slug, *_ in COMPANIES:
        base  = rng.randint(2, 8)
        boost = PIPELINE_BOOST.get((uni_slug, co_slug), 0)
        count = base + boost + rng.randint(0, 5)
        for i in range(count):
            cat, title = pick_role(industry_slug, rng)
            rows.append({
                "student_hash":    student_hash(uni_slug, co_slug, i),
                "company_slug":    co_slug,
                "university_slug": uni_slug,
                "role_title":      title,
                "role_category":   cat,
                "year":            2024,
                "season":          "Summer",
                "source":          "synthetic",
            })

print(f"Inserting {len(rows)} internship rows in batches...")
batch_size = 200
for start in range(0, len(rows), batch_size):
    batch = rows[start : start + batch_size]
    client.table("internships").insert(batch).execute()
    print(f"  {min(start + batch_size, len(rows))}/{len(rows)}")

print("Refreshing materialized views...")
client.rpc("refresh_materialized_views", {}).execute()

print(f"Done — {len(COMPANIES)} companies × {len(UNIVERSITIES)} universities → {len(rows)} intern rows")
