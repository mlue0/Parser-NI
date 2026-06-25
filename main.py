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
from logs.setup import setup_logging, get_logger
from ui.main_window import MainWindow


def main() -> int:
    """Точка входа приложения."""
    setup_logging()
    logger = get_logger(__name__)

    if not ENV_PATH.exists():
        logger.warning(
            "Файл .env не найден (%s). Скопируйте .env.example в .env",
            ENV_PATH,
        )

    logger.info("Рабочая директория: %s", BASE_DIR)

    app = QApplication(sys.argv)
    app.setApplicationName("SimpleMeasure")
    app.setOrganizationName("SimpleMeasure")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
