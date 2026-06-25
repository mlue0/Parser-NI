"""Тесты парсеров файлов."""

from pathlib import Path

import pandas as pd
import pytest

from parsers.base import ParserError
from parsers.csv_parser import CsvParser
from parsers.registry import get_parser, supported_extensions


SAMPLE_ROWS = [
    ("Годные кристаллы", 100),
    ("Бракованные кристаллы", 5),
    ("Общее количество кристаллов", 105),
    ("Брак по Contact", 1),
    ("Брак по Icc", 2),
    ("Брак по FC", 1),
    ("Брак по Static", 1),
    ("Маркировка пластины", "PL-001"),
    ("Номер зашивки", "FW-10"),
    ("Номер коррекции", "CR-01"),
    ("Номер партии БМК", "BMK-2024-01"),
    ("Номер пластины", "P-123"),
    ("Исходное количество кристаллов", 110),
    ("Тип разбраковки", "Полная"),
    ("Цель разбраковки", "ПР-ОВ"),
]


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    path = tmp_path / "sample.csv"
    df = pd.DataFrame(SAMPLE_ROWS)
    df.to_csv(path, index=False, header=False, encoding="utf-8-sig")
    return path


@pytest.fixture
def sample_txt(tmp_path: Path) -> Path:
    path = tmp_path / "sample.txt"
    content = "\n".join(f"* {label}- {value}" for label, value in SAMPLE_ROWS)
    path.write_text(content, encoding="utf-8")
    return path


def test_supported_extensions():
    exts = supported_extensions()
    assert ".csv" in exts
    assert ".xlsx" in exts
    assert ".txt" in exts


def test_csv_parser(sample_csv: Path):
    parser = CsvParser()
    data = parser.parse(sample_csv)
    assert data.good_crystals == 100
    assert data.plate_marking == "PL-001"
    assert data.sorting_target == "ПР-ОВ"


def test_txt_parser(sample_txt: Path):
    parser = get_parser(sample_txt)
    data = parser.parse(sample_txt)
    assert data.good_crystals == 100
    assert data.plate_marking == "PL-001"
    assert data.sorting_target == "ПР-ОВ"


def test_get_parser_unknown_extension(tmp_path: Path):
    bad_file = tmp_path / "data.bin"
    bad_file.write_text("test", encoding="utf-8")
    with pytest.raises(ParserError):
        get_parser(bad_file)
