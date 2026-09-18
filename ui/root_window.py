"""Janela raiz: orquestra o fluxo de autenticacao e a troca para o shell
principal apos login bem-sucedido. E o unico QMainWindow da aplicacao -
todas as telas trocam dentro de um QStackedWidget central, evitando
flicker de multiplas janelas top-level.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from app_container import AppContainer
from app_state import AppState
from config.constants import Theme
from models.user import AuthSession
from ui.forgot_password.forgot_password_screen import ForgotPasswordScreen
from ui.login.login_screen import LoginScreen
from ui.main_window.main_shell import MainShell
from ui.register.register_screen import RegisterScreen
from ui.verify_email.verify_email_screen import VerifyEmailScreen
from widgets.charts import configure_pyqtgraph_theme
from widgets.dialogs import show_error
from widgets.theme import apply_theme
from workers.async_worker import AsyncTaskRunner


class RootWindow(QMainWindow):
    def __init__(self, container: AppContainer, app_state: AppState):
        super().__init__()
        self._container = container
        self._app_state = app_state
        self._runner = AsyncTaskRunner(self)
        self._main_shell: MainShell | None = None
        self._app_state.theme_changed.connect(self._on_theme_changed)

        self.setWindowTitle("Hubi Time")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._loading_screen = self._build_loading_screen()
        self._login_screen = LoginScreen(container)
        self._register_screen = RegisterScreen(container)
        self._verify_screen = VerifyEmailScreen(container)
        self._forgot_screen = ForgotPasswordScreen(container)

        for widget in (
            self._loading_screen, self._login_screen, self._register_screen,
            self._verify_screen, self._forgot_screen,
        ):
            self._stack.addWidget(widget)

        self._login_screen.login_succeeded.connect(self._on_authenticated)
        self._login_screen.go_register.connect(lambda: self._stack.setCurrentWidget(self._register_screen))
        self._login_screen.go_forgot_password.connect(lambda: self._stack.setCurrentWidget(self._forgot_screen))

        self._register_screen.registered.connect(self._on_registered)
        self._register_screen.go_login.connect(lambda: self._stack.setCurrentWidget(self._login_screen))

        self._verify_screen.verified.connect(self._on_authenticated)
        self._verify_screen.go_login.connect(lambda: self._stack.setCurrentWidget(self._login_screen))
        self._verify_screen.change_email_requested.connect(
            lambda: self._stack.setCurrentWidget(self._register_screen)
        )

        self._forgot_screen.go_login.connect(lambda: self._stack.setCurrentWidget(self._login_screen))

        self._stack.setCurrentWidget(self._loading_screen)
        self._try_restore_session()

    @staticmethod
    def _build_loading_screen() -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel("Carregando...")
        label.setProperty("role", "subtitle")
        layout.addWidget(label)
        return widget

    # ------------------------------------------------------------------
    def _try_restore_session(self) -> None:
        self._runner.run(
            self._container.auth_service.restore_session,
            on_success=self._on_restore_result,
            on_error=lambda _msg: self._stack.setCurrentWidget(self._login_screen),
        )

    def _on_restore_result(self, session: AuthSession | None) -> None:
        if session is None:
            self._stack.setCurrentWidget(self._login_screen)
            return
        self._on_authenticated(session)

    def _on_registered(self, email: str) -> None:
        self._verify_screen.set_email(email)
        self._stack.setCurrentWidget(self._verify_screen)

    # ------------------------------------------------------------------
    def _on_authenticated(self, session: AuthSession) -> None:
        self._app_state.session = session
        self._stack.setCurrentWidget(self._loading_screen)
        self._runner.run(
            self._container.user_repository.get_profile,
            self._app_state.user_id,
            on_success=self._on_profile_loaded,
            on_error=self._on_bootstrap_error,
        )

    def _on_profile_loaded(self, profile) -> None:
        self._app_state.profile = profile
        self._runner.run(
            self._container.user_repository.get_settings,
            self._app_state.user_id,
            on_success=self._on_settings_loaded,
            on_error=self._on_bootstrap_error,
        )

    def _on_settings_loaded(self, settings) -> None:
        self._app_state.settings = settings
        theme = self._app_state.current_theme()
        apply_theme(QApplication.instance(), theme)
        # Widgets de grafico (PyQtGraph) leem a cor de fundo/texto no momento
        # em que sao criados: configuramos o tema aqui, antes do MainShell
        # (e seus graficos) serem construidos pela primeira vez nesta sessao.
        configure_pyqtgraph_theme(theme)
        self._ensure_main_shell()
        self._stack.setCurrentWidget(self._main_shell)

    def _on_bootstrap_error(self, message: str) -> None:
        show_error(self, message, title="Nao foi possivel carregar seus dados")
        self._container.auth_service.sign_out()
        self._app_state.clear()
        self._stack.setCurrentWidget(self._login_screen)

    def _on_theme_changed(self, theme: Theme) -> None:
        # Reaplica o stylesheet Qt imediatamente em toda a aplicacao. Os
        # graficos PyQtGraph ja renderizados mantem as cores de quando foram
        # criados (limitacao documentada no README) ate a tela ser reaberta.
        apply_theme(QApplication.instance(), theme)

    def _ensure_main_shell(self) -> None:
        if self._main_shell is not None:
            return
        self._main_shell = MainShell(self._container, self._app_state)
        self._main_shell.logout_requested.connect(self._on_logout_requested)
        self._stack.addWidget(self._main_shell)

    # ------------------------------------------------------------------
    def _on_logout_requested(self) -> None:
        self._runner.run(self._container.auth_service.sign_out, on_finished=self._after_logout)

    def _after_logout(self) -> None:
        self._app_state.clear()
        if self._main_shell is not None:
            self._stack.removeWidget(self._main_shell)
            self._main_shell.deleteLater()
            self._main_shell = None
        apply_theme(QApplication.instance(), Theme.LIGHT)
        last_email = self._container.auth_service.last_remembered_email()
        if last_email:
            self._login_screen.prefill_email(last_email)
        self._stack.setCurrentWidget(self._login_screen)

    def closeEvent(self, event) -> None:  # noqa: N802 - metodo Qt
        self._runner.shutdown()
        super().closeEvent(event)
