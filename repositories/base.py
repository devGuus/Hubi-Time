"""Utilidades compartilhadas pelos repositories."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

import httpx
from postgrest.exceptions import APIError

from repositories.exceptions import ConnectionUnavailableError, RepositoryError

logger = logging.getLogger(__name__)


@contextmanager
def translate_errors(operation: str) -> Iterator[None]:
    """Converte excecoes do SDK/rede em RepositoryError com mensagem amigavel.

    O detalhe tecnico e sempre logado; a UI so ve a mensagem amigavel.
    """
    try:
        yield
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
        logger.error("Falha de conexao durante '%s': %s", operation, exc)
        raise ConnectionUnavailableError(
            "Nao foi possivel conectar ao servidor. Verifique sua internet e tente novamente.",
            technical_detail=str(exc),
        ) from exc
    except APIError as exc:
        logger.error("Erro da API do Supabase durante '%s': %s", operation, exc)
        raise RepositoryError(
            "Ocorreu um erro ao acessar seus dados. Tente novamente em instantes.",
            technical_detail=str(exc),
        ) from exc
    except RepositoryError:
        raise
    except Exception as exc:  # pragma: no cover - rede de seguranca
        logger.exception("Erro inesperado durante '%s'", operation)
        raise RepositoryError(
            "Ocorreu um erro inesperado. Tente novamente.",
            technical_detail=str(exc),
        ) from exc
