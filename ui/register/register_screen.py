"""Tela de cadastro de usuario."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from app_container import AppContainer
from utils.validators import is_valid_email, passwords_match, validate_password
from widgets.dialogs import show_error
from widgets.loading_button import LoadingButton
from workers.async_worker import AsyncTaskRunner


class RegisterScreen(QWidget):
    registered = Signal(str)  # email
    go_login = Signal()

    def __init__(self, container: AppContainer, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._runner = AsyncTaskRunner(self)

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setProperty("card", "true")
        card.setFixedWidth(400)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(10)

        title = QLabel("Criar conta")
        title.setProperty("role", "title")
        subtitle = QLabel("Leva menos de um minuto.")
        subtitle.setProperty("role", "subtitle")

        self._name = QLineEdit()
        self._name.setPlaceholderText("Seu nome completo")
        self._email = QLineEdit()
        self._email.setPlaceholderText("seu.email@empresa.com")
        self._password = QLineEdit()
        self._password.setPlaceholderText("Senha (minimo 8 caracteres)")
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm_password = QLineEdit()
        self._confirm_password.setPlaceholderText("Confirmar senha")
        self._confirm_password.setEchoMode(QLineEdit.EchoMode.Password)

        self._submit_button = LoadingButton("Criar conta", variant="primary")
        self._submit_button.clicked.connect(self._on_submit)

        back_button = QPushButton("Ja tenho conta - Entrar")
        back_button.setProperty("variant", "link")
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.clicked.connect(self.go_login.emit)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Nome"))
        layout.addWidget(self._name)
        layout.addWidget(QLabel("E-mail"))
        layout.addWidget(self._email)
        layout.addWidget(QLabel("Senha"))
        layout.addWidget(self._password)
        layout.addWidget(QLabel("Confirmar senha"))
        layout.addWidget(self._confirm_password)
        layout.addSpacing(6)
        layout.addWidget(self._submit_button)
        layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignCenter)

        outer.addWidget(card)

    def _on_submit(self) -> None:
        name = self._name.text().strip()
        email = self._email.text().strip()
        password = self._password.text()
        confirm = self._confirm_password.text()

        if not name:
            show_error(self, "Informe seu nome.")
            return
        if not is_valid_email(email):
            show_error(self, "Informe um e-mail valido.")
            return
        password_result = validate_password(password)
        if not password_result.is_valid:
            show_error(self, "\n".join(password_result.errors), title="Senha nao atende aos requisitos")
            return
        if not passwords_match(password, confirm):
            show_error(self, "As senhas informadas nao coincidem.")
            return

        self._submit_button.set_loading(True, "Criando conta...")
        self._runner.run(
            self._container.auth_service.sign_up,
            name,
            email,
            password,
            on_success=lambda _result: self._on_success(email),
            on_error=lambda msg: show_error(self, msg, title="Nao foi possivel criar a conta"),
            on_finished=lambda: self._submit_button.set_loading(False),
        )

    def _on_success(self, email: str) -> None:
        self._password.clear()
        self._confirm_password.clear()
        self.registered.emit(email)
