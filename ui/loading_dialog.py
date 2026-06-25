"""Индикатор загрузки при отправке данных."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout


class LoadingDialog(QDialog):
    """Модальный диалог с прогресс-баром (неопределённый режим)."""

    def __init__(self, message: str = "Отправка данных...", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Подождите")
        self.setModal(True)
        self.setFixedSize(360, 120)
        self.setWindowFlags(
            self.windowFlags()
            & ~Qt.WindowType.WindowCloseButtonHint
            & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        layout = QVBoxLayout(self)
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        progress = QProgressBar()
        progress.setRange(0, 0)
        layout.addWidget(progress)
