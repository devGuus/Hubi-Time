"""Tela de calendario mensal com indicacao visual de status por dia."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import QCalendarWidget, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app_container import AppContainer
from app_state import AppState
from config.constants import DayType
from models.work_record import WorkRecord
from utils.dates import iter_dates, month_range
from utils.validators import detect_time_inconsistencies
from widgets.day_editor import DayEditorWidget
from workers.async_worker import AsyncTaskRunner

_STATUS_LEGEND = [
    ("#16A34A", "Completo"),
    ("#D97706", "Incompleto"),
    ("#DC2626", "Inconsistencia"),
    ("#9CA3AF", "Sem jornada"),
    ("#4F6EF7", "Selecionado"),
]


class CalendarScreen(QWidget):
    def __init__(self, container: AppContainer, app_state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._app_state = app_state
        self._runner = AsyncTaskRunner(self)
        self._records_by_date: dict[date, WorkRecord] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Calendario")
        title.setProperty("role", "title")

        legend_row = QHBoxLayout()
        legend_row.setSpacing(6)
        for color, text in _STATUS_LEGEND:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 14px;")
            caption = QLabel(text)
            caption.setProperty("role", "caption")
            legend_row.addWidget(dot)
            legend_row.addWidget(caption)
            legend_row.addSpacing(10)
        legend_row.addStretch()

        content_row = QHBoxLayout()
        content_row.setSpacing(20)

        self._calendar = QCalendarWidget()
        self._calendar.setGridVisible(True)
        self._calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self._calendar.currentPageChanged.connect(self._on_page_changed)
        self._calendar.clicked.connect(self._on_day_clicked)
        content_row.addWidget(self._calendar, 2)

        self._editor = DayEditorWidget(container, app_state)
        self._editor.record_saved.connect(lambda _r: self._reload_current_month())
        self._editor.record_archived.connect(lambda _r: self._reload_current_month())
        self._editor.record_restored.connect(lambda _r: self._reload_current_month())
        content_row.addWidget(self._editor, 3)

        layout.addWidget(title)
        layout.addLayout(legend_row)
        layout.addLayout(content_row)

    def showEvent(self, event) -> None:  # noqa: N802 - metodo Qt
        super().showEvent(event)
        today = QDate.currentDate()
        self._calendar.setSelectedDate(today)
        self._load_month(today.year(), today.month())
        self._editor.load_date(date.today())

    def _on_page_changed(self, year: int, month: int) -> None:
        self._load_month(year, month)

    def _reload_current_month(self) -> None:
        current = self._calendar.selectedDate()
        self._load_month(current.year(), current.month())

    def _load_month(self, year: int, month: int) -> None:
        start, end = month_range(year, month)
        self._runner.run(
            self._container.work_service.list_range,
            self._app_state.user_id,
            start,
            end,
            False,
            on_success=lambda records: self._on_records_loaded(records, start, end),
        )

    def _on_records_loaded(self, records: list[WorkRecord], start: date, end: date) -> None:
        self._records_by_date = {r.work_date: r for r in records}
        self._paint_calendar(start, end)

    def _paint_calendar(self, start: date, end: date) -> None:
        blank_format = QTextCharFormat()
        for day in iter_dates(start, end):
            self._calendar.setDateTextFormat(QDate(day.year, day.month, day.day), blank_format)

        for day in iter_dates(start, end):
            record = self._records_by_date.get(day)
            color = self._color_for(record)
            if color is None:
                continue
            fmt = QTextCharFormat()
            fmt.setBackground(QColor(color))
            fmt.setForeground(QColor("#FFFFFF"))
            self._calendar.setDateTextFormat(QDate(day.year, day.month, day.day), fmt)

    @staticmethod
    def _color_for(record: WorkRecord | None) -> str | None:
        if record is None:
            return None
        warnings = detect_time_inconsistencies(
            record.entry_time, record.lunch_start, record.lunch_end, record.exit_time
        )
        if warnings:
            return "#DC2626"
        if record.is_complete:
            return "#16A34A"
        if record.entry_time or record.day_type != DayType.NORMAL:
            return "#D97706"
        return None

    def _on_day_clicked(self, qdate: QDate) -> None:
        selected = date(qdate.year(), qdate.month(), qdate.day())
        self._editor.load_date(selected)
