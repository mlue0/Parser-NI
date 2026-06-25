"""Базовый класс парсера и общие утилиты."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd

from models.crystal_data import HEADER_ALIASES, CrystalData


class ParserError(Exception):
    """Ошибка при чтении или разборе файла."""


class BaseParser(ABC):
    """Абстрактный парсер: читает файл и возвращает CrystalData."""

    extensions: tuple[str, ...] = ()

    @abstractmethod
    def parse(self, file_path: str | Path) -> CrystalData:
        """Извлекает данные из файла."""

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

        # Формат: колонка A — название поля, колонка B — значение
        if df.shape[1] >= 2 and df.shape[0] >= 1:
            key_col = df.iloc[:, 0]
            val_col = df.iloc[:, 1]
            for key, val in zip(key_col, val_col, strict=False):
                header = cls._normalize_header(key)
                if not header:
                    continue
                field_name = HEADER_ALIASES.get(header)
                if field_name:
                    result[field_name] = cls._clean_value(val)

        # Формат: заголовки в первой строке
        if not result and df.shape[0] >= 1:
            headers = [cls._normalize_header(h) for h in df.columns]
            values = df.iloc[0].tolist()
            for header, val in zip(headers, values, strict=False):
                field_name = HEADER_ALIASES.get(header)
                if field_name:
                    result[field_name] = cls._clean_value(val)

        # Формат: первая строка — заголовки, данные во второй
        if not result and df.shape[0] >= 2:
            headers = [cls._normalize_header(h) for h in df.iloc[0].tolist()]
            values = df.iloc[1].tolist()
            for header, val in zip(headers, values, strict=False):
                field_name = HEADER_ALIASES.get(header)
                if field_name:
                    result[field_name] = cls._clean_value(val)

        if not result:
            raise ParserError(
                "Не удалось сопоставить поля файла. "
                "Убедитесь, что заголовки совпадают с ожидаемыми названиями."
            )
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

    def _build_model(self, raw: dict[str, Any]) -> CrystalData:
        """Создаёт модель с дефолтами для отсутствующих числовых полей."""
        defaults: dict[str, Any] = {
            "good_crystals": 0,
            "defective_crystals": 0,
            "total_crystals": 0,
            "defect_contact": 0,
            "defect_icc": 0,
            "defect_fc": 0,
            "defect_static": 0,
            "plate_marking": "",
            "firmware_number": "",
            "correction_number": "",
            "bmk_batch_number": "",
            "plate_number": "",
            "initial_crystals": 0,
            "sorting_type": "",
            "sorting_target": "",
        }
        merged = {**defaults, **{k: v for k, v in raw.items() if v is not None}}
        try:
            return CrystalData.model_validate(merged)
        except Exception as exc:
            raise ParserError(f"Ошибка валидации распарсенных данных: {exc}") from exc
