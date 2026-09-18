"""Tela 'Financeiro': estimativas pessoais de valor do trabalho e horas extras.

Os valores exibidos sao SEMPRE estimativas de controle pessoal - isso e
deixado explicito na propria tela, conforme requisito do produto.
"""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QComboBox, QDateEdit, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app_container import AppContainer
from app_state import AppState
from config.constants import DATE_FORMAT_DISPLAY
from models.work_record import WorkRecord
from services.calculation_service import CalculationService, DayCalculation
from services.salary_service import SalaryService
from services.schedule_service import ScheduleService
from utils.dates import iter_dates, month_range, year_range
from utils.formatting import format_minutes_as_hours
from utils.money import format_brl
from widgets.cards import StatCard
from widgets.charts import BarChartWidget, LineChartWidget
from workers.async_worker import AsyncTaskRunner

PERIOD_OPTIONS = ["Mes atual", "Trimestre atual", "Semestre atual", "Ano atual", "Personalizado"]


class FinanceScreen(QWidget):
    def __init__(self, container: AppContainer, app_state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._app_state = app_state
        self._runner = AsyncTaskRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Financeiro")
        title.setProperty("role", "title")

        disclaimer = QLabel(
            "Valores estimados para controle pessoal. Nao substituem sua folha de pagamento oficial."
        )
        disclaimer.setProperty("role", "caption")
        disclaimer.setStyleSheet("font-style: italic;")

        period_row = QHBoxLayout()
        period_row.setSpacing(10)
        self._period_combo = QComboBox()
        self._period_combo.addItems(PERIOD_OPTIONS)
        self._period_combo.currentIndexChanged.connect(self._on_period_changed)
        self._custom_start = QDateEdit()
        self._custom_start.setCalendarPopup(True)
        self._custom_start.setDisplayFormat(DATE_FORMAT_DISPLAY.upper())
        self._custom_start.setVisible(False)
        self._custom_start.dateChanged.connect(self._load)
        self._custom_end = QDateEdit()
        self._custom_end.setCalendarPopup(True)
        self._custom_end.setDisplayFormat(DATE_FORMAT_DISPLAY.upper())
        self._custom_end.setVisible(False)
        self._custom_end.dateChanged.connect(self._load)
        period_row.addWidget(QLabel("Periodo"))
        period_row.addWidget(self._period_combo)
        period_row.addWidget(self._custom_start)
        period_row.addWidget(QLabel("ate"))
        period_row.addWidget(self._custom_end)
        period_row.addStretch()

        cards_row1 = QHBoxLayout()
        cards_row1.setSpacing(14)
        self._salary_card = StatCard("Salario mensal vigente", "--")
        self._hourly_card = StatCard("Valor estimado da hora", "--")
        self._worked_card = StatCard("Horas trabalhadas", "--")
        self._overtime_hours_card = StatCard("Horas extras", "--")
        for card in (self._salary_card, self._hourly_card, self._worked_card, self._overtime_hours_card):
            cards_row1.addWidget(card)

        cards_row2 = QHBoxLayout()
        cards_row2.setSpacing(14)
        self._bank_card = StatCard("Banco de horas do periodo", "--")
        self._regular_value_card = StatCard("Estimativa horas normais", "--")
        self._overtime_value_card = StatCard("Estimativa horas extras", "--")
        self._total_value_card = StatCard("Estimativa total", "--", accent_color="#4F6EF7")
        for card in (
            self._bank_card, self._regular_value_card, self._overtime_value_card, self._total_value_card
        ):
            cards_row2.addWidget(card)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)
        self._salary_chart = LineChartWidget("Evolucao salarial")
        self._hours_chart = BarChartWidget("Horas normais x extras por mes")
        charts_row.addWidget(self._salary_chart)
        charts_row.addWidget(self._hours_chart)

        layout.addWidget(title)
        layout.addWidget(disclaimer)
        layout.addLayout(period_row)
        layout.addLayout(cards_row1)
        layout.addLayout(cards_row2)
        layout.addLayout(charts_row)

    def showEvent(self, event) -> None:  # noqa: N802 - metodo Qt
        super().showEvent(event)
        self._load()

    def _on_period_changed(self) -> None:
        is_custom = self._period_combo.currentIndex() == len(PERIOD_OPTIONS) - 1
        self._custom_start.setVisible(is_custom)
        self._custom_end.setVisible(is_custom)
        self._load()

    def _current_range(self) -> tuple[date, date]:
        idx = self._period_combo.currentIndex()
        today = date.today()
        if idx == 0:
            return month_range(today.year, today.month)
        if idx == 1:
            quarter_start_month = ((today.month - 1) // 3) * 3 + 1
            start = date(today.year, quarter_start_month, 1)
            end = month_range(today.year, quarter_start_month + 2)[1]
            return start, end
        if idx == 2:
            half_start_month = 1 if today.month <= 6 else 7
            start = date(today.year, half_start_month, 1)
            end = month_range(today.year, half_start_month + 5)[1]
            return start, end
        if idx == 3:
            return year_range(today.year)
        start = date(
            self._custom_start.date().year(), self._custom_start.date().month(), self._custom_start.date().day()
        )
        end = date(self._custom_end.date().year(), self._custom_end.date().month(), self._custom_end.date().day())
        return (start, end) if start <= end else (end, start)

    def _load(self) -> None:
        start, end = self._current_range()
        self._runner.run(
            self._container.work_service.list_range,
            self._app_state.user_id,
            start,
            end,
            False,
            on_success=lambda records: self._with_schedule(records, start, end),
        )

    def _with_schedule(self, records: list[WorkRecord], start: date, end: date) -> None:
        self._runner.run(
            self._container.schedule_service.list_history,
            self._app_state.user_id,
            on_success=lambda schedule_history: self._with_salary(records, schedule_history, start, end),
        )

    def _with_salary(self, records: list[WorkRecord], schedule_history: list, start: date, end: date) -> None:
        self._runner.run(
            self._container.salary_service.list_history,
            self._app_state.user_id,
            on_success=lambda salary_history: self._with_overtime_rules(
                records, schedule_history, salary_history, start, end
            ),
        )

    def _with_overtime_rules(
        self, records: list[WorkRecord], schedule_history: list, salary_history: list, start: date, end: date
    ) -> None:
        self._runner.run(
            self._container.salary_service.list_overtime_rules,
            self._app_state.user_id,
            on_success=lambda rules: self._compute(records, schedule_history, salary_history, rules, start, end),
        )

    def _compute(
        self,
        records: list[WorkRecord],
        schedule_history: list,
        salary_history: list,
        overtime_rules: list,
        start: date,
        end: date,
    ) -> None:
        records_by_date = {r.work_date: r for r in records}
        days: list[DayCalculation] = []
        for d in iter_dates(start, end):
            record = records_by_date.get(d) or WorkRecord(id=None, user_id=self._app_state.user_id, work_date=d)
            schedule = ScheduleService.pick_effective(schedule_history, d)
            days.append(CalculationService.compute_day(record, schedule))

        summary = CalculationService.summarize_period(days, start, end)
        current_salary = SalaryService.pick_effective(salary_history, date.today())

        applicable_rule = None
        candidates = [r for r in overtime_rules if r.effective_from <= date.today()]
        if candidates:
            applicable_rule = max(candidates, key=lambda r: r.effective_from)

        estimate = SalaryService.estimate_period_value(summary, current_salary, applicable_rule)

        self._salary_card.set_value(format_brl(current_salary.salary) if current_salary else "Nao configurado")
        self._hourly_card.set_value(format_brl(current_salary.hourly_rate) if current_salary else "--")
        self._worked_card.set_value(format_minutes_as_hours(summary.worked_minutes))
        self._overtime_hours_card.set_value(format_minutes_as_hours(summary.overtime_minutes))
        self._bank_card.set_value(format_minutes_as_hours(summary.balance_minutes, show_sign=True))
        self._regular_value_card.set_value(format_brl(estimate.regular_value))
        self._overtime_value_card.set_value(format_brl(estimate.overtime_value))
        self._total_value_card.set_value(format_brl(estimate.total_value))

        sorted_salary = sorted(salary_history, key=lambda s: s.effective_from)
        salary_labels = [s.effective_from.strftime("%m/%Y") for s in sorted_salary]
        salary_values = [float(s.salary) for s in sorted_salary]
        self._salary_chart.set_series(
            salary_labels, {"Salario (R$)": salary_values}, value_formatter=lambda v: f"R$ {v:,.2f}"
        )

        months = self._group_by_month(days)
        month_labels = [d.strftime("%m/%Y") for d, _ in months]
        regular_by_month = []
        overtime_by_month = []
        for _, month_days in months:
            worked = sum(d.worked_minutes for d in month_days)
            overtime = sum(d.overtime_minutes for d in month_days)
            regular_by_month.append(round((worked - overtime) / 60, 2))
            overtime_by_month.append(round(overtime / 60, 2))
        self._hours_chart.set_series(
            month_labels, {"Normais (h)": regular_by_month, "Extras (h)": overtime_by_month}
        )

    @staticmethod
    def _group_by_month(days: list[DayCalculation]) -> list[tuple[date, list[DayCalculation]]]:
        groups: dict[tuple[int, int], list[DayCalculation]] = {}
        for d in days:
            key = (d.work_date.year, d.work_date.month)
            groups.setdefault(key, []).append(d)
        ordered_keys = sorted(groups.keys())
        return [(date(y, m, 1), groups[(y, m)]) for y, m in ordered_keys]
