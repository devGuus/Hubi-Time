-- Hubi Time - 0008_work_record_history
-- Historico de auditoria, append-only, preenchido automaticamente por trigger
-- (ver 0012_functions_and_triggers.sql). Usuarios comuns NAO tem permissao de
-- INSERT/UPDATE/DELETE nesta tabela (ver 0013_row_level_security.sql) -- somente
-- a funcao SECURITY DEFINER do trigger pode gravar aqui.

create table if not exists public.work_record_history (
    id uuid primary key default gen_random_uuid(),
    work_record_id uuid not null references public.work_records(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    action text not null check (action in ('CREATE', 'UPDATE', 'ARCHIVE', 'RESTORE')),
    field_changed text null,
    old_value text null,
    new_value text null,
    changed_at timestamptz not null default now(),
    changed_by uuid not null references auth.users(id)
);

create index if not exists idx_work_record_history_record_id on public.work_record_history(work_record_id);
create index if not exists idx_work_record_history_user_id on public.work_record_history(user_id);
create index if not exists idx_work_record_history_changed_at on public.work_record_history(changed_at desc);

comment on table public.work_record_history is
    'Trilha de auditoria append-only dos registros de jornada. Gravada exclusivamente por trigger SECURITY DEFINER.';
