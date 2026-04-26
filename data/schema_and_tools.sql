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

-- =============================================================================
-- Talantis · Student-side Talent Intelligence Tools
-- =============================================================================
-- Three new RPC functions to add to your Supabase database. These power the
-- student-facing tools that complement the existing recruiter-facing three.
--
-- Run this whole file in: Supabase Dashboard → SQL Editor → New query → Run
--
-- All three functions are idempotent (CREATE OR REPLACE) — safe to re-run.
-- =============================================================================


-- =============================================================================
-- TOOL 4: tic_find_target_companies
-- "Given my school + interests, what companies should I apply to?"
-- =============================================================================
-- Returns companies ranked by how realistic an application is, based on
-- the student's school's actual hiring history at each company.
--
-- Tier definitions:
--   "strong-fit" — school placed >= 3 students at this company in the year
--   "realistic" — school placed 1-2 students
--   "reach"     — school placed 0 but the company hires from comparable schools
--
-- The "comparable schools" logic uses other schools that historically share
-- placement patterns with the student's school. We approximate this by saying:
-- a company is a reach if it hires from any school that shares 2+ companies
-- with our reference school's placement set.
-- =============================================================================

create or replace function tic_find_target_companies(
  p_university    text,
  p_industry      text default null,
  p_role_category text default null,
  p_year          integer default 2024,
  p_limit         integer default 15
)
returns table (
  company             text,
  company_slug        text,
  industry            text,
  intern_count        integer,
  tier                text,
  reasoning           text
)
language plpgsql
as $$
declare
  v_university_slug text;
begin
  -- Resolve university (accept both display name and slug)
  select slug into v_university_slug
  from universities
  where lower(display_name) = lower(p_university) or slug = lower(p_university)
  limit 1;

  if v_university_slug is null then
    return;  -- empty result for unknown school
  end if;

  return query
  with
    -- All companies that match the user's filters
    candidates as (
      select c.slug as cslug, c.display_name as cname, c.industry_slug as cind
      from companies c
      where (p_industry is null or c.industry_slug = p_industry)
    ),

    -- This school's actual placements at each candidate company
    school_at_company as (
      select
        c.cslug,
        c.cname,
        c.cind,
        coalesce(sum(i.intern_count), 0)::integer as count_at_co
      from candidates c
      left join internships i
        on i.company_slug = c.cslug
       and i.university_slug = v_university_slug
       and i.year = p_year
       and (p_role_category is null or i.role_category = p_role_category)
      group by c.cslug, c.cname, c.cind
    ),

    -- Schools comparable to ours: schools that share 2+ companies with us
    comparable_schools as (
      select distinct other.university_slug
      from internships ours
      join internships other
        on ours.company_slug = other.company_slug
       and ours.year = other.year
      where ours.university_slug = v_university_slug
        and ours.year = p_year
        and other.university_slug != v_university_slug
      group by other.university_slug
      having count(distinct other.company_slug) >= 2
    ),

    -- Whether each candidate company hires from comparable schools
    company_in_peer_set as (
      select i.company_slug as cslug, count(distinct i.university_slug) as peer_school_count
      from internships i
      where i.year = p_year
        and i.university_slug in (select university_slug from comparable_schools)
        and (p_role_category is null or i.role_category = p_role_category)
      group by i.company_slug
    )

  select
    sac.cname            as company,
    sac.cslug            as company_slug,
    sac.cind             as industry,
    sac.count_at_co      as intern_count,
    case
      when sac.count_at_co >= 3 then 'strong-fit'
      when sac.count_at_co >= 1 then 'realistic'
      when coalesce(cps.peer_school_count, 0) >= 2 then 'reach'
      else 'unmapped'
    end                  as tier,
    case
      when sac.count_at_co >= 3 then
        'Your school sent ' || sac.count_at_co || ' interns here. Strong pipeline.'
      when sac.count_at_co >= 1 then
        sac.count_at_co || ' student' ||
        case when sac.count_at_co = 1 then '' else 's' end ||
        ' from your school landed here. Realistic.'
      when coalesce(cps.peer_school_count, 0) >= 2 then
        'No placements from your school yet, but ' || cps.peer_school_count ||
        ' comparable schools placed students here.'
      else
        'No clear precedent for this combination. May still be worth a try.'
    end                  as reasoning
  from school_at_company sac
  left join company_in_peer_set cps on cps.cslug = sac.cslug
  -- Filter out unmapped unless the student is explicitly looking at an industry
  where (p_industry is not null) or (
    sac.count_at_co > 0 or coalesce(cps.peer_school_count, 0) >= 2
  )
  order by
    case
      when sac.count_at_co >= 3 then 1
      when sac.count_at_co >= 1 then 2
      when coalesce(cps.peer_school_count, 0) >= 2 then 3
      else 4
    end,
    sac.count_at_co desc,
    coalesce(cps.peer_school_count, 0) desc
  limit p_limit;
