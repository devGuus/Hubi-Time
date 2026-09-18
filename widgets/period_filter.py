"""Filtro de periodo reutilizavel: Hoje / Semana / Mes / Ano / Intervalo personalizado."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QDateEdit, QHBoxLayout, QLabel, QWidget

from config.constants import DATE_FORMAT_DISPLAY
from utils.dates import month_range, week_range, year_range

OPTIONS = ["Hoje", "Semana", "Mes", "Ano", "Intervalo personalizado"]


class PeriodFilter(QWidget):
    range_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._combo = QComboBox()
        self._combo.addItems(OPTIONS)
        self._combo.currentIndexChanged.connect(self._on_changed)

        self._start = QDateEdit()
        self._start.setCalendarPopup(True)
        self._start.setDisplayFormat(DATE_FORMAT_DISPLAY.upper())
        self._start.setVisible(False)
        self._start.dateChanged.connect(self.range_changed.emit)

        self._end = QDateEdit()
        self._end.setCalendarPopup(True)
        self._end.setDisplayFormat(DATE_FORMAT_DISPLAY.upper())
        self._end.setVisible(False)
        self._end.dateChanged.connect(self.range_changed.emit)

        self._label_to = QLabel("ate")
        self._label_to.setVisible(False)

        layout.addWidget(QLabel("Periodo"))
        layout.addWidget(self._combo)
        layout.addWidget(self._start)
        layout.addWidget(self._label_to)
        layout.addWidget(self._end)
        layout.addStretch()

    def _on_changed(self) -> None:
        is_custom = self._combo.currentIndex() == len(OPTIONS) - 1
        self._start.setVisible(is_custom)
        self._end.setVisible(is_custom)
        self._label_to.setVisible(is_custom)
        self.range_changed.emit()

    def current_range(self) -> tuple[date, date]:
        idx = self._combo.currentIndex()
        today = date.today()
        if idx == 0:
            return today, today
        if idx == 1:
            return week_range(today)
        if idx == 2:
            return month_range(today.year, today.month)
        if idx == 3:
            return year_range(today.year)
        start = date(self._start.date().year(), self._start.date().month(), self._start.date().day())
        end = date(self._end.date().year(), self._end.date().month(), self._end.date().day())
        return (start, end) if start <= end else (end, start)

    def current_label(self) -> str:
        return self._combo.currentText()
