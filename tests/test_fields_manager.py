"""Тесты менеджера полей."""

from typing import Any

import pytest

from config.fields_manager import FieldConfig, FieldGroup, get_fields_manager


@pytest.fixture
def fields_manager():
    """Получает экземпляр fields_manager."""
    return get_fields_manager()


def test_fields_manager_singleton(fields_manager):
    """Тестирует что fields_manager - синглтон."""
    manager2 = get_fields_manager()
    assert fields_manager is manager2


def test_get_all_fields(fields_manager):
    """Тестирует получение всех полей."""
    fields = fields_manager.get_all_fields()
    assert isinstance(fields, list)
    assert len(fields) > 0
    
    # Проверяем что это FieldConfig объекты
    for field in fields:
        assert isinstance(field, FieldConfig)


def test_get_fields_by_group(fields_manager):
    """Тестирует получение полей конкретной группы."""
    fields = fields_manager.get_fields_by_group("required_base")
    assert isinstance(fields, list)
    assert len(fields) > 0


def test_get_field(fields_manager):
    """Тестирует поиск одного поля."""
    field = fields_manager.get_field("plate_marking")
    assert field is not None
    assert field.key == "plate_marking"
    assert field.label == "Маркировка пластины"


def test_get_field_not_found(fields_manager):
    """Тестирует что несуществующее поле возвращает None."""
    field = fields_manager.get_field("nonexistent_field")
    assert field is None


def test_detect_plate_type_digital(fields_manager):
    """Тестирует определение цифровой пластины."""
    data: dict[str, Any] = {
        "plate_marking": "HV101",
        "good_crystals": 100,
        "defect_contact": 5,
    }
    
    plate_type = fields_manager._detect_plate_type(data)
    assert plate_type == "digital"


def test_detect_plate_type_analog(fields_manager):
    """Тестирует определение аналоговой пластины."""
    data: dict[str, Any] = {
        "plate_marking": "K04",
        "good_crystals": 100,
        "defect_inl": 5,
    }
    
    plate_type = fields_manager._detect_plate_type(data)
    assert plate_type == "analog"


def test_get_fields_from_data_digital(fields_manager):
    """Тестирует получение полей из данных для цифровой пластины."""
    data: dict[str, Any] = {
        "plate_marking": "HV101",
        "bmk_batch_number": "BMK-2024-01",
        "plate_number": "P-123",
        "good_crystals": 100,
        "defective_crystals": 10,
        "defect_contact": 5,
    }
    
    fields = fields_manager.get_fields_from_data(data)
    assert isinstance(fields, list)
    assert len(fields) > 0
    
    # Проверяем что обязательные поля включены
    field_keys = {f.key for f in fields}
    assert "plate_marking" in field_keys


def test_get_fields_from_data_analog(fields_manager):
    """Тестирует получение полей из данных для аналоговой пластины."""
    data: dict[str, Any] = {
        "plate_marking": "K04",
        "good_crystals": 100,
        "defect_inl": 5,
        "norm_inl": "5 nA",
    }
    
    fields = fields_manager.get_fields_from_data(data)
    field_keys = {f.key for f in fields}
    
    # Для аналоговой пластины должны быть аналоговые поля
    # если включены в show_only_parsed_fields


def test_get_field_aliases(fields_manager):
    """Тестирует получение aliases полей."""
    from models.dynamic_crystal_data import get_field_aliases
    
    aliases = get_field_aliases()
    assert isinstance(aliases, dict)
    assert len(aliases) > 0
    
    # Проверяем что есть стандартные aliases
    assert "Маркировка пластины" in aliases
    assert aliases["Маркировка пластины"] == "plate_marking"


def test_field_config_to_dict(fields_manager):
    """Тестирует преобразование FieldConfig в dict."""
    field = fields_manager.get_field("plate_marking")
    assert field is not None
    
    field_dict = field.to_dict()
    assert isinstance(field_dict, dict)
    assert field_dict["key"] == "plate_marking"
    assert field_dict["label"] == "Маркировка пластины"
