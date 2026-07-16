"""Тесты разбора единиц измерения в форме норм (SI-приставки)."""

from __future__ import annotations

import pytest

from ui.dynamic_edit_form import _base_quantity, _resolve_unit, _split_value_unit


@pytest.mark.parametrize(
    ("raw", "base", "expected_num", "expected_unit"),
    [
        # Главный баг: одиночная приставка не должна удваивать приставку базы.
        ("25u", "мкА", "25", "мкА"),
        ("25U", "мкА", "25", "мкА"),
        # Значение со своей составной единицей переопределяет базовую.
        ("5mA", "мкА", "5", "мА"),
        ("5nA", "мкА", "5", "нА"),
        ("11A", "мкА", "11", "А"),
        # Приставка к другой базовой величине.
        ("0.5m", "В", "0.5", "мВ"),
        ("17p", "МЗР", "17", "пМЗР"),
        # Без суффикса — берётся базовая единица.
        ("2", "В", "2", "В"),
        ("1.5", "МЗР", "1.5", "МЗР"),
        # Пробел между числом и единицей.
        ("3.12 mA", "мкА", "3.12", "мА"),
        # Идемпотентность: уже нормализованное значение не меняется.
        ("25 мкА", "мкА", "25", "мкА"),
        ("5 мВ", "В", "5", "мВ"),
    ],
)
def test_split_value_unit(raw: str, base: str, expected_num: str, expected_unit: str) -> None:
    num, unit = _split_value_unit(raw, base)
    assert num == expected_num
    assert unit == expected_unit


def test_no_double_prefix() -> None:
    """Регресс на «мкмкА»: 'u' + базовая 'мкА' = 'мкА', не 'мкмкА'."""
    assert _resolve_unit("u", "мкА") == "мкА"
    assert "мкмк" not in _resolve_unit("u", "мкА")


@pytest.mark.parametrize(
    ("unit", "expected"),
    [
        ("мкА", "А"),
        ("мА", "А"),
        ("нА", "А"),
        ("мВ", "В"),
        ("кВ", "В"),
        ("В", "В"),
        ("МЗР", "МЗР"),  # «М» здесь не приставка
        ("Ом", "Ом"),
    ],
)
def test_base_quantity(unit: str, expected: str) -> None:
    assert _base_quantity(unit) == expected
