-- Hubi Time - 0007_work_records
-- Tabela principal de registros de jornada. Um registro por usuario/dia.
-- Os quatro horarios sao opcionais e podem ser preenchidos progressivamente.

create table if not exists public.work_records (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    work_date date not null,

    entry_time time null,
    lunch_start time null,
    lunch_end time null,
    exit_time time null,

    day_type text not null default 'normal' check (
        day_type in ('normal', 'folga', 'ferias', 'feriado', 'atestado', 'ausencia', 'outro')
    ),
    notes text null,

    status text not null default 'active' check (status in ('active', 'archived')),
    archived_at timestamptz null,
    archived_by uuid null references auth.users(id),

    -- Concorrencia otimista: incrementado automaticamente a cada UPDATE (ver trigger).
    version integer not null default 1,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique (user_id, work_date)
);

create index if not exists idx_work_records_user_id on public.work_records(user_id);
create index if not exists idx_work_records_work_date on public.work_records(work_date);
create index if not exists idx_work_records_user_date on public.work_records(user_id, work_date);
create index if not exists idx_work_records_user_status on public.work_records(user_id, status);

comment on table public.work_records is
    'Registro diario de jornada. Delecao e sempre logica (status=archived); nunca DELETE fisico no fluxo normal.';
