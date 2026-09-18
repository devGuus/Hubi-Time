"""Acesso a dados de profiles e user_settings."""
from __future__ import annotations

from supabase import Client

from models.user import Profile, UserSettings
from repositories.base import translate_errors
from repositories.exceptions import NotFoundError

PROFILES_TABLE = "profiles"
SETTINGS_TABLE = "user_settings"


class UserRepository:
    def __init__(self, client: Client):
        self._client = client

    def get_profile(self, user_id: str) -> Profile:
        with translate_errors("buscar perfil"):
            resp = (
                self._client.table(PROFILES_TABLE)
                .select("*")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
        rows = resp.data or []
        if not rows:
            raise NotFoundError("Perfil nao encontrado.")
        return Profile.from_dict(rows[0])

    def update_profile_name(self, user_id: str, name: str) -> Profile:
        with translate_errors("atualizar perfil"):
            resp = (
                self._client.table(PROFILES_TABLE)
                .update({"name": name})
                .eq("user_id", user_id)
                .execute()
            )
        rows = resp.data or []
        if not rows:
            raise NotFoundError("Perfil nao encontrado.")
        return Profile.from_dict(rows[0])

    def get_settings(self, user_id: str) -> UserSettings:
        with translate_errors("buscar configuracoes"):
            resp = (
                self._client.table(SETTINGS_TABLE)
                .select("*")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
        rows = resp.data or []
        if not rows:
            raise NotFoundError("Configuracoes nao encontradas.")
        return UserSettings.from_dict(rows[0])

    def update_settings(self, user_id: str, **fields) -> UserSettings:
        with translate_errors("atualizar configuracoes"):
            resp = (
                self._client.table(SETTINGS_TABLE)
                .update(fields)
                .eq("user_id", user_id)
                .execute()
            )
        rows = resp.data or []
        if not rows:
            raise NotFoundError("Configuracoes nao encontradas.")
        return UserSettings.from_dict(rows[0])
