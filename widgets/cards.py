"""Cards reutilizaveis: cartao de estatistica (dashboard) e cartao de secao."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QVBoxLayout, QWidget


def _apply_card_shadow(widget: QWidget) -> None:
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(24)
    effect.setXOffset(0)
    effect.setYOffset(4)
    effect.setColor(QColor(17, 24, 39, 30))
    widget.setGraphicsEffect(effect)


class StatCard(QWidget):
    """Cartao compacto com rotulo, valor em destaque e legenda opcional."""

    def __init__(
        self,
        label: str,
        value: str = "--",
        caption: str = "",
        accent_color: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setProperty("card", "true")
        _apply_card_shadow(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        self._label = QLabel(label)
        self._label.setProperty("role", "stat-label")

        self._value = QLabel(value)
        self._value.setProperty("role", "stat-value")
        if accent_color:
            self._value.setStyleSheet(f"color: {accent_color};")

        self._caption = QLabel(caption)
        self._caption.setProperty("role", "caption")
        self._caption.setVisible(bool(caption))

        layout.addWidget(self._label)
        layout.addWidget(self._value)
        layout.addWidget(self._caption)
        layout.addStretch()

    def set_value(self, value: str, accent_color: str | None = None) -> None:
        self._value.setText(value)
        if accent_color:
            self._value.setStyleSheet(f"color: {accent_color};")

    def set_caption(self, caption: str) -> None:
        self._caption.setText(caption)
        self._caption.setVisible(bool(caption))


class SectionCard(QWidget):
    """Cartao maior com titulo e uma area de conteudo (para telas de detalhe)."""

    def __init__(self, title: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("card", "true")
        _apply_card_shadow(self)

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(20, 18, 20, 18)
        self._outer.setSpacing(12)

        self._header = QHBoxLayout()
        self._title_label = QLabel(title)
        self._title_label.setProperty("role", "section")
        self._title_label.setVisible(bool(title))
        self._header.addWidget(self._title_label)
        self._header.addStretch()
        self._outer.addLayout(self._header)

        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(10)
        self._outer.addLayout(self.content_layout)

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)
        self._title_label.setVisible(bool(title))

    def add_header_widget(self, widget: QWidget) -> None:
        self._header.addWidget(widget)

    def body(self) -> QVBoxLayout:
        return self.content_layout
