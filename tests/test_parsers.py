"""Тесты парсеров файлов."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from parsers.base import ParserError
from parsers.csv_parser import CsvParser
from parsers.excel_parser import ExcelParser
from parsers.registry import get_parser, supported_extensions
from parsers.txt_parser import TxtParser

# ── Тестовые данные ────────────────────────────────────────────
SAMPLE_ROWS = [
    ("Годные кристаллы", 100),
    ("Бракованные кристаллы", 5),
    ("Общее количество кристаллов", 105),
    ("Брак по Contact", 1),
    ("Брак по Icc", 2),          # намеренно «Icc» (не «ICC») — тест case-insensitive
    ("Брак по FC", 1),
    ("Брак по Static", 1),
    ("Маркировка пластины", "HV23"),
    ("Номер зашивки", "FW-10"),
    ("Номер коррекции", "CR-01"),
    ("Номер партии БМК", "BMK-2024-01"),
    ("Номер пластины", "P-123"),
    ("Исходное количество кристаллов", 110),
    ("Тип разбраковки", "Разбраковка NI"),
    ("Цель разбраковки", "ПР-ОВ"),
]

ANALOG_ROWS = [
    ("Годные кристаллы", 80),
    ("Бракованные кристаллы", 10),
    ("Общее количество кристаллов", 90),
    ("Брак по Contact", 2),
    ("Брак по ICC", 1),
    ("Брак по FC", 1),
    ("Брак по Static", 1),
    ("Брак по INL", 3),
    ("Брак по DNL", 2),
    ("Маркировка пластины", "HV81"),
    ("Норма INL", 1.5),
    ("Норма DNL", 1.0),
]


# ── Фикстуры ──────────────────────────────────────────────────

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


@pytest.fixture
def sample_xlsx(tmp_path: Path) -> Path:
    path = tmp_path / "sample.xlsx"
    df = pd.DataFrame(SAMPLE_ROWS)
    df.to_excel(path, index=False, header=False)
    return path


@pytest.fixture
def analog_txt(tmp_path: Path) -> Path:
    path = tmp_path / "analog.txt"
    content = "\n".join(f"* {label}- {value}" for label, value in ANALOG_ROWS)
    path.write_text(content, encoding="utf-8")
    return path


# ── Тесты реестра ─────────────────────────────────────────────

def test_supported_extensions():
    exts = supported_extensions()
    assert ".csv" in exts
    assert ".xlsx" in exts
    assert ".txt" in exts


def test_get_parser_returns_correct_type_for_csv(sample_csv: Path):
    parser = get_parser(sample_csv)
    assert isinstance(parser, CsvParser)


def test_get_parser_returns_correct_type_for_txt(sample_txt: Path):
    parser = get_parser(sample_txt)
    assert isinstance(parser, TxtParser)


def test_get_parser_returns_correct_type_for_xlsx(sample_xlsx: Path):
    parser = get_parser(sample_xlsx)
    assert isinstance(parser, ExcelParser)


def test_get_parser_unknown_extension_raises(tmp_path: Path):
    bad_file = tmp_path / "data.bin"
    bad_file.write_text("test", encoding="utf-8")
    with pytest.raises(ParserError):
        get_parser(bad_file)


# ── Тесты CSV-парсера ─────────────────────────────────────────

def test_csv_parser_basic_fields(sample_csv: Path):
    data: dict[str, Any] = CsvParser().parse(sample_csv)
    assert data.get("good_crystals") == 100
    assert data.get("defective_crystals") == 5
    assert data.get("total_crystals") == 105


def test_csv_parser_identity_fields(sample_csv: Path):
    data = CsvParser().parse(sample_csv)
    assert data.get("plate_marking") == "HV23"
    assert data.get("firmware_number") == "FW-10"
    assert data.get("sorting_target") == "ПР-ОВ"


def test_csv_parser_icc_case_insensitive(sample_csv: Path):
    """Поле «Брак по Icc» (строчное c) должно маппиться в defect_icc."""
    data = CsvParser().parse(sample_csv)
    assert "defect_icc" in data, "defect_icc не найден — нарушена case-insensitive логика"
    assert data["defect_icc"] == 2


def test_csv_empty_file_raises(tmp_path: Path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ParserError):
        CsvParser().parse(path)


def test_csv_missing_file_raises():
    with pytest.raises(ParserError):
        CsvParser().parse(Path("/nonexistent/path/file.csv"))


def test_csv_file_with_unmapped_headers_raises(tmp_path: Path):
    path = tmp_path / "bad.csv"
    df = pd.DataFrame([("Неизвестный столбец", 99), ("Другой", 0)])
    df.to_csv(path, index=False, header=False, encoding="utf-8-sig")
    with pytest.raises(ParserError):
        CsvParser().parse(path)


# ── Тесты TXT-парсера ─────────────────────────────────────────

def test_txt_parser_basic_fields(sample_txt: Path):
    data = TxtParser().parse(sample_txt)
    assert data.get("good_crystals") == 100
    assert data.get("defective_crystals") == 5
    assert data.get("total_crystals") == 105


def test_txt_parser_icc_case_insensitive(sample_txt: Path):
    """TXT-файл содержит «Брак по Icc» — должен маппиться в defect_icc."""
    data = TxtParser().parse(sample_txt)
    assert data.get("defect_icc") == 2


def test_txt_parser_identity_fields(sample_txt: Path):
    data = TxtParser().parse(sample_txt)
    assert data.get("plate_marking") == "HV23"
    assert data.get("sorting_target") == "ПР-ОВ"


def test_txt_parser_skips_empty_lines(tmp_path: Path):
    path = tmp_path / "sparse.txt"
    path.write_text(
        "\n\n* Годные кристаллы- 50\n\n* Маркировка пластины- HV23\n",
        encoding="utf-8",
    )
    data = TxtParser().parse(path)
    assert data.get("good_crystals") == 50


def test_txt_parser_empty_file_raises(tmp_path: Path):
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ParserError):
        TxtParser().parse(path)


def test_txt_parser_lines_without_dash_skipped(tmp_path: Path):
    path = tmp_path / "nodash.txt"
    # Строка без дефиса должна просто игнорироваться
    path.write_text(
        "* Годные кристаллы- 50\n"
        "строка без дефиса\n"
        "* Маркировка пластины- HV23\n",
        encoding="utf-8",
    )
    data = TxtParser().parse(path)
    assert data.get("good_crystals") == 50


# ── Тесты Excel-парсера ───────────────────────────────────────

def test_excel_parser_basic_fields(sample_xlsx: Path):
    data = ExcelParser().parse(sample_xlsx)
    assert data.get("good_crystals") == 100
    assert data.get("defective_crystals") == 5


def test_excel_parser_identity_fields(sample_xlsx: Path):
    data = ExcelParser().parse(sample_xlsx)
    assert data.get("plate_marking") == "HV23"
    assert data.get("sorting_target") == "ПР-ОВ"


def test_excel_parser_icc_case_insensitive(sample_xlsx: Path):
    data = ExcelParser().parse(sample_xlsx)
    assert data.get("defect_icc") == 2


def test_excel_missing_file_raises():
    with pytest.raises(ParserError):
        ExcelParser().parse(Path("/nonexistent/path/file.xlsx"))


# ── Тесты аналоговых данных ───────────────────────────────────

def test_analog_fields_parsed(analog_txt: Path):
    data = TxtParser().parse(analog_txt)
    assert "defect_inl" in data
    assert "defect_dnl" in data
    assert data.get("defect_inl") == 3


# ── Тесты кросс-валидации модели ─────────────────────────────

def test_cross_validation_sum_mismatch():
    """Если good+bad != total — должно появиться предупреждение в модели."""
    from models.dynamic_crystal_data import create_dynamic_crystal_data_model

    raw = {
        "good_crystals": 90,
        "defective_crystals": 5,
        "total_crystals": 100,  # 90+5 ≠ 100
        "plate_marking": "HV23",
        "plate_number": "P-1",
        "bmk_batch_number": "BMK-1",
        "sorting_type": "Разбраковка NI",
        "sorting_target": "ПР-ОВ",
    }
    Model = create_dynamic_crystal_data_model(raw)
    instance = Model.model_validate(raw)
    warnings = instance.__dict__.get("_cross_field_warnings", [])
    assert any("Годные" in w for w in warnings), f"Ожидали предупреждение о сумме, получили: {warnings}"


def test_cross_validation_defect_sum_exceeds_bad():
    """Если сумма видов брака > бракованных — должно быть предупреждение."""
    from models.dynamic_crystal_data import create_dynamic_crystal_data_model

    raw = {
        "good_crystals": 90,
        "defective_crystals": 5,
        "total_crystals": 95,
        "defect_contact": 3,
        "defect_icc": 4,  # 3+4=7 > 5
        "plate_marking": "HV23",
        "plate_number": "P-1",
        "bmk_batch_number": "BMK-1",
        "sorting_type": "Разбраковка NI",
        "sorting_target": "ПР-ОВ",
    }
    Model = create_dynamic_crystal_data_model(raw)
    instance = Model.model_validate(raw)
    warnings = instance.__dict__.get("_cross_field_warnings", [])
    assert any("Сумма" in w for w in warnings), f"Ожидали предупреждение о браке, получили: {warnings}"


def test_cross_validation_no_warnings_when_correct():
    """При корректных данных предупреждений быть не должно."""
    from models.dynamic_crystal_data import create_dynamic_crystal_data_model

    raw = {
        "good_crystals": 95,
        "defective_crystals": 5,
        "total_crystals": 100,
        "defect_contact": 2,
        "defect_icc": 3,
        "plate_marking": "HV23",
        "plate_number": "P-1",
        "bmk_batch_number": "BMK-1",
        "sorting_type": "Разбраковка NI",
        "sorting_target": "ПР-ОВ",
    }
    Model = create_dynamic_crystal_data_model(raw)
    instance = Model.model_validate(raw)
    warnings = instance.__dict__.get("_cross_field_warnings", [])
    assert warnings == [], f"Неожиданные предупреждения: {warnings}"
