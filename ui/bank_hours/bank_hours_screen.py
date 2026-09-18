"""Tela 'Banco de Horas': saldo diario/semanal/mensal/anual/acumulado e evolucao."""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app_container import AppContainer
from app_state import AppState
from models.work_record import WorkRecord
from services.calculation_service import CalculationService, DayCalculation
from services.schedule_service import ScheduleService
from utils.dates import add_months, iter_dates, month_range, week_range, year_range
from utils.formatting import format_minutes_as_hours
from widgets.cards import StatCard
from widgets.charts import LineChartWidget
from workers.async_worker import AsyncTaskRunner

PERIOD_OPTIONS = ["Mes atual", "Ano atual", "Ultimos 12 meses"]


def _fmt(minutes: int) -> str:
    return format_minutes_as_hours(minutes, show_sign=True)


class BankHoursScreen(QWidget):
    def __init__(self, container: AppContainer, app_state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._app_state = app_state
        self._runner = AsyncTaskRunner(self)
        self._schedule_history: list = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        title = QLabel("Banco de Horas")
        title.setProperty("role", "title")
        self._period_combo = QComboBox()
        self._period_combo.addItems(PERIOD_OPTIONS)
        self._period_combo.setCurrentIndex(1)
        self._period_combo.currentIndexChanged.connect(self._load)
        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(QLabel("Periodo do grafico"))
        header_row.addWidget(self._period_combo)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)
        self._today_card = StatCard("Saldo do dia", "--")
        self._week_card = StatCard("Saldo da semana", "--")
        self._month_card = StatCard("Saldo do mes", "--")
        self._year_card = StatCard("Saldo do ano", "--")
        self._accumulated_card = StatCard("Saldo acumulado", "--")
        for card in (
            self._today_card, self._week_card, self._month_card, self._year_card, self._accumulated_card
        ):
            cards_row.addWidget(card)

        self._chart = LineChartWidget("Evolucao do banco de horas")

        layout.addLayout(header_row)
        layout.addLayout(cards_row)
        layout.addWidget(self._chart)

    def showEvent(self, event) -> None:  # noqa: N802 - metodo Qt
        super().showEvent(event)
        self._load()

    def _range_for_chart(self) -> tuple[date, date]:
        today = date.today()
        idx = self._period_combo.currentIndex()
        if idx == 0:
            return month_range(today.year, today.month)
        if idx == 1:
            return year_range(today.year)
        start = add_months(today.replace(day=1), -11)
        return start, today

    def _load(self) -> None:
        self._runner.run(
            self._container.schedule_service.list_history,
            self._app_state.user_id,
            on_success=self._on_schedule_loaded,
        )

    def _on_schedule_loaded(self, schedule_history: list) -> None:
        self._schedule_history = schedule_history
        chart_start, chart_end = self._range_for_chart()
        today = date.today()
        year_start, _ = year_range(today.year)

        fetch_start = min(chart_start, year_start)
        fetch_end = max(chart_end, today)

        self._runner.run(
            self._container.work_service.list_range,
            self._app_state.user_id,
            fetch_start,
            fetch_end,
            False,
            on_success=lambda records: self._compute(records, fetch_start, fetch_end),
        )

    def _compute(self, records: list[WorkRecord], fetch_start: date, fetch_end: date) -> None:
        records_by_date = {r.work_date: r for r in records}
        all_days: list[DayCalculation] = []
        for d in iter_dates(fetch_start, fetch_end):
            record = records_by_date.get(d) or WorkRecord(id=None, user_id=self._app_state.user_id, work_date=d)
            schedule = ScheduleService.pick_effective(self._schedule_history, d)
            all_days.append(CalculationService.compute_day(record, schedule))

        today = date.today()
        by_date = {d.work_date: d for d in all_days}
        today_calc = by_date.get(today)
        week_start, week_end = week_range(today)
        week_days = [d for d in all_days if week_start <= d.work_date <= week_end]
        month_days = [d for d in all_days if d.work_date.year == today.year and d.work_date.month == today.month]
        year_days = [d for d in all_days if d.work_date.year == today.year]

        self._today_card.set_value(_fmt(today_calc.balance_minutes if today_calc else 0))
        self._week_card.set_value(_fmt(sum(d.balance_minutes for d in week_days)))
        self._month_card.set_value(_fmt(sum(d.balance_minutes for d in month_days)))
        self._year_card.set_value(_fmt(sum(d.balance_minutes for d in year_days)))

        chart_start, chart_end = self._range_for_chart()
        chart_days = [d for d in all_days if chart_start <= d.work_date <= chart_end]
        accumulated_minutes = sum(d.balance_minutes for d in chart_days)
        self._accumulated_card.set_value(_fmt(accumulated_minutes))
        self._accumulated_card.set_caption(f"Periodo: {self._period_combo.currentText()}")

        running = CalculationService.running_balance(chart_days)
        labels = [d.strftime("%d/%m") for d, _ in running]
        values = [round(v / 60, 2) for _, v in running]
        self._chart.set_series(labels, {"Banco de horas (h)": values})
