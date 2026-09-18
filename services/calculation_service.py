"""Calculos de jornada, banco de horas e horas extras.

Modulo puro (sem I/O, sem Qt, sem Supabase) para ser facilmente testavel.
Todos os calculos internos usam minutos inteiros; a conversao para o
formato de exibicao ("08h34") acontece apenas na camada de UI/utils.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal

from config.constants import DayType
from models.salary import OvertimeRule
from models.schedule import WorkScheduleEntry
from models.work_record import WorkRecord
from utils.dates import to_weekday


def _diff_minutes(start: time, end: time) -> int:
    return (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)


@dataclass
class DayCalculation:
    work_date: date
    day_type: DayType
    worked_minutes: int
    expected_minutes: int
    balance_minutes: int
    morning_minutes: int
    afternoon_minutes: int
    break_minutes: int
    is_complete: bool
    is_in_progress: bool

    @property
    def overtime_minutes(self) -> int:
        return max(self.balance_minutes, 0)

    @property
    def deficit_minutes(self) -> int:
        return max(-self.balance_minutes, 0)


@dataclass
class PeriodSummary:
    start_date: date
    end_date: date
    expected_minutes: int
    worked_minutes: int
    worked_days_count: int
    incomplete_days_count: int
    days: list[DayCalculation] = field(default_factory=list)

    @property
    def balance_minutes(self) -> int:
        return self.worked_minutes - self.expected_minutes

    @property
    def overtime_minutes(self) -> int:
        return sum(d.overtime_minutes for d in self.days)

    @property
    def average_daily_minutes(self) -> int:
        if self.worked_days_count == 0:
            return 0
        return self.worked_minutes // self.worked_days_count


class CalculationService:
    """Regras de calculo de jornada. Todos os metodos sao estaticos e puros."""

    @staticmethod
    def compute_worked_minutes(record: WorkRecord) -> int:
        """Minutos efetivamente trabalhados, a partir dos horarios preenchidos.

        Campos vazios (NULL) simplesmente nao contribuem para o total -
        nenhum horario e obrigatorio.
        """
        total = 0
        has_lunch_pair = record.lunch_start is not None and record.lunch_end is not None

        if record.entry_time and record.lunch_start:
            total += max(_diff_minutes(record.entry_time, record.lunch_start), 0)
        if has_lunch_pair and record.exit_time:
            total += max(_diff_minutes(record.lunch_end, record.exit_time), 0)
        if record.entry_time and record.exit_time and not record.lunch_start and not record.lunch_end:
            total += max(_diff_minutes(record.entry_time, record.exit_time), 0)
        return total

    @staticmethod
    def compute_break_minutes(record: WorkRecord) -> int:
        if record.lunch_start and record.lunch_end:
            return max(_diff_minutes(record.lunch_start, record.lunch_end), 0)
        return 0

    @staticmethod
    def compute_elapsed_minutes_until_now(record: WorkRecord, now: datetime) -> int:
        """Horas trabalhadas ate o momento atual, para um dia em andamento."""
        current_time = now.time()
        total = 0

        if record.entry_time and record.lunch_start:
            total += max(_diff_minutes(record.entry_time, record.lunch_start), 0)
        elif record.entry_time and not record.lunch_start:
            return max(_diff_minutes(record.entry_time, current_time), 0)

        if record.lunch_end and record.exit_time:
            total += max(_diff_minutes(record.lunch_end, record.exit_time), 0)
        elif record.lunch_end and not record.exit_time:
            total += max(_diff_minutes(record.lunch_end, current_time), 0)

        return total

    @staticmethod
    def expected_minutes_for_day(
        work_date: date, day_type: DayType, schedule: WorkScheduleEntry | None
    ) -> int:
        """Carga prevista para o dia. Dias que nao contam (folga, ferias,
        feriado, atestado, ausencia, outro) nao geram saldo negativo."""
        if not day_type.counts_as_expected_workday:
            return 0
        if schedule is None:
            return 0
        weekday = to_weekday(work_date)
        hours = schedule.expected_hours_for_weekday(weekday)
        return round(hours * 60)

    @classmethod
    def compute_day(
        cls, record: WorkRecord, schedule: WorkScheduleEntry | None, *, now: datetime | None = None
    ) -> DayCalculation:
        worked = cls.compute_worked_minutes(record)
        expected = cls.expected_minutes_for_day(record.work_date, record.day_type, schedule)
        morning = (
            max(_diff_minutes(record.entry_time, record.lunch_start), 0)
            if record.entry_time and record.lunch_start
            else 0
        )
        afternoon = (
            max(_diff_minutes(record.lunch_end, record.exit_time), 0)
            if record.lunch_end and record.exit_time
            else 0
        )
        is_in_progress = bool(record.entry_time) and not record.is_complete
        if now is not None and record.work_date == now.date() and is_in_progress:
            worked = cls.compute_elapsed_minutes_until_now(record, now)

        return DayCalculation(
            work_date=record.work_date,
            day_type=record.day_type,
            worked_minutes=worked,
            expected_minutes=expected,
            balance_minutes=worked - expected,
            morning_minutes=morning,
            afternoon_minutes=afternoon,
            break_minutes=cls.compute_break_minutes(record),
            is_complete=record.is_complete,
            is_in_progress=is_in_progress,
        )

    @staticmethod
    def summarize_period(days: list[DayCalculation], start_date: date, end_date: date) -> PeriodSummary:
        worked_days = [d for d in days if d.worked_minutes > 0]
        incomplete_days = [
            d for d in days if d.day_type.counts_as_expected_workday and not d.is_complete
        ]
        return PeriodSummary(
            start_date=start_date,
            end_date=end_date,
            expected_minutes=sum(d.expected_minutes for d in days),
            worked_minutes=sum(d.worked_minutes for d in days),
            worked_days_count=len(worked_days),
            incomplete_days_count=len(incomplete_days),
            days=days,
        )

    @staticmethod
    def running_balance(days: list[DayCalculation], starting_balance: int = 0) -> list[tuple[date, int]]:
        """Saldo acumulado (banco de horas) dia a dia, a partir de um saldo inicial."""
        running = starting_balance
        result = []
        for day in sorted(days, key=lambda d: d.work_date):
            running += day.balance_minutes
            result.append((day.work_date, running))
        return result

    @staticmethod
    def average_time(times: list[time]) -> time | None:
        valid = [t for t in times if t is not None]
        if not valid:
            return None
        total_minutes = sum(t.hour * 60 + t.minute for t in valid)
        average_minutes = round(total_minutes / len(valid))
        return time(hour=(average_minutes // 60) % 24, minute=average_minutes % 60)

    @staticmethod
    def overtime_value(overtime_minutes: int, hourly_rate: Decimal, rule: OvertimeRule | None) -> Decimal:
        """Estimativa de valor de horas extras. Sem regra configurada, usa
        o valor normal da hora (multiplicador 1x)."""
        if overtime_minutes <= 0:
            return Decimal("0.00")
        multiplier = rule.multiplier if rule else Decimal("1")
        hours = Decimal(overtime_minutes) / Decimal(60)
        return (hours * hourly_rate * multiplier).quantize(Decimal("0.01"))

    @staticmethod
    def regular_hours_value(worked_minutes: int, overtime_minutes: int, hourly_rate: Decimal) -> Decimal:
        regular_minutes = max(worked_minutes - overtime_minutes, 0)
        hours = Decimal(regular_minutes) / Decimal(60)
        return (hours * hourly_rate).quantize(Decimal("0.01"))
