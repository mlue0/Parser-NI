"""Парсер текстовых файлов (.txt)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from parsers.base import BaseParser, ParserError


class TxtParser(BaseParser):
    """Читает текстовые файлы в формате «* Название- значение»."""

    extensions = (".txt",)
    allowed_mimetypes = ("text/plain",)

    def parse(self, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path)
        self.validate_file(path)

        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            try:
                content = path.read_text(encoding="cp1251")
            except UnicodeDecodeError as exc:
                raise ParserError("Не удалось прочитать текстовый файл") from exc
        except OSError as exc:
            raise ParserError(f"Не удалось прочитать текстовый файл: {exc}") from exc

        raw = self._extract_from_text(content)
        return raw

    @staticmethod
    def _extract_from_text(content: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("*"):
                line = line[1:].strip()
            if "-" not in line:
                continue

            key, value = line.split("-", 1)
            header = key.strip()
            if not header:
                continue

            normalized = value.strip()
            result[header] = normalized

        if not result:
            raise ParserError("Не удалось извлечь данные из текстового файла")

        # Получаем aliases для парсинга
        from models.dynamic_crystal_data import get_field_aliases
        HEADER_ALIASES = get_field_aliases()
        # Нижний регистр для поиска без учёта регистра (например, ICC vs Icc)
        HEADER_ALIASES_LOWER = {k.lower(): v for k, v in HEADER_ALIASES.items()}

        mapped_result: dict[str, Any] = {}
        for header, value in result.items():
            field_name = HEADER_ALIASES.get(header) or HEADER_ALIASES_LOWER.get(header.lower())
            if field_name:
                mapped_result[field_name] = TxtParser._clean_value(value)

        if not mapped_result:
            raise ParserError(
                "Не удалось сопоставить поля текстового файла. "
                "Проверьте, что строки имеют формат «Название- значение»."
            )
        return mapped_result
