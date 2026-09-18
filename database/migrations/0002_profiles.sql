-- Hubi Time - 0002_profiles
-- Perfil publico do usuario, 1:1 com auth.users.

create table if not exists public.profiles (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique references auth.users(id) on delete cascade,
    name text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_profiles_user_id on public.profiles(user_id);

comment on table public.profiles is 'Dados publicos de perfil do usuario (1:1 com auth.users).';
