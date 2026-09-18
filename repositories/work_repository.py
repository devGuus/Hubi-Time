"""Acesso a dados de work_records e work_record_history."""
from __future__ import annotations

from datetime import date, datetime, timezone

from supabase import Client

from config.constants import RecordStatus
from models.work_record import WorkRecord, WorkRecordHistoryEntry
from repositories.base import translate_errors
from repositories.exceptions import ConflictError, NotFoundError

TABLE = "work_records"
HISTORY_TABLE = "work_record_history"


class WorkRepository:
    def __init__(self, client: Client):
        self._client = client

    def get_by_date(self, user_id: str, work_date: date) -> WorkRecord | None:
        with translate_errors("buscar registro do dia"):
            resp = (
                self._client.table(TABLE)
                .select("*")
                .eq("user_id", user_id)
                .eq("work_date", work_date.isoformat())
                .limit(1)
                .execute()
            )
        rows = resp.data or []
        return WorkRecord.from_dict(rows[0]) if rows else None

    def get_by_id(self, user_id: str, record_id: str) -> WorkRecord:
        with translate_errors("buscar registro"):
            resp = (
                self._client.table(TABLE)
                .select("*")
                .eq("user_id", user_id)
                .eq("id", record_id)
                .limit(1)
                .execute()
            )
        rows = resp.data or []
        if not rows:
            raise NotFoundError("Registro nao encontrado.")
        return WorkRecord.from_dict(rows[0])

    def list_by_range(
        self,
        user_id: str,
        start_date: date,
        end_date: date,
        include_archived: bool = False,
    ) -> list[WorkRecord]:
        with translate_errors("listar registros do periodo"):
            query = (
                self._client.table(TABLE)
                .select("*")
                .eq("user_id", user_id)
                .gte("work_date", start_date.isoformat())
                .lte("work_date", end_date.isoformat())
            )
            if not include_archived:
                query = query.eq("status", RecordStatus.ACTIVE.value)
            resp = query.order("work_date", desc=False).execute()
        return [WorkRecord.from_dict(row) for row in (resp.data or [])]

    def list_archived(self, user_id: str) -> list[WorkRecord]:
        with translate_errors("listar registros arquivados"):
            resp = (
                self._client.table(TABLE)
                .select("*")
                .eq("user_id", user_id)
                .eq("status", RecordStatus.ARCHIVED.value)
                .order("work_date", desc=True)
                .execute()
            )
        return [WorkRecord.from_dict(row) for row in (resp.data or [])]

    def create(self, record: WorkRecord) -> WorkRecord:
        with translate_errors("criar registro de jornada"):
            resp = self._client.table(TABLE).insert(record.to_upsert_payload()).execute()
        return WorkRecord.from_dict(resp.data[0])

    def update(self, record_id: str, user_id: str, expected_version: int, record: WorkRecord) -> WorkRecord:
        """Atualiza com verificacao de concorrencia otimista.

        Se a versao no banco nao bater com `expected_version`, significa que o
        registro foi alterado por outra sessao/dispositivo desde a leitura, e
        uma ConflictError e levantada para a service layer decidir como agir.
        """
        with translate_errors("atualizar registro de jornada"):
            resp = (
                self._client.table(TABLE)
                .update(record.to_upsert_payload())
                .eq("id", record_id)
                .eq("user_id", user_id)
                .eq("version", expected_version)
                .execute()
            )
        rows = resp.data or []
        if not rows:
            raise ConflictError(
                "Este registro foi alterado em outro lugar. Recarregue o dia e tente novamente."
            )
        return WorkRecord.from_dict(rows[0])

    def archive(self, record_id: str, user_id: str, archived_by: str) -> WorkRecord:
        with translate_errors("arquivar registro"):
            resp = (
                self._client.table(TABLE)
                .update(
                    {
                        "status": RecordStatus.ARCHIVED.value,
                        "archived_at": datetime.now(timezone.utc).isoformat(),
                        "archived_by": archived_by,
                    }
                )
                .eq("id", record_id)
                .eq("user_id", user_id)
                .execute()
            )
        rows = resp.data or []
        if not rows:
            raise NotFoundError("Registro nao encontrado para arquivar.")
        return WorkRecord.from_dict(rows[0])

    def restore(self, record_id: str, user_id: str) -> WorkRecord:
        with translate_errors("restaurar registro"):
            resp = (
                self._client.table(TABLE)
                .update({"status": RecordStatus.ACTIVE.value, "archived_at": None, "archived_by": None})
                .eq("id", record_id)
                .eq("user_id", user_id)
                .execute()
            )
        rows = resp.data or []
        if not rows:
            raise NotFoundError("Registro nao encontrado para restaurar.")
        return WorkRecord.from_dict(rows[0])

    def get_history(self, user_id: str, work_record_id: str) -> list[WorkRecordHistoryEntry]:
        with translate_errors("buscar historico do registro"):
            resp = (
                self._client.table(HISTORY_TABLE)
                .select("*")
                .eq("user_id", user_id)
                .eq("work_record_id", work_record_id)
                .order("changed_at", desc=False)
                .execute()
            )
        return [WorkRecordHistoryEntry.from_dict(row) for row in (resp.data or [])]
