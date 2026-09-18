"""Regras de negocio para historico salarial, horas extras e estimativas
financeiras pessoais. Os valores aqui sao SEMPRE estimativas de controle
pessoal, nunca uma folha de pagamento oficial.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from models.salary import OvertimeRule, SalaryEntry
from repositories.salary_repository import SalaryRepository
from services.calculation_service import CalculationService, PeriodSummary


@dataclass
class FinancialEstimate:
    hourly_rate: Decimal
    regular_value: Decimal
    overtime_value: Decimal

    @property
    def total_value(self) -> Decimal:
        return self.regular_value + self.overtime_value

    @classmethod
    def empty(cls) -> "FinancialEstimate":
        return cls(hourly_rate=Decimal("0"), regular_value=Decimal("0"), overtime_value=Decimal("0"))


class SalaryService:
    def __init__(self, repository: SalaryRepository):
        self._repo = repository

    def get_effective(self, user_id: str, at_date: date) -> SalaryEntry | None:
        return self._repo.get_effective_at(user_id, at_date)

    def list_history(self, user_id: str) -> list[SalaryEntry]:
        return self._repo.list_history(user_id)

    def create_vigencia(
        self, user_id: str, effective_from: date, salary: Decimal, monthly_hours: Decimal
    ) -> SalaryEntry:
        entry = SalaryEntry(
            id=None, user_id=user_id, effective_from=effective_from, salary=salary, monthly_hours=monthly_hours
        )
        return self._repo.create(entry)

    def list_overtime_rules(self, user_id: str) -> list[OvertimeRule]:
        return self._repo.list_overtime_rules(user_id)

    def create_overtime_rule(
        self, user_id: str, name: str, percentage: Decimal, effective_from: date
    ) -> OvertimeRule:
        rule = OvertimeRule(
            id=None, user_id=user_id, name=name, percentage=percentage, effective_from=effective_from
        )
        return self._repo.create_overtime_rule(rule)

    @staticmethod
    def pick_effective(entries: list[SalaryEntry], at_date: date) -> SalaryEntry | None:
        """Seleciona, em uma lista ja carregada, a vigencia salarial valida
        para `at_date`. Evita 1 consulta por dia em relatorios/graficos."""
        candidates = [e for e in entries if e.effective_from <= at_date]
        if not candidates:
            return None
        return max(candidates, key=lambda e: e.effective_from)

    @staticmethod
    def estimate_period_value(
        period_summary: PeriodSummary,
        salary_entry: SalaryEntry | None,
        overtime_rule: OvertimeRule | None,
    ) -> FinancialEstimate:
        if salary_entry is None:
            return FinancialEstimate.empty()

        hourly_rate = salary_entry.hourly_rate
        overtime_minutes = period_summary.overtime_minutes
        overtime_value = CalculationService.overtime_value(overtime_minutes, hourly_rate, overtime_rule)
        regular_value = CalculationService.regular_hours_value(
            period_summary.worked_minutes, overtime_minutes, hourly_rate
        )
        return FinancialEstimate(
            hourly_rate=hourly_rate, regular_value=regular_value, overtime_value=overtime_value
        )
