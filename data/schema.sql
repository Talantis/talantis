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

-- ============================================================
-- TALANTIS · Talent Intelligence Core SQL Functions
-- ============================================================
-- Append this to the end of schema.sql.
-- Three Postgres functions back the three Python tools:
--   tic_filter_internships    →  filter_internships()
--   tic_compare_companies     →  compare_companies()
--   tic_find_similar_schools  →  find_similar_schools()
--
-- Why SQL functions instead of Python queries?
--   1. ONE network round-trip to Supabase per tool call (vs many)
--   2. Postgres can use indexes and materialized views directly
--   3. Logic is enforceable at the database layer
-- ============================================================

drop function if exists tic_filter_internships(text, text, text, text, int, text, int) cascade;
drop function if exists tic_compare_companies(text[], int, int) cascade;
drop function if exists tic_find_similar_schools(text, text[], int, int) cascade;

-- ============================================================
-- 1. tic_filter_internships
-- Count internships with optional filters, grouped by a dimension.
-- ============================================================

create or replace function tic_filter_internships(
  p_university    text default null,
  p_company       text default null,
  p_industry      text default null,
  p_role_category text default null,
  p_year          int  default 2024,
  p_group_by      text default 'company',
  p_limit         int  default 15
)
returns table(key text, count bigint)
language plpgsql security definer as $$
begin
  -- Use dynamic SQL because the GROUP BY column varies.
  -- Safe because p_group_by is checked against a whitelist below.
  if p_group_by not in ('company', 'university', 'industry', 'role_category') then
    p_group_by := 'company';
  end if;

  return query execute format($f$
    select
      case %1$L
        when 'company'       then c.display_name
        when 'university'    then u.display_name
        when 'industry'      then c.industry_slug
        when 'role_category' then i.role_category
      end as key,
      count(*)::bigint as count
    from internships i
    join companies    c on c.slug = i.company_slug
    join universities u on u.slug = i.university_slug
    where i.year = %2$L
      and (%3$L is null or u.display_name ilike %3$L or u.slug = lower(replace(%3$L, ' ', '-')))
      and (%4$L is null or c.display_name ilike %4$L or c.slug = lower(replace(%4$L, ' ', '-')))
      and (%5$L is null or c.industry_slug = %5$L)
      and (%6$L is null or i.role_category = %6$L)
    group by key
    order by count desc
    limit %7$L
  $f$, p_group_by, p_year, p_university, p_company, p_industry, p_role_category, p_limit);
end;
$$;

-- ============================================================
-- 2. tic_compare_companies
-- Compare 2+ companies' top feeder universities side-by-side.
-- Returns JSON because the column shape is dynamic.
-- ============================================================

create or replace function tic_compare_companies(
  p_companies text[],
  p_year      int default 2024,
  p_top_n     int default 10
)
returns json
language plpgsql security definer as $$
declare
  result json;
begin
  with normalized as (
    -- Resolve company display names OR slugs to canonical display_name
    select c.display_name as company
    from companies c
    where c.display_name = any(p_companies)
       or c.slug = any(array(select lower(replace(s, ' ', '-')) from unnest(p_companies) s))
  ),
  per_uni_company as (
    -- intern counts per (company, university) for the requested companies
    select
      u.display_name as university,
      c.display_name as company,
      count(*)::int  as cnt
    from internships i
    join companies    c on c.slug = i.company_slug
    join universities u on u.slug = i.university_slug
    where i.year = p_year
      and c.display_name in (select company from normalized)
    group by u.display_name, c.display_name
  ),
  uni_totals as (
    -- Sum intern counts across the requested companies, per university
    select university, sum(cnt) as total
    from per_uni_company
    group by university
    order by total desc
    limit p_top_n
  ),
  pivot as (
    -- For each top university, build a JSON object with one key per company
    select
      ut.university,
      json_object_agg(coalesce(p.company, ''), coalesce(p.cnt, 0))
        filter (where p.company is not null) as company_counts
    from uni_totals ut
    left join per_uni_company p on p.university = ut.university
    group by ut.university
    order by ut.university
  ),
  per_company_summary as (
    select
      company,
      json_build_object(
        'total', sum(cnt),
        'unique_universities', count(distinct university)
      ) as summary
    from per_uni_company
    group by company
  )
  select json_build_object(
    'year', p_year,
    'companies', (select array_agg(company) from normalized),
    'comparison', (
      select coalesce(json_agg(json_build_object(
        'university', p.university
      ) || p.company_counts), '[]'::json)
      from pivot p
    ),
    'summary', (
      select coalesce(json_object_agg(company, summary), '{}'::json)
      from per_company_summary
    )
  ) into result;
  return result;
