"""Реестр парсеров по расширению файла."""

from __future__ import annotations

from pathlib import Path

from parsers.base import BaseParser, ParserError
from parsers.csv_parser import CsvParser
from parsers.excel_parser import ExcelParser
from parsers.txt_parser import TxtParser

_PARSERS: list[BaseParser] = [
    ExcelParser(),
    CsvParser(),
    TxtParser(),
]

_EXTENSION_MAP: dict[str, BaseParser] = {}
for parser in _PARSERS:
    for ext in parser.extensions:
        _EXTENSION_MAP[ext.lower()] = parser


def supported_extensions() -> tuple[str, ...]:
    """Возвращает поддерживаемые расширения файлов."""
    return tuple(sorted(_EXTENSION_MAP.keys()))


def get_parser(file_path: str | Path) -> BaseParser:
    """Возвращает парсер для указанного файла."""
    suffix = Path(file_path).suffix.lower()
    parser = _EXTENSION_MAP.get(suffix)
    if parser is None:
        allowed = ", ".join(supported_extensions())
        raise ParserError(
            f"Формат '{suffix}' не поддерживается. Допустимые форматы: {allowed}"
        )
    return parser
