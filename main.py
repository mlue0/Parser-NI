"""
SimpleMeasure — desktop-приложение для парсинга и загрузки данных разбраковки.

Запуск:
    python main.py

Сборка PyInstaller:
    pyinstaller SimpleMeasure.spec
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from config.settings import BASE_DIR, ENV_PATH

sys.path.insert(0, str(BASE_DIR))
from logs.setup import get_logger, setup_logging
from ui.launcher import LauncherWindow


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

    # Применяем тему согласно сохранённой настройке (light по умолчанию).
    # Единый источник правды — флаг dark_theme в app_state.json.
    from ui.theme import load_and_apply_theme
    load_and_apply_theme(app)

    # Стартовое окно выбора режима: «Добавить пластину» / «Разбраковать пластину».
    window = LauncherWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
