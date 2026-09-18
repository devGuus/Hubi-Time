"""Regras de autenticacao: cadastro, verificacao por OTP, login, sessao
persistente e recuperacao de senha. Toda a autenticacao real e delegada ao
Supabase Auth - este modulo apenas orquestra chamadas e traduz erros.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from supabase import Client

from models.user import AuthSession
from security.session_storage import SessionStorage
from services.exceptions import AuthenticationError, translate_auth_errors

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, client: Client, session_storage: SessionStorage):
        self._client = client
        self._session_storage = session_storage

    # ------------------------------------------------------------------
    # Cadastro e verificacao de e-mail por OTP
    # ------------------------------------------------------------------
    def sign_up(self, name: str, email: str, password: str) -> None:
        with translate_auth_errors("cadastrar usuario"):
            self._client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": {"name": name}},
                }
            )

    def verify_signup_otp(self, email: str, code: str) -> AuthSession:
        with translate_auth_errors("verificar codigo de e-mail"):
            response = self._client.auth.verify_otp(
                {"email": email, "token": code, "type": "signup"}
            )
        return self._session_from_response(response)

    def resend_signup_otp(self, email: str) -> None:
        with translate_auth_errors("reenviar codigo de verificacao"):
            self._client.auth.resend({"type": "signup", "email": email})

    # ------------------------------------------------------------------
    # Login / logout / sessao persistente
    # ------------------------------------------------------------------
    def sign_in(self, email: str, password: str, keep_signed_in: bool) -> AuthSession:
        with translate_auth_errors("entrar"):
            response = self._client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        session = self._session_from_response(response)
        if keep_signed_in:
            self._session_storage.save_refresh_token(session.refresh_token, session.email)
        else:
            self._session_storage.clear()
        return session

    def restore_session(self) -> AuthSession | None:
        """Tenta restaurar a sessao salva (recurso 'Manter-me conectado').

        Retorna None se nao houver sessao salva ou se ela estiver expirada -
        nesses casos, a tela de login deve ser exibida normalmente.
        """
        refresh_token = self._session_storage.load_refresh_token()
        if not refresh_token:
            return None
        try:
            response = self._client.auth.refresh_session(refresh_token)
        except Exception:
            logger.info("Sessao salva invalida ou expirada; solicitando novo login.")
            self._session_storage.clear()
            return None

        session = self._session_from_response(response)
        self._session_storage.save_refresh_token(session.refresh_token, session.email)
        return session

    def sign_out(self) -> None:
        try:
            self._client.auth.sign_out()
        except Exception:
            logger.warning("Falha ao encerrar sessao no servidor; prosseguindo com logout local.")
        self._session_storage.clear()

    def last_remembered_email(self) -> str | None:
        return self._session_storage.load_last_email()

    # ------------------------------------------------------------------
    # Recuperacao e alteracao de senha
    # ------------------------------------------------------------------
    def request_password_reset(self, email: str) -> None:
        with translate_auth_errors("solicitar recuperacao de senha"):
            self._client.auth.reset_password_for_email(email)

    def confirm_password_reset(self, email: str, code: str, new_password: str) -> None:
        with translate_auth_errors("confirmar nova senha"):
            self._client.auth.verify_otp({"email": email, "token": code, "type": "recovery"})
            self._client.auth.update_user({"password": new_password})

    def change_password(self, new_password: str) -> None:
        with translate_auth_errors("alterar senha"):
            self._client.auth.update_user({"password": new_password})

    # ------------------------------------------------------------------
    def _session_from_response(self, response) -> AuthSession:
        session = getattr(response, "session", None)
        user = getattr(response, "user", None)
        if session is None or user is None:
            raise AuthenticationError(
                "Nao foi possivel concluir o login. Confirme seu e-mail antes de entrar."
            )
        expires_at = None
        if getattr(session, "expires_at", None):
            expires_at = datetime.fromtimestamp(session.expires_at, tz=timezone.utc)
        return AuthSession(
            user_id=user.id,
            email=user.email or "",
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_at=expires_at,
        )