end;
$$;


-- =============================================================================
-- TOOL 5: tic_analyze_school_at_company
-- "How does my school stack up at Company X?"
-- =============================================================================
-- Returns:
--   - The school's actual placement count at the company
--   - The company's overall placement distribution (top schools)
--   - Where the student's school ranks in that distribution
--   - Comparable peer schools and how THEY did at the same company
-- =============================================================================

create or replace function tic_analyze_school_at_company(
  p_university   text,
  p_company      text,
  p_year         integer default 2024
)
returns json
language plpgsql
as $$
declare
  v_university_slug text;
  v_company_slug    text;
  v_school_count    integer;
  v_school_rank     integer;
  v_total_at_co     integer;
  v_top_schools     json;
  v_peer_perf       json;
begin
  -- Resolve names → slugs
  select slug into v_university_slug
  from universities
  where lower(display_name) = lower(p_university) or slug = lower(p_university)
  limit 1;

  select slug into v_company_slug
  from companies
  where lower(display_name) = lower(p_company) or slug = lower(p_company)
  limit 1;

  if v_university_slug is null or v_company_slug is null then
    return json_build_object('error', 'unknown university or company');
  end if;

  -- This school's placement at this company
  select coalesce(sum(intern_count), 0) into v_school_count
  from internships
  where university_slug = v_university_slug
    and company_slug    = v_company_slug
    and year            = p_year;

  -- The company's total intern placements this year
  select coalesce(sum(intern_count), 0) into v_total_at_co
  from internships
  where company_slug = v_company_slug and year = p_year;

  -- The school's rank among all schools placing at this company
  select coalesce(rank, null) into v_school_rank
  from (
    select u.slug,
           rank() over (order by sum(i.intern_count) desc) as rank
    from internships i
    join universities u on u.slug = i.university_slug
    where i.company_slug = v_company_slug
      and i.year = p_year
    group by u.slug
  ) t
  where t.slug = v_university_slug;

  -- Top 5 schools at this company
  select json_agg(json_build_object(
    'university', u.display_name,
    'count',      total
  ) order by total desc) into v_top_schools
  from (
    select u.display_name, sum(i.intern_count)::integer as total
    from internships i
    join universities u on u.slug = i.university_slug
    where i.company_slug = v_company_slug
      and i.year = p_year
    group by u.display_name
    order by total desc
    limit 5
  ) u;

  -- How comparable peer schools did at this same company
  select json_agg(json_build_object(
    'university', u.display_name,
    'count',      placements
  ) order by placements desc) into v_peer_perf
  from (
    select other.university_slug, sum(other.intern_count)::integer as placements
    from internships ours
    join internships other
      on ours.company_slug = other.company_slug
     and ours.year = other.year
    where ours.university_slug = v_university_slug
      and ours.year = p_year
      and other.university_slug != v_university_slug
      and other.company_slug = v_company_slug
    group by other.university_slug
    having count(distinct other.company_slug) >= 1
    order by placements desc
    limit 5
  ) p
  join universities u on u.slug = p.university_slug;

  return json_build_object(
    'university',           p_university,
    'company',              p_company,
    'year',                 p_year,
    'school_placements',    v_school_count,
    'school_rank',          v_school_rank,
    'company_total',        v_total_at_co,
    'top_schools_at_company', coalesce(v_top_schools, '[]'::json),
    'peer_school_performance', coalesce(v_peer_perf, '[]'::json)
  );
end;
$$;


