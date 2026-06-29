"""Тесты Pydantic-модели CrystalData."""

import pytest
from pydantic import ValidationError

from models.crystal_data import (
    CrystalData,
    SORTING_TARGETS,
    get_correction_options,
    get_firmware_options,
    get_initial_crystals_default,
)


def _valid_payload() -> dict:
    return {
        "good_crystals": 100,
        "defective_crystals": 5,
        "total_crystals": 105,
        "defect_contact": 1,
        "defect_icc": 2,
        "defect_fc": 1,
        "defect_static": 1,
        "defect_inl": 0,
        "defect_dnl": 0,
        "defect_burn": 0,
        "defect_u0_adc": 0,
        "plate_marking": "PL-001",
        "firmware_number": "FW-10",
        "correction_number": "CR-01",
        "bmk_batch_number": "BMK-2024-01",
        "plate_number": "P-123",
        "initial_crystals": 110,
        "sorting_type": "Полная",
        "sorting_target": SORTING_TARGETS[0],
    }


def test_valid_model():
    data = CrystalData.model_validate(_valid_payload())
    assert data.good_crystals == 100
    assert data.sorting_target in SORTING_TARGETS


def test_invalid_sorting_target():
    payload = _valid_payload()
    payload["sorting_target"] = "INVALID"
    with pytest.raises(ValidationError):
        CrystalData.model_validate(payload)


def test_negative_crystals_rejected():
    payload = _valid_payload()
    payload["good_crystals"] = -1
    with pytest.raises(ValidationError):
        CrystalData.model_validate(payload)


def test_to_api_payload():
    data = CrystalData.model_validate(_valid_payload())
    payload = data.to_api_payload()
    assert payload["plate_number"] == "P-123"
    assert "sorting_target" in payload


def test_plate_marking_rules():
    corrections = get_correction_options("K03")
    firmwares = get_firmware_options("K03")
    assert "K03" in corrections
    assert "K03" in firmwares
    assert get_initial_crystals_default("HV101M") == 400
    assert "HV101M" in get_correction_options("HV101M")
