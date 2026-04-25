-- ============================================================
-- TALANTIS · Postgres schema (Supabase)
-- Paste this entire file into the Supabase SQL editor and run.
-- ============================================================

-- Drop everything in reverse dependency order
drop function if exists refresh_materialized_views() cascade;
drop function if exists get_data_summary(int) cascade;
drop function if exists get_company_counts(text, int) cascade;
drop function if exists get_universities_list() cascade;
drop materialized view if exists mv_university_counts_by_company;
drop materialized view if exists mv_company_counts_by_uni;
drop table if exists internships cascade;
drop table if exists companies cascade;
drop table if exists universities cascade;
drop table if exists industries cascade;

-- Extensions
create extension if not exists "uuid-ossp";
create extension if not exists "pg_trgm";

-- ==========================================================
-- DIMENSION TABLES
-- ==========================================================

create table industries (
  slug         text primary key,
  display_name text not null,
  description  text
);

create table companies (
  slug          text primary key,
  display_name  text not null,
  industry_slug text not null references industries(slug),
  logo_url      text,
  hq_location   text,
  size_bucket   text check (size_bucket in ('startup', 'mid-market', 'big-tech', 'enterprise')),
  created_at    timestamptz not null default now()
);

create table universities (
  slug         text primary key,
  display_name text not null,
  region       text,
  tier         text check (tier in ('top-tier', 'strong', 'emerging')),
  created_at   timestamptz not null default now()
);

-- ==========================================================
-- FACT TABLE
-- ==========================================================

create table internships (
  id              bigint generated always as identity primary key,
  student_hash    text not null,

  company_slug    text not null references companies(slug),
  university_slug text not null references universities(slug),

  role_title      text not null,
  role_category   text not null check (role_category in
    ('SWE', 'PM', 'Data', 'Design', 'Research', 'Business', 'Other')),

  year            smallint not null check (year between 2020 and 2030),
  season          text not null default 'Summer'
    check (season in ('Summer', 'Fall', 'Winter', 'Spring')),

  source          text not null default 'synthetic'
    check (source in ('real', 'synthetic')),

  created_at      timestamptz not null default now(),

  unique (student_hash, company_slug, year, season)
);

-- ==========================================================
-- INDEXES
-- ==========================================================

create index idx_internships_uni_year_company
  on internships (university_slug, year, company_slug);

create index idx_internships_company_year_uni
  on internships (company_slug, year, university_slug);

create index idx_internships_year_company
  on internships (year, company_slug);

create index idx_internships_uni_year
  on internships (university_slug, year);

create index idx_companies_name_trgm
  on companies using gin (display_name gin_trgm_ops);

create index idx_universities_name_trgm
  on universities using gin (display_name gin_trgm_ops);

-- ==========================================================
-- MATERIALIZED VIEWS
-- ==========================================================

create materialized view mv_company_counts_by_uni as
select
  university_slug,
  company_slug,
  year,
  count(*)::int as intern_count
from internships
group by university_slug, company_slug, year;

create unique index on mv_company_counts_by_uni (university_slug, company_slug, year);

create materialized view mv_university_counts_by_company as
select
  company_slug,
  university_slug,
  year,
  count(*)::int as intern_count
from internships
group by company_slug, university_slug, year;

create unique index on mv_university_counts_by_company (company_slug, university_slug, year);

-- Grant read access to the materialized views
grant select on mv_company_counts_by_uni to anon, authenticated;
grant select on mv_university_counts_by_company to anon, authenticated;

-- ==========================================================
-- ROW LEVEL SECURITY
-- ==========================================================

alter table industries   enable row level security;
alter table companies    enable row level security;
alter table universities enable row level security;
alter table internships  enable row level security;

create policy "public read industries"   on industries   for select using (true);
create policy "public read companies"    on companies    for select using (true);
create policy "public read universities" on universities for select using (true);
create policy "public read internships"  on internships  for select using (true);

-- ==========================================================
-- RPC FUNCTIONS — called by the FastAPI backend
-- ==========================================================

-- List all universities sorted alphabetically
create or replace function get_universities_list()
returns table(display_name text)
language sql security definer as $$
  select display_name from universities order by display_name;
$$;

-- Intern counts per company, optionally filtered by university display name
create or replace function get_company_counts(
  p_university text default null,
  p_year       int  default 2024
)
returns table(
  company      text,
  logo_url     text,
  industry     text,
  university   text,
  intern_count bigint
)
language sql security definer as $$
  select
    c.display_name  as company,
    c.logo_url,
    c.industry_slug as industry,
    u.display_name  as university,
    count(*)::bigint as intern_count
  from internships i
  join companies  c on c.slug = i.company_slug
  join universities u on u.slug = i.university_slug
  where (p_university is null or u.display_name = p_university)
    and i.year = p_year
  group by c.slug, c.display_name, c.logo_url, c.industry_slug, u.display_name
  order by intern_count desc;
$$;

-- Full dataset summary with metadata — used as Atlas AI context
create or replace function get_data_summary(p_year int default 2024)
returns json
language sql security definer as $$
  select json_agg(row_to_json(t)) from (
    select
      c.display_name  as company,
      c.industry_slug as industry,
      c.size_bucket   as size,
      u.display_name  as university,
      u.region,
      u.tier,
      count(*)::int   as intern_count
    from internships i
    join companies    c on c.slug = i.company_slug
    join universities u on u.slug = i.university_slug
    where i.year = p_year
    group by
      c.slug, c.display_name, c.industry_slug, c.size_bucket,
      u.slug, u.display_name, u.region, u.tier
    order by intern_count desc
  ) t;
$$;

-- Refresh both materialized views — call after seeding
create or replace function refresh_materialized_views()
returns void
language plpgsql security definer as $$
begin
  refresh materialized view mv_company_counts_by_uni;
  refresh materialized view mv_university_counts_by_company;
end;
$$;
