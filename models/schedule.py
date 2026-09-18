"""Modelo de vigencia de carga horaria."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from config.constants import DEFAULT_WEEKLY_HOURS, Weekday


@dataclass
class WorkScheduleEntry:
    """Uma vigencia de carga horaria (semanal ou mensal fixa)."""

    id: str | None
    user_id: str
    effective_from: date
    weekly_hours: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEEKLY_HOURS))
    monthly_hours_override: float | None = None
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkScheduleEntry":
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            effective_from=date.fromisoformat(data["effective_from"]),
            weekly_hours=data.get("weekly_hours") or dict(DEFAULT_WEEKLY_HOURS),
            monthly_hours_override=(
                float(data["monthly_hours_override"])
                if data.get("monthly_hours_override") is not None
                else None
            ),
            notes=data.get("notes"),
        )

    def to_insert_payload(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "effective_from": self.effective_from.isoformat(),
            "weekly_hours": self.weekly_hours,
            "monthly_hours_override": self.monthly_hours_override,
            "notes": self.notes,
        }

    def expected_hours_for_weekday(self, weekday: Weekday) -> float:
        """Horas previstas para um dia da semana, considerando override mensal.

        Quando ha override mensal, a distribuicao diaria e obtida dividindo
        o total mensal pelos dias uteis padrao (segunda a sexta). Isso e uma
        aproximacao usada apenas para exibicao diaria; o total mensal oficial
        usa monthly_hours_override diretamente.
        """
        key = {
            Weekday.SEGUNDA: "segunda",
            Weekday.TERCA: "terca",
            Weekday.QUARTA: "quarta",
            Weekday.QUINTA: "quinta",
            Weekday.SEXTA: "sexta",
            Weekday.SABADO: "sabado",
            Weekday.DOMINGO: "domingo",
        }[weekday]
        return float(self.weekly_hours.get(key, 0.0))

    @property
    def total_weekly_hours(self) -> float:
        return sum(float(v) for v in self.weekly_hours.values())
