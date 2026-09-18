-- Hubi Time - 0009_holidays
-- Feriados/datas especiais cadastrados pelo usuario, usados no calendario
-- e nos calculos (um feriado nao gera saldo negativo automatico).

create table if not exists public.holidays (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    holiday_date date not null,
    name text not null,
    created_at timestamptz not null default now(),
    unique (user_id, holiday_date)
);

create index if not exists idx_holidays_user_date on public.holidays(user_id, holiday_date);

comment on table public.holidays is 'Feriados cadastrados por usuario.';
