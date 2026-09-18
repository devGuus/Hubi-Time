-- Hubi Time - 0010_notifications
-- Notificacoes/alertas exibidos ao usuario dentro da aplicacao.

create table if not exists public.notifications (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    type text not null,
    message text not null,
    read boolean not null default false,
    metadata jsonb null,
    created_at timestamptz not null default now()
);

create index if not exists idx_notifications_user_read on public.notifications(user_id, read);
create index if not exists idx_notifications_user_created on public.notifications(user_id, created_at desc);

comment on table public.notifications is 'Notificacoes/alertas do usuario dentro da aplicacao.';
