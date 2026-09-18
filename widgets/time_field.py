"""Campo de horario com botao 'Agora', suportando valor vazio (NULL)."""
from __future__ import annotations

from datetime import datetime, time

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


class TimeEntryField(QWidget):
    """Composto por rotulo + campo HH:MM + botoes 'Agora' e 'Limpar'.

    Nenhum dos quatro horarios da jornada e obrigatorio: o campo vazio
    representa NULL de forma explicita (nao "00:00").
    """

    valueChanged = Signal()

    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._label = QLabel(label)
        self._label.setProperty("role", "stat-label")

        row = QHBoxLayout()
        row.setSpacing(8)

        self._edit = QLineEdit()
        self._edit.setInputMask("99:99;_")
        self._edit.setPlaceholderText("--:--")
        self._edit.setFixedWidth(90)
        self._edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._edit.editingFinished.connect(self._on_edit_finished)

        self._now_button = QPushButton("Agora")
        self._now_button.setProperty("variant", "ghost")
        self._now_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._now_button.clicked.connect(self._set_now)

        self._clear_button = QPushButton("Limpar")
        self._clear_button.setProperty("variant", "ghost")
        self._clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_button.clicked.connect(self.clear)

        row.addWidget(self._edit)
        row.addWidget(self._now_button)
        row.addWidget(self._clear_button)
        row.addStretch()

        layout.addWidget(self._label)
        layout.addLayout(row)

    def value(self) -> time | None:
        raw = self._edit.text()
        digits_only = raw.replace(":", "").replace("_", "")
        if len(digits_only) < 4:
            return None
        hh, mm = raw[0:2], raw[3:5]
        if "_" in hh or "_" in mm:
            return None
        try:
            return time(hour=int(hh), minute=int(mm))
        except ValueError:
            return None

    def set_value(self, value: time | None) -> None:
        self._edit.blockSignals(True)
        if value is None:
            self._edit.clear()
        else:
            self._edit.setText(value.strftime("%H:%M"))
        self._edit.blockSignals(False)
        self.set_error(False)

    def clear(self) -> None:
        self._edit.clear()
        self.set_error(False)
        self.valueChanged.emit()

    def set_enabled_editing(self, enabled: bool) -> None:
        self._edit.setEnabled(enabled)
        self._now_button.setEnabled(enabled)
        self._clear_button.setEnabled(enabled)

    def set_error(self, has_error: bool) -> None:
        self._edit.setStyleSheet("border: 1px solid #DC2626;" if has_error else "")

    def _set_now(self) -> None:
        now = datetime.now().time().replace(second=0, microsecond=0)
        self.set_value(now)
        self.valueChanged.emit()

    def _on_edit_finished(self) -> None:
        raw = self._edit.text()
        digits_only = raw.replace(":", "").replace("_", "")
        if len(digits_only) == 0:
            self.set_error(False)
            self.valueChanged.emit()
            return
        if len(digits_only) < 4 or self.value() is None:
            self.set_error(True)
            return
        self.set_error(False)
        self.valueChanged.emit()
