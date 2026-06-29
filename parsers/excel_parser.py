"""Парсер Excel-файлов (.xlsx, .xls)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from parsers.base import BaseParser, ParserError


class ExcelParser(BaseParser):
    """Читает XLSX/XLS через pandas."""

    extensions = (".xlsx", ".xls")
    allowed_mimetypes = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    )

    def parse(self, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path)
        self.validate_file(path)

        try:
            df = self._read_dataframe(path)
        except Exception as exc:
            raise ParserError(f"Не удалось прочитать Excel-файл: {exc}") from exc

        raw = self._extract_from_key_value(df)
        return raw

    def _read_dataframe(self, file_path: Path) -> pd.DataFrame:
        suffix = file_path.suffix.lower()
        engine = "openpyxl" if suffix == ".xlsx" else "xlrd"
        return pd.read_excel(file_path, header=None, engine=engine)
