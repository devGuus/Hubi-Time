"""Tela de historico: listagem filtravel de registros e registros arquivados."""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from app_container import AppContainer
from app_state import AppState
from models.work_record import WorkRecord
from services.calculation_service import CalculationService
from services.schedule_service import ScheduleService
from utils.dates import format_date_br
from utils.formatting import format_minutes_as_hours, format_time_or_placeholder
from widgets.day_editor import DayEditorWidget
from widgets.dialogs import show_error, show_success
from widgets.period_filter import PeriodFilter
from workers.async_worker import AsyncTaskRunner

TABLE_HEADERS = [
    "Data", "Entrada", "Almoco", "Retorno", "Saida",
    "Trabalhadas", "Previstas", "Saldo", "Status",
]


class HistoryScreen(QWidget):
    def __init__(self, container: AppContainer, app_state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._app_state = app_state
        self._runner = AsyncTaskRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Historico")
        title.setProperty("role", "title")

        self._period_filter = PeriodFilter()
        self._period_filter.range_changed.connect(self._load_records)

        self._tabs = QTabWidget()

        self._table = QTableWidget(0, len(TABLE_HEADERS))
        self._table.setHorizontalHeaderLabels(TABLE_HEADERS)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.doubleClicked.connect(self._on_row_double_clicked)

        self._archived_table = QTableWidget(0, 4)
        self._archived_table.setHorizontalHeaderLabels(["Data", "Tipo de dia", "Arquivado em", ""])
        self._archived_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._archived_table.horizontalHeader().setStretchLastSection(True)

        self._tabs.addTab(self._table, "Registros")
        self._tabs.addTab(self._archived_table, "Arquivados")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(title)
        layout.addWidget(self._period_filter)
        layout.addWidget(self._tabs)

    def showEvent(self, event) -> None:  # noqa: N802 - metodo Qt
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        if self._tabs.currentIndex() == 0:
            self._load_records()
        else:
            self._load_archived()

    def _on_tab_changed(self, index: int) -> None:
        if index == 0:
            self._load_records()
        else:
            self._load_archived()

    # ------------------------------------------------------------------
    def _load_records(self) -> None:
        start, end = self._period_filter.current_range()
        self._runner.run(
            self._container.work_service.list_range,
            self._app_state.user_id,
            start,
            end,
            False,
            on_success=lambda records: self._load_schedule_then_populate(records),
        )

    def _load_schedule_then_populate(self, records: list[WorkRecord]) -> None:
        self._runner.run(
            self._container.schedule_service.list_history,
            self._app_state.user_id,
            on_success=lambda history: self._populate_table(records, history),
        )

    def _populate_table(self, records: list[WorkRecord], schedule_history: list) -> None:
        self._table.setRowCount(0)
        for record in sorted(records, key=lambda r: r.work_date):
            schedule = ScheduleService.pick_effective(schedule_history, record.work_date)
            calc = CalculationService.compute_day(record, schedule)
            row = self._table.rowCount()
            self._table.insertRow(row)
            values = [
                format_date_br(record.work_date),
                format_time_or_placeholder(record.entry_time),
                format_time_or_placeholder(record.lunch_start),
                format_time_or_placeholder(record.lunch_end),
                format_time_or_placeholder(record.exit_time),
                format_minutes_as_hours(calc.worked_minutes),
                format_minutes_as_hours(calc.expected_minutes),
                format_minutes_as_hours(calc.balance_minutes, show_sign=True),
                "Completo" if calc.is_complete else "Incompleto",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, record.work_date.isoformat())
                self._table.setItem(row, col, item)

    def _on_row_double_clicked(self, index) -> None:
        item = self._table.item(index.row(), 0)
        work_date = date.fromisoformat(item.data(Qt.ItemDataRole.UserRole))
        self._open_day_dialog(work_date)

    def _open_day_dialog(self, work_date: date) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Registro de {format_date_br(work_date)}")
        dialog.resize(720, 580)
        layout = QVBoxLayout(dialog)
        editor = DayEditorWidget(self._container, self._app_state)
        editor.record_saved.connect(lambda _r: self._load_records())
        editor.record_archived.connect(lambda _r: self._load_records())
        editor.record_restored.connect(lambda _r: self._load_records())
        layout.addWidget(editor)
        editor.load_date(work_date)
        dialog.exec()

    # ------------------------------------------------------------------
    def _load_archived(self) -> None:
        self._runner.run(
            self._container.work_service.list_archived,
            self._app_state.user_id,
            on_success=self._populate_archived,
        )

    def _populate_archived(self, records: list[WorkRecord]) -> None:
        self._archived_table.setRowCount(0)
        for record in records:
            row = self._archived_table.rowCount()
            self._archived_table.insertRow(row)
            self._archived_table.setItem(row, 0, QTableWidgetItem(format_date_br(record.work_date)))
            self._archived_table.setItem(row, 1, QTableWidgetItem(record.day_type.label_pt))
            archived_at = record.archived_at.strftime("%d/%m/%Y %H:%M") if record.archived_at else "--"
            self._archived_table.setItem(row, 2, QTableWidgetItem(archived_at))

            restore_button = QPushButton("Restaurar")
            restore_button.setProperty("variant", "primary")
            restore_button.setCursor(Qt.CursorShape.PointingHandCursor)
            restore_button.clicked.connect(lambda _checked=False, r=record: self._restore(r))
            self._archived_table.setCellWidget(row, 3, restore_button)

    def _restore(self, record: WorkRecord) -> None:
        self._runner.run(
            self._container.work_service.restore,
            record,
            on_success=lambda _r: self._on_restore_success(),
            on_error=lambda msg: show_error(self, msg),
        )

    def _on_restore_success(self) -> None:
        show_success(self, "Registro restaurado com sucesso.")
        self._load_archived()
