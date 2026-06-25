"""Парсер CSV-файлов."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from models.crystal_data import CrystalData
from parsers.base import BaseParser, ParserError


class CsvParser(BaseParser):
    """Читает CSV с автоопределением разделителя."""

    extensions = (".csv",)

    def parse(self, file_path: str | Path) -> CrystalData:
        path = Path(file_path)
        if path.suffix.lower() not in self.extensions:
            raise ParserError(f"Неподдерживаемое расширение: {path.suffix}")

        try:
            df = self._read_dataframe(path)
        except Exception as exc:
            raise ParserError(f"Не удалось прочитать CSV-файл: {exc}") from exc

        raw = self._extract_from_key_value(df)
        return self._build_model(raw)

    def _read_dataframe(self, file_path: Path) -> pd.DataFrame:
        for encoding in ("utf-8-sig", "utf-8", "cp1251"):
            try:
                return pd.read_csv(
                    file_path,
                    header=None,
                    sep=None,
                    engine="python",
                    encoding=encoding,
                )
            except UnicodeDecodeError:
                continue
        raise ParserError("Не удалось определить кодировку CSV-файла")
