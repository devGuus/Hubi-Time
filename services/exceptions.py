"""Excecoes da camada de servicos + traducao de erros de autenticacao."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

import httpx
from supabase_auth.errors import AuthApiError, AuthRetryableError

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Erro generico de regra de negocio, com mensagem amigavel para a UI."""

    def __init__(self, friendly_message: str, technical_detail: str | None = None):
        super().__init__(technical_detail or friendly_message)
        self.friendly_message = friendly_message
        self.technical_detail = technical_detail or friendly_message


class AuthenticationError(ServiceError):
    """Falha de autenticacao (login, cadastro, OTP, recuperacao de senha)."""


_MESSAGE_TRANSLATIONS = {
    "invalid login credentials": "E-mail ou senha incorretos.",
    "email not confirmed": "Seu e-mail ainda nao foi confirmado. Verifique sua caixa de entrada.",
    "user already registered": "Ja existe uma conta cadastrada com este e-mail.",
    "token has expired or is invalid": "Codigo invalido ou expirado. Solicite um novo codigo.",
    "invalid token": "Codigo invalido. Verifique os numeros digitados.",
    "email rate limit exceeded": "Muitas tentativas em pouco tempo. Aguarde alguns minutos e tente novamente.",
    "over_email_send_rate_limit": "Muitas tentativas em pouco tempo. Aguarde alguns minutos e tente novamente.",
    "user not found": "Nao encontramos uma conta com este e-mail.",
    "password should be at least": "A senha nao atende aos requisitos minimos de seguranca.",
    "same_password": "A nova senha deve ser diferente da senha atual.",
    "new password should be different from the old password": "A nova senha deve ser diferente da senha atual.",
}


def _translate(message: str) -> str:
    lowered = message.lower()
    for fragment, friendly in _MESSAGE_TRANSLATIONS.items():
        if fragment in lowered:
            return friendly
    return "Nao foi possivel concluir a operacao. Verifique os dados e tente novamente."


@contextmanager
def translate_auth_errors(operation: str) -> Iterator[None]:
    try:
        yield
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
        logger.error("Falha de conexao durante '%s': %s", operation, exc)
        raise AuthenticationError(
            "Nao foi possivel conectar ao servidor. Verifique sua internet e tente novamente.",
            technical_detail=str(exc),
        ) from exc
    except AuthRetryableError as exc:
        logger.error("Erro retentavel de autenticacao durante '%s': %s", operation, exc)
        raise AuthenticationError(
            "Servico de autenticacao temporariamente indisponivel. Tente novamente em instantes.",
            technical_detail=str(exc),
        ) from exc
    except AuthApiError as exc:
        logger.error("Erro de autenticacao durante '%s': %s", operation, exc)
        raise AuthenticationError(_translate(str(exc)), technical_detail=str(exc)) from exc
    except ServiceError:
        raise
    except Exception as exc:  # pragma: no cover - rede de seguranca
        logger.exception("Erro inesperado durante '%s'", operation)
        raise AuthenticationError(
            "Ocorreu um erro inesperado. Tente novamente.",
            technical_detail=str(exc),
        ) from exc
