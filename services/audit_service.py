"""Leitura e formatacao amigavel do historico de auditoria de jornada, e
registro de auditoria generica (salario, carga horaria, configuracoes)."""
from __future__ import annotations

from typing import Any

from models.work_record import WorkRecordHistoryEntry
from repositories.audit_repository import AuditRepository
from repositories.work_repository import WorkRepository

FIELD_LABELS_PT = {
    "entry_time": "Entrada",
    "lunch_start": "Saida para almoco",
    "lunch_end": "Retorno do almoco",
    "exit_time": "Saida",
    "day_type": "Tipo de dia",
    "notes": "Observacoes",
    "status": "Status",
}


class AuditService:
    def __init__(self, work_repository: WorkRepository, audit_repository: AuditRepository):
        self._work_repo = work_repository
        self._audit_repo = audit_repository

    def get_work_record_history(self, user_id: str, work_record_id: str) -> list[WorkRecordHistoryEntry]:
        return self._work_repo.get_history(user_id, work_record_id)

    @staticmethod
    def describe(entry: WorkRecordHistoryEntry) -> str:
        label = FIELD_LABELS_PT.get(entry.field_changed or "", entry.field_changed or "Registro")
        if entry.action == "CREATE":
            return f"{label} registrado: {entry.new_value}"
        if entry.action == "ARCHIVE":
            return "Registro arquivado"
        if entry.action == "RESTORE":
            return "Registro restaurado"
        old = entry.old_value if entry.old_value not in (None, "") else "--:--"
        return f"{label} alterado: {old} -> {entry.new_value}"

    def log_generic(
        self,
        user_id: str,
        entity: str,
        action: str,
        entity_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._audit_repo.log(user_id, entity, action, entity_id, metadata)
