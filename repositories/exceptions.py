"""Excecoes da camada de acesso a dados.

A UI nunca deve capturar excecoes de baixo nivel do SDK do Supabase; os
repositories traduzem qualquer falha para uma destas excecoes, com uma
mensagem tecnica (para log) separada de uma mensagem amigavel (para UI).
"""
from __future__ import annotations


class RepositoryError(Exception):
    """Erro generico de acesso a dados."""

    def __init__(self, friendly_message: str, technical_detail: str | None = None):
        super().__init__(technical_detail or friendly_message)
        self.friendly_message = friendly_message
        self.technical_detail = technical_detail or friendly_message


class NotFoundError(RepositoryError):
    """Registro nao encontrado."""


class ConflictError(RepositoryError):
    """Conflito de concorrencia otimista (o registro foi alterado por outra sessao)."""


class ConnectionUnavailableError(RepositoryError):
    """Falha de rede/conexao com o Supabase."""
