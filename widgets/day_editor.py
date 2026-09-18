"""Editor de um dia de jornada: os 4 horarios, tipo de dia, observacoes,
avisos de inconsistencia, salvar/arquivar/restaurar e aba de historico.

Usado tanto na tela "Hoje" (travado no dia atual) quanto em "Registrar
Horas" (com selecao de data), evitando duplicar a logica de CRUD.
"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QListWidget, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from app_container import AppContainer
from app_state import AppState
from config.constants import DayType, RecordStatus
from models.work_record import WorkRecord
from services.audit_service import AuditService
from utils.validators import detect_time_inconsistencies
from widgets.dialogs import confirm, show_error, show_warning
from widgets.loading_button import LoadingButton
from widgets.time_field import TimeEntryField
from workers.async_worker import AsyncTaskRunner


class DayEditorWidget(QWidget):
    record_loaded = Signal(object)  # WorkRecord
    record_saved = Signal(object)  # WorkRecord
    record_archived = Signal(object)  # WorkRecord
    record_restored = Signal(object)  # WorkRecord

    def __init__(self, container: AppContainer, app_state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._app_state = app_state
        self._runner = AsyncTaskRunner(self)
        self._record: WorkRecord | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_form_tab(), "Registro")
        self._tabs.addTab(self._build_history_tab(), "Historico de alteracoes")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self._tabs)

    # ------------------------------------------------------------------
    def _build_form_tab(self) -> QWidget:
        tab = QWidget()
        form_layout = QVBoxLayout(tab)
        form_layout.setSpacing(14)

        self._incomplete_label = QLabel("Registro deste dia ainda esta incompleto.")
        self._incomplete_label.setProperty("role", "caption")
        self._incomplete_label.setStyleSheet("color: #D97706;")
        self._incomplete_label.setVisible(False)

        self._warnings_label = QLabel("")
        self._warnings_label.setWordWrap(True)
        self._warnings_label.setStyleSheet("color: #DC2626; font-weight: 600;")
        self._warnings_label.setVisible(False)

        self._archived_label = QLabel("Este registro esta arquivado e nao pode ser editado.")
        self._archived_label.setStyleSheet("color: #6B7280; font-style: italic;")
        self._archived_label.setVisible(False)

        fields_row = QHBoxLayout()
        fields_row.setSpacing(24)
        self._entry_field = TimeEntryField("Entrada")
        self._lunch_start_field = TimeEntryField("Saida para almoco")
        self._lunch_end_field = TimeEntryField("Retorno")
        self._exit_field = TimeEntryField("Saida")
        for field in (self._entry_field, self._lunch_start_field, self._lunch_end_field, self._exit_field):
            field.valueChanged.connect(self._update_status_labels)
            fields_row.addWidget(field)
        fields_row.addStretch()

        meta_row = QHBoxLayout()
        meta_row.setSpacing(10)
        self._day_type_combo = QComboBox()
        for day_type in DayType:
            self._day_type_combo.addItem(day_type.label_pt, day_type.value)
        self._day_type_combo.currentIndexChanged.connect(self._update_status_labels)
        meta_row.addWidget(QLabel("Tipo de dia"))
        meta_row.addWidget(self._day_type_combo)
        meta_row.addStretch()

        self._notes_edit = QTextEdit()
        self._notes_edit.setPlaceholderText("Observacoes sobre o dia (opcional)")
        self._notes_edit.setFixedHeight(70)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(10)
        self._save_button = LoadingButton("Salvar", variant="primary")
        self._save_button.clicked.connect(self._on_save_clicked)
        self._archive_button = LoadingButton("Arquivar registro", variant="danger")
        self._archive_button.clicked.connect(self._on_archive_clicked)
        self._archive_button.setVisible(False)
        self._restore_button = LoadingButton("Restaurar registro", variant="primary")
        self._restore_button.clicked.connect(self._on_restore_clicked)
        self._restore_button.setVisible(False)
        buttons_row.addWidget(self._save_button)
        buttons_row.addWidget(self._archive_button)
        buttons_row.addWidget(self._restore_button)
        buttons_row.addStretch()

        form_layout.addWidget(self._incomplete_label)
        form_layout.addWidget(self._warnings_label)
        form_layout.addWidget(self._archived_label)
        form_layout.addLayout(fields_row)
        form_layout.addLayout(meta_row)
        form_layout.addWidget(QLabel("Observacoes"))
        form_layout.addWidget(self._notes_edit)
        form_layout.addLayout(buttons_row)
        form_layout.addStretch()
        return tab

    def _build_history_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self._history_list = QListWidget()
        layout.addWidget(self._history_list)
        return tab

    # ------------------------------------------------------------------
    def load_date(self, work_date: date) -> None:
        self._save_button.set_loading(True, "Carregando...")
        self._runner.run(
            self._container.work_service.get_day,
            self._app_state.user_id,
            work_date,
            on_success=self._on_record_loaded,
            on_error=lambda msg: show_error(self, msg),
            on_finished=lambda: self._save_button.set_loading(False),
        )

    def _on_record_loaded(self, record: WorkRecord) -> None:
        self._record = record
        self._entry_field.set_value(record.entry_time)
        self._lunch_start_field.set_value(record.lunch_start)
        self._lunch_end_field.set_value(record.lunch_end)
        self._exit_field.set_value(record.exit_time)

        index = self._day_type_combo.findData(record.day_type.value)
        self._day_type_combo.setCurrentIndex(max(index, 0))
        self._notes_edit.setPlainText(record.notes or "")

        is_active_or_new = record.status == RecordStatus.ACTIVE
        self._set_editing_enabled(is_active_or_new)
        self._archive_button.setVisible(record.id is not None and is_active_or_new)
        self._restore_button.setVisible(record.id is not None and not is_active_or_new)
        self._archived_label.setVisible(not is_active_or_new)

        self._update_status_labels()
        self._history_list.clear()
        if self._tabs.currentIndex() == 1:
            self._load_history()
        self.record_loaded.emit(record)

    def _set_editing_enabled(self, enabled: bool) -> None:
        for field in (self._entry_field, self._lunch_start_field, self._lunch_end_field, self._exit_field):
            field.set_enabled_editing(enabled)
        self._day_type_combo.setEnabled(enabled)
        self._notes_edit.setEnabled(enabled)
        self._save_button.setEnabled(enabled)

    def _update_status_labels(self) -> None:
        warnings = detect_time_inconsistencies(
            self._entry_field.value(),
            self._lunch_start_field.value(),
            self._lunch_end_field.value(),
            self._exit_field.value(),
        )
        if warnings:
            self._warnings_label.setText("\n".join(f"⚠ {w.message}" for w in warnings))
            self._warnings_label.setVisible(True)
        else:
            self._warnings_label.setVisible(False)

        day_type = DayType(self._day_type_combo.currentData())
        filled = [
            self._entry_field.value(),
            self._lunch_start_field.value(),
            self._lunch_end_field.value(),
            self._exit_field.value(),
        ]
        self._incomplete_label.setVisible(day_type.counts_as_expected_workday and not all(filled))

    # ------------------------------------------------------------------
    def _on_save_clicked(self) -> None:
        if self._record is None:
            return
        self._save_button.set_loading(True)
        self._runner.run(
            self._container.work_service.save_fields,
            self._record,
            entry_time=self._entry_field.value(),
            lunch_start=self._lunch_start_field.value(),
            lunch_end=self._lunch_end_field.value(),
            exit_time=self._exit_field.value(),
            day_type=DayType(self._day_type_combo.currentData()),
            notes=self._notes_edit.toPlainText().strip() or None,
            on_success=self._on_save_success,
            on_error=self._on_save_error,
            on_finished=lambda: self._save_button.set_loading(False),
        )

    def _on_save_success(self, record: WorkRecord) -> None:
        self._record = record
        self._archive_button.setVisible(True)
        self.record_saved.emit(record)

    def _on_save_error(self, message: str) -> None:
        if self._record is not None and "alterado em outro lugar" in message.lower():
            show_warning(self, message)
            self.load_date(self._record.work_date)
        else:
            show_error(self, message)

    def _on_archive_clicked(self) -> None:
        if self._record is None:
            return
        if not confirm(
            self,
            "Deseja arquivar este registro? Ele deixara de aparecer na listagem "
            "normal, mas podera ser restaurado depois em Historico > Arquivados.",
            title="Arquivar registro",
        ):
            return
        self._runner.run(
            self._container.work_service.archive,
            self._record,
            self._app_state.user_id,
            on_success=self._on_archive_success,
            on_error=lambda msg: show_error(self, msg),
        )

    def _on_archive_success(self, record: WorkRecord) -> None:
        self._record = record
        self._set_editing_enabled(False)
        self._archive_button.setVisible(False)
        self._restore_button.setVisible(True)
        self._archived_label.setVisible(True)
        self.record_archived.emit(record)

    def _on_restore_clicked(self) -> None:
        if self._record is None:
            return
        self._runner.run(
            self._container.work_service.restore,
            self._record,
            on_success=self._on_restore_success,
            on_error=lambda msg: show_error(self, msg),
        )

    def _on_restore_success(self, record: WorkRecord) -> None:
        self._record = record
        self._set_editing_enabled(True)
        self._archive_button.setVisible(True)
        self._restore_button.setVisible(False)
        self._archived_label.setVisible(False)
        self.record_restored.emit(record)

    # ------------------------------------------------------------------
    def _on_tab_changed(self, index: int) -> None:
        if index == 1 and self._record is not None and self._record.id is not None:
            self._load_history()

    def _load_history(self) -> None:
        if self._record is None or self._record.id is None:
            return
        self._runner.run(
            self._container.audit_service.get_work_record_history,
            self._app_state.user_id,
            self._record.id,
            on_success=self._on_history_loaded,
            on_error=lambda msg: show_error(self, msg),
        )

    def _on_history_loaded(self, entries: list) -> None:
        self._history_list.clear()
        if not entries:
            self._history_list.addItem("Nenhuma alteracao registrada ainda.")
            return
        for entry in entries:
            timestamp = entry.changed_at.strftime("%d/%m/%Y %H:%M")
            self._history_list.addItem(f"{timestamp}  -  {AuditService.describe(entry)}")
