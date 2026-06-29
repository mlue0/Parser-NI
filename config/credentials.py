"""Безопасное хранение credentials через keyring."""

from __future__ import annotations

import keyring
from logs.setup import get_logger

logger = get_logger(__name__)

SERVICE_NAME = "SimpleMeasure"
USERNAME_KEY = "api_login"
PASSWORD_KEY = "api_password"
TOKEN_KEY = "api_token"


def save_credentials(login: str, password: str) -> None:
    """Сохраняет учётные данные в системное хранилище."""
    try:
        keyring.set_password(SERVICE_NAME, USERNAME_KEY, login)
        keyring.set_password(SERVICE_NAME, PASSWORD_KEY, password)
        logger.info("Учётные данные сохранены в системное хранилище")
    except Exception as exc:
        logger.warning("Не удалось сохранить credentials в keyring: %s", exc)
        raise


def get_login() -> str | None:
    """Получает логин из системного хранилища."""
    try:
        return keyring.get_password(SERVICE_NAME, USERNAME_KEY)
    except Exception as exc:
        logger.warning("Не удалось получить login из keyring: %s", exc)
        return None


def get_password() -> str | None:
    """Получает пароль из системного хранилища."""
    try:
        return keyring.get_password(SERVICE_NAME, PASSWORD_KEY)
    except Exception as exc:
        logger.warning("Не удалось получить password из keyring: %s", exc)
        return None


def save_token(token: str) -> None:
    """Сохраняет API токен в системное хранилище."""
    try:
        keyring.set_password(SERVICE_NAME, TOKEN_KEY, token)
        logger.info("API токен сохранён в системное хранилище")
    except Exception as exc:
        logger.warning("Не удалось сохранить токен в keyring: %s", exc)
        raise


def get_token() -> str | None:
    """Получает API токен из системного хранилища."""
    try:
        return keyring.get_password(SERVICE_NAME, TOKEN_KEY)
    except Exception as exc:
        logger.warning("Не удалось получить токен из keyring: %s", exc)
        return None


def clear_credentials() -> None:
    """Удаляет все сохранённые учётные данные."""
    try:
        keyring.delete_password(SERVICE_NAME, USERNAME_KEY)
        keyring.delete_password(SERVICE_NAME, PASSWORD_KEY)
        keyring.delete_password(SERVICE_NAME, TOKEN_KEY)
        logger.info("Учётные данные удалены из системного хранилища")
    except keyring.errors.PasswordDeleteError:
        pass  # Уже удалены
    except Exception as exc:
        logger.warning("Ошибка при удалении credentials: %s", exc)
