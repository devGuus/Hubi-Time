-- Hubi Time - 0011_audit_log
-- Log de auditoria generico para acoes fora do ciclo de vida de work_records
-- (ex.: alteracao de salario, de carga horaria, de configuracoes, de perfil).

create table if not exists public.audit_log (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    entity text not null,
    entity_id uuid null,
    action text not null,
    metadata jsonb null,
    created_at timestamptz not null default now()
);

create index if not exists idx_audit_log_user_created on public.audit_log(user_id, created_at desc);
create index if not exists idx_audit_log_entity on public.audit_log(entity, entity_id);

comment on table public.audit_log is 'Log de auditoria generico (nao relacionado a work_records).';
