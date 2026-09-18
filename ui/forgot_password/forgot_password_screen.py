"""Fluxo de recuperacao de senha: e-mail -> codigo + nova senha -> concluido."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from app_container import AppContainer
from utils.validators import is_valid_email, passwords_match, validate_password
from widgets.dialogs import show_error, show_success
from widgets.loading_button import LoadingButton
from widgets.otp_input import OtpInput
from workers.async_worker import AsyncTaskRunner


class ForgotPasswordScreen(QWidget):
    go_login = Signal()

    def __init__(self, container: AppContainer, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._runner = AsyncTaskRunner(self)
        self._email = ""

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._card = QFrame()
        self._card.setProperty("card", "true")
        self._card.setFixedWidth(420)
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(36, 36, 36, 36)

        self._stack = QStackedWidget()
        card_layout.addWidget(self._stack)

        self._stack.addWidget(self._build_request_step())
        self._stack.addWidget(self._build_confirm_step())

        outer.addWidget(self._card)

    # ------------------------------------------------------------------
    # Passo 1: informar e-mail
    # ------------------------------------------------------------------
    def _build_request_step(self) -> QWidget:
        step = QWidget()
        layout = QVBoxLayout(step)
        layout.setSpacing(12)

        title = QLabel("Recuperar senha")
        title.setProperty("role", "title")
        subtitle = QLabel("Informe seu e-mail para receber um codigo de recuperacao.")
        subtitle.setProperty("role", "subtitle")
        subtitle.setWordWrap(True)

        self._request_email = QLineEdit()
        self._request_email.setPlaceholderText("seu.email@empresa.com")

        self._request_button = LoadingButton("Enviar codigo", variant="primary")
        self._request_button.clicked.connect(self._on_request_clicked)

        back_button = QPushButton("Voltar para o login")
        back_button.setProperty("variant", "link")
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.clicked.connect(self.go_login.emit)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addWidget(QLabel("E-mail"))
        layout.addWidget(self._request_email)
        layout.addSpacing(6)
        layout.addWidget(self._request_button)
        layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignCenter)
        return step

    def _on_request_clicked(self) -> None:
        email = self._request_email.text().strip()
        if not is_valid_email(email):
            show_error(self, "Informe um e-mail valido.")
            return

        self._request_button.set_loading(True, "Enviando...")
        self._runner.run(
            self._container.auth_service.request_password_reset,
            email,
            on_success=lambda _r: self._go_to_confirm_step(email),
            on_error=lambda msg: show_error(self, msg, title="Nao foi possivel enviar o codigo"),
            on_finished=lambda: self._request_button.set_loading(False),
        )

    def _go_to_confirm_step(self, email: str) -> None:
        self._email = email
        self._confirm_subtitle.setText(f"Enviamos um codigo para {email}. Informe-o abaixo com a nova senha.")
        self._otp.clear()
        self._new_password.clear()
        self._confirm_password.clear()
        self._stack.setCurrentIndex(1)

    # ------------------------------------------------------------------
    # Passo 2: codigo + nova senha
    # ------------------------------------------------------------------
    def _build_confirm_step(self) -> QWidget:
        step = QWidget()
        layout = QVBoxLayout(step)
        layout.setSpacing(12)

        title = QLabel("Digite o codigo e a nova senha")
        title.setProperty("role", "title")
        title.setWordWrap(True)

        self._confirm_subtitle = QLabel("")
        self._confirm_subtitle.setProperty("role", "subtitle")
        self._confirm_subtitle.setWordWrap(True)

        self._otp = OtpInput(length=6)

        self._new_password = QLineEdit()
        self._new_password.setPlaceholderText("Nova senha")
        self._new_password.setEchoMode(QLineEdit.EchoMode.Password)

        self._confirm_password = QLineEdit()
        self._confirm_password.setPlaceholderText("Confirmar nova senha")
        self._confirm_password.setEchoMode(QLineEdit.EchoMode.Password)

        self._confirm_button = LoadingButton("Redefinir senha", variant="primary")
        self._confirm_button.clicked.connect(self._on_confirm_clicked)

        back_button = QPushButton("Voltar")
        back_button.setProperty("variant", "link")
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.clicked.connect(lambda: self._stack.setCurrentIndex(0))

        layout.addWidget(title)
        layout.addWidget(self._confirm_subtitle)
        layout.addSpacing(6)
        layout.addWidget(self._otp, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(6)
        layout.addWidget(QLabel("Nova senha"))
        layout.addWidget(self._new_password)
        layout.addWidget(QLabel("Confirmar nova senha"))
        layout.addWidget(self._confirm_password)
        layout.addSpacing(6)
        layout.addWidget(self._confirm_button)
        layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignCenter)
        return step

    def _on_confirm_clicked(self) -> None:
        code = self._otp.value()
        password = self._new_password.text()
        confirm = self._confirm_password.text()

        if len(code) != 6:
            show_error(self, "Informe os 6 digitos do codigo recebido.")
            return
        password_result = validate_password(password)
        if not password_result.is_valid:
            show_error(self, "\n".join(password_result.errors), title="Senha nao atende aos requisitos")
            return
        if not passwords_match(password, confirm):
            show_error(self, "As senhas informadas nao coincidem.")
            return

        self._confirm_button.set_loading(True, "Redefinindo...")
        self._runner.run(
            self._container.auth_service.confirm_password_reset,
            self._email,
            code,
            password,
            on_success=lambda _r: self._on_reset_success(),
            on_error=lambda msg: show_error(self, msg, title="Nao foi possivel redefinir a senha"),
            on_finished=lambda: self._confirm_button.set_loading(False),
        )

    def _on_reset_success(self) -> None:
        show_success(self, "Senha redefinida com sucesso. Entre com sua nova senha.")
        self._stack.setCurrentIndex(0)
        self.go_login.emit()

    def reset_to_start(self) -> None:
        self._stack.setCurrentIndex(0)
        self._request_email.clear()
