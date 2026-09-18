"""Ponto unico de acesso ao SDK do Supabase.

Mantem um cliente singleton por processo, configurado apenas com a URL e a
chave publica (anon). A sessao autenticada (access/refresh token) e definida
em tempo de execucao pelo AuthService apos login/restauracao de sessao.
"""
from __future__ import annotations

import logging

from supabase import Client, create_client

from config.settings import get_settings

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_supabase_client() -> Client:
    """Retorna o cliente Supabase singleton, criando-o na primeira chamada."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = create_client(settings.supabase_url, settings.supabase_anon_key)
        logger.debug("Cliente Supabase inicializado para %s", settings.supabase_url)
    return _client


def reset_supabase_client() -> None:
    """Descarta o cliente atual (usado no logout para limpar qualquer estado)."""
    global _client
    _client = None
