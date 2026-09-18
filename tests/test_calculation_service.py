"""Testes do CalculationService: jornada, intervalos, banco de horas e horas extras."""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from config.constants import DayType
from models.salary import OvertimeRule
from models.schedule import WorkScheduleEntry
from models.work_record import WorkRecord
from services.calculation_service import CalculationService


def make_record(**overrides) -> WorkRecord:
    defaults = dict(id="rec-1", user_id="user-1", work_date=date(2026, 9, 14))  # segunda-feira
    defaults.update(overrides)
    return WorkRecord(**defaults)


def make_schedule(**weekly_hours_overrides) -> WorkScheduleEntry:
    entry = WorkScheduleEntry(id="sched-1", user_id="user-1", effective_from=date(2026, 1, 1))
    entry.weekly_hours.update(weekly_hours_overrides)
    return entry


class TestWorkedMinutes:
    def test_full_day_computes_correct_total(self):
        # Entrada 08:00, almoco 12:00-13:00, saida 18:00 -> manha 4h + tarde 5h = 9h.
        record = make_record(
            entry_time=time(8, 0), lunch_start=time(12, 0), lunch_end=time(13, 0), exit_time=time(18, 0)
        )
        assert CalculationService.compute_worked_minutes(record) == 9 * 60

    def test_day_without_lunch_uses_entry_to_exit(self):
        record = make_record(entry_time=time(9, 0), exit_time=time(13, 0))
        assert CalculationService.compute_worked_minutes(record) == 4 * 60

    def test_only_entry_filled_counts_zero_worked_minutes(self):
        record = make_record(entry_time=time(8, 0))
        assert CalculationService.compute_worked_minutes(record) == 0

    def test_empty_record_counts_zero(self):
        record = make_record()
        assert CalculationService.compute_worked_minutes(record) == 0


class TestBreakMinutes:
    def test_break_computed_when_both_lunch_fields_present(self):
        record = make_record(lunch_start=time(12, 0), lunch_end=time(13, 15))
        assert CalculationService.compute_break_minutes(record) == 75

    def test_break_is_zero_when_incomplete(self):
        record = make_record(lunch_start=time(12, 0))
        assert CalculationService.compute_break_minutes(record) == 0


class TestElapsedUntilNow:
    def test_in_progress_before_lunch(self):
        record = make_record(entry_time=time(8, 0))
        now = datetime(2026, 9, 14, 10, 30)
        assert CalculationService.compute_elapsed_minutes_until_now(record, now) == 150

    def test_in_progress_after_lunch_return(self):
        record = make_record(entry_time=time(8, 0), lunch_start=time(12, 0), lunch_end=time(13, 0))
        now = datetime(2026, 9, 14, 15, 0)
        assert CalculationService.compute_elapsed_minutes_until_now(record, now) == 4 * 60 + 2 * 60


class TestExpectedMinutes:
    def test_normal_day_uses_schedule(self):
        schedule = make_schedule(segunda=8.0)
        minutes = CalculationService.expected_minutes_for_day(date(2026, 9, 14), DayType.NORMAL, schedule)
        assert minutes == 480

    def test_day_off_never_generates_expected_minutes(self):
        schedule = make_schedule(segunda=8.0)
        minutes = CalculationService.expected_minutes_for_day(date(2026, 9, 14), DayType.FOLGA, schedule)
        assert minutes == 0

    def test_missing_schedule_returns_zero(self):
        minutes = CalculationService.expected_minutes_for_day(date(2026, 9, 14), DayType.NORMAL, None)
        assert minutes == 0


class TestIncompleteRecords:
    def test_normal_day_is_incomplete_without_all_four_fields(self):
        record = make_record(entry_time=time(8, 0))
        assert record.is_complete is False

    def test_folga_is_always_considered_complete(self):
        record = make_record(day_type=DayType.FOLGA)
        assert record.is_complete is True

    def test_full_day_is_complete(self):
        record = make_record(
            entry_time=time(8, 0), lunch_start=time(12, 0), lunch_end=time(13, 0), exit_time=time(17, 0)
        )
        assert record.is_complete is True


class TestBankOfHours:
    def test_running_balance_accumulates_across_days(self):
        schedule = make_schedule(segunda=8.0, terca=8.0, quarta=8.0)
        records = [
            make_record(work_date=date(2026, 9, 14), entry_time=time(8, 0), lunch_start=time(12, 0),
                        lunch_end=time(13, 0), exit_time=time(17, 14)),  # +14min
            make_record(work_date=date(2026, 9, 15), entry_time=time(8, 0), lunch_start=time(12, 0),
                        lunch_end=time(13, 0), exit_time=time(16, 53)),  # -7min
            make_record(work_date=date(2026, 9, 16), entry_time=time(8, 0), lunch_start=time(12, 0),
                        lunch_end=time(13, 0), exit_time=time(17, 41)),  # +41min
        ]
        days = [CalculationService.compute_day(r, schedule) for r in records]
        running = CalculationService.running_balance(days)

        assert [minutes for _, minutes in running] == [14, 7, 48]

    def test_summarize_period_totals(self):
        schedule = make_schedule(segunda=8.0, terca=8.0)
        records = [
            make_record(work_date=date(2026, 9, 14), entry_time=time(8, 0), lunch_start=time(12, 0),
                        lunch_end=time(13, 0), exit_time=time(17, 0)),
            make_record(work_date=date(2026, 9, 15)),  # sem lancamento
        ]
        days = [CalculationService.compute_day(r, schedule) for r in records]
        summary = CalculationService.summarize_period(days, date(2026, 9, 14), date(2026, 9, 15))

        assert summary.worked_minutes == 8 * 60
        assert summary.expected_minutes == 16 * 60
        assert summary.balance_minutes == -8 * 60
        assert summary.worked_days_count == 1
        assert summary.incomplete_days_count == 1


class TestOvertimeAndSalary:
    def test_overtime_value_applies_rule_multiplier(self):
        rule = OvertimeRule(id="r1", user_id="user-1", name="Extra 50%", percentage=Decimal("50"), effective_from=date(2026, 1, 1))
        value = CalculationService.overtime_value(60, Decimal("20.00"), rule)
        assert value == Decimal("30.00")

    def test_overtime_value_without_rule_uses_regular_rate(self):
        value = CalculationService.overtime_value(60, Decimal("20.00"), None)
        assert value == Decimal("20.00")

    def test_overtime_value_zero_when_no_extra_minutes(self):
        value = CalculationService.overtime_value(0, Decimal("20.00"), None)
        assert value == Decimal("0.00")

    def test_regular_hours_value_excludes_overtime_minutes(self):
        value = CalculationService.regular_hours_value(worked_minutes=540, overtime_minutes=60, hourly_rate=Decimal("10.00"))
        assert value == Decimal("80.00")

    def test_average_time(self):
        avg = CalculationService.average_time([time(8, 0), time(8, 30), time(9, 0)])
        assert avg == time(8, 30)

    def test_average_time_with_no_values_returns_none(self):
        assert CalculationService.average_time([]) is None