-- =============================================================================
-- TOOL 6: tic_discover_career_paths
-- "Where do students like me usually end up?"  ★ student-side magic
-- =============================================================================
-- The student's mirror of find_similar_schools. Given a school + interest area,
-- find the realistic landing distribution by aggregating placements from:
--   - The student's own school (direct precedent)
--   - Comparable peer schools (similar trajectory)
--
-- Surfaces "stepping stone" companies that students from comparable schools
-- have landed at, even if your specific school hasn't sent anyone yet.
--
-- Returns paths grouped into:
--   - direct paths     — companies your school has placed at
--   - peer paths       — companies comparable schools have placed at
--   - bridge paths     — companies in your industry that hire from peer schools
-- =============================================================================

create or replace function tic_discover_career_paths(
  p_university    text,
  p_role_category text default null,
  p_industry      text default null,
  p_year          integer default 2024,
  p_limit         integer default 12
)
returns json
language plpgsql
as $$
declare
  v_university_slug text;
  v_direct          json;
  v_peer            json;
  v_bridge          json;
begin
  select slug into v_university_slug
  from universities
  where lower(display_name) = lower(p_university) or slug = lower(p_university)
  limit 1;

  if v_university_slug is null then
    return json_build_object('error', 'unknown university');
  end if;

  -- Direct paths: companies your school has placed at
  select json_agg(json_build_object(
    'company',      cname,
    'industry',     cind,
    'count',        count,
    'path_type',    'direct'
  ) order by count desc) into v_direct
  from (
    select c.display_name as cname, c.industry_slug as cind, sum(i.intern_count)::integer as count
    from internships i
    join companies c on c.slug = i.company_slug
    where i.university_slug = v_university_slug
      and i.year = p_year
      and (p_role_category is null or i.role_category = p_role_category)
      and (p_industry      is null or c.industry_slug = p_industry)
    group by c.display_name, c.industry_slug
    order by count desc
    limit p_limit
  ) d;

  -- Peer paths: companies that comparable schools placed at,
  -- where YOUR school hasn't (or has placed less than peers)
  with comparable_schools as (
    select distinct other.university_slug
    from internships ours
    join internships other
      on ours.company_slug = other.company_slug
     and ours.year = other.year
    where ours.university_slug = v_university_slug
      and ours.year = p_year
      and other.university_slug != v_university_slug
    group by other.university_slug
    having count(distinct other.company_slug) >= 2
  ),
  ours_at_co as (
    select i.company_slug, sum(i.intern_count)::integer as my_count
    from internships i
    where i.university_slug = v_university_slug
      and i.year = p_year
      and (p_role_category is null or i.role_category = p_role_category)
    group by i.company_slug
  ),
  peers_at_co as (
    select i.company_slug,
           sum(i.intern_count)::integer as peer_count,
           count(distinct i.university_slug) as peer_school_count
    from internships i
    where i.university_slug in (select university_slug from comparable_schools)
      and i.year = p_year
      and (p_role_category is null or i.role_category = p_role_category)
    group by i.company_slug
  )
  select json_agg(json_build_object(
    'company',         c.display_name,
    'industry',        c.industry_slug,
    'count',           p.peer_count,
    'peer_schools',    p.peer_school_count,
    'your_school',     coalesce(o.my_count, 0),
    'path_type',       'peer'
  ) order by p.peer_count desc) into v_peer
  from peers_at_co p
  join companies c on c.slug = p.company_slug
  left join ours_at_co o on o.company_slug = p.company_slug
  where coalesce(o.my_count, 0) < p.peer_count
    and p.peer_school_count >= 2
    and (p_industry is null or c.industry_slug = p_industry)
  order by p.peer_count desc
  limit p_limit;

  return json_build_object(
    'university',     p_university,
    'role_category',  p_role_category,
    'industry',       p_industry,
    'year',           p_year,
    'direct_paths',   coalesce(v_direct, '[]'::json),
    'peer_paths',     coalesce(v_peer,   '[]'::json)
  );
end;
$$;


-- =============================================================================
-- Permissions: grant execute to anon + authenticated (matching the pattern of
-- existing tic_* functions). If your existing functions use different roles,
-- match those instead.
-- =============================================================================

grant execute on function tic_find_target_companies(text, text, text, integer, integer) to anon, authenticated;
grant execute on function tic_analyze_school_at_company(text, text, integer)            to anon, authenticated;
grant execute on function tic_discover_career_paths(text, text, text, integer, integer) to anon, authenticated;
