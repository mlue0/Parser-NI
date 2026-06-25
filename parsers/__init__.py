"""Модуль парсеров файлов."""

from parsers.registry import get_parser, supported_extensions

__all__ = ["get_parser", "supported_extensions"]
