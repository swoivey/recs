-- =========================================================
-- recs — Supabase Database Schema
-- =========================================================
-- Run this in the Supabase SQL Editor after creating your project
-- =========================================================

-- 1. PROFILES
-- Stores user display info (anonymous or authenticated)
create table public.profiles (
  id uuid primary key default gen_random_uuid(),
  anon_id text unique,                    -- anonymous session ID
  display_name text default 'Anonymous',
  avatar_emoji text default '🙂',
  created_at timestamptz default now()
);

-- Enable RLS
alter table public.profiles enable row level security;

-- Anyone can read profiles
create policy "Profiles are viewable by everyone"
  on public.profiles for select using (true);

-- Users can insert their own profile (matched by anon_id)
create policy "Users can insert own profile"
  on public.profiles for insert with check (true);

-- Users can update their own profile
create policy "Users can update own profile"
  on public.profiles for update using (anon_id = current_setting('request.jwt.claims', true)::json->>'sub');


-- 2. CHECK-INS ("Been Here")
-- Records that a user has visited a venue
create table public.checkins (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references public.profiles(id) on delete cascade,
  venue_id text not null,                 -- matches RECS_VENUES key (e.g., "cgu-001")
  created_at timestamptz default now(),
  unique(profile_id, venue_id)            -- one check-in per user per venue
);

alter table public.checkins enable row level security;

-- Anyone can read check-ins
create policy "Check-ins are viewable by everyone"
  on public.checkins for select using (true);

-- Authenticated users can insert their own check-ins
create policy "Users can insert own check-ins"
  on public.checkins for insert with check (true);

-- Users can delete their own check-ins
create policy "Users can delete own check-ins"
  on public.checkins for delete using (
    profile_id in (
      select id from public.profiles where anon_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );


-- 3. THUMBS (up/down ratings)
-- Tracks thumbs up or thumbs down on venues
create table public.thumbs (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references public.profiles(id) on delete cascade,
  venue_id text not null,
  direction text not null check (direction in ('up', 'down')),
  created_at timestamptz default now(),
  unique(profile_id, venue_id)            -- one thumb per user per venue
);

alter table public.thumbs enable row level security;

create policy "Thumbs are viewable by everyone"
  on public.thumbs for select using (true);

create policy "Users can insert own thumbs"
  on public.thumbs for insert with check (true);

create policy "Users can update own thumbs"
  on public.thumbs for update using (
    profile_id in (
      select id from public.profiles where anon_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

create policy "Users can delete own thumbs"
  on public.thumbs for delete using (
    profile_id in (
      select id from public.profiles where anon_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );


-- 4. USER SAVES (synced from localStorage)
-- Persists saved/favorited venues
create table public.user_saves (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references public.profiles(id) on delete cascade,
  venue_id text not null,
  created_at timestamptz default now(),
  unique(profile_id, venue_id)
);

alter table public.user_saves enable row level security;

create policy "Users can view own saves"
  on public.user_saves for select using (
    profile_id in (
      select id from public.profiles where anon_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

create policy "Users can insert own saves"
  on public.user_saves for insert with check (true);

create policy "Users can delete own saves"
  on public.user_saves for delete using (
    profile_id in (
      select id from public.profiles where anon_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );


-- 5. SHARED LISTS
-- Curated shareable lists of venues
create table public.shared_lists (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references public.profiles(id) on delete cascade,
  slug text unique not null,              -- URL-friendly slug (e.g., "harrys-bali-picks")
  title text not null,
  description text,
  venue_ids text[] not null,              -- array of venue IDs
  is_public boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.shared_lists enable row level security;

-- Public lists are viewable by everyone
create policy "Public lists are viewable by everyone"
  on public.shared_lists for select using (is_public = true);

-- Users can view their own private lists
create policy "Users can view own lists"
  on public.shared_lists for select using (
    profile_id in (
      select id from public.profiles where anon_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

create policy "Users can insert own lists"
  on public.shared_lists for insert with check (true);

create policy "Users can update own lists"
  on public.shared_lists for update using (
    profile_id in (
      select id from public.profiles where anon_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );

create policy "Users can delete own lists"
  on public.shared_lists for delete using (
    profile_id in (
      select id from public.profiles where anon_id = current_setting('request.jwt.claims', true)::json->>'sub'
    )
  );


-- 6. AGGREGATION VIEW — venue stats
-- Fast access to check-in count + thumbs up/down per venue
create or replace view public.venue_stats as
select
  v.venue_id,
  coalesce(c.checkin_count, 0) as checkin_count,
  coalesce(tu.thumbs_up_count, 0) as thumbs_up_count,
  coalesce(td.thumbs_down_count, 0) as thumbs_down_count
from (
  select distinct venue_id from public.checkins
  union
  select distinct venue_id from public.thumbs
) v
left join (
  select venue_id, count(*) as checkin_count
  from public.checkins
  group by venue_id
) c on v.venue_id = c.venue_id
left join (
  select venue_id, count(*) as thumbs_up_count
  from public.thumbs where direction = 'up'
  group by venue_id
) tu on v.venue_id = tu.venue_id
left join (
  select venue_id, count(*) as thumbs_down_count
  from public.thumbs where direction = 'down'
  group by venue_id
) td on v.venue_id = td.venue_id;


-- 7. REALTIME — enable for check-ins and thumbs
-- (Enable in Supabase Dashboard > Database > Replication > toggle on for checkins, thumbs)

-- 8. INDEX for fast lookups
create index idx_checkins_venue on public.checkins(venue_id);
create index idx_thumbs_venue on public.thumbs(venue_id);
create index idx_thumbs_direction on public.thumbs(venue_id, direction);
create index idx_user_saves_profile on public.user_saves(profile_id);
create index idx_shared_lists_slug on public.shared_lists(slug);
create index idx_profiles_anon on public.profiles(anon_id);
