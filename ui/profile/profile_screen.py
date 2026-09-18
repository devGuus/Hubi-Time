"""Tela 'Meu Perfil': dados pessoais, alteracao de senha e atalhos."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from app_container import AppContainer
from app_state import AppState
from utils.validators import passwords_match, validate_password
from widgets.cards import SectionCard
from widgets.dialogs import confirm, show_error, show_success
from widgets.loading_button import LoadingButton
from workers.async_worker import AsyncTaskRunner


class ProfileScreen(QWidget):
    navigate_settings = Signal()
    logout_requested = Signal()

    def __init__(self, container: AppContainer, app_state: AppState, parent: QWidget | None = None):
        super().__init__(parent)
        self._container = container
        self._app_state = app_state
        self._runner = AsyncTaskRunner(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Meu Perfil")
        title.setProperty("role", "title")

        personal_card = SectionCard("Dados pessoais")
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Nome"))
        self._name_input = QLineEdit()
        name_row.addWidget(self._name_input)
        self._save_name_button = LoadingButton("Salvar nome", variant="primary")
        self._save_name_button.clicked.connect(self._on_save_name)
        name_row.addWidget(self._save_name_button)
        personal_card.body().addLayout(name_row)

        email_row = QHBoxLayout()
        email_row.addWidget(QLabel("E-mail"))
        self._email_input = QLineEdit()
        self._email_input.setEnabled(False)
        email_row.addWidget(self._email_input)
        personal_card.body().addLayout(email_row)

        password_card = SectionCard("Alterar senha")
        self._new_password = QLineEdit()
        self._new_password.setPlaceholderText("Nova senha")
        self._new_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm_password = QLineEdit()
        self._confirm_password.setPlaceholderText("Confirmar nova senha")
        self._confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._change_password_button = LoadingButton("Alterar senha", variant="primary")
        self._change_password_button.clicked.connect(self._on_change_password)
        password_card.body().addWidget(self._new_password)
        password_card.body().addWidget(self._confirm_password)
        password_card.body().addWidget(self._change_password_button)

        shortcuts_card = SectionCard("Preferencias")
        shortcuts_row = QHBoxLayout()
        settings_button = LoadingButton(
            "Configuracoes de jornada, salario, tema e notificacoes", variant="ghost"
        )
        settings_button.clicked.connect(self.navigate_settings.emit)
        shortcuts_row.addWidget(settings_button)
        shortcuts_card.body().addLayout(shortcuts_row)

        logout_button = LoadingButton("Sair da conta", variant="danger")
        logout_button.clicked.connect(self._on_logout_clicked)

        layout.addWidget(title)
        layout.addWidget(personal_card)
        layout.addWidget(password_card)
        layout.addWidget(shortcuts_card)
        layout.addWidget(logout_button)
        layout.addStretch()

    def showEvent(self, event) -> None:  # noqa: N802 - metodo Qt
        super().showEvent(event)
        if self._app_state.session:
            self._email_input.setText(self._app_state.session.email)
        if self._app_state.profile:
            self._name_input.setText(self._app_state.profile.name)

    def _on_save_name(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            show_error(self, "Informe seu nome.")
            return
        self._save_name_button.set_loading(True)
        self._runner.run(
            self._container.user_repository.update_profile_name,
            self._app_state.user_id,
            name,
            on_success=self._on_name_saved,
            on_error=lambda msg: show_error(self, msg),
            on_finished=lambda: self._save_name_button.set_loading(False),
        )

    def _on_name_saved(self, profile) -> None:
        self._app_state.profile = profile
        show_success(self, "Nome atualizado com sucesso.")

    def _on_change_password(self) -> None:
        password = self._new_password.text()
        confirm_value = self._confirm_password.text()
        result = validate_password(password)
        if not result.is_valid:
            show_error(self, "\n".join(result.errors), title="Senha nao atende aos requisitos")
            return
        if not passwords_match(password, confirm_value):
            show_error(self, "As senhas informadas nao coincidem.")
            return

        self._change_password_button.set_loading(True)
        self._runner.run(
            self._container.auth_service.change_password,
            password,
            on_success=self._on_password_changed,
            on_error=lambda msg: show_error(self, msg),
            on_finished=lambda: self._change_password_button.set_loading(False),
        )

    def _on_password_changed(self, _result) -> None:
        self._new_password.clear()
        self._confirm_password.clear()
        show_success(self, "Senha alterada com sucesso.")

    def _on_logout_clicked(self) -> None:
        if confirm(self, "Deseja realmente sair da sua conta?", title="Sair"):
            self.logout_requested.emit()
