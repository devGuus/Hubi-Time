"""Campo de codigo OTP (6 digitos individuais, com avanco automatico)."""
from __future__ import annotations

from PySide6.QtCore import QEvent, QRegularExpression, Qt, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget


class OtpInput(QWidget):
    completed = Signal(str)

    def __init__(self, length: int = 6, parent: QWidget | None = None):
        super().__init__(parent)
        self._length = length
        self._boxes: list[QLineEdit] = []

        layout = QHBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        validator = QRegularExpressionValidator(QRegularExpression("[0-9]"))
        for i in range(length):
            box = QLineEdit()
            box.setMaxLength(1)
            box.setFixedSize(44, 52)
            box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            box.setValidator(validator)
            box.setStyleSheet("font-size: 20px; font-weight: 600;")
            box.textChanged.connect(lambda text, idx=i: self._on_text_changed(idx, text))
            box.installEventFilter(self)
            layout.addWidget(box)
            self._boxes.append(box)

    def _on_text_changed(self, idx: int, text: str) -> None:
        if text and idx + 1 < self._length:
            self._boxes[idx + 1].setFocus()
            self._boxes[idx + 1].selectAll()
        if self.is_complete():
            self.completed.emit(self.value())

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress and watched in self._boxes:
            idx = self._boxes.index(watched)
            if event.key() == Qt.Key.Key_Backspace and not watched.text() and idx > 0:
                self._boxes[idx - 1].setFocus()
                self._boxes[idx - 1].clear()
        return super().eventFilter(watched, event)

    def value(self) -> str:
        return "".join(box.text() for box in self._boxes)

    def is_complete(self) -> bool:
        return len(self.value()) == self._length

    def clear(self) -> None:
        for box in self._boxes:
            box.blockSignals(True)
            box.clear()
            box.blockSignals(False)
        self._boxes[0].setFocus()

    def focus_first(self) -> None:
        self._boxes[0].setFocus()
