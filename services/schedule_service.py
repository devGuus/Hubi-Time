"""Regras de negocio para vigencias de carga horaria."""
from __future__ import annotations

from datetime import date

from config.constants import DEFAULT_WEEKLY_HOURS
from models.schedule import WorkScheduleEntry
from repositories.schedule_repository import ScheduleRepository


class ScheduleService:
    def __init__(self, repository: ScheduleRepository):
        self._repo = repository

    def get_effective(self, user_id: str, at_date: date) -> WorkScheduleEntry | None:
        """Vigencia valida para `at_date`. None significa que o usuario ainda
        nao configurou nenhuma carga horaria - a UI deve orientar a configurar."""
        return self._repo.get_effective_at(user_id, at_date)

    def list_history(self, user_id: str) -> list[WorkScheduleEntry]:
        return self._repo.list_history(user_id)

    def create_vigencia(
        self,
        user_id: str,
        effective_from: date,
        weekly_hours: dict[str, float] | None = None,
        monthly_hours_override: float | None = None,
        notes: str | None = None,
    ) -> WorkScheduleEntry:
        entry = WorkScheduleEntry(
            id=None,
            user_id=user_id,
            effective_from=effective_from,
            weekly_hours=weekly_hours or dict(DEFAULT_WEEKLY_HOURS),
            monthly_hours_override=monthly_hours_override,
            notes=notes,
        )
        return self._repo.create(entry)

    @staticmethod
    def pick_effective(entries: list[WorkScheduleEntry], at_date: date) -> WorkScheduleEntry | None:
        """Seleciona, em uma lista ja carregada (ordem qualquer), a vigencia
        valida para `at_date`. Evita 1 consulta por dia ao montar relatorios
        / graficos que cobrem varios dias."""
        candidates = [e for e in entries if e.effective_from <= at_date]
        if not candidates:
            return None
        return max(candidates, key=lambda e: e.effective_from)
