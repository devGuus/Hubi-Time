-- Hubi Time - 0003_user_settings
-- Preferencias do usuario: tema, notificacoes habilitadas, localizacao.

create table if not exists public.user_settings (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique references auth.users(id) on delete cascade,
    theme text not null default 'light' check (theme in ('light', 'dark')),
    locale text not null default 'pt-BR',
    notifications_enabled jsonb not null default '{
        "missing_lunch_return": true,
        "incomplete_today": true,
        "time_inconsistency": true,
        "incomplete_month": true
    }'::jsonb,
    keep_signed_in boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_user_settings_user_id on public.user_settings(user_id);

comment on table public.user_settings is 'Preferencias de interface e notificacoes por usuario.';
