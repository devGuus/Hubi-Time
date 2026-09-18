"""Sidebar de navegacao principal."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

NAV_ITEMS: list[tuple[str, str, str]] = [
    ("today", "Hoje", "\U0001F3E0"),
    ("register", "Registrar Horas", "\U0001F550"),
    ("calendar", "Calendario", "\U0001F4C5"),
    ("history", "Historico", "\U0001F553"),
    ("hours_control", "Controle de Horas", "\U0001F4CA"),
    ("bank_hours", "Banco de Horas", "\U0001F3E6"),
    ("finance", "Financeiro", "\U0001F4B0"),
    ("reports", "Relatorios", "\U0001F4C4"),
    ("settings", "Configuracoes", "⚙"),
    ("profile", "Perfil", "\U0001F464"),
]


class Sidebar(QWidget):
    navigate = Signal(str)
    logout_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(232)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 16)
        layout.setSpacing(4)

        brand = QLabel("Hubi Time")
        brand.setProperty("role", "title")
        brand.setContentsMargins(6, 0, 0, 24)
        layout.addWidget(brand)

        self._buttons: dict[str, QPushButton] = {}
        for key, label, icon in NAV_ITEMS:
            button = QPushButton(f"  {icon}   {label}")
            button.setObjectName("sidebarItem")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setCheckable(False)
            button.clicked.connect(lambda _checked=False, k=key: self.navigate.emit(k))
            layout.addWidget(button)
            self._buttons[key] = button

        layout.addStretch()

        logout_button = QPushButton("  \U0001F6AA   Sair")
        logout_button.setObjectName("sidebarItem")
        logout_button.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_button.clicked.connect(self.logout_requested.emit)
        layout.addWidget(logout_button)

    def set_active(self, key: str) -> None:
        for item_key, button in self._buttons.items():
            is_active = item_key == key
            button.setProperty("active", "true" if is_active else "false")
            button.style().unpolish(button)
            button.style().polish(button)
