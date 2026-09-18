"""Modelos de historico salarial e regras de hora extra."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass
class SalaryEntry:
    """Uma vigencia salarial. Nunca sobrescrita; cada mudanca cria uma linha."""

    id: str | None
    user_id: str
    effective_from: date
    salary: Decimal
    monthly_hours: Decimal

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SalaryEntry":
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            effective_from=date.fromisoformat(data["effective_from"]),
            salary=Decimal(str(data["salary"])),
            monthly_hours=Decimal(str(data["monthly_hours"])),
        )

    def to_insert_payload(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "effective_from": self.effective_from.isoformat(),
            "salary": str(self.salary),
            "monthly_hours": str(self.monthly_hours),
        }

    @property
    def hourly_rate(self) -> Decimal:
        if self.monthly_hours <= 0:
            return Decimal("0")
        return (self.salary / self.monthly_hours).quantize(Decimal("0.01"))


@dataclass
class OvertimeRule:
    """Percentual configuravel de hora extra (ex.: 50%, 100%), com vigencia."""

    id: str | None
    user_id: str
    name: str
    percentage: Decimal
    effective_from: date

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OvertimeRule":
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            name=data["name"],
            percentage=Decimal(str(data["percentage"])),
            effective_from=date.fromisoformat(data["effective_from"]),
        )

    def to_insert_payload(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "percentage": str(self.percentage),
            "effective_from": self.effective_from.isoformat(),
        }

    @property
    def multiplier(self) -> Decimal:
        """Ex.: 50% -> 1.50 (valor pago por hora extra sobre o valor normal)."""
        return Decimal("1") + (self.percentage / Decimal("100"))
