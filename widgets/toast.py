"""Toast/snackbar flutuante para feedback rapido (salvando, salvo, erro)."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QWidget

_COLORS = {
    "info": ("#2563EB", "#FFFFFF"),
    "success": ("#16A34A", "#FFFFFF"),
    "error": ("#DC2626", "#FFFFFF"),
    "warning": ("#D97706", "#FFFFFF"),
}


class Toast(QLabel):
    """Mensagem flutuante que aparece no canto inferior direito da janela pai
    e desaparece sozinha apos `duration_ms`."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.SubWindow)
        self.setVisible(False)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, message: str, kind: str = "info", duration_ms: int = 2500) -> None:
        bg, fg = _COLORS.get(kind, _COLORS["info"])
        self.setText(message)
        self.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 600;
            }}
            """
        )
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self._timer.start(duration_ms)

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        margin = 24
        x = parent.width() - self.width() - margin
        y = parent.height() - self.height() - margin
        self.move(max(x, margin), max(y, margin))
