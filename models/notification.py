"""Modelos de notificacao/alerta e feriado."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass
class Notification:
    id: str | None
    user_id: str
    type: str
    message: str
    read: bool = False
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Notification":
        created = data.get("created_at")
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            type=data["type"],
            message=data["message"],
            read=bool(data.get("read", False)),
            metadata=data.get("metadata"),
            created_at=datetime.fromisoformat(created.replace("Z", "+00:00")) if created else None,
        )


@dataclass
class Holiday:
    id: str | None
    user_id: str
    holiday_date: date
    name: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Holiday":
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            holiday_date=date.fromisoformat(data["holiday_date"]),
            name=data["name"],
        )

    def to_insert_payload(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "holiday_date": self.holiday_date.isoformat(),
            "name": self.name,
        }
