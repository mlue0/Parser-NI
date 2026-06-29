"""Базовый класс парсера и общие утилиты."""

from __future__ import annotations

import mimetypes
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd

from logs.setup import get_logger

logger = get_logger(__name__)


class ParserError(Exception):
    """Ошибка при чтении или разборе файла."""


class BaseParser(ABC):
    """Абстрактный парсер: читает файл и возвращает словарь с данными."""

    extensions: tuple[str, ...] = ()
    allowed_mimetypes: tuple[str, ...] = ()

    @abstractmethod
    def parse(self, file_path: str | Path) -> dict[str, Any]:
        """Извлекает данные из файла.
        
        Returns:
            Словарь с данными (не CrystalData модель!)
        """

    def validate_file(self, file_path: Path) -> None:
        """Валидация файла перед парсингом.
        
        Raises:
            ParserError: если файл не прошёл валидацию
        """
        if not file_path.exists():
            raise ParserError(f"Файл не найден: {file_path}")
        
        if not file_path.is_file():
            raise ParserError(f"Путь не является файлом: {file_path}")
        
        # Проверка размера (макс 100 MB)
        max_size = 100 * 1024 * 1024
        file_size = file_path.stat().st_size
        if file_size > max_size:
            raise ParserError(
                f"Файл слишком большой: {file_size / (1024*1024):.1f} MB "
                f"(максимум {max_size / (1024*1024):.0f} MB)"
            )
        
        if file_size == 0:
            raise ParserError("Файл пустой")
        
        # Проверка расширения
        if file_path.suffix.lower() not in self.extensions:
            raise ParserError(
                f"Неподдерживаемое расширение {file_path.suffix}. "
                f"Ожидается: {', '.join(self.extensions)}"
            )
        
        # Проверка MIME типа (если указаны)
        if self.allowed_mimetypes:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and mime_type not in self.allowed_mimetypes:
                raise ParserError(
                    f"Некорректный тип файла: {mime_type}. "
                    f"Ожидается: {', '.join(self.allowed_mimetypes)}"
                )

    def _read_dataframe(self, file_path: Path) -> pd.DataFrame:
        raise NotImplementedError

    @staticmethod
    def _normalize_header(value: Any) -> str:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return ""
        return str(value).strip()

    @classmethod
    def _extract_from_key_value(cls, df: pd.DataFrame) -> dict[str, Any]:
        """
        Извлекает поля из таблицы «ключ — значение» (2 колонки)
        или из строки заголовков + первой строки данных.
        """
        result: dict[str, Any] = {}

        if df.empty:
            raise ParserError("Файл не содержит данных")

        # Получаем aliases для парсинга
        from models.dynamic_crystal_data import get_field_aliases
        HEADER_ALIASES = get_field_aliases()
        # Нижний регистр для поиска без учёта регистра (например, ICC vs Icc)
        HEADER_ALIASES_LOWER = {k.lower(): v for k, v in HEADER_ALIASES.items()}

        def resolve(header: str) -> str | None:
            return HEADER_ALIASES.get(header) or HEADER_ALIASES_LOWER.get(header.lower())

        # Формат: колонка A — название поля, колонка B — значение
        if df.shape[1] >= 2 and df.shape[0] >= 1:
            key_col = df.iloc[:, 0]
            val_col = df.iloc[:, 1]
            for key, val in zip(key_col, val_col, strict=False):
                header = cls._normalize_header(key)
                if not header:
                    continue
                field_name = resolve(header)
                if field_name:
                    result[field_name] = cls._clean_value(val)

        # Формат: заголовки в первой строке
        if not result and df.shape[0] >= 1:
            headers = [cls._normalize_header(h) for h in df.columns]
            values = df.iloc[0].tolist()
            for header, val in zip(headers, values, strict=False):
                field_name = resolve(header)
                if field_name:
                    result[field_name] = cls._clean_value(val)

        # Формат: первая строка — заголовки, данные во второй
        if not result and df.shape[0] >= 2:
            headers = [cls._normalize_header(h) for h in df.iloc[0].tolist()]
            values = df.iloc[1].tolist()
            for header, val in zip(headers, values, strict=False):
                field_name = resolve(header)
                if field_name:
                    result[field_name] = cls._clean_value(val)

        if not result:
            raise ParserError(
                "Не удалось сопоставить поля файла. "
                "Убедитесь, что заголовки совпадают с ожидаемыми названиями."
            )
        
        logger.info(f"Распарсено {len(result)} полей из файла")
        return result

    @staticmethod
    def _clean_value(value: Any) -> Any:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, str):
            text = value.strip()
            return text if text else None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if float(value).is_integer():
                return int(value)
            return value
        return value
