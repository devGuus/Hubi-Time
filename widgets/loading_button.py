"""Botao com estado de carregamento, evitando cliques duplicados durante
operacoes assincronas (requisito de nunca disparar requisicoes duplicadas)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QWidget


class LoadingButton(QPushButton):
    def __init__(self, text: str, variant: str = "primary", parent: QWidget | None = None):
        super().__init__(text, parent)
        self._default_text = text
        self.setProperty("variant", variant)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_loading(self, loading: bool, loading_text: str = "Salvando...") -> None:
        self.setDisabled(loading)
        self.setText(loading_text if loading else self._default_text)

    def set_default_text(self, text: str) -> None:
        self._default_text = text
        if not self.isEnabled():
            return
        self.setText(text)
