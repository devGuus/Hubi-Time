"""Regras de negocio para registros de jornada: salvamento parcial, arquivamento,
restauracao e deteccao de inconsistencias. Nao acessa o banco diretamente -
delega ao WorkRepository.
"""
from __future__ import annotations

from datetime import date

from models.work_record import WorkRecord
from repositories.work_repository import WorkRepository
from services.exceptions import ServiceError
from utils.validators import TimeInconsistencyWarning, detect_time_inconsistencies


class WorkService:
    def __init__(self, work_repository: WorkRepository):
        self._repo = work_repository

    def get_day(self, user_id: str, work_date: date) -> WorkRecord:
        """Registro do dia, ou um registro vazio (nao persistido) se nao existir.

        Isso implementa o requisito de que abrir uma data sem lancamento deve
        apresentar campos vazios prontos para preenchimento.
        """
        record = self._repo.get_by_date(user_id, work_date)
        if record is None:
            record = WorkRecord(id=None, user_id=user_id, work_date=work_date)
        return record

    def save_fields(self, current: WorkRecord, **changes) -> WorkRecord:
        """Atualiza somente os campos informados e persiste.

        Cria o registro na primeira gravacao do dia; nas gravacoes seguintes
        atualiza o mesmo registro (nunca duplica por UNIQUE(user_id, work_date)
        + verificacao previa de existencia), com checagem de concorrencia
        otimista via `version`.
        """
        for field_name, value in changes.items():
            if not hasattr(current, field_name):
                raise ServiceError(f"Campo desconhecido: {field_name}")
            setattr(current, field_name, value)

        if current.id is None:
            return self._repo.create(current)
        return self._repo.update(current.id, current.user_id, current.version, current)

    def list_range(
        self, user_id: str, start_date: date, end_date: date, include_archived: bool = False
    ) -> list[WorkRecord]:
        return self._repo.list_by_range(user_id, start_date, end_date, include_archived)

    def list_archived(self, user_id: str) -> list[WorkRecord]:
        return self._repo.list_archived(user_id)

    def archive(self, record: WorkRecord, archived_by: str) -> WorkRecord:
        if record.id is None:
            raise ServiceError("Nao ha registro salvo neste dia para arquivar.")
        return self._repo.archive(record.id, record.user_id, archived_by)

    def restore(self, record: WorkRecord) -> WorkRecord:
        if record.id is None:
            raise ServiceError("Registro invalido para restaurar.")
        return self._repo.restore(record.id, record.user_id)

    def detect_warnings(self, record: WorkRecord) -> list[TimeInconsistencyWarning]:
        return detect_time_inconsistencies(
            record.entry_time, record.lunch_start, record.lunch_end, record.exit_time
        )
