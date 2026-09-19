"""Tela de verificacao de e-mail por codigo OTP (pos-cadastro)."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from app_container import AppContainer
from config.constants import OTP_CODE_LENGTH
from models.user import AuthSession
from widgets.dialogs import show_error
from widgets.loading_button import LoadingButton
from widgets.otp_input import OtpInput
from workers.async_worker import AsyncTaskRunner

RESEND_COOLDOWN_SECONDS = 30


class VerifyEmailScreen(QWidget):
    verified = Signal(object)  # AuthSession
    go_login = Signal()
    change_email_requested = Signal()

    def __init__(self, container: AppContainer, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._runner = AsyncTaskRunner(self)
        self._email = ""
        self._cooldown_remaining = 0

        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.setInterval(1000)
        self._cooldown_timer.timeout.connect(self._tick_cooldown)

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setProperty("card", "true")
        card.setFixedWidth(420)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        title = QLabel("Verifique seu e-mail")
        title.setProperty("role", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._subtitle = QLabel("Enviamos um codigo de verificacao para o seu e-mail.")
        self._subtitle.setProperty("role", "subtitle")
        self._subtitle.setWordWrap(True)
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._otp = OtpInput(length=OTP_CODE_LENGTH)
        self._otp.completed.connect(lambda _code: self._on_verify_clicked())

        self._verify_button = LoadingButton("Verificar", variant="primary")
        self._verify_button.clicked.connect(self._on_verify_clicked)

        self._resend_button = QPushButton("Reenviar codigo")
        self._resend_button.setProperty("variant", "link")
        self._resend_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._resend_button.clicked.connect(self._on_resend_clicked)

        change_email_button = QPushButton("Alterar e-mail")
        change_email_button.setProperty("variant", "ghost")
        change_email_button.setCursor(Qt.CursorShape.PointingHandCursor)
        change_email_button.clicked.connect(self.change_email_requested.emit)

        back_button = QPushButton("Voltar para o login")
        back_button.setProperty("variant", "link")
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.clicked.connect(self.go_login.emit)

        layout.addWidget(title)
        layout.addWidget(self._subtitle)
        layout.addSpacing(6)
        layout.addWidget(self._otp, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(6)
        layout.addWidget(self._verify_button)
        layout.addWidget(self._resend_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(change_email_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        outer.addWidget(card)

    def set_email(self, email: str) -> None:
        self._email = email
        self._subtitle.setText(f"Enviamos um codigo de verificacao para {email}.")
        self._otp.clear()
        self._start_cooldown()

    def _on_verify_clicked(self) -> None:
        code = self._otp.value()
        if len(code) != OTP_CODE_LENGTH:
            show_error(self, f"Informe os {OTP_CODE_LENGTH} digitos do codigo recebido.")
            return

        self._verify_button.set_loading(True, "Verificando...")
        self._runner.run(
            self._container.auth_service.verify_signup_otp,
            self._email,
            code,
            on_success=self._on_verify_success,
            on_error=self._on_verify_error,
            on_finished=lambda: self._verify_button.set_loading(False),
        )

    def _on_verify_success(self, session: AuthSession) -> None:
        self.verified.emit(session)

    def _on_verify_error(self, message: str) -> None:
        self._otp.clear()
        show_error(self, message, title="Codigo invalido")

    def _on_resend_clicked(self) -> None:
        if self._cooldown_remaining > 0:
            return
        self._resend_button.setEnabled(False)
        self._runner.run(
            self._container.auth_service.resend_signup_otp,
            self._email,
            on_success=lambda _r: self._start_cooldown(),
            on_error=lambda msg: show_error(self, msg, title="Nao foi possivel reenviar"),
        )

    def _start_cooldown(self) -> None:
        self._cooldown_remaining = RESEND_COOLDOWN_SECONDS
        self._update_resend_label()
        self._cooldown_timer.start()

    def _tick_cooldown(self) -> None:
        self._cooldown_remaining -= 1
        if self._cooldown_remaining <= 0:
            self._cooldown_timer.stop()
            self._resend_button.setEnabled(True)
            self._resend_button.setText("Reenviar codigo")
        else:
            self._update_resend_label()

    def _update_resend_label(self) -> None:
        self._resend_button.setText(f"Reenviar codigo ({self._cooldown_remaining}s)")
