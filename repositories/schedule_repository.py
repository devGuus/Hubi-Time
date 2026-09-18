"""Acesso a dados de work_schedule_history."""
from __future__ import annotations

from datetime import date

from supabase import Client

from models.schedule import WorkScheduleEntry
from repositories.base import translate_errors

TABLE = "work_schedule_history"


class ScheduleRepository:
    def __init__(self, client: Client):
        self._client = client

    def list_history(self, user_id: str) -> list[WorkScheduleEntry]:
        with translate_errors("listar historico de carga horaria"):
            resp = (
                self._client.table(TABLE)
                .select("*")
                .eq("user_id", user_id)
                .order("effective_from", desc=True)
                .execute()
            )
        return [WorkScheduleEntry.from_dict(row) for row in (resp.data or [])]

    def get_effective_at(self, user_id: str, at_date: date) -> WorkScheduleEntry | None:
        with translate_errors("buscar carga horaria vigente"):
            resp = (
                self._client.table(TABLE)
                .select("*")
                .eq("user_id", user_id)
                .lte("effective_from", at_date.isoformat())
                .order("effective_from", desc=True)
                .limit(1)
                .execute()
            )
        rows = resp.data or []
        return WorkScheduleEntry.from_dict(rows[0]) if rows else None

    def create(self, entry: WorkScheduleEntry) -> WorkScheduleEntry:
        with translate_errors("criar vigencia de carga horaria"):
            resp = self._client.table(TABLE).insert(entry.to_insert_payload()).execute()
        return WorkScheduleEntry.from_dict(resp.data[0])
