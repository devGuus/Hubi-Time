"""Geracao e gerenciamento de alertas/notificacoes do usuario."""
from __future__ import annotations

from typing import Any

from models.notification import Notification
from models.work_record import WorkRecord
from repositories.notification_repository import NotificationRepository
from utils.validators import TimeInconsistencyWarning


class NotificationService:
    def __init__(self, repository: NotificationRepository):
        self._repo = repository

    def list_recent(self, user_id: str, limit: int = 30) -> list[Notification]:
        return self._repo.list_recent(user_id, limit)

    def count_unread(self, user_id: str) -> int:
        return self._repo.count_unread(user_id)

    def mark_as_read(self, user_id: str, notification_id: str) -> None:
        self._repo.mark_as_read(user_id, notification_id)

    def mark_all_as_read(self, user_id: str) -> None:
        self._repo.mark_all_as_read(user_id)

    def push(self, user_id: str, type_: str, message: str, metadata: dict[str, Any] | None = None) -> Notification:
        notification = Notification(id=None, user_id=user_id, type=type_, message=message, metadata=metadata)
        return self._repo.create(notification)

    @staticmethod
    def build_today_alerts(
        record: WorkRecord, warnings: list[TimeInconsistencyWarning], enabled: dict[str, bool] | None = None
    ) -> list[str]:
        """Alertas nao persistidos, calculados a partir do estado atual do dia
        (a persistencia via `push` fica a criterio da tela, para nao poluir
        o banco com alertas repetidos a cada abertura da tela)."""
        enabled = enabled or {}
        alerts: list[str] = []

        if enabled.get("missing_lunch_return", True) and record.lunch_start and not record.lunch_end:
            alerts.append("Voce ainda nao registrou o retorno do almoco.")

        if (
            enabled.get("incomplete_today", True)
            and record.day_type.counts_as_expected_workday
            and record.entry_time
            and not record.is_complete
        ):
            alerts.append("Registro de hoje ainda esta incompleto.")

        if enabled.get("time_inconsistency", True):
            alerts.extend(w.message for w in warnings)

        return alerts

    @staticmethod
    def build_month_incomplete_alert(incomplete_count: int, enabled: dict[str, bool] | None = None) -> str | None:
        enabled = enabled or {}
        if not enabled.get("incomplete_month", True):
            return None
        if incomplete_count > 0:
            plural = "s" if incomplete_count != 1 else ""
            return f"Voce possui {incomplete_count} registro{plural} incompleto{plural} neste mes."
        return None
