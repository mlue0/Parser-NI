"""Парсер Excel-файлов (.xlsx, .xls)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from models.crystal_data import CrystalData
from parsers.base import BaseParser, ParserError


class ExcelParser(BaseParser):
    """Читает XLSX/XLS через pandas."""

    extensions = (".xlsx", ".xls")

    def parse(self, file_path: str | Path) -> CrystalData:
        path = Path(file_path)
        if path.suffix.lower() not in self.extensions:
            raise ParserError(f"Неподдерживаемое расширение: {path.suffix}")

        try:
            df = self._read_dataframe(path)
        except Exception as exc:
            raise ParserError(f"Не удалось прочитать Excel-файл: {exc}") from exc

        raw = self._extract_from_key_value(df)
        return self._build_model(raw)

    def _read_dataframe(self, file_path: Path) -> pd.DataFrame:
        suffix = file_path.suffix.lower()
        engine = "openpyxl" if suffix == ".xlsx" else "xlrd"
        return pd.read_excel(file_path, header=None, engine=engine)
