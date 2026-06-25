"""Исключения REST API клиента."""

from __future__ import annotations


class ApiError(Exception):
    """Базовая ошибка API."""


class ApiAuthError(ApiError):
    """Ошибка авторизации (401/403)."""


class ApiConnectionError(ApiError):
    """Ошибка соединения с сервером."""


class ApiValidationError(ApiError):
    """Ошибка валидации данных на сервере (422 и др.)."""
