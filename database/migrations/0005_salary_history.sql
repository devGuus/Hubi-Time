-- Hubi Time - 0005_salary_history
-- Historico de vigencias salariais. Nunca sobrescrito.

create table if not exists public.salary_history (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    effective_from date not null,
    salary numeric(12, 2) not null check (salary >= 0),
    monthly_hours numeric(6, 2) not null check (monthly_hours > 0),
    created_at timestamptz not null default now(),
    unique (user_id, effective_from)
);

create index if not exists idx_salary_history_user_effective
    on public.salary_history(user_id, effective_from desc);

comment on table public.salary_history is 'Vigencias historicas de salario/carga mensal por usuario. Dados financeiros privados.';
