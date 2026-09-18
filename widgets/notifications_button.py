"""Botao/area de notificacoes: agrega alertas uteis (dia incompleto, retorno
do almoco pendente, inconsistencias, mes incompleto) e os exibe em um painel,
respeitando as preferencias de habilitar/desabilitar de Configuracoes.
"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QListWidget, QPushButton, QVBoxLayout, QWidget

from app_container import AppContainer
from app_state import AppState
from services.notification_service import NotificationService
from utils.dates import month_range
from workers.async_worker import AsyncTaskRunner

REFRESH_INTERVAL_MS = 5 * 60 * 1000


class NotificationsButton(QWidget):
    def __init__(self, container: AppContainer, app_state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._app_state = app_state
        self._runner = AsyncTaskRunner(self)
        self._alerts: list[str] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._button = QPushButton("\U0001F514 Notificacoes")
        self._button.setProperty("variant", "ghost")
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button.clicked.connect(self._open_panel)
        layout.addWidget(self._button)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(REFRESH_INTERVAL_MS)
        self._refresh_timer.timeout.connect(self.refresh_count)
        self._refresh_timer.start()

    def showEvent(self, event) -> None:  # noqa: N802 - metodo Qt
        super().showEvent(event)
        self.refresh_count()

    def refresh_count(self) -> None:
        self._runner.run(self._collect_alerts, on_success=self._on_alerts_loaded)

    def _collect_alerts(self) -> list[str]:
        user_id = self._app_state.user_id
        today = date.today()
        settings = self._app_state.settings
        enabled = (settings.notifications_enabled if settings else None) or {}

        record = self._container.work_service.get_day(user_id, today)
        warnings = self._container.work_service.detect_warnings(record)
        alerts = NotificationService.build_today_alerts(record, warnings, enabled)

        start, end = month_range(today.year, today.month)
        month_records = self._container.work_service.list_range(user_id, start, end, False)
        incomplete_count = sum(
            1 for r in month_records if r.day_type.counts_as_expected_workday and not r.is_complete
        )
        month_alert = NotificationService.build_month_incomplete_alert(incomplete_count, enabled)
        if month_alert:
            alerts.append(month_alert)
        return alerts

    def _on_alerts_loaded(self, alerts: list[str]) -> None:
        self._alerts = alerts
        count = len(alerts)
        self._button.setText(f"\U0001F514 Notificacoes ({count})" if count else "\U0001F514 Notificacoes")
        self._button.setStyleSheet("font-weight: 700; color: #DC2626;" if count else "")

    def _open_panel(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Notificacoes")
        dialog.resize(420, 360)
        layout = QVBoxLayout(dialog)

        list_widget = QListWidget()
        if not self._alerts:
            list_widget.addItem("Nenhum alerta no momento. Tudo em dia!")
        else:
            for alert in self._alerts:
                list_widget.addItem(f"⚠ {alert}")
        layout.addWidget(list_widget)

        close_button = QPushButton("Fechar")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec()