end;
$$;

-- ============================================================
-- 3. tic_find_similar_schools  ★
-- The signature insight. Find schools peers recruit from but
-- the reference company does not.
-- ============================================================

create or replace function tic_find_similar_schools(
  p_reference_company text,
  p_peer_companies    text[],
  p_year              int default 2024,
  p_limit             int default 8
)
returns json
language plpgsql security definer as $$
declare
  result json;
begin
  with ref_company as (
    select c.slug, c.display_name
    from companies c
    where c.display_name ilike p_reference_company
       or c.slug = lower(replace(p_reference_company, ' ', '-'))
    limit 1
  ),
  peer_set as (
    select c.slug, c.display_name
    from companies c
    where c.display_name = any(p_peer_companies)
       or c.slug = any(array(select lower(replace(s, ' ', '-')) from unnest(p_peer_companies) s))
  ),
  peer_signal as (
    -- How many interns from each university go to the peer group?
    select
      u.display_name as university,
      sum(cnt)::int  as peer_count
    from (
      select i.university_slug, count(*)::int as cnt
      from internships i
      where i.year = p_year
        and i.company_slug in (select slug from peer_set)
      group by i.university_slug
    ) p
    join universities u on u.slug = p.university_slug
    group by u.display_name
  ),
  ref_signal as (
    -- How many interns from each university go to the reference?
    select
      u.display_name as university,
      count(*)::int  as ref_count
    from internships i
    join universities u on u.slug = i.university_slug
    where i.year = p_year
      and i.company_slug = (select slug from ref_company)
    group by u.display_name
  ),
  gaps as (
    -- For each university with non-zero peer signal, compute the gap
    select
      ps.university,
      ps.peer_count,
      coalesce(rs.ref_count, 0) as ref_count,
      greatest(ps.peer_count - coalesce(rs.ref_count, 0), 0) as gap
    from peer_signal ps
    left join ref_signal rs on rs.university = ps.university
  ),
  ranked as (
    select
      university,
      peer_count,
      ref_count,
      gap,
      case
        when ref_count = 0 and peer_count >= 3 then 'Peers hire heavily; you don''t recruit here.'
        when ref_count = 0                       then 'Peers have a presence; you don''t.'
        when gap >= 5                             then 'You under-recruit relative to peers.'
        else 'Pipeline gap.'
      end as interpretation
    from gaps
    where gap > 0
    order by gap desc, peer_count desc
    limit p_limit
  )
  select json_build_object(
    'reference_company', (select display_name from ref_company),
    'peer_companies',    (select array_agg(display_name) from peer_set),
    'year',              p_year,
    'hidden_pipelines',  coalesce((select json_agg(row_to_json(r)) from ranked r), '[]'::json)
  ) into result;
  return result;
end;
$$;

-- ============================================================
-- Grant execute on all three functions to the anon role
-- (Supabase's default role for service-key calls)
-- ============================================================

grant execute on function tic_filter_internships(text, text, text, text, int, text, int) to anon, authenticated;
grant execute on function tic_compare_companies(text[], int, int)                          to anon, authenticated;
grant execute on function tic_find_similar_schools(text, text[], int, int)                 to anon, authenticated;
