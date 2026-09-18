"""Acesso a dados de salary_history e overtime_rules."""
from __future__ import annotations

from datetime import date

from supabase import Client

from models.salary import OvertimeRule, SalaryEntry
from repositories.base import translate_errors

SALARY_TABLE = "salary_history"
OVERTIME_TABLE = "overtime_rules"


class SalaryRepository:
    def __init__(self, client: Client):
        self._client = client

    def list_history(self, user_id: str) -> list[SalaryEntry]:
        with translate_errors("listar historico salarial"):
            resp = (
                self._client.table(SALARY_TABLE)
                .select("*")
                .eq("user_id", user_id)
                .order("effective_from", desc=True)
                .execute()
            )
        return [SalaryEntry.from_dict(row) for row in (resp.data or [])]

    def get_effective_at(self, user_id: str, at_date: date) -> SalaryEntry | None:
        with translate_errors("buscar salario vigente"):
            resp = (
                self._client.table(SALARY_TABLE)
                .select("*")
                .eq("user_id", user_id)
                .lte("effective_from", at_date.isoformat())
                .order("effective_from", desc=True)
                .limit(1)
                .execute()
            )
        rows = resp.data or []
        return SalaryEntry.from_dict(rows[0]) if rows else None

    def create(self, entry: SalaryEntry) -> SalaryEntry:
        with translate_errors("criar vigencia salarial"):
            resp = self._client.table(SALARY_TABLE).insert(entry.to_insert_payload()).execute()
        return SalaryEntry.from_dict(resp.data[0])

    def list_overtime_rules(self, user_id: str) -> list[OvertimeRule]:
        with translate_errors("listar regras de hora extra"):
            resp = (
                self._client.table(OVERTIME_TABLE)
                .select("*")
                .eq("user_id", user_id)
                .order("effective_from", desc=True)
                .execute()
            )
        return [OvertimeRule.from_dict(row) for row in (resp.data or [])]

    def create_overtime_rule(self, rule: OvertimeRule) -> OvertimeRule:
        with translate_errors("criar regra de hora extra"):
            resp = self._client.table(OVERTIME_TABLE).insert(rule.to_insert_payload()).execute()
        return OvertimeRule.from_dict(resp.data[0])
