"""Testes de selecao de vigencia (salario e carga horaria) e valor/hora."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from models.salary import SalaryEntry
from models.schedule import WorkScheduleEntry
from services.salary_service import SalaryService
from services.schedule_service import ScheduleService


def salary(effective_from: str, value: str, monthly_hours: str = "220") -> SalaryEntry:
    return SalaryEntry(
        id=None, user_id="user-1",
        effective_from=date.fromisoformat(effective_from),
        salary=Decimal(value), monthly_hours=Decimal(monthly_hours),
    )


def schedule(effective_from: str) -> WorkScheduleEntry:
    return WorkScheduleEntry(id=None, user_id="user-1", effective_from=date.fromisoformat(effective_from))


class TestSalaryHistory:
    def test_pick_effective_uses_most_recent_entry_not_after_date(self):
        entries = [salary("2026-01-01", "3000"), salary("2026-07-01", "3500")]

        assert SalaryService.pick_effective(entries, date(2026, 3, 15)).salary == Decimal("3000")
        assert SalaryService.pick_effective(entries, date(2026, 9, 1)).salary == Decimal("3500")

    def test_pick_effective_returns_none_before_any_vigencia(self):
        entries = [salary("2026-07-01", "3500")]
        assert SalaryService.pick_effective(entries, date(2026, 1, 1)) is None

    def test_hourly_rate_calculation(self):
        entry = salary("2026-01-01", "3500", "220")
        assert entry.hourly_rate == Decimal("15.91")

    def test_hourly_rate_never_uses_float_division_rounding_errors(self):
        entry = salary("2026-01-01", "1000", "3")
        # 1000/3 = 333.333... -> deve arredondar para 2 casas decimais via Decimal
        assert entry.hourly_rate == Decimal("333.33")


class TestScheduleHistory:
    def test_pick_effective_uses_most_recent_entry_not_after_date(self):
        entries = [schedule("2026-01-01"), schedule("2026-08-01")]

        assert ScheduleService.pick_effective(entries, date(2026, 3, 1)).effective_from == date(2026, 1, 1)
        assert ScheduleService.pick_effective(entries, date(2026, 9, 1)).effective_from == date(2026, 8, 1)

    def test_pick_effective_returns_none_when_no_vigencia_applies(self):
        entries = [schedule("2026-08-01")]
        assert ScheduleService.pick_effective(entries, date(2026, 1, 1)) is None
