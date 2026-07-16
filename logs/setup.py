"""Инициализация системы логирования."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler


def setup_logging(log_level: str = "INFO") -> None:
    """Настраивает консольный и файловый лог с ротацией.
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    from config.settings import LOGS_DIR
    
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "app.log"

    root = logging.getLogger()
    if root.handlers:
        return

    # Преобразуем строку в уровень
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root.setLevel(logging.DEBUG)  # Root всегда DEBUG, фильтруем на handlers

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Файловый handler с ротацией: 5 MB × 5 файлов = 25 MB
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)  # В файл пишем всё
    file_handler.setFormatter(formatter)

    # Консольный handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)  # Настраиваемый уровень
    console_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Снижаем шумность внешних библиотек
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    logging.info("Logging initialized (level=%s, file=%s)", log_level, log_file)


def get_logger(name: str) -> logging.Logger:
    """Возвращает именованный логгер."""
    return logging.getLogger(name)
