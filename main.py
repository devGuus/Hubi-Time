"""Ponto de entrada da aplicacao Hubi Time.

Responsavel apenas por inicializar logging, montar o container de
dependencias, criar a QApplication e exibir a janela raiz. Nenhuma logica
de negocio ou de interface vive aqui.
"""
from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from app_container import build_container
from app_state import AppState
from config.constants import Theme
from config.settings import ConfigurationError, get_settings
from ui.root_window import RootWindow
from widgets.theme import apply_theme


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


def main() -> int:
    try:
        settings = get_settings()
    except ConfigurationError as exc:
        print(f"Erro de configuracao: {exc}", file=sys.stderr)
        print("Copie .env.example para .env e preencha SUPABASE_URL e SUPABASE_ANON_KEY.", file=sys.stderr)
        return 1

    _configure_logging(settings.log_level)
    logger = logging.getLogger("hubi_time")
    logger.info("Iniciando Hubi Time...")

    app = QApplication(sys.argv)
    app.setApplicationName("Hubi Time")
    app.setOrganizationName("Hubi Happiness")

    apply_theme(app, Theme.LIGHT)

    container = build_container()
    app_state = AppState()

    window = RootWindow(container, app_state)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
