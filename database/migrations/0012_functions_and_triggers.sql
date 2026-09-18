-- Hubi Time - 0012_functions_and_triggers
-- Funcoes auxiliares e triggers:
--   1. set_updated_at            -> mantem updated_at atualizado
--   2. bump_version              -> concorrencia otimista em work_records
--   3. handle_new_user           -> cria profile/user_settings ao registrar usuario
--   4. work_records_audit        -> grava work_record_history automaticamente
--   5. prevent_history_mutation  -> bloqueia UPDATE/DELETE em work_record_history

-- =========================================================================
-- 1. updated_at automatico
-- =========================================================================
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_profiles_updated_at on public.profiles;
create trigger trg_profiles_updated_at
    before update on public.profiles
    for each row execute function public.set_updated_at();

drop trigger if exists trg_user_settings_updated_at on public.user_settings;
create trigger trg_user_settings_updated_at
    before update on public.user_settings
    for each row execute function public.set_updated_at();

drop trigger if exists trg_work_records_updated_at on public.work_records;
create trigger trg_work_records_updated_at
    before update on public.work_records
    for each row execute function public.set_updated_at();

-- =========================================================================
-- 2. Concorrencia otimista em work_records
-- =========================================================================
create or replace function public.bump_version()
returns trigger
language plpgsql
as $$
begin
    new.version = old.version + 1;
    return new;
end;
$$;

drop trigger if exists trg_work_records_bump_version on public.work_records;
create trigger trg_work_records_bump_version
    before update on public.work_records
    for each row execute function public.bump_version();

-- =========================================================================
-- 3. Criacao automatica de profile + user_settings ao cadastrar usuario
--    SECURITY DEFINER: necessario pois o trigger dispara no schema auth,
--    fora do contexto JWT do usuario. search_path fixo previne hijacking.
-- =========================================================================
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
    insert into public.profiles (user_id, name)
    values (new.id, coalesce(new.raw_user_meta_data ->> 'name', ''))
    on conflict (user_id) do nothing;

    insert into public.user_settings (user_id)
    values (new.id)
    on conflict (user_id) do nothing;

    return new;
end;
$$;

drop trigger if exists trg_auth_user_created on auth.users;
create trigger trg_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- =========================================================================
-- 4. Auditoria automatica de work_records -> work_record_history
--    SECURITY DEFINER: garante que a trilha de auditoria seja gravada
--    mesmo sem conceder INSERT na tabela de historico ao usuario comum
--    (ver 0013_row_level_security.sql). Isso torna o historico confiavel:
--    o cliente nao pode inserir linhas falsas diretamente via API.
-- =========================================================================
create or replace function public.work_records_audit()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
    actor uuid := auth.uid();
begin
    if actor is null then
        actor := coalesce(new.user_id, old.user_id);
    end if;

    if tg_op = 'INSERT' then
        if new.entry_time is not null then
            insert into public.work_record_history
                (work_record_id, user_id, action, field_changed, old_value, new_value, changed_by)
            values (new.id, new.user_id, 'CREATE', 'entry_time', null, new.entry_time::text, actor);
        end if;
        if new.lunch_start is not null then
            insert into public.work_record_history
                (work_record_id, user_id, action, field_changed, old_value, new_value, changed_by)
            values (new.id, new.user_id, 'CREATE', 'lunch_start', null, new.lunch_start::text, actor);
        end if;
        if new.lunch_end is not null then
            insert into public.work_record_history
                (work_record_id, user_id, action, field_changed, old_value, new_value, changed_by)
            values (new.id, new.user_id, 'CREATE', 'lunch_end', null, new.lunch_end::text, actor);
        end if;
        if new.exit_time is not null then
            insert into public.work_record_history
                (work_record_id, user_id, action, field_changed, old_value, new_value, changed_by)
            values (new.id, new.user_id, 'CREATE', 'exit_time', null, new.exit_time::text, actor);
        end if;
        if new.notes is not null and new.notes <> '' then
            insert into public.work_record_history
                (work_record_id, user_id, action, field_changed, old_value, new_value, changed_by)
            values (new.id, new.user_id, 'CREATE', 'notes', null, new.notes, actor);
        end if;
        insert into public.work_record_history
            (work_record_id, user_id, action, field_changed, old_value, new_value, changed_by)
        values (new.id, new.user_id, 'CREATE', 'day_type', null, new.day_type, actor);

        return new;
    end if;

    if tg_op = 'UPDATE' then
        if old.entry_time is distinct from new.entry_time then
            insert into public.work_record_history
                (work_record_id, user_id, action, field_changed, old_value, new_value, changed_by)
            values (new.id, new.user_id, 'UPDATE', 'entry_time', old.entry_time::text, new.entry_time::text, actor);
        end if;
        if old.lunch_start is distinct from new.lunch_start then
            insert into public.work_record_history
                (work_record_id, user_id, action, field_changed, old_value, new_value, changed_by)
            values (new.id, new.user_id, 'UPDATE', 'lunch_start', old.lunch_start::text, new.lunch_start::text, actor);
        end if;
        if old.lunch_end is distinct from new.lunch_end then
            insert into public.work_record_history
                (work_record_id, user_id, action, field_changed, old_value, new_value, changed_by)
            values (new.id, new.user_id, 'UPDATE', 'lunch_end', old.lunch_end::text, new.lunch_end::text, actor);
        end if;
        if old.exit_time is distinct from new.exit_time then
            insert into public.work_record_history
                (work_record_id, user_id, action, field_changed, old_value, new_value, changed_by)
            values (new.id, new.user_id, 'UPDATE', 'exit_time', old.exit_time::text, new.exit_time::text, actor);
        end if;
        if old.day_type is distinct from new.day_type then
            insert into public.work_record_history
                (work_record_id, user_id, action, field_changed, old_value, new_value, changed_by)
            values (new.id, new.user_id, 'UPDATE', 'day_type', old.day_type, new.day_type, actor);
        end if;
        if old.notes is distinct from new.notes then
            insert into public.work_record_history
                (work_record_id, user_id, action, field_changed, old_value, new_value, changed_by)
            values (new.id, new.user_id, 'UPDATE', 'notes', old.notes, new.notes, actor);
        end if;
        if old.status is distinct from new.status then
            insert into public.work_record_history
                (work_record_id, user_id, action, field_changed, old_value, new_value, changed_by)
            values (
                new.id, new.user_id,
                case when new.status = 'archived' then 'ARCHIVE' else 'RESTORE' end,
                'status', old.status, new.status, actor
            );
        end if;

        return new;
    end if;

    return coalesce(new, old);
end;
$$;

drop trigger if exists trg_work_records_audit on public.work_records;
create trigger trg_work_records_audit
    after insert or update on public.work_records
    for each row execute function public.work_records_audit();

-- =========================================================================
-- 5. Protecao adicional: ninguem (nem via bypass de RLS) atualiza ou apaga
--    linhas do historico. Defesa em profundidade alem das policies de RLS.
-- =========================================================================
create or replace function public.prevent_history_mutation()
returns trigger
language plpgsql
as $$
begin
    raise exception 'work_record_history e append-only: UPDATE/DELETE nao permitido';
end;
$$;

drop trigger if exists trg_prevent_history_update on public.work_record_history;
create trigger trg_prevent_history_update
    before update on public.work_record_history
    for each row execute function public.prevent_history_mutation();

drop trigger if exists trg_prevent_history_delete on public.work_record_history;
create trigger trg_prevent_history_delete
    before delete on public.work_record_history
    for each row execute function public.prevent_history_mutation();
