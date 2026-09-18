"""Tela de login."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from app_container import AppContainer
from models.user import AuthSession
from utils.validators import is_valid_email
from widgets.dialogs import show_error
from widgets.loading_button import LoadingButton
from workers.async_worker import AsyncTaskRunner


class LoginScreen(QWidget):
    login_succeeded = Signal(object)  # AuthSession
    go_register = Signal()
    go_forgot_password = Signal()

    def __init__(self, container: AppContainer, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._runner = AsyncTaskRunner(self)

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setProperty("card", "true")
        card.setFixedWidth(380)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(12)

        title = QLabel("Bem-vindo de volta")
        title.setProperty("role", "title")
        subtitle = QLabel("Entre para continuar controlando sua jornada.")
        subtitle.setProperty("role", "subtitle")
        subtitle.setWordWrap(True)

        self._email = QLineEdit()
        self._email.setPlaceholderText("seu.email@empresa.com")

        password_row = QHBoxLayout()
        self._password = QLineEdit()
        self._password.setPlaceholderText("Senha")
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._toggle_password = QPushButton("Mostrar")
        self._toggle_password.setProperty("variant", "ghost")
        self._toggle_password.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_password.clicked.connect(self._toggle_password_visibility)
        password_row.addWidget(self._password)
        password_row.addWidget(self._toggle_password)

        self._keep_signed_in = QCheckBox("Manter-me conectado")

        self._login_button = LoadingButton("Entrar", variant="primary")
        self._login_button.clicked.connect(self._on_login_clicked)
        self._email.returnPressed.connect(self._on_login_clicked)
        self._password.returnPressed.connect(self._on_login_clicked)

        links_row = QHBoxLayout()
        register_link = QPushButton("Criar conta")
        register_link.setProperty("variant", "link")
        register_link.setCursor(Qt.CursorShape.PointingHandCursor)
        register_link.clicked.connect(self.go_register.emit)

        forgot_link = QPushButton("Esqueci minha senha")
        forgot_link.setProperty("variant", "link")
        forgot_link.setCursor(Qt.CursorShape.PointingHandCursor)
        forgot_link.clicked.connect(self.go_forgot_password.emit)

        links_row.addWidget(register_link)
        links_row.addStretch()
        links_row.addWidget(forgot_link)

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(8)
        card_layout.addWidget(QLabel("E-mail"))
        card_layout.addWidget(self._email)
        card_layout.addWidget(QLabel("Senha"))
        card_layout.addLayout(password_row)
        card_layout.addWidget(self._keep_signed_in)
        card_layout.addSpacing(6)
        card_layout.addWidget(self._login_button)
        card_layout.addLayout(links_row)

        outer.addWidget(card)

        last_email = self._container.auth_service.last_remembered_email()
        if last_email:
            self._email.setText(last_email)
            self._keep_signed_in.setChecked(True)

    def _toggle_password_visibility(self) -> None:
        if self._password.echoMode() == QLineEdit.EchoMode.Password:
            self._password.setEchoMode(QLineEdit.EchoMode.Normal)
            self._toggle_password.setText("Ocultar")
        else:
            self._password.setEchoMode(QLineEdit.EchoMode.Password)
            self._toggle_password.setText("Mostrar")

    def _on_login_clicked(self) -> None:
        email = self._email.text().strip()
        password = self._password.text()

        if not is_valid_email(email):
            show_error(self, "Informe um e-mail valido.")
            return
        if not password:
            show_error(self, "Informe sua senha.")
            return

        self._login_button.set_loading(True, "Entrando...")
        self._runner.run(
            self._container.auth_service.sign_in,
            email,
            password,
            self._keep_signed_in.isChecked(),
            on_success=self._on_login_success,
            on_error=self._on_login_error,
            on_finished=lambda: self._login_button.set_loading(False),
        )

    def _on_login_success(self, session: AuthSession) -> None:
        self._password.clear()
        self.login_succeeded.emit(session)

    def _on_login_error(self, message: str) -> None:
        show_error(self, message, title="Nao foi possivel entrar")

    def prefill_email(self, email: str) -> None:
        self._email.setText(email)
