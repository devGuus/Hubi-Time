"""Tela de Configuracoes: tema, notificacoes, carga horaria, salario e horas extras.

Vigencias de carga horaria e salario nunca sao sobrescritas: cada alteracao
cria uma nova linha com `effective_from`, preservando o historico usado nos
calculos de meses anteriores.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDateEdit, QDoubleSpinBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app_container import AppContainer
from app_state import AppState
from config.constants import DATE_FORMAT_DISPLAY, Theme
from utils.dates import weekday_label
from utils.money import format_brl
from widgets.cards import SectionCard
from widgets.dialogs import show_error, show_success
from widgets.loading_button import LoadingButton
from workers.async_worker import AsyncTaskRunner

_WEEKDAY_KEYS = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
_WEEKDAY_LABELS = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]

_NOTIFICATION_LABELS = {
    "missing_lunch_return": "Avisar quando faltar registrar o retorno do almoco",
    "incomplete_today": "Avisar quando o registro do dia estiver incompleto",
    "time_inconsistency": "Avisar sobre horarios inconsistentes",
    "incomplete_month": "Avisar sobre registros incompletos no mes",
}


class SettingsScreen(QWidget):
    def __init__(self, container: AppContainer, app_state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._app_state = app_state
        self._runner = AsyncTaskRunner(self)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        title = QLabel("Configuracoes")
        title.setProperty("role", "title")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)
        content_layout.addWidget(self._build_theme_card())
        content_layout.addWidget(self._build_notifications_card())
        content_layout.addWidget(self._build_schedule_card())
        content_layout.addWidget(self._build_salary_card())
        content_layout.addWidget(self._build_overtime_card())
        content_layout.addStretch()

        scroll.setWidget(content)

        outer.addWidget(title)
        outer.addWidget(scroll)

    def showEvent(self, event) -> None:  # noqa: N802 - metodo Qt
        super().showEvent(event)
        self._refresh_theme_buttons()
        self._refresh_notifications()
        self._load_schedule()
        self._load_salary()
        self._load_overtime_rules()

    # ------------------------------------------------------------------
    # Tema
    # ------------------------------------------------------------------
    def _build_theme_card(self) -> SectionCard:
        card = SectionCard("Tema")
        row = QHBoxLayout()
        self._light_button = QPushButton("Claro")
        self._light_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._light_button.clicked.connect(lambda: self._set_theme(Theme.LIGHT))
        self._dark_button = QPushButton("Escuro")
        self._dark_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dark_button.clicked.connect(lambda: self._set_theme(Theme.DARK))
        row.addWidget(self._light_button)
        row.addWidget(self._dark_button)
        row.addStretch()
        card.body().addLayout(row)
        return card

    def _refresh_theme_buttons(self) -> None:
        current = self._app_state.current_theme()
        self._light_button.setProperty("variant", "primary" if current == Theme.LIGHT else "ghost")
        self._dark_button.setProperty("variant", "primary" if current == Theme.DARK else "ghost")
        for btn in (self._light_button, self._dark_button):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _set_theme(self, theme: Theme) -> None:
        self._app_state.set_theme(theme)
        self._refresh_theme_buttons()
        self._runner.run(
            self._container.user_repository.update_settings,
            self._app_state.user_id,
            theme=theme.value,
            on_error=lambda msg: show_error(self, msg),
        )

    # ------------------------------------------------------------------
    # Notificacoes
    # ------------------------------------------------------------------
    def _build_notifications_card(self) -> SectionCard:
        card = SectionCard("Notificacoes")
        self._notification_checks: dict[str, QCheckBox] = {}
        for key, label in _NOTIFICATION_LABELS.items():
            checkbox = QCheckBox(label)
            checkbox.stateChanged.connect(lambda _state, k=key: self._on_notification_toggled(k))
            self._notification_checks[key] = checkbox
            card.body().addWidget(checkbox)
        return card

    def _refresh_notifications(self) -> None:
        settings = self._app_state.settings
        enabled = (settings.notifications_enabled if settings else None) or {}
        for key, checkbox in self._notification_checks.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(enabled.get(key, True))
            checkbox.blockSignals(False)

    def _on_notification_toggled(self, key: str) -> None:
        if self._app_state.settings is None:
            return
        current = dict(self._app_state.settings.notifications_enabled or {})
        current[key] = self._notification_checks[key].isChecked()
        self._app_state.settings.notifications_enabled = current
        self._runner.run(
            self._container.user_repository.update_settings,
            self._app_state.user_id,
            notifications_enabled=current,
            on_error=lambda msg: show_error(self, msg),
        )

    # ------------------------------------------------------------------
    # Carga horaria
    # ------------------------------------------------------------------
    def _build_schedule_card(self) -> SectionCard:
        card = SectionCard("Carga horaria")
        self._schedule_status_label = QLabel("Nenhuma carga horaria configurada ainda.")
        self._schedule_status_label.setWordWrap(True)
        card.body().addWidget(self._schedule_status_label)

        form_row = QHBoxLayout()
        form_row.setSpacing(8)
        self._weekday_spins: list[QDoubleSpinBox] = []
        for label in _WEEKDAY_LABELS:
            col = QVBoxLayout()
            col.addWidget(QLabel(label))
            spin = QDoubleSpinBox()
            spin.setRange(0, 24)
            spin.setSingleStep(0.5)
            spin.setDecimals(1)
            spin.setValue(8.0 if label not in ("Sabado", "Domingo") else 0.0)
            col.addWidget(spin)
            form_row.addLayout(col)
            self._weekday_spins.append(spin)
        card.body().addLayout(form_row)

        effective_row = QHBoxLayout()
        effective_row.addWidget(QLabel("Vigente a partir de"))
        self._schedule_effective_date = QDateEdit()
        self._schedule_effective_date.setCalendarPopup(True)
        self._schedule_effective_date.setDisplayFormat(DATE_FORMAT_DISPLAY.upper())
        self._schedule_effective_date.setDate(date.today())
        effective_row.addWidget(self._schedule_effective_date)
        effective_row.addStretch()
        self._save_schedule_button = LoadingButton("Salvar nova vigencia", variant="primary")
        self._save_schedule_button.clicked.connect(self._on_save_schedule)
        effective_row.addWidget(self._save_schedule_button)
        card.body().addLayout(effective_row)
        return card

    def _load_schedule(self) -> None:
        self._runner.run(
            self._container.schedule_service.get_effective,
            self._app_state.user_id,
            date.today(),
            on_success=self._on_schedule_loaded,
        )

    def _on_schedule_loaded(self, schedule) -> None:
        if schedule is None:
            self._schedule_status_label.setText(
                "Nenhuma carga horaria configurada ainda. Defina uma abaixo."
            )
            return
        parts = [f"{lbl}: {schedule.weekly_hours.get(key, 0):.1f}h" for lbl, key in zip(_WEEKDAY_LABELS, _WEEKDAY_KEYS)]
        self._schedule_status_label.setText(
            f"Vigente desde {schedule.effective_from.strftime('%d/%m/%Y')} – " + " | ".join(parts)
        )

    def _on_save_schedule(self) -> None:
        weekly_hours = {key: spin.value() for key, spin in zip(_WEEKDAY_KEYS, self._weekday_spins)}
        qd = self._schedule_effective_date.date()
        effective_from = date(qd.year(), qd.month(), qd.day())

        self._save_schedule_button.set_loading(True)
        self._runner.run(
            self._container.schedule_service.create_vigencia,
            self._app_state.user_id,
            effective_from,
            weekly_hours,
            None,
            None,
            on_success=lambda _entry: self._on_schedule_saved(),
            on_error=lambda msg: show_error(self, msg),
            on_finished=lambda: self._save_schedule_button.set_loading(False),
        )

    def _on_schedule_saved(self) -> None:
        show_success(self, "Nova vigencia de carga horaria salva.")
        self._load_schedule()

    # ------------------------------------------------------------------
    # Salario
    # ------------------------------------------------------------------
    def _build_salary_card(self) -> SectionCard:
        card = SectionCard("Salario")
        self._salary_status_label = QLabel("Nenhum salario configurado ainda.")
        self._salary_status_label.setWordWrap(True)
        card.body().addWidget(self._salary_status_label)

        form_row = QHBoxLayout()
        form_row.setSpacing(10)
        salary_col = QVBoxLayout()
        salary_col.addWidget(QLabel("Salario mensal (R$)"))
        self._salary_input = QLineEdit()
        self._salary_input.setPlaceholderText("Ex.: 3500,00")
        salary_col.addWidget(self._salary_input)

        hours_col = QVBoxLayout()
        hours_col.addWidget(QLabel("Carga mensal (horas)"))
        self._monthly_hours_spin = QDoubleSpinBox()
        self._monthly_hours_spin.setRange(1, 744)
        self._monthly_hours_spin.setDecimals(2)
        self._monthly_hours_spin.setValue(220.0)
        hours_col.addWidget(self._monthly_hours_spin)

        date_col = QVBoxLayout()
        date_col.addWidget(QLabel("Vigente a partir de"))
        self._salary_effective_date = QDateEdit()
        self._salary_effective_date.setCalendarPopup(True)
        self._salary_effective_date.setDisplayFormat(DATE_FORMAT_DISPLAY.upper())
        self._salary_effective_date.setDate(date.today())
        date_col.addWidget(self._salary_effective_date)

        form_row.addLayout(salary_col)
        form_row.addLayout(hours_col)
        form_row.addLayout(date_col)
        card.body().addLayout(form_row)

        self._save_salary_button = LoadingButton("Salvar nova vigencia", variant="primary")
        self._save_salary_button.clicked.connect(self._on_save_salary)
        card.body().addWidget(self._save_salary_button)
        return card

    def _load_salary(self) -> None:
        self._runner.run(
            self._container.salary_service.get_effective,
            self._app_state.user_id,
            date.today(),
            on_success=self._on_salary_loaded,
        )

    def _on_salary_loaded(self, salary) -> None:
        if salary is None:
            self._salary_status_label.setText("Nenhum salario configurado ainda. Defina abaixo.")
            return
        self._salary_status_label.setText(
            f"Vigente desde {salary.effective_from.strftime('%d/%m/%Y')} – "
            f"{format_brl(salary.salary)} / {salary.monthly_hours}h – "
            f"hora estimada: {format_brl(salary.hourly_rate)}"
        )

    def _on_save_salary(self) -> None:
        try:
            salary_value = Decimal(self._salary_input.text().strip().replace(".", "").replace(",", "."))
        except InvalidOperation:
            show_error(self, "Informe um valor de salario valido.")
            return
        if salary_value < 0:
            show_error(self, "O salario nao pode ser negativo.")
            return

        qd = self._salary_effective_date.date()
        effective_from = date(qd.year(), qd.month(), qd.day())
        monthly_hours = Decimal(str(self._monthly_hours_spin.value()))

        self._save_salary_button.set_loading(True)
        self._runner.run(
            self._container.salary_service.create_vigencia,
            self._app_state.user_id,
            effective_from,
            salary_value,
            monthly_hours,
            on_success=lambda _entry: self._on_salary_saved(),
            on_error=lambda msg: show_error(self, msg),
            on_finished=lambda: self._save_salary_button.set_loading(False),
        )

    def _on_salary_saved(self) -> None:
        show_success(self, "Nova vigencia salarial salva.")
        self._salary_input.clear()
        self._load_salary()

    # ------------------------------------------------------------------
    # Horas extras
    # ------------------------------------------------------------------
    def _build_overtime_card(self) -> SectionCard:
        card = SectionCard("Percentuais de hora extra")
        self._overtime_list = QListWidget()
        self._overtime_list.setFixedHeight(90)
        card.body().addWidget(self._overtime_list)

        form_row = QHBoxLayout()
        form_row.setSpacing(10)
        self._overtime_name = QLineEdit()
        self._overtime_name.setPlaceholderText("Ex.: Hora extra 50%")
        self._overtime_percentage = QDoubleSpinBox()
        self._overtime_percentage.setRange(0, 500)
        self._overtime_percentage.setSuffix(" %")
        self._overtime_percentage.setValue(50.0)
        self._overtime_effective_date = QDateEdit()
        self._overtime_effective_date.setCalendarPopup(True)
        self._overtime_effective_date.setDisplayFormat(DATE_FORMAT_DISPLAY.upper())
        self._overtime_effective_date.setDate(date.today())

        form_row.addWidget(self._overtime_name)
        form_row.addWidget(self._overtime_percentage)
        form_row.addWidget(self._overtime_effective_date)
        card.body().addLayout(form_row)

        self._save_overtime_button = LoadingButton("Adicionar regra", variant="primary")
        self._save_overtime_button.clicked.connect(self._on_save_overtime_rule)
        card.body().addWidget(self._save_overtime_button)
        return card

    def _load_overtime_rules(self) -> None:
        self._runner.run(
            self._container.salary_service.list_overtime_rules,
            self._app_state.user_id,
            on_success=self._on_overtime_rules_loaded,
        )

    def _on_overtime_rules_loaded(self, rules: list) -> None:
        self._overtime_list.clear()
        if not rules:
            self._overtime_list.addItem("Nenhuma regra cadastrada.")
            return
        for rule in rules:
            self._overtime_list.addItem(
                f"{rule.name} – {rule.percentage}% – vigente desde {rule.effective_from.strftime('%d/%m/%Y')}"
            )

    def _on_save_overtime_rule(self) -> None:
        name = self._overtime_name.text().strip()
        if not name:
            show_error(self, "Informe um nome para a regra (ex.: Hora extra 50%).")
            return
        qd = self._overtime_effective_date.date()
        effective_from = date(qd.year(), qd.month(), qd.day())
        percentage = Decimal(str(self._overtime_percentage.value()))

        self._save_overtime_button.set_loading(True)
        self._runner.run(
            self._container.salary_service.create_overtime_rule,
            self._app_state.user_id,
            name,
            percentage,
            effective_from,
            on_success=lambda _rule: self._on_overtime_saved(),
            on_error=lambda msg: show_error(self, msg),
            on_finished=lambda: self._save_overtime_button.set_loading(False),
        )

    def _on_overtime_saved(self) -> None:
        show_success(self, "Regra de hora extra adicionada.")
        self._overtime_name.clear()
        self._load_overtime_rules()
