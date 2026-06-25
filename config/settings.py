"""Загрузка настроек из .env и локального состояния приложения."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
import os


def get_base_dir() -> Path:
    """Корневая директория проекта (учитывает сборку PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
ENV_PATH = BASE_DIR / ".env"
STATE_PATH = BASE_DIR / "config" / "app_state.json"
LOGS_DIR = BASE_DIR / "logs"


@dataclass(frozen=True)
class Settings:
    """Параметры подключения к API."""

    api_url: str
    api_login: str
    api_password: str
    api_token: str

    @property
    def has_static_token(self) -> bool:
        return bool(self.api_token.strip())

    @property
    def is_configured(self) -> bool:
        if not self.api_url.strip():
            return False
        return self.has_static_token or (
            bool(self.api_login.strip()) and bool(self.api_password.strip())
        )


def load_last_file_path() -> str | None:
    """Возвращает путь к последнему открытому файлу."""
    if not STATE_PATH.exists():
        return None
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        path = data.get("last_file")
        if path and Path(path).exists():
            return path
    except (json.JSONDecodeError, OSError):
        pass
    return None


def save_last_file_path(file_path: str) -> None:
    """Сохраняет путь к последнему открытому файлу."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps({"last_file": file_path}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Загружает настройки из .env (кэшируется на время работы приложения)."""
    load_dotenv(ENV_PATH)
    return Settings(
        api_url=os.getenv("API_URL", "").strip(),
        api_login=os.getenv("API_LOGIN", "").strip(),
        api_password=os.getenv("API_PASSWORD", "").strip(),
        api_token=os.getenv("API_TOKEN", "").strip(),
    )
