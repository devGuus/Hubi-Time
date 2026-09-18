"""Tela de relatorios: exportacao de jornada e financeiro em Excel/CSV/PDF."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app_container import AppContainer
from app_state import AppState
from models.work_record import WorkRecord
from services.calculation_service import CalculationService, DayCalculation
from services.report_service import (
    FINANCE_REPORT_HEADERS, WORK_REPORT_HEADERS, ReportService,
    build_finance_report_rows, build_work_report_rows,
)
from services.salary_service import SalaryService
from services.schedule_service import ScheduleService
from utils.dates import iter_dates
from widgets.dialogs import show_error, show_success
from widgets.loading_button import LoadingButton
from widgets.period_filter import PeriodFilter
from workers.async_worker import AsyncTaskRunner

REPORT_TYPES = ["Registros de jornada", "Financeiro"]


class ReportsScreen(QWidget):
    def __init__(self, container: AppContainer, app_state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._app_state = app_state
        self._runner = AsyncTaskRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Relatorios")
        title.setProperty("role", "title")

        self._period_filter = PeriodFilter()

        type_row = QHBoxLayout()
        type_row.setSpacing(10)
        self._type_combo = QComboBox()
        self._type_combo.addItems(REPORT_TYPES)
        type_row.addWidget(QLabel("Tipo de relatorio"))
        type_row.addWidget(self._type_combo)
        type_row.addStretch()

        self._summary_label = QLabel("Selecione um periodo para exportar.")
        self._summary_label.setProperty("role", "subtitle")

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(10)
        self._xlsx_button = LoadingButton("Exportar Excel (.xlsx)", variant="primary")
        self._xlsx_button.clicked.connect(lambda: self._export("xlsx"))
        self._csv_button = LoadingButton("Exportar CSV", variant="ghost")
        self._csv_button.clicked.connect(lambda: self._export("csv"))
        self._pdf_button = LoadingButton("Exportar PDF", variant="ghost")
        self._pdf_button.clicked.connect(lambda: self._export("pdf"))
        buttons_row.addWidget(self._xlsx_button)
        buttons_row.addWidget(self._csv_button)
        buttons_row.addWidget(self._pdf_button)
        buttons_row.addStretch()

        layout.addWidget(title)
        layout.addWidget(self._period_filter)
        layout.addLayout(type_row)
        layout.addWidget(self._summary_label)
        layout.addLayout(buttons_row)
        layout.addStretch()

    def _export(self, fmt: str) -> None:
        start, end = self._period_filter.current_range()
        report_type = self._type_combo.currentIndex()

        default_name = f"relatorio_{start.isoformat()}_a_{end.isoformat()}.{fmt}"
        filters = {"xlsx": "Excel (*.xlsx)", "csv": "CSV (*.csv)", "pdf": "PDF (*.pdf)"}
        path, _ = QFileDialog.getSaveFileName(self, "Salvar relatorio", default_name, filters[fmt])
        if not path:
            return

        self._set_buttons_loading(True)
        self._runner.run(
            self._container.work_service.list_range,
            self._app_state.user_id,
            start,
            end,
            False,
            on_success=lambda records: self._continue_export(records, start, end, report_type, fmt, path),
            on_error=lambda msg: (show_error(self, msg), self._set_buttons_loading(False)),
        )

    def _continue_export(
        self, records: list[WorkRecord], start: date, end: date, report_type: int, fmt: str, path: str
    ) -> None:
        self._runner.run(
            self._container.schedule_service.list_history,
            self._app_state.user_id,
            on_success=lambda schedule_history: self._build_and_save(
                records, schedule_history, start, end, report_type, fmt, path
            ),
            on_error=lambda msg: (show_error(self, msg), self._set_buttons_loading(False)),
        )

    def _build_and_save(
        self,
        records: list[WorkRecord],
        schedule_history: list,
        start: date,
        end: date,
        report_type: int,
        fmt: str,
        path: str,
    ) -> None:
        records_by_date = {r.work_date: r for r in records}
        days: list[DayCalculation] = []
        for d in iter_dates(start, end):
            record = records_by_date.get(d) or WorkRecord(id=None, user_id=self._app_state.user_id, work_date=d)
            schedule = ScheduleService.pick_effective(schedule_history, d)
            days.append(CalculationService.compute_day(record, schedule))

        if report_type == 0:
            rows = build_work_report_rows(days, records_by_date)
            headers = WORK_REPORT_HEADERS
            title = "Relatorio de Jornada"
            self._write_report(fmt, path, rows, headers, title)
            self._set_buttons_loading(False)
            return

        self._runner.run(
            self._container.salary_service.list_history,
            self._app_state.user_id,
            on_success=lambda salary_history: self._with_overtime_rules(days, salary_history, start, end, fmt, path),
            on_error=lambda msg: (show_error(self, msg), self._set_buttons_loading(False)),
        )

    def _with_overtime_rules(
        self, days: list[DayCalculation], salary_history: list, start: date, end: date, fmt: str, path: str
    ) -> None:
        self._runner.run(
            self._container.salary_service.list_overtime_rules,
            self._app_state.user_id,
            on_success=lambda rules: self._build_finance_report(days, salary_history, rules, start, end, fmt, path),
            on_error=lambda msg: (show_error(self, msg), self._set_buttons_loading(False)),
        )

    def _build_finance_report(
        self,
        days: list[DayCalculation],
        salary_history: list,
        overtime_rules: list,
        start: date,
        end: date,
        fmt: str,
        path: str,
    ) -> None:
        salary_entry = SalaryService.pick_effective(salary_history, end)
        hourly_rate = salary_entry.hourly_rate if salary_entry else Decimal("0")
        summary = CalculationService.summarize_period(days, start, end)

        applicable_rule = None
        candidates = [r for r in overtime_rules if r.effective_from <= end]
        if candidates:
            applicable_rule = max(candidates, key=lambda r: r.effective_from)

        overtime_minutes = summary.overtime_minutes
        overtime_value = CalculationService.overtime_value(overtime_minutes, hourly_rate, applicable_rule)
        regular_value = CalculationService.regular_hours_value(summary.worked_minutes, overtime_minutes, hourly_rate)

        entries = [
            {
                "label": f"{start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')}",
                "regular_minutes": summary.worked_minutes - overtime_minutes,
                "overtime_minutes": overtime_minutes,
                "hourly_rate": hourly_rate,
                "regular_value": regular_value,
                "overtime_value": overtime_value,
                "total_value": regular_value + overtime_value,
            }
        ]
        rows = build_finance_report_rows(entries)
        self._write_report(fmt, path, rows, FINANCE_REPORT_HEADERS, "Relatorio Financeiro (estimativa)")
        self._set_buttons_loading(False)

    def _write_report(self, fmt: str, path: str, rows: list[dict], headers: list[str], title: str) -> None:
        try:
            if fmt == "xlsx":
                ReportService.export_xlsx(path, rows, headers, title)
            elif fmt == "csv":
                ReportService.export_csv(path, rows, headers)
            else:
                ReportService.export_pdf(path, rows, headers, title)
            show_success(self, f"Relatorio exportado com sucesso para:\n{path}")
        except Exception as exc:  # ServiceError ja traduzido; outras excecoes viram mensagem generica
            message = getattr(exc, "friendly_message", "Nao foi possivel exportar o relatorio.")
            show_error(self, message)

    def _set_buttons_loading(self, loading: bool) -> None:
        self._xlsx_button.set_loading(loading, "Exportando...")
        self._csv_button.set_loading(loading, "Exportando...")
        self._pdf_button.set_loading(loading, "Exportando...")
