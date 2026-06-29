"""Тесты динамической модели кристаллов."""

from typing import Any

import pytest

from models.dynamic_crystal_data import create_dynamic_crystal_data_model


@pytest.fixture
def digital_data() -> dict[str, Any]:
    """Данные для цифровой пластины."""
    return {
        "plate_marking": "HV101",
        "bmk_batch_number": "BMK-2024-01",
        "plate_number": "P-123",
        "firmware_number": "FW-10",
        "correction_number": "CR-01",
        "good_crystals": 150,
        "defective_crystals": 10,
        "total_crystals": 160,
        "initial_crystals": 160,
        "defect_contact": 2,
        "defect_icc": 3,
        "defect_fc": 2,
        "defect_static": 3,
    }


@pytest.fixture
def analog_data() -> dict[str, Any]:
    """Данные для аналоговой пластины."""
    return {
        "plate_marking": "K04",
        "bmk_batch_number": "BMK-2024-02",
        "plate_number": "P-124",
        "good_crystals": 120,
        "defective_crystals": 15,
        "total_crystals": 135,
        "initial_crystals": 135,
        "defect_contact": 1,
        "defect_icc": 2,
        "defect_fc": 1,
        "defect_static": 2,
        "defect_inl": 5,
        "defect_dnl": 3,
        "defect_burn": 1,
        "norm_inl": "5 nA",
        "norm_dnl": "3 nA",
    }


def test_create_dynamic_model_digital(digital_data):
    """Тестирует создание динамической модели для цифровой пластины."""
    DynamicModel = create_dynamic_crystal_data_model(digital_data)
    data = DynamicModel.model_validate(digital_data)
    
    assert data.plate_marking == "HV101"
    assert data.good_crystals == 150
    assert data.defect_contact == 2
    assert data.defect_icc == 3


def test_create_dynamic_model_analog(analog_data):
    """Тестирует создание динамической модели для аналоговой пластины."""
    DynamicModel = create_dynamic_crystal_data_model(analog_data)
    data = DynamicModel.model_validate(analog_data)
    
    assert data.plate_marking == "K04"
    assert data.good_crystals == 120
    assert data.defect_inl == 5
    assert data.norm_inl == "5 nA"


def test_model_has_labeled_values(digital_data):
    """Тестирует что модель имеет метод labeled_values."""
    DynamicModel = create_dynamic_crystal_data_model(digital_data)
    data = DynamicModel.model_validate(digital_data)
    
    labeled_values = data.labeled_values()
    assert isinstance(labeled_values, list)
    assert len(labeled_values) > 0
    
    # Проверяем что это пары (label, value)
    for label, value in labeled_values:
        assert isinstance(label, str)
        assert isinstance(value, str)


def test_model_has_to_api_payload(digital_data):
    """Тестирует что модель имеет метод to_api_payload."""
    DynamicModel = create_dynamic_crystal_data_model(digital_data)
    data = DynamicModel.model_validate(digital_data)
    
    payload = data.to_api_payload()
    assert isinstance(payload, dict)
    assert payload["plate_marking"] == "HV101"


def test_dynamic_model_validation_error(digital_data):
    """Тестирует валидацию на ошибки."""
    # Удаляем обязательное поле
    digital_data.pop("plate_marking")
    
    DynamicModel = create_dynamic_crystal_data_model(digital_data)
    
    with pytest.raises(Exception):  # ValidationError
        DynamicModel.model_validate(digital_data)


def test_model_defaults(digital_data):
    """Тестирует значения по умолчанию."""
    # Удаляем опциональные поля
    minimal_data = {
        "plate_marking": "HV101",
        "bmk_batch_number": "BMK-2024-01",
        "plate_number": "P-123",
        "good_crystals": 150,
        "defective_crystals": 10,
        "total_crystals": 160,
        "initial_crystals": 160,
    }
    
    DynamicModel = create_dynamic_crystal_data_model(minimal_data)
    data = DynamicModel.model_validate(minimal_data)
    
    # Проверяем что опциональные поля имеют значения по умолчанию
    assert data.sorting_type == "Разбраковка NI"
    assert data.sorting_target == "ПР-ОВ"
    assert data.comment == ""
