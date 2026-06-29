"""Загрузка настроек из .env и локального состояния приложения."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

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

HISTORY_MAX = 50  # Максимальное число записей в истории


@dataclass(frozen=True)
class Settings:
    """Параметры подключения к API."""

    api_url: str
    api_login: str
    api_password: str
    api_token: str
    log_level: str = "INFO"

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


# ──────────────────────────────────────────────────────────────
# Вспомогательные функции для чтения/записи app_state.json
# ──────────────────────────────────────────────────────────────

def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ──────────────────────────────────────────────────────────────
# Последний открытый файл
# ──────────────────────────────────────────────────────────────

def load_last_file_path() -> str | None:
    """Возвращает путь к последнему открытому файлу."""
    state = _load_state()
    path = state.get("last_file")
    if path and Path(path).exists():
        return path
    return None


def save_last_file_path(file_path: str) -> None:
    """Сохраняет путь к последнему открытому файлу."""
    state = _load_state()
    state["last_file"] = file_path
    _save_state(state)


# ──────────────────────────────────────────────────────────────
# История загрузок
# ──────────────────────────────────────────────────────────────

def load_upload_history() -> list[dict[str, Any]]:
    """Возвращает историю загрузок (новые — первые)."""
    return _load_state().get("history", [])


def save_upload_entry(
    file_path: str,
    plate_marking: str,
    status: str,        # "ok" | "error"
    message: str,
) -> None:
    """Добавляет запись в историю загрузок."""
    state = _load_state()
    history: list[dict[str, Any]] = state.get("history", [])
    history.insert(0, {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file": file_path,
        "plate_marking": plate_marking,
        "status": status,
        "message": message,
    })
    state["history"] = history[:HISTORY_MAX]
    _save_state(state)


def clear_upload_history() -> None:
    """Очищает историю загрузок."""
    state = _load_state()
    state["history"] = []
    _save_state(state)


# ──────────────────────────────────────────────────────────────
# Шаблон (предзаполненные значения)
# ──────────────────────────────────────────────────────────────

def load_template() -> dict[str, Any]:
    """Возвращает сохранённый шаблон редактируемых полей."""
    return _load_state().get("template", {})


def save_template(values: dict[str, Any]) -> None:
    """Сохраняет значения редактируемых полей как шаблон."""
    state = _load_state()
    state["template"] = values
    _save_state(state)


# ──────────────────────────────────────────────────────────────
# Черновик (автосохранение незавершённой формы)
# ──────────────────────────────────────────────────────────────

def load_draft(file_path: str) -> dict[str, Any] | None:
    """Возвращает черновик для конкретного файла, если он есть."""
    drafts: dict[str, Any] = _load_state().get("drafts", {})
    entry = drafts.get(file_path)
    return entry.get("values") if entry and isinstance(entry, dict) else None


def save_draft(file_path: str, values: dict[str, Any]) -> None:
    """Сохраняет черновик формы для файла."""
    state = _load_state()
    drafts: dict[str, Any] = state.get("drafts", {})
    drafts[file_path] = {
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "values": values,
    }
    if len(drafts) > 20:
        del drafts[next(iter(drafts))]
    state["drafts"] = drafts
    _save_state(state)


def clear_draft(file_path: str) -> None:
    """Удаляет черновик для файла (после успешной отправки)."""
    state = _load_state()
    drafts: dict[str, Any] = state.get("drafts", {})
    drafts.pop(file_path, None)
    state["drafts"] = drafts
    _save_state(state)


# ──────────────────────────────────────────────────────────────
# Горячие клавиши
# ──────────────────────────────────────────────────────────────

DEFAULT_HOTKEYS: dict[str, str] = {
    "open_file": "Ctrl+O",
    "open_batch": "Ctrl+Shift+O",
    "submit": "Ctrl+Return",
    "api_settings": "Ctrl+,",
    "history": "Ctrl+H",
    "log": "Ctrl+L",
    "fields_editor": "Ctrl+E",
}


def load_hotkeys() -> dict[str, str]:
    """Возвращает словарь {action: shortcut}."""
    saved = _load_state().get("hotkeys", {})
    return {**DEFAULT_HOTKEYS, **saved}


def save_hotkeys(hotkeys: dict[str, str]) -> None:
    state = _load_state()
    state["hotkeys"] = hotkeys
    _save_state(state)


# ──────────────────────────────────────────────────────────────
# Тип пластины (принудительный выбор / авто-определение)
# ──────────────────────────────────────────────────────────────

# Допустимые значения: None (авто), "digital", "analog"
def load_plate_type_override() -> str | None:
    """Возвращает принудительный тип пластины или None для авто-определения."""
    return _load_state().get("plate_type_override") or None


def save_plate_type_override(value: str | None) -> None:
    """Сохраняет принудительный тип пластины (None = авто)."""
    state = _load_state()
    state["plate_type_override"] = value
    _save_state(state)


# ──────────────────────────────────────────────────────────────
# Настройки API
# ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Загружает настройки из .env с приоритетом keyring (кэшируется)."""
    load_dotenv(ENV_PATH)

    from config.credentials import get_login, get_password, get_token

    env_login = os.getenv("API_LOGIN", "").strip()
    env_password = os.getenv("API_PASSWORD", "").strip()
    env_token = os.getenv("API_TOKEN", "").strip()

    keyring_login = get_login()
    keyring_password = get_password()
    keyring_token = get_token()

    return Settings(
        api_url=os.getenv("API_URL", "").strip(),
        api_login=keyring_login or env_login,
        api_password=keyring_password or env_password,
        api_token=keyring_token or env_token,
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
    )


def reset_settings_cache() -> None:
    """Сбрасывает кэш настроек — при следующем вызове они перечитаются."""
    get_settings.cache_clear()
