"""Тесты REST API клиента (без реального сервера)."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from api.client import ApiClient
from api.exceptions import ApiAuthError, ApiConnectionError, ApiValidationError
from config.settings import Settings
from models.crystal_data import CrystalData, SORTING_TARGETS


def _settings(**overrides) -> Settings:
    base = {
        "api_url": "https://example.com/api",
        "api_login": "user",
        "api_password": "pass",
        "api_token": "",
    }
    base.update(overrides)
    return Settings(**base)


def _sample_data() -> CrystalData:
    return CrystalData.model_validate(
        {
            "good_crystals": 10,
            "defective_crystals": 1,
            "total_crystals": 11,
            "defect_contact": 0,
            "defect_icc": 1,
            "defect_fc": 0,
            "defect_static": 0,
            "plate_marking": "PL",
            "firmware_number": "FW",
            "correction_number": "CR",
            "bmk_batch_number": "BMK",
            "plate_number": "P1",
            "initial_crystals": 12,
            "sorting_type": "Полная",
            "sorting_target": SORTING_TARGETS[0],
        }
    )


def test_login_success():
    client = ApiClient(_settings())
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.status_code = 200
    mock_response.json.return_value = {"token": "abc123"}

    with patch.object(client._session, "post", return_value=mock_response) as post:
        token = client.login()
        assert token == "abc123"
        post.assert_called_once()


def test_login_auth_error():
    client = ApiClient(_settings())
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    with patch.object(client._session, "post", return_value=mock_response):
        with pytest.raises(ApiAuthError):
            client.login()


def test_send_data_validation_error():
    client = ApiClient(_settings(api_token="static-token"))
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 422
    mock_response.json.return_value = {"detail": "plate_number required"}

    with patch.object(client._session, "post", return_value=mock_response):
        with pytest.raises(ApiValidationError):
            client.send_data(_sample_data())


def test_send_data_connection_error():
    client = ApiClient(_settings(api_token="static-token"))

    with patch.object(
        client._session,
        "post",
        side_effect=requests.exceptions.ConnectionError("fail"),
    ):
        with pytest.raises(ApiConnectionError):
            client.send_data(_sample_data())
