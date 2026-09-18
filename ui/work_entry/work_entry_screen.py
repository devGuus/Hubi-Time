"""Tela 'Registrar Horas': edicao completa de qualquer dia, com seletor de data.

Ao abrir, a data selecionada e sempre a data atual do computador (requisito
de secao 2). O usuario pode escolher outra data pelo calendario a qualquer
momento; se ja existir registro, os dados sao carregados, senao os campos
ficam vazios prontos para preenchimento.
"""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QDateEdit, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app_container import AppContainer
from app_state import AppState
from config.constants import DATE_FORMAT_DISPLAY
from widgets.day_editor import DayEditorWidget
from widgets.toast import Toast


class WorkEntryScreen(QWidget):
    def __init__(self, container: AppContainer, app_state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._app_state = app_state

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        title = QLabel("Registrar Horas")
        title.setProperty("role", "title")

        date_row = QHBoxLayout()
        date_row.setSpacing(10)
        date_label = QLabel("Data")
        self._date_edit = QDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat(DATE_FORMAT_DISPLAY.upper())
        self._date_edit.dateChanged.connect(self._on_date_changed)
        date_row.addWidget(date_label)
        date_row.addWidget(self._date_edit)
        date_row.addStretch()

        self._editor = DayEditorWidget(container, app_state)
        self._editor.record_saved.connect(lambda _r: self._toast.show_message("Registro salvo com sucesso.", "success"))
        self._editor.record_archived.connect(lambda _r: self._toast.show_message("Registro arquivado.", "info"))
        self._editor.record_restored.connect(lambda _r: self._toast.show_message("Registro restaurado.", "success"))

        layout.addWidget(title)
        layout.addLayout(date_row)
        layout.addWidget(self._editor)

        self._toast = Toast(self)

    def showEvent(self, event) -> None:  # noqa: N802 - metodo Qt
        super().showEvent(event)
        today = date.today()
        self._date_edit.blockSignals(True)
        self._date_edit.setDate(today)
        self._date_edit.blockSignals(False)
        self._editor.load_date(today)

    def _on_date_changed(self, qdate) -> None:
        selected = date(qdate.year(), qdate.month(), qdate.day())
        self._editor.load_date(selected)
