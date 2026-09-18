"""Tela 'Hoje': visao rapida do dia atual com relogio ao vivo e registro."""
from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app_container import AppContainer
from app_state import AppState
from models.schedule import WorkScheduleEntry
from models.work_record import WorkRecord
from services.calculation_service import CalculationService
from utils.dates import format_date_br, weekday_label
from utils.formatting import format_minutes_as_hours
from widgets.cards import StatCard
from widgets.day_editor import DayEditorWidget
from workers.async_worker import AsyncTaskRunner


class TodayScreen(QWidget):
    def __init__(self, container: AppContainer, app_state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._app_state = app_state
        self._runner = AsyncTaskRunner(self)
        self._schedule: WorkScheduleEntry | None = None
        self._current_record: WorkRecord | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        self._date_label = QLabel("")
        self._date_label.setProperty("role", "title")
        self._clock_label = QLabel("")
        self._clock_label.setProperty("role", "subtitle")
        layout.addWidget(self._date_label)
        layout.addWidget(self._clock_label)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        self._worked_card = StatCard("Horas trabalhadas ate agora", "00h00")
        self._balance_card = StatCard("Saldo estimado do dia", "00h00")
        self._status_card = StatCard("Situacao do registro", "--")
        stats_row.addWidget(self._worked_card)
        stats_row.addWidget(self._balance_card)
        stats_row.addWidget(self._status_card)
        layout.addLayout(stats_row)

        self._editor = DayEditorWidget(container, app_state)
        self._editor.record_loaded.connect(self._on_record_changed)
        self._editor.record_saved.connect(self._on_record_changed)
        self._editor.record_archived.connect(self._on_record_changed)
        self._editor.record_restored.connect(self._on_record_changed)
        layout.addWidget(self._editor)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick)
        self._clock_timer.start(1000)
        self._tick()

    def showEvent(self, event) -> None:  # noqa: N802 - metodo Qt
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        today = date.today()
        self._date_label.setText(f"Hoje, {format_date_br(today)}")
        self._runner.run(
            self._container.schedule_service.get_effective,
            self._app_state.user_id,
            today,
            on_success=self._on_schedule_loaded,
        )
        self._editor.load_date(today)

    def _on_schedule_loaded(self, schedule: WorkScheduleEntry | None) -> None:
        self._schedule = schedule
        self._update_stats()

    def _on_record_changed(self, record: WorkRecord) -> None:
        self._current_record = record
        self._update_stats()

    def _tick(self) -> None:
        now = datetime.now()
        self._clock_label.setText(f"{weekday_label(now.date())} – {now.strftime('%H:%M:%S')}")
        self._update_stats()

    def _update_stats(self) -> None:
        if self._current_record is None:
            return
        now = datetime.now()
        calc = CalculationService.compute_day(self._current_record, self._schedule, now=now)

        self._worked_card.set_value(format_minutes_as_hours(calc.worked_minutes))
        self._balance_card.set_value(
            format_minutes_as_hours(calc.balance_minutes, show_sign=True),
            accent_color="#16A34A" if calc.balance_minutes >= 0 else "#DC2626",
        )
        if calc.is_complete:
            status = "Completo"
        elif calc.is_in_progress:
            status = "Em andamento"
        else:
            status = "Nao iniciado"
        self._status_card.set_value(status)
