-- =========================================================
-- recs — Supabase Database Schema
-- =========================================================
-- Run this in the Supabase SQL Editor after creating your project.
-- Requires Supabase Auth (email/password + Google OAuth).
-- =========================================================

-- 1. PROFILES
-- Linked to auth.users via id. Auto-created on first login.
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  display_name text default 'User',
  avatar_emoji text default '🙂',
  created_at timestamptz default now()
);

alter table public.profiles enable row level security;

-- Anyone can read profiles (needed for social features)
create policy "Profiles are viewable by everyone"
  on public.profiles for select using (true);

-- Users can insert their own profile
create policy "Users can insert own profile"
  on public.profiles for insert with check (auth.uid() = id);

-- Users can update their own profile
create policy "Users can update own profile"
  on public.profiles for update using (auth.uid() = id);


-- 2. FOLLOWS
-- Users can follow other users to see their activity
create table public.follows (
  id uuid primary key default gen_random_uuid(),
  follower_id uuid references public.profiles(id) on delete cascade,
  following_id uuid references public.profiles(id) on delete cascade,
  created_at timestamptz default now(),
  unique(follower_id, following_id)
);

alter table public.follows enable row level security;

-- Anyone can see follow relationships
create policy "Follows are viewable by everyone"
  on public.follows for select using (true);

-- Users can follow others
create policy "Users can insert own follows"
  on public.follows for insert with check (auth.uid() = follower_id);

-- Users can unfollow
create policy "Users can delete own follows"
  on public.follows for delete using (auth.uid() = follower_id);


-- 3. CHECK-INS ("Been Here")
create table public.checkins (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references public.profiles(id) on delete cascade,
  venue_id text not null,
  created_at timestamptz default now(),
  unique(profile_id, venue_id)
);

alter table public.checkins enable row level security;

create policy "Check-ins are viewable by everyone"
  on public.checkins for select using (true);

create policy "Users can insert own check-ins"
  on public.checkins for insert with check (auth.uid() = profile_id);

create policy "Users can delete own check-ins"
  on public.checkins for delete using (auth.uid() = profile_id);


-- 4. THUMBS (up/down ratings)
create table public.thumbs (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references public.profiles(id) on delete cascade,
  venue_id text not null,
  direction text not null check (direction in ('up', 'down')),
  created_at timestamptz default now(),
  unique(profile_id, venue_id)
);

alter table public.thumbs enable row level security;

create policy "Thumbs are viewable by everyone"
  on public.thumbs for select using (true);

create policy "Users can insert own thumbs"
  on public.thumbs for insert with check (auth.uid() = profile_id);

create policy "Users can update own thumbs"
  on public.thumbs for update using (auth.uid() = profile_id);

create policy "Users can delete own thumbs"
  on public.thumbs for delete using (auth.uid() = profile_id);


-- 5. USER SAVES (synced favorites)
create table public.user_saves (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references public.profiles(id) on delete cascade,
  venue_id text not null,
  created_at timestamptz default now(),
  unique(profile_id, venue_id)
);

alter table public.user_saves enable row level security;

create policy "Users can view own saves"
  on public.user_saves for select using (auth.uid() = profile_id);

create policy "Users can insert own saves"
  on public.user_saves for insert with check (auth.uid() = profile_id);

create policy "Users can delete own saves"
  on public.user_saves for delete using (auth.uid() = profile_id);


-- 6. SHARED LISTS
create table public.shared_lists (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid references public.profiles(id) on delete cascade,
  slug text unique not null,
  title text not null,
  description text,
  venue_ids text[] not null,
  is_public boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.shared_lists enable row level security;

create policy "Public lists are viewable by everyone"
  on public.shared_lists for select using (is_public = true);

create policy "Users can view own lists"
  on public.shared_lists for select using (auth.uid() = profile_id);

create policy "Users can insert own lists"
  on public.shared_lists for insert with check (auth.uid() = profile_id);

create policy "Users can update own lists"
  on public.shared_lists for update using (auth.uid() = profile_id);

create policy "Users can delete own lists"
  on public.shared_lists for delete using (auth.uid() = profile_id);


-- 7. AGGREGATION VIEW — venue stats
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
  from public.checkins group by venue_id
) c on v.venue_id = c.venue_id
left join (
  select venue_id, count(*) as thumbs_up_count
  from public.thumbs where direction = 'up' group by venue_id
) tu on v.venue_id = tu.venue_id
left join (
  select venue_id, count(*) as thumbs_down_count
  from public.thumbs where direction = 'down' group by venue_id
) td on v.venue_id = td.venue_id;


-- 8. INDEXES
create index idx_checkins_venue on public.checkins(venue_id);
create index idx_checkins_profile on public.checkins(profile_id);
create index idx_thumbs_venue on public.thumbs(venue_id);
create index idx_thumbs_direction on public.thumbs(venue_id, direction);
create index idx_user_saves_profile on public.user_saves(profile_id);
create index idx_shared_lists_slug on public.shared_lists(slug);
create index idx_follows_follower on public.follows(follower_id);
create index idx_follows_following on public.follows(following_id);

-- 9. REALTIME — enable for checkins, thumbs, follows
-- (Enable in Supabase Dashboard > Database > Replication > toggle on)
