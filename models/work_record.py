"""Modelos do registro de jornada e do historico de auditoria."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from config.constants import DayType, RecordStatus


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    # Supabase pode retornar "HH:MM:SS" ou "HH:MM:SS+00:00".
    raw = value.split("+")[0].split("-")[0] if len(value) > 8 else value
    parts = raw.strip().split(":")
    hour, minute = int(parts[0]), int(parts[1])
    second = int(parts[2]) if len(parts) > 2 else 0
    return time(hour=hour, minute=minute, second=second)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass
class WorkRecord:
    """Registro diario de jornada. Todos os horarios sao opcionais (NULL)."""

    id: str | None
    user_id: str
    work_date: date
    entry_time: time | None = None
    lunch_start: time | None = None
    lunch_end: time | None = None
    exit_time: time | None = None
    day_type: DayType = DayType.NORMAL
    notes: str | None = None
    status: RecordStatus = RecordStatus.ACTIVE
    archived_at: datetime | None = None
    archived_by: str | None = None
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkRecord":
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            work_date=_parse_date(data["work_date"]),
            entry_time=_parse_time(data.get("entry_time")),
            lunch_start=_parse_time(data.get("lunch_start")),
            lunch_end=_parse_time(data.get("lunch_end")),
            exit_time=_parse_time(data.get("exit_time")),
            day_type=DayType(data.get("day_type", "normal")),
            notes=data.get("notes"),
            status=RecordStatus(data.get("status", "active")),
            archived_at=_parse_dt(data.get("archived_at")),
            archived_by=data.get("archived_by"),
            version=data.get("version", 1),
            created_at=_parse_dt(data.get("created_at")),
            updated_at=_parse_dt(data.get("updated_at")),
        )

    def to_upsert_payload(self) -> dict[str, Any]:
        """Payload para INSERT/UPDATE. Campos vazios viram NULL explicito."""
        return {
            "user_id": self.user_id,
            "work_date": self.work_date.isoformat(),
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "lunch_start": self.lunch_start.isoformat() if self.lunch_start else None,
            "lunch_end": self.lunch_end.isoformat() if self.lunch_end else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "day_type": self.day_type.value,
            "notes": self.notes,
        }

    @property
    def is_complete(self) -> bool:
        if not self.day_type.counts_as_expected_workday:
            return True
        return all(
            [self.entry_time, self.lunch_start, self.lunch_end, self.exit_time]
        )

    @property
    def is_archived(self) -> bool:
        return self.status == RecordStatus.ARCHIVED


@dataclass
class WorkRecordHistoryEntry:
    id: str
    work_record_id: str
    user_id: str
    action: str
    field_changed: str | None
    old_value: str | None
    new_value: str | None
    changed_at: datetime
    changed_by: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkRecordHistoryEntry":
        return cls(
            id=data["id"],
            work_record_id=data["work_record_id"],
            user_id=data["user_id"],
            action=data["action"],
            field_changed=data.get("field_changed"),
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            changed_at=_parse_dt(data["changed_at"]),
            changed_by=data["changed_by"],
        )
