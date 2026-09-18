"""Shell principal pos-login: sidebar + area de conteudo com todas as telas."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from app_container import AppContainer
from app_state import AppState
from ui.bank_hours.bank_hours_screen import BankHoursScreen
from ui.calendar.calendar_screen import CalendarScreen
from ui.finance.finance_screen import FinanceScreen
from ui.history.history_screen import HistoryScreen
from ui.hours_control.hours_control_screen import HoursControlScreen
from ui.profile.profile_screen import ProfileScreen
from ui.reports.reports_screen import ReportsScreen
from ui.settings.settings_screen import SettingsScreen
from ui.today.today_screen import TodayScreen
from ui.work_entry.work_entry_screen import WorkEntryScreen
from widgets.notifications_button import NotificationsButton
from widgets.sidebar import Sidebar


class MainShell(QWidget):
    logout_requested = Signal()

    def __init__(self, container: AppContainer, app_state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._app_state = app_state
        self._screens: dict[str, QWidget] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._sidebar = Sidebar()
        self._sidebar.navigate.connect(self._on_navigate)
        self._sidebar.logout_requested.connect(self.logout_requested.emit)

        content_column = QVBoxLayout()
        content_column.setContentsMargins(0, 0, 0, 0)
        content_column.setSpacing(0)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(20, 12, 20, 0)
        top_bar.addStretch()
        top_bar.addWidget(NotificationsButton(container, app_state))
        content_column.addLayout(top_bar)

        self._content = QStackedWidget()
        content_column.addWidget(self._content)

        self._register("today", TodayScreen(container, app_state))
        self._register("register", WorkEntryScreen(container, app_state))
        self._register("calendar", CalendarScreen(container, app_state))
        self._register("history", HistoryScreen(container, app_state))
        self._register("hours_control", HoursControlScreen(container, app_state))
        self._register("bank_hours", BankHoursScreen(container, app_state))
        self._register("finance", FinanceScreen(container, app_state))
        self._register("reports", ReportsScreen(container, app_state))
        self._register("settings", SettingsScreen(container, app_state))

        profile_screen = ProfileScreen(container, app_state)
        profile_screen.navigate_settings.connect(lambda: self._on_navigate("settings"))
        profile_screen.logout_requested.connect(self.logout_requested.emit)
        self._register("profile", profile_screen)

        layout.addWidget(self._sidebar)
        layout.addLayout(content_column)

        self._on_navigate("today")

    def _register(self, key: str, widget: QWidget) -> None:
        self._screens[key] = widget
        self._content.addWidget(widget)

    def _on_navigate(self, key: str) -> None:
        self._sidebar.set_active(key)
        self._content.setCurrentWidget(self._screens[key])
