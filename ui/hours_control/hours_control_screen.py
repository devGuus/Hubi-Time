"""Tela 'Controle de Horas': indicadores mensais e graficos previsto x realizado."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app_container import AppContainer
from app_state import AppState
from models.work_record import WorkRecord
from services.calculation_service import CalculationService, DayCalculation
from services.schedule_service import ScheduleService
from utils.dates import add_months, iter_dates, month_label, month_range, week_range
from utils.formatting import format_minutes_as_hours
from widgets.cards import StatCard
from widgets.charts import BarChartWidget
from workers.async_worker import AsyncTaskRunner


class HoursControlScreen(QWidget):
    def __init__(self, container: AppContainer, app_state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._app_state = app_state
        self._runner = AsyncTaskRunner(self)
        self._current_month = date.today().replace(day=1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Controle de Horas")
        title.setProperty("role", "title")

        nav_row = QHBoxLayout()
        prev_button = QPushButton("‹")
        prev_button.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_button.clicked.connect(lambda: self._change_month(-1))
        self._month_label = QLabel("")
        self._month_label.setProperty("role", "section")
        next_button = QPushButton("›")
        next_button.setCursor(Qt.CursorShape.PointingHandCursor)
        next_button.clicked.connect(lambda: self._change_month(1))
        nav_row.addWidget(prev_button)
        nav_row.addWidget(self._month_label)
        nav_row.addWidget(next_button)
        nav_row.addStretch()

        cards_row1 = QHBoxLayout()
        cards_row1.setSpacing(14)
        self._expected_card = StatCard("Horas previstas", "--")
        self._worked_card = StatCard("Horas trabalhadas", "--")
        self._balance_card = StatCard("Saldo do mes", "--")
        self._average_card = StatCard("Media diaria", "--")
        for card in (self._expected_card, self._worked_card, self._balance_card, self._average_card):
            cards_row1.addWidget(card)

        cards_row2 = QHBoxLayout()
        cards_row2.setSpacing(14)
        self._worked_days_card = StatCard("Dias trabalhados", "--")
        self._incomplete_days_card = StatCard("Dias incompletos", "--")
        self._overtime_card = StatCard("Horas extras", "--")
        self._bank_card = StatCard("Banco de horas do mes", "--")
        for card in (
            self._worked_days_card, self._incomplete_days_card, self._overtime_card, self._bank_card
        ):
            cards_row2.addWidget(card)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)
        self._daily_chart = BarChartWidget("Horas trabalhadas por dia")
        self._compare_chart = BarChartWidget("Previsto x Realizado (semanal)")
        charts_row.addWidget(self._daily_chart)
        charts_row.addWidget(self._compare_chart)

        layout.addWidget(title)
        layout.addLayout(nav_row)
        layout.addLayout(cards_row1)
        layout.addLayout(cards_row2)
        layout.addLayout(charts_row)

    def showEvent(self, event) -> None:  # noqa: N802 - metodo Qt
        super().showEvent(event)
        self._load()

    def _change_month(self, delta: int) -> None:
        self._current_month = add_months(self._current_month, delta)
        self._load()

    def _load(self) -> None:
        year, month = self._current_month.year, self._current_month.month
        self._month_label.setText(f"{month_label(month)} de {year}")
        start, end = month_range(year, month)
        self._runner.run(
            self._container.work_service.list_range,
            self._app_state.user_id,
            start,
            end,
            False,
            on_success=lambda records: self._load_schedule(records, start, end),
        )

    def _load_schedule(self, records: list[WorkRecord], start: date, end: date) -> None:
        self._runner.run(
            self._container.schedule_service.list_history,
            self._app_state.user_id,
            on_success=lambda history: self._compute(records, history, start, end),
        )

    def _compute(self, records: list[WorkRecord], schedule_history: list, start: date, end: date) -> None:
        records_by_date = {r.work_date: r for r in records}
        days: list[DayCalculation] = []
        for d in iter_dates(start, end):
            record = records_by_date.get(d) or WorkRecord(id=None, user_id=self._app_state.user_id, work_date=d)
            schedule = ScheduleService.pick_effective(schedule_history, d)
            days.append(CalculationService.compute_day(record, schedule))

        summary = CalculationService.summarize_period(days, start, end)

        self._expected_card.set_value(format_minutes_as_hours(summary.expected_minutes))
        self._worked_card.set_value(format_minutes_as_hours(summary.worked_minutes))
        self._balance_card.set_value(
            format_minutes_as_hours(summary.balance_minutes, show_sign=True),
            accent_color="#16A34A" if summary.balance_minutes >= 0 else "#DC2626",
        )
        self._average_card.set_value(format_minutes_as_hours(summary.average_daily_minutes))
        self._worked_days_card.set_value(str(summary.worked_days_count))
        self._incomplete_days_card.set_value(str(summary.incomplete_days_count))
        self._overtime_card.set_value(format_minutes_as_hours(summary.overtime_minutes))
        self._bank_card.set_value(
            format_minutes_as_hours(summary.balance_minutes, show_sign=True),
            accent_color="#16A34A" if summary.balance_minutes >= 0 else "#DC2626",
        )

        day_labels = [d.work_date.strftime("%d") for d in days]
        worked_hours = [round(d.worked_minutes / 60, 2) for d in days]
        self._daily_chart.set_series(day_labels, {"Trabalhadas (h)": worked_hours})

        weeks = self._group_by_week(days)
        week_labels = [f"Sem {i + 1}" for i in range(len(weeks))]
        expected_by_week = [round(sum(d.expected_minutes for d in w) / 60, 2) for w in weeks]
        worked_by_week = [round(sum(d.worked_minutes for d in w) / 60, 2) for w in weeks]
        self._compare_chart.set_series(
            week_labels, {"Previsto (h)": expected_by_week, "Realizado (h)": worked_by_week}
        )

    @staticmethod
    def _group_by_week(days: list[DayCalculation]) -> list[list[DayCalculation]]:
        weeks: list[list[DayCalculation]] = []
        current: list[DayCalculation] = []
        current_week_start = None
        for calc in days:
            week_start, _ = week_range(calc.work_date)
            if current_week_start is None:
                current_week_start = week_start
            if week_start != current_week_start:
                weeks.append(current)
                current = []
                current_week_start = week_start
            current.append(calc)
        if current:
            weeks.append(current)
        return weeks
