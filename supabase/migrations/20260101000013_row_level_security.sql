-- Hubi Time - 0013_row_level_security
-- Habilita RLS em todas as tabelas e cria policies que restringem cada
-- usuario aos seus proprios dados. O app desktop usa somente a chave anon,
-- entao TODO acesso passa obrigatoriamente por estas policies.

-- =========================================================================
-- profiles
-- =========================================================================
alter table public.profiles enable row level security;

create policy profiles_select_own on public.profiles
    for select using (auth.uid() = user_id);

create policy profiles_insert_own on public.profiles
    for insert with check (auth.uid() = user_id);

create policy profiles_update_own on public.profiles
    for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- sem policy de DELETE: perfil nao e removido pelo usuario final.

-- =========================================================================
-- user_settings
-- =========================================================================
alter table public.user_settings enable row level security;

create policy user_settings_select_own on public.user_settings
    for select using (auth.uid() = user_id);

create policy user_settings_insert_own on public.user_settings
    for insert with check (auth.uid() = user_id);

create policy user_settings_update_own on public.user_settings
    for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- =========================================================================
-- work_schedule_history (append-only do ponto de vista funcional: a UI so
-- insere novas vigencias, nunca edita as antigas; UPDATE fica disponivel
-- apenas para corrigir a vigencia mais recente antes de outra ser criada,
-- por isso mantemos a policy de update restrita ao proprio usuario).
-- =========================================================================
alter table public.work_schedule_history enable row level security;

create policy work_schedule_history_select_own on public.work_schedule_history
    for select using (auth.uid() = user_id);

create policy work_schedule_history_insert_own on public.work_schedule_history
    for insert with check (auth.uid() = user_id);

-- =========================================================================
-- salary_history (dados financeiros privados)
-- =========================================================================
alter table public.salary_history enable row level security;

create policy salary_history_select_own on public.salary_history
    for select using (auth.uid() = user_id);

create policy salary_history_insert_own on public.salary_history
    for insert with check (auth.uid() = user_id);

-- =========================================================================
-- overtime_rules
-- =========================================================================
alter table public.overtime_rules enable row level security;

create policy overtime_rules_select_own on public.overtime_rules
    for select using (auth.uid() = user_id);

create policy overtime_rules_insert_own on public.overtime_rules
    for insert with check (auth.uid() = user_id);

create policy overtime_rules_update_own on public.overtime_rules
    for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- =========================================================================
-- work_records
-- =========================================================================
alter table public.work_records enable row level security;

create policy work_records_select_own on public.work_records
    for select using (auth.uid() = user_id);

create policy work_records_insert_own on public.work_records
    for insert with check (auth.uid() = user_id);

create policy work_records_update_own on public.work_records
    for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- sem policy de DELETE: exclusao e sempre logica (status='archived').

-- =========================================================================
-- work_record_history
-- Somente SELECT para o dono. NENHUMA policy de INSERT/UPDATE/DELETE e
-- concedida ao papel authenticated: as linhas so podem ser criadas pela
-- funcao SECURITY DEFINER work_records_audit(), que roda com privilegios
-- do dono da tabela e ignora RLS. Isso impede que o usuario grave
-- historico falso diretamente pela API.
-- =========================================================================
alter table public.work_record_history enable row level security;

create policy work_record_history_select_own on public.work_record_history
    for select using (auth.uid() = user_id);

-- =========================================================================
-- holidays
-- =========================================================================
alter table public.holidays enable row level security;

create policy holidays_select_own on public.holidays
    for select using (auth.uid() = user_id);

create policy holidays_insert_own on public.holidays
    for insert with check (auth.uid() = user_id);

create policy holidays_update_own on public.holidays
    for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy holidays_delete_own on public.holidays
    for delete using (auth.uid() = user_id);

-- =========================================================================
-- notifications
-- =========================================================================
alter table public.notifications enable row level security;

create policy notifications_select_own on public.notifications
    for select using (auth.uid() = user_id);

create policy notifications_update_own on public.notifications
    for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy notifications_delete_own on public.notifications
    for delete using (auth.uid() = user_id);

-- Notificacoes sao geradas pelo proprio app em nome do usuario logado
-- (ex.: ao detectar inconsistencia), entao INSERT tambem fica liberado
-- apenas para o dono.
create policy notifications_insert_own on public.notifications
    for insert with check (auth.uid() = user_id);

-- =========================================================================
-- audit_log (generico) - somente leitura + insercao pelo proprio usuario;
-- sem UPDATE/DELETE para preservar integridade.
-- =========================================================================
alter table public.audit_log enable row level security;

create policy audit_log_select_own on public.audit_log
    for select using (auth.uid() = user_id);

create policy audit_log_insert_own on public.audit_log
    for insert with check (auth.uid() = user_id);
