"""Modelos relacionados a usuario, sessao e perfil."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AuthSession:
    """Sessao autenticada retornada pelo Supabase Auth."""

    user_id: str
    email: str
    access_token: str
    refresh_token: str
    expires_at: datetime | None = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(self.expires_at.tzinfo) >= self.expires_at


@dataclass
class Profile:
    id: str | None
    user_id: str
    name: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Profile":
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            name=data.get("name") or "",
            created_at=_parse_dt(data.get("created_at")),
            updated_at=_parse_dt(data.get("updated_at")),
        )


@dataclass
class UserSettings:
    id: str | None
    user_id: str
    theme: str = "light"
    locale: str = "pt-BR"
    notifications_enabled: dict[str, bool] | None = None
    keep_signed_in: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserSettings":
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            theme=data.get("theme", "light"),
            locale=data.get("locale", "pt-BR"),
            notifications_enabled=data.get("notifications_enabled") or {},
            keep_signed_in=bool(data.get("keep_signed_in", False)),
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
