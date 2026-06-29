"""
SimpleMeasure — desktop-приложение для парсинга и загрузки данных разбраковки.

Запуск:
    python main.py

Сборка PyInstaller:
    pyinstaller crystal_uploader.spec
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from config.settings import BASE_DIR, ENV_PATH
sys.path.insert(0, str(BASE_DIR))
from logs.setup import setup_logging, get_logger
from ui.main_window import MainWindow

DARK_STYLE = """
QWidget {
    background-color: #050608;
    color: #e7edf5;
    font-family: "Segoe UI", "Roboto", Arial, sans-serif;
    font-size: 13px;
}
QMainWindow {
    background-color: #040507;
}
QStatusBar {
    background-color: #060708;
    color: #8ca2b8;
    border-top: 1px solid rgba(255,255,255,0.06);
}
QLabel {
    color: #e5e9f2;
}
QPushButton {
    background-color: #0e1720;
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 10px;
    color: #eaf6ff;
    padding: 8px 14px;
    min-height: 36px;
}
QPushButton:hover {
    background-color: #13202a;
}
QPushButton:pressed {
    background-color: #0b1419;
}
QLineEdit, QComboBox, QPlainTextEdit, QSpinBox {
    background-color: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    color: #e7eef8;
    border-radius: 8px;
    padding: 8px;
}
QLineEdit:hover, QComboBox:hover, QPlainTextEdit:hover, QSpinBox:hover {
    border: 1px solid rgba(255,255,255,0.10);
}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QSpinBox:focus {
    border: 1px solid rgba(100, 180, 255, 0.9);
    background-color: rgba(20, 35, 50, 0.6);
}
QPlainTextEdit {
    padding: 10px;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid rgba(255,255,255,0.04);
}
QComboBox::down-arrow {
    width: 0;
    height: 0;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 8px solid #8ddcff;
}
QTabWidget::pane {
    background-color: transparent;
    border: none;
}
QTabBar::tab {
    background-color: transparent;
    color: #c8d6e8;
    padding: 8px 12px;
    border-radius: 6px;
    min-width: 100px;
    margin: 2px;
}
QTabBar::tab:selected {
    background-color: rgba(15, 103, 201, 0.12);
    color: #eff8ff;
}
QTabBar::tab:hover {
    background-color: rgba(255,255,255,0.02);
}
QScrollArea {
    background: transparent;
    border: none;
}
QMessageBox {
    background-color: #0b0d11;
    color: #f4f7ff;
}
"""


def main() -> int:
    """Точка входа приложения."""
    from config.settings import get_settings
    settings = get_settings()
    setup_logging(log_level=settings.log_level)
    logger = get_logger(__name__)

    if not ENV_PATH.exists():
        logger.warning(
            "Файл .env не найден (%s). Скопируйте .env.example в .env",
            ENV_PATH,
        )

    logger.info("Рабочая директория: %s", BASE_DIR)
    logger.info("Уровень логирования: %s", settings.log_level)

    app = QApplication(sys.argv)
    app.setApplicationName("SimpleMeasure")
    app.setOrganizationName("SimpleMeasure")

    # Базовый стиль — всегда применяем как основу
    app.setStyleSheet(DARK_STYLE)

    # Поверх базового — применяем тему из настроек пользователя
    from config.settings import _load_state
    if _load_state().get("dark_theme", False):
        from ui.theme import apply_dark_theme
        apply_dark_theme(app)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
