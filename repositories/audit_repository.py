"""Acesso a dados de audit_log (auditoria generica, fora do ciclo de work_records)."""
from __future__ import annotations

from typing import Any

from supabase import Client

from repositories.base import translate_errors

TABLE = "audit_log"


class AuditRepository:
    def __init__(self, client: Client):
        self._client = client

    def log(self, user_id: str, entity: str, action: str, entity_id: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        with translate_errors("registrar auditoria"):
            self._client.table(TABLE).insert(
                {
                    "user_id": user_id,
                    "entity": entity,
                    "entity_id": entity_id,
                    "action": action,
                    "metadata": metadata,
                }
            ).execute()

    def list_for_entity(self, user_id: str, entity: str, entity_id: str) -> list[dict[str, Any]]:
        with translate_errors("listar auditoria da entidade"):
            resp = (
                self._client.table(TABLE)
                .select("*")
                .eq("user_id", user_id)
                .eq("entity", entity)
                .eq("entity_id", entity_id)
                .order("created_at", desc=True)
                .execute()
            )
        return resp.data or []
