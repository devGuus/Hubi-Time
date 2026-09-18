"""Sistema de tema (claro/escuro) da aplicacao.

Define tokens de cor e gera a folha de estilo (QSS) global, para que a
aplicacao tenha aparencia de software SaaS moderno em vez do visual padrao
do Qt. `apply_theme` deve ser chamada uma vez no QApplication e sempre que
o usuario alternar o tema nas Configuracoes.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication

from config.constants import Theme


@dataclass(frozen=True)
class ColorTokens:
    background: str
    surface: str
    surface_alt: str
    border: str
    text_primary: str
    text_secondary: str
    primary: str
    primary_hover: str
    primary_soft: str
    success: str
    warning: str
    danger: str
    info: str
    shadow: str


LIGHT_TOKENS = ColorTokens(
    background="#F4F6FB",
    surface="#FFFFFF",
    surface_alt="#EEF1F8",
    border="#E3E7F0",
    text_primary="#1B2130",
    text_secondary="#6B7280",
    primary="#4F6EF7",
    primary_hover="#3E5AE0",
    primary_soft="#E9EDFE",
    success="#16A34A",
    warning="#D97706",
    danger="#DC2626",
    info="#2563EB",
    shadow="rgba(31, 41, 55, 0.08)",
)

DARK_TOKENS = ColorTokens(
    background="#10131C",
    surface="#181C29",
    surface_alt="#1F2433",
    border="#2A3040",
    text_primary="#E8EAF1",
    text_secondary="#9AA1B4",
    primary="#6C86FF",
    primary_hover="#8398FF",
    primary_soft="#232B4D",
    success="#22C55E",
    warning="#F59E0B",
    danger="#EF4444",
    info="#3B82F6",
    shadow="rgba(0, 0, 0, 0.35)",
)


def tokens_for(theme: Theme) -> ColorTokens:
    return DARK_TOKENS if theme == Theme.DARK else LIGHT_TOKENS


def build_stylesheet(theme: Theme) -> str:
    t = tokens_for(theme)
    return f"""
    * {{
        font-family: "Segoe UI", "Inter", sans-serif;
        outline: none;
    }}

    QWidget {{
        background-color: {t.background};
        color: {t.text_primary};
        font-size: 13px;
    }}

    QWidget#sidebar {{
        background-color: {t.surface};
        border-right: 1px solid {t.border};
    }}

    QWidget[card="true"] {{
        background-color: {t.surface};
        border: 1px solid {t.border};
        border-radius: 12px;
    }}

    QLabel[role="title"] {{
        font-size: 20px;
        font-weight: 600;
        color: {t.text_primary};
    }}

    QLabel[role="subtitle"] {{
        font-size: 13px;
        color: {t.text_secondary};
    }}

    QLabel[role="section"] {{
        font-size: 15px;
        font-weight: 600;
        color: {t.text_primary};
    }}

    QLabel[role="stat-value"] {{
        font-size: 26px;
        font-weight: 700;
        color: {t.text_primary};
    }}

    QLabel[role="stat-label"] {{
        font-size: 12px;
        color: {t.text_secondary};
        font-weight: 500;
    }}

    QLabel[role="caption"] {{
        font-size: 11px;
        color: {t.text_secondary};
    }}

    QLineEdit, QDateEdit, QTimeEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {{
        background-color: {t.surface};
        border: 1px solid {t.border};
        border-radius: 8px;
        padding: 8px 10px;
        color: {t.text_primary};
        selection-background-color: {t.primary};
    }}

    QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus, QComboBox:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {t.primary};
    }}

    QLineEdit:disabled, QDateEdit:disabled, QTimeEdit:disabled {{
        background-color: {t.surface_alt};
        color: {t.text_secondary};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    QPushButton {{
        background-color: {t.surface_alt};
        border: 1px solid {t.border};
        border-radius: 8px;
        padding: 8px 16px;
        color: {t.text_primary};
        font-weight: 500;
    }}

    QPushButton:hover {{
        background-color: {t.border};
    }}

    QPushButton:disabled {{
        color: {t.text_secondary};
    }}

    QPushButton[variant="primary"] {{
        background-color: {t.primary};
        border: 1px solid {t.primary};
        color: #FFFFFF;
        font-weight: 600;
    }}

    QPushButton[variant="primary"]:hover {{
        background-color: {t.primary_hover};
        border: 1px solid {t.primary_hover};
    }}

    QPushButton[variant="primary"]:disabled {{
        background-color: {t.border};
        border: 1px solid {t.border};
        color: {t.text_secondary};
    }}

    QPushButton[variant="danger"] {{
        background-color: transparent;
        border: 1px solid {t.danger};
        color: {t.danger};
    }}

    QPushButton[variant="danger"]:hover {{
        background-color: {t.danger};
        color: #FFFFFF;
    }}

    QPushButton[variant="link"] {{
        background-color: transparent;
        border: none;
        color: {t.primary};
        font-weight: 600;
        padding: 4px;
    }}

    QPushButton[variant="link"]:hover {{
        color: {t.primary_hover};
        text-decoration: underline;
    }}

    QPushButton[variant="ghost"] {{
        background-color: transparent;
        border: 1px solid transparent;
    }}

    QPushButton[variant="ghost"]:hover {{
        background-color: {t.surface_alt};
    }}

    QPushButton#sidebarItem {{
        background-color: transparent;
        border: none;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: left;
        color: {t.text_secondary};
        font-weight: 500;
    }}

    QPushButton#sidebarItem:hover {{
        background-color: {t.surface_alt};
        color: {t.text_primary};
    }}

    QPushButton#sidebarItem[active="true"] {{
        background-color: {t.primary_soft};
        color: {t.primary};
        font-weight: 600;
    }}

    QTableWidget {{
        background-color: {t.surface};
        border: 1px solid {t.border};
        border-radius: 10px;
        gridline-color: {t.border};
        selection-background-color: {t.primary_soft};
        selection-color: {t.text_primary};
    }}

    QHeaderView::section {{
        background-color: {t.surface_alt};
        color: {t.text_secondary};
        padding: 8px;
        border: none;
        border-bottom: 1px solid {t.border};
        font-weight: 600;
    }}

    QTableWidget::item {{
        padding: 6px;
        border-bottom: 1px solid {t.border};
    }}

    QTabWidget::pane {{
        border: 1px solid {t.border};
        border-radius: 10px;
        top: -1px;
    }}

    QTabBar::tab {{
        background-color: transparent;
        color: {t.text_secondary};
        padding: 8px 16px;
        margin-right: 4px;
        border-bottom: 2px solid transparent;
        font-weight: 500;
    }}

    QTabBar::tab:selected {{
        color: {t.primary};
        border-bottom: 2px solid {t.primary};
        font-weight: 600;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
    }}

    QScrollBar::handle:vertical {{
        background: {t.border};
        border-radius: 5px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {t.text_secondary};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
    }}

    QScrollBar::handle:horizontal {{
        background: {t.border};
        border-radius: 5px;
        min-width: 30px;
    }}

    QToolTip {{
        background-color: {t.text_primary};
        color: {t.surface};
        border: none;
        padding: 6px 10px;
        border-radius: 6px;
    }}

    QCheckBox {{
        spacing: 8px;
        color: {t.text_primary};
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 1px solid {t.border};
        background-color: {t.surface};
    }}

    QCheckBox::indicator:checked {{
        background-color: {t.primary};
        border: 1px solid {t.primary};
    }}

    QMenu {{
        background-color: {t.surface};
        border: 1px solid {t.border};
        border-radius: 8px;
        padding: 6px;
    }}

    QMenu::item {{
        padding: 8px 14px;
        border-radius: 6px;
    }}

    QMenu::item:selected {{
        background-color: {t.primary_soft};
        color: {t.primary};
    }}

    QCalendarWidget QToolButton {{
        color: {t.text_primary};
        background-color: transparent;
        border-radius: 6px;
        padding: 4px;
    }}

    QCalendarWidget QToolButton:hover {{
        background-color: {t.surface_alt};
    }}

    QCalendarWidget QWidget#qt_calendar_navigationbar {{
        background-color: {t.surface};
    }}

    QCalendarWidget QAbstractItemView:enabled {{
        background-color: {t.surface};
        color: {t.text_primary};
        selection-background-color: {t.primary};
        selection-color: #FFFFFF;
    }}
    """


def apply_theme(app: QApplication, theme: Theme) -> None:
    app.setStyleSheet(build_stylesheet(theme))
