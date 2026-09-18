"""Acesso a dados de notifications."""
from __future__ import annotations

from supabase import Client

from models.notification import Notification
from repositories.base import translate_errors

TABLE = "notifications"


class NotificationRepository:
    def __init__(self, client: Client):
        self._client = client

    def list_recent(self, user_id: str, limit: int = 30) -> list[Notification]:
        with translate_errors("listar notificacoes"):
            resp = (
                self._client.table(TABLE)
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
        return [Notification.from_dict(row) for row in (resp.data or [])]

    def count_unread(self, user_id: str) -> int:
        with translate_errors("contar notificacoes nao lidas"):
            resp = (
                self._client.table(TABLE)
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("read", False)
                .execute()
            )
        return resp.count or 0

    def create(self, notification: Notification) -> Notification:
        with translate_errors("criar notificacao"):
            resp = (
                self._client.table(TABLE)
                .insert(
                    {
                        "user_id": notification.user_id,
                        "type": notification.type,
                        "message": notification.message,
                        "metadata": notification.metadata,
                    }
                )
                .execute()
            )
        return Notification.from_dict(resp.data[0])

    def mark_as_read(self, user_id: str, notification_id: str) -> None:
        with translate_errors("marcar notificacao como lida"):
            self._client.table(TABLE).update({"read": True}).eq("user_id", user_id).eq(
                "id", notification_id
            ).execute()

    def mark_all_as_read(self, user_id: str) -> None:
        with translate_errors("marcar todas as notificacoes como lidas"):
            self._client.table(TABLE).update({"read": True}).eq("user_id", user_id).eq(
                "read", False
            ).execute()
