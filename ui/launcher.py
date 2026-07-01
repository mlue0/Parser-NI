"""Стартовое окно выбора режима работы приложения."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from logs.setup import get_logger

logger = get_logger(__name__)


class LauncherWindow(QWidget):
    """Окно выбора: «Добавить пластину» или «Разбраковать пластину»."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SimpleMeasure")
        self.resize(520, 320)
        self.setMinimumSize(420, 280)
        # Держим ссылку на открытое окно режима, чтобы оно не было удалено GC.
        self._child: QWidget | None = None
        self._build_ui()
        logger.info("Открыто окно выбора режима")

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)
        layout.addStretch()

        title = QLabel("SimpleMeasure")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel("Выберите режим работы")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 13px;")
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        buttons = QHBoxLayout()
        buttons.setSpacing(16)

        add_btn = QPushButton("➕ Добавить пластину")
        add_btn.setMinimumHeight(72)
        add_btn.setToolTip("Занести метаданные новой пластины в базу")
        add_btn.clicked.connect(self._open_add_plate)
        buttons.addWidget(add_btn)

        sort_btn = QPushButton("🧪 Разбраковать пластину")
        sort_btn.setMinimumHeight(72)
        sort_btn.setToolTip("Загрузить файл разбраковки и отправить данные (текущий режим)")
        sort_btn.clicked.connect(self._open_sort)
        buttons.addWidget(sort_btn)

        layout.addLayout(buttons)
        layout.addStretch()

    def _open_add_plate(self) -> None:
        from ui.add_plate_window import AddPlateWindow
        logger.info("Выбран режим: добавить пластину")
        self._child = AddPlateWindow()
        self._child.show()
        self.close()

    def _open_sort(self) -> None:
        from ui.main_window import MainWindow
        logger.info("Выбран режим: разбраковать пластину")
        self._child = MainWindow()
        self._child.show()
        self.close()
