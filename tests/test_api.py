"""Тесты REST API клиента с retry механизмом."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from api.client import ApiClient, ApiResponse
from api.exceptions import ApiAuthError, ApiConnectionError, ApiError, ApiValidationError
from config.settings import Settings
from models.crystal_data import CrystalData, SORTING_TARGETS


def _settings(**overrides) -> Settings:
    base = {
        "api_url": "https://example.com/api",
        "api_login": "user",
        "api_password": "pass",
        "api_token": "",
        "log_level": "DEBUG",
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
            "defect_inl": 0,
            "defect_dnl": 0,
            "defect_burn": 0,
            "defect_u0_adc": 0,
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


class TestApiClientAuth:
    """Тесты авторизации."""

    def test_login_success(self):
        """Тест успешной авторизации."""
        client = ApiClient(_settings(), max_retries=3)
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "abc123"}

        with patch.object(client._session, "post", return_value=mock_response) as post:
            token = client.login()
            assert token == "abc123"
            post.assert_called_once()

    def test_login_with_access_token(self):
        """Тест авторизации с полем access_token."""
        client = ApiClient(_settings())
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "xyz789"}

        with patch.object(client._session, "post", return_value=mock_response):
            token = client.login()
            assert token == "xyz789"

    def test_login_auth_error(self):
        """Тест ошибки авторизации 401."""
        client = ApiClient(_settings())
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch.object(client._session, "post", return_value=mock_response):
            with pytest.raises(ApiAuthError):
                client.login()

    def test_login_static_token(self):
        """Тест использования статического токена."""
        client = ApiClient(_settings(api_token="static-123"))
        token = client.login()
        assert token == "static-123"

    def test_login_no_token_in_response(self):
        """Тест отсутствия токена в ответе."""
        client = ApiClient(_settings())
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}

        with patch.object(client._session, "post", return_value=mock_response):
            with pytest.raises(ApiAuthError, match="не вернул токен"):
                client.login()


class TestApiClientRetry:
    """Тесты retry механизма."""

    def test_login_retry_on_500(self):
        """Тест retry при серверной ошибке."""
        client = ApiClient(_settings(), max_retries=3, backoff_factor=0.01)
        
        # Первые 2 попытки — ошибка, 3-я — успех
        responses = [
            MagicMock(ok=False, status_code=500, text="Error"),
            MagicMock(ok=False, status_code=500, text="Error"),
            MagicMock(ok=True, status_code=200, json=lambda: {"token": "retry-success"}),
        ]
        
        with patch.object(client._session, "post", side_effect=responses):
            token = client.login()
            assert token == "retry-success"

    def test_login_exhausted_retries(self):
        """Тест исчерпания попыток."""
        client = ApiClient(_settings(), max_retries=2, backoff_factor=0.01)
        
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = "Server error"

        with patch.object(client._session, "post", return_value=mock_response):
            with pytest.raises(ApiError, match="отклонена"):
                client.login()

    def test_send_data_connection_retry(self):
        """Тест retry при ConnectionError."""
        client = ApiClient(_settings(api_token="token"), max_retries=3, backoff_factor=0.01)
        
        # Первая попытка — ошибка, вторая — успех
        call_count = [0]
        
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise requests.exceptions.ConnectionError("Connection failed")
            
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.status_code = 201
            mock_resp.json.return_value = {"id": 123, "status": "saved"}
            return mock_resp

        with patch.object(client._session, "post", side_effect=side_effect):
            response = client.send_data(_sample_data())
            assert response.success
            assert call_count[0] == 2


class TestApiClientSendData:
    """Тесты отправки данных."""

    def test_send_data_success(self):
        """Тест успешной отправки."""
        client = ApiClient(_settings(api_token="static-token"))
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123, "message": "Saved"}

        with patch.object(client._session, "post", return_value=mock_response):
            response = client.send_data(_sample_data())
            assert response.success
            assert response.message == "Saved"
            assert response.status_code == 201

    def test_send_data_validation_error(self):
        """Тест ошибки валидации 422."""
        client = ApiClient(_settings(api_token="static-token"))
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 422
        mock_response.json.return_value = {"detail": "plate_number required"}

        with patch.object(client._session, "post", return_value=mock_response):
            with pytest.raises(ApiValidationError):
                client.send_data(_sample_data())

    def test_send_data_connection_error(self):
        """Тест ошибки соединения."""
        client = ApiClient(_settings(api_token="static-token"), max_retries=2, backoff_factor=0.01)

        with patch.object(
            client._session,
            "post",
            side_effect=requests.exceptions.ConnectionError("fail"),
        ):
            with pytest.raises(ApiConnectionError):
                client.send_data(_sample_data())

    def test_send_data_auto_login(self):
        """Тест автоматической авторизации."""
        client = ApiClient(_settings())
        
        # Mock login response
        login_response = MagicMock()
        login_response.ok = True
        login_response.status_code = 200
        login_response.json.return_value = {"token": "auto-token"}
        
        # Mock send response
        send_response = MagicMock()
        send_response.ok = True
        send_response.status_code = 201
        send_response.json.return_value = {"id": 456}
        
        with patch.object(client._session, "post", side_effect=[login_response, send_response]):
            response = client.send_data(_sample_data())
            assert response.success
            assert client._token == "auto-token"

    def test_send_data_token_refresh_on_401(self):
        """Тест обновления токена при 401."""
        client = ApiClient(_settings(), max_retries=3, backoff_factor=0.01)
        client._token = "expired-token"
        
        # Первая попытка — 401
        first_response = MagicMock()
        first_response.ok = False
        first_response.status_code = 401
        first_response.json.return_value = {"error": "Token expired"}
        
        # Reauth
        auth_response = MagicMock()
        auth_response.ok = True
        auth_response.status_code = 200
        auth_response.json.return_value = {"token": "new-token"}
        
        # Повторная отправка — успех
        success_response = MagicMock()
        success_response.ok = True
        success_response.status_code = 201
        success_response.json.return_value = {"id": 789}
        
        with patch.object(client._session, "post", side_effect=[first_response, auth_response, success_response]):
            response = client.send_data(_sample_data())
            assert response.success
            assert client._token == "new-token"


class TestApiClientEdgeCases:
    """Тесты граничных случаев."""

    def test_empty_response_body(self):
        """Тест пустого тела ответа."""
        client = ApiClient(_settings(api_token="token"))
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_response.json.side_effect = ValueError("No JSON")
        mock_response.text = ""

        with patch.object(client._session, "post", return_value=mock_response):
            response = client.send_data(_sample_data())
            assert response.success
            assert "raw" in response.payload

    def test_custom_timeout(self):
        """Тест кастомного timeout."""
        client = ApiClient(_settings(), timeout=15.0)
        assert client._timeout == 15.0

    def test_custom_retry_params(self):
        """Тест кастомных параметров retry."""
        client = ApiClient(_settings(), max_retries=5, backoff_factor=2.0)
        assert client._max_retries == 5
        assert client._backoff_factor == 2.0

    def test_extract_error_detail_from_dict(self):
        """Тест извлечения detail из JSON ошибки."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"detail": "Error message"}
        
        detail = ApiClient._extract_error_detail(mock_response)
        assert detail == "Error message"

    def test_extract_error_from_malformed_json(self):
        """Тест обработки невалидного JSON в ошибке."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Plain text error"
        
        detail = ApiClient._extract_error_detail(mock_response)
        assert detail == "Plain text error"
