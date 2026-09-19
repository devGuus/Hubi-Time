-- Hubi Time - 0014_grants
-- RLS (policies) e GRANT (privilegios de tabela) sao camadas independentes
-- no Postgres: uma policy de RLS so e avaliada DEPOIS que o papel ja tem o
-- privilegio basico (SELECT/INSERT/UPDATE/DELETE) na tabela. As migrations
-- anteriores criaram as policies mas nao concederam esses privilegios ao
-- papel "authenticated", causando "permission denied for table X" em toda
-- consulta feita pelo aplicativo (mesmo com policies corretas).

grant usage on schema public to authenticated;

grant select, insert, update on public.profiles to authenticated;
grant select, insert, update on public.user_settings to authenticated;
grant select, insert on public.work_schedule_history to authenticated;
grant select, insert on public.salary_history to authenticated;
grant select, insert, update on public.overtime_rules to authenticated;
grant select, insert, update on public.work_records to authenticated;

-- Somente SELECT: a gravacao de work_record_history acontece exclusivamente
-- pela funcao SECURITY DEFINER do trigger (que roda como dona da tabela e
-- ignora privilegios de GRANT), entao "authenticated" nunca recebe INSERT
-- aqui - e assim que o historico permanece a prova de adulteracao.
grant select on public.work_record_history to authenticated;

grant select, insert, update, delete on public.holidays to authenticated;
grant select, insert, update, delete on public.notifications to authenticated;
grant select, insert on public.audit_log to authenticated;
