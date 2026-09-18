"""Acesso a dados de holidays."""
from __future__ import annotations

from datetime import date

from supabase import Client

from models.notification import Holiday
from repositories.base import translate_errors

TABLE = "holidays"


class HolidayRepository:
    def __init__(self, client: Client):
        self._client = client

    def list_in_range(self, user_id: str, start_date: date, end_date: date) -> list[Holiday]:
        with translate_errors("listar feriados"):
            resp = (
                self._client.table(TABLE)
                .select("*")
                .eq("user_id", user_id)
                .gte("holiday_date", start_date.isoformat())
                .lte("holiday_date", end_date.isoformat())
                .execute()
            )
        return [Holiday.from_dict(row) for row in (resp.data or [])]

    def create(self, holiday: Holiday) -> Holiday:
        with translate_errors("cadastrar feriado"):
            resp = self._client.table(TABLE).insert(holiday.to_insert_payload()).execute()
        return Holiday.from_dict(resp.data[0])

    def delete(self, user_id: str, holiday_id: str) -> None:
        with translate_errors("remover feriado"):
            self._client.table(TABLE).delete().eq("user_id", user_id).eq("id", holiday_id).execute()
