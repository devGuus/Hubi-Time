-- Hubi Time - 0006_overtime_rules
-- Regras configuraveis de percentual de hora extra (ex.: 50%, 100%).
-- Nao fixamos regras trabalhistas no codigo; o usuario define e mantem vigencia.

create table if not exists public.overtime_rules (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    name text not null,
    percentage numeric(5, 2) not null check (percentage >= 0),
    effective_from date not null,
    created_at timestamptz not null default now(),
    unique (user_id, name, effective_from)
);

create index if not exists idx_overtime_rules_user_effective
    on public.overtime_rules(user_id, effective_from desc);

comment on table public.overtime_rules is 'Percentuais de hora extra configuraveis por usuario, com vigencia.';
