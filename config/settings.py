"""Carregamento de configuracoes de ambiente (.env) para a aplicacao.

Somente valores nao sensiveis para o cliente desktop (URL do projeto e a
chave publica anon) sao esperados aqui. Nenhuma credencial administrativa
deve ser lida ou utilizada neste modulo.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _app_base_dir() -> Path:
    """Retorna o diretorio base, considerando execucao via PyInstaller."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


APP_BASE_DIR = _app_base_dir()
_env_path = APP_BASE_DIR / ".env"
load_dotenv(dotenv_path=_env_path if _env_path.exists() else None)


class ConfigurationError(RuntimeError):
    """Levantado quando uma variavel de ambiente obrigatoria esta ausente."""


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"Variavel de ambiente obrigatoria ausente: {name}. "
            f"Copie .env.example para .env e preencha os valores do seu projeto Supabase."
        )
    return value


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_anon_key: str
    keyring_service: str
    log_level: str
    base_dir: Path

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            supabase_url=_require_env("SUPABASE_URL"),
            supabase_anon_key=_require_env("SUPABASE_ANON_KEY"),
            keyring_service=os.getenv("APP_KEYRING_SERVICE", "HubiTime"),
            log_level=os.getenv("APP_LOG_LEVEL", "INFO").upper(),
            base_dir=APP_BASE_DIR,
        )


def get_settings() -> Settings:
    """Retorna as configuracoes carregadas, levantando erro amigavel se invalidas."""
    return Settings.load()
