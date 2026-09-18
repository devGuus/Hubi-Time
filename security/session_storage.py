"""Armazenamento seguro do token de sessao para o recurso 'Manter-me conectado'.

Usa o modulo `keyring`, que no Windows grava no Windows Credential Manager
(protegido pelo DPAPI da conta do usuario do SO). NUNCA armazenamos senha
aqui - apenas o refresh_token emitido pelo Supabase Auth, que pode ser
revogado a qualquer momento no logout ou pelo backend.
"""
from __future__ import annotations

import logging

import keyring
from keyring.errors import KeyringError

from config.constants import SESSION_KEYRING_EMAIL_KEY, SESSION_KEYRING_KEY
from config.settings import get_settings

logger = logging.getLogger(__name__)


class SessionStorage:
    def __init__(self, service_name: str | None = None):
        self._service_name = service_name or get_settings().keyring_service

    def save_refresh_token(self, refresh_token: str, email: str) -> None:
        try:
            keyring.set_password(self._service_name, SESSION_KEYRING_KEY, refresh_token)
            keyring.set_password(self._service_name, SESSION_KEYRING_EMAIL_KEY, email)
        except KeyringError:
            logger.exception("Falha ao salvar sessao no cofre de credenciais do sistema.")

    def load_refresh_token(self) -> str | None:
        try:
            return keyring.get_password(self._service_name, SESSION_KEYRING_KEY)
        except KeyringError:
            logger.exception("Falha ao ler sessao do cofre de credenciais do sistema.")
            return None

    def load_last_email(self) -> str | None:
        try:
            return keyring.get_password(self._service_name, SESSION_KEYRING_EMAIL_KEY)
        except KeyringError:
            return None

    def clear(self) -> None:
        for key in (SESSION_KEYRING_KEY, SESSION_KEYRING_EMAIL_KEY):
            try:
                keyring.delete_password(self._service_name, key)
            except KeyringError:
                pass
