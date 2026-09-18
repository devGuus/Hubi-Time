"""Estado da sessao do usuario logado, compartilhado entre as telas.

Nao e um cache de dados de negocio (isso e responsabilidade dos services) -
apenas identidade/preferencias correntes: quem esta logado e o tema ativo.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from config.constants import Theme
from models.user import AuthSession, Profile, UserSettings


class AppState(QObject):
    theme_changed = Signal(Theme)

    def __init__(self):
        super().__init__()
        self.session: AuthSession | None = None
        self.profile: Profile | None = None
        self.settings: UserSettings | None = None

    @property
    def user_id(self) -> str:
        if self.session is None:
            raise RuntimeError("Nenhuma sessao ativa.")
        return self.session.user_id

    @property
    def is_authenticated(self) -> bool:
        return self.session is not None

    def current_theme(self) -> Theme:
        if self.settings and self.settings.theme == Theme.DARK.value:
            return Theme.DARK
        return Theme.LIGHT

    def set_theme(self, theme: Theme) -> None:
        if self.settings:
            self.settings.theme = theme.value
        self.theme_changed.emit(theme)

    def clear(self) -> None:
        self.session = None
        self.profile = None
        self.settings = None
