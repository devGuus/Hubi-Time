-- Hubi Time - 0004_work_schedule_history
-- Historico de vigencias da carga horaria configurada pelo usuario.
-- Nunca sobrescrito: cada mudanca cria uma nova linha com effective_from.

create table if not exists public.work_schedule_history (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    effective_from date not null,
    -- Horas por dia da semana, em horas decimais. Chaves: segunda..domingo.
    weekly_hours jsonb not null default '{
        "segunda": 8, "terca": 8, "quarta": 8, "quinta": 8,
        "sexta": 8, "sabado": 0, "domingo": 0
    }'::jsonb,
    -- Se preenchido, o usuario optou por configurar carga mensal fixa
    -- em vez da distribuicao semanal acima.
    monthly_hours_override numeric(6, 2) null check (monthly_hours_override is null or monthly_hours_override > 0),
    notes text null,
    created_at timestamptz not null default now(),
    unique (user_id, effective_from)
);

create index if not exists idx_work_schedule_history_user_effective
    on public.work_schedule_history(user_id, effective_from desc);

comment on table public.work_schedule_history is 'Vigencias historicas de carga horaria por usuario. Append-only pela aplicacao.';
