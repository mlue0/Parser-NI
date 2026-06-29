"""
REST API клиент для авторизации и отправки данных.

Примеры запросов (адаптируйте под реальный API):

1. Авторизация:
   POST {API_URL}/auth/login
   Content-Type: application/json
   Body: {"login": "...", "password": "..."}
   Response 200: {"token": "jwt-token", "expires_in": 3600}

2. Отправка данных:
   POST {API_URL}/crystals/sorting
   Authorization: Bearer {token}
   Content-Type: application/json
   Body: { ... поля CrystalData ... }
   Response 201: {"id": 123, "status": "saved"}
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests
from pydantic import BaseModel, ValidationError
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout
from urllib3.util.retry import Retry

from api.exceptions import ApiAuthError, ApiConnectionError, ApiError, ApiValidationError
from config.settings import Settings
from logs.setup import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ApiResponse:
    """Результат успешной отправки данных."""

    success: bool
    message: str
    status_code: int
    payload: dict[str, Any] | None = None


class ApiClient:
    """
    Клиент REST API с автоматическими повторными попытками.

    Методы login() и send_data() спроектированы для простой адаптации
    под конкретный backend: измените URL, тела запросов и разбор ответов.
    """

    def __init__(
        self, 
        settings: Settings, 
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ) -> None:
        self._settings = settings
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._session = self._create_session()
        self._token: str | None = settings.api_token or None

    def _create_session(self) -> requests.Session:
        """Создаёт сессию с retry стратегией."""
        session = requests.Session()
        
        # Retry стратегия: повторы для 500, 502, 503, 504 и connection errors
        retry_strategy = Retry(
            total=self._max_retries,
            backoff_factor=self._backoff_factor,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
            raise_on_status=False,
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    @property
    def base_url(self) -> str:
        return self._settings.api_url.rstrip("/")

    def login(self) -> str:
        """
        Авторизация на сервере с повторными попытками.

        Returns:
            JWT/ Bearer токен.

        Raises:
            ApiAuthError: неверные учётные данные.
            ApiConnectionError: сервер недоступен.
        """
        if self._settings.has_static_token:
            self._token = self._settings.api_token
            logger.info("Использован статический API_TOKEN")
            return self._token

        url = f"{self.base_url}/auth/login"
        payload = {
            "login": self._settings.api_login,
            "password": self._settings.api_password,
        }

        logger.info("Авторизация: POST %s", url)
        
        # Ручной retry с exponential backoff для критичных операций
        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._session.post(
                    url,
                    json=payload,
                    timeout=self._timeout,
                )
                
                if response.status_code in (401, 403):
                    logger.warning("Ошибка авторизации: HTTP %s", response.status_code)
                    raise ApiAuthError("Ошибка авторизации. Проверьте логин и пароль.")

                if not response.ok:
                    if attempt < self._max_retries:
                        wait_time = self._backoff_factor * (2 ** (attempt - 1))
                        logger.warning(
                            "Авторизация неудачна (попытка %d/%d), повтор через %.1f сек",
                            attempt, self._max_retries, wait_time
                        )
                        time.sleep(wait_time)
                        continue
                    raise ApiError(
                        f"Авторизация отклонена (HTTP {response.status_code}): {response.text}"
                    )

                data = response.json()
                token = data.get("token") or data.get("access_token")
                if not token:
                    raise ApiAuthError("Сервер не вернул токен авторизации")

                self._token = str(token)
                logger.info("Авторизация успешна")
                return self._token
                
            except (RequestsConnectionError, Timeout) as exc:
                if attempt < self._max_retries:
                    wait_time = self._backoff_factor * (2 ** (attempt - 1))
                    logger.warning(
                        "Ошибка соединения (попытка %d/%d), повтор через %.1f сек: %s",
                        attempt, self._max_retries, wait_time, exc
                    )
                    time.sleep(wait_time)
                    continue
                logger.exception("Ошибка соединения при авторизации после %d попыток", self._max_retries)
                raise ApiConnectionError("Ошибка соединения с сервером") from exc
            except (ApiAuthError, ApiError):
                raise  # Пробрасываем без retry
            except RequestException as exc:
                logger.exception("Ошибка HTTP при авторизации")
                raise ApiError(f"Ошибка запроса авторизации: {exc}") from exc
        
        raise ApiError("Не удалось авторизоваться после всех попыток")

    def send_data(self, data: BaseModel) -> ApiResponse:
        """
        Отправляет данные разбраковки на сервер с повторными попытками.

        Args:
            data: Валидированная Pydantic-модель с данными разбраковки.

        Returns:
            ApiResponse с результатом операции.
        """
        try:
            payload = data.to_api_payload()
        except ValidationError as exc:
            raise ApiValidationError(str(exc)) from exc

        if not self._token:
            self.login()

        url = f"{self.base_url}/crystals/sorting"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        logger.info("Отправка данных: POST %s", url)
        logger.debug("Payload: %s", payload)

        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self._timeout,
                )
                
                if response.status_code in (401, 403):
                    logger.warning("Токен недействителен: HTTP %s", response.status_code)
                    # Повторная авторизация и один дополнительный retry
                    if attempt == 1:
                        logger.info("Попытка повторной авторизации")
                        self.login()
                        headers["Authorization"] = f"Bearer {self._token}"
                        continue
                    raise ApiAuthError("Ошибка авторизации. Токен недействителен.")

                if response.status_code == 422:
                    detail = self._extract_error_detail(response)
                    logger.warning("Ошибка валидации на сервере: %s", detail)
                    raise ApiValidationError(f"Ошибка валидации данных на сервере: {detail}")

                if not response.ok:
                    if attempt < self._max_retries and response.status_code >= 500:
                        wait_time = self._backoff_factor * (2 ** (attempt - 1))
                        logger.warning(
                            "Ошибка сервера (попытка %d/%d), повтор через %.1f сек",
                            attempt, self._max_retries, wait_time
                        )
                        time.sleep(wait_time)
                        continue
                    detail = self._extract_error_detail(response)
                    raise ApiError(f"Сервер вернул ошибку (HTTP {response.status_code}): {detail}")

                body: dict[str, Any] | None = None
                try:
                    body = response.json()
                except ValueError:
                    body = {"raw": response.text}

                message = "Данные успешно сохранены."
                if body and body.get("message"):
                    message = str(body["message"])

                logger.info("Данные успешно отправлены (HTTP %s)", response.status_code)
                return ApiResponse(
                    success=True,
                    message=message,
                    status_code=response.status_code,
                    payload=body,
                )
                
            except (RequestsConnectionError, Timeout) as exc:
                if attempt < self._max_retries:
                    wait_time = self._backoff_factor * (2 ** (attempt - 1))
                    logger.warning(
                        "Ошибка соединения (попытка %d/%d), повтор через %.1f сек: %s",
                        attempt, self._max_retries, wait_time, exc
                    )
                    time.sleep(wait_time)
                    continue
                logger.exception("Ошибка соединения при отправке данных после %d попыток", self._max_retries)
                raise ApiConnectionError("Ошибка соединения с сервером") from exc
            except (ApiAuthError, ApiValidationError, ApiError):
                raise  # Пробрасываем без retry
            except RequestException as exc:
                logger.exception("Ошибка HTTP при отправке данных")
                raise ApiError(f"Ошибка отправки данных: {exc}") from exc
        
        raise ApiError("Не удалось отправить данные после всех попыток")

    @staticmethod
    def _extract_error_detail(response: requests.Response) -> str:
        try:
            data = response.json()
            if isinstance(data, dict):
                if "detail" in data:
                    return str(data["detail"])
                if "message" in data:
                    return str(data["message"])
                if "errors" in data:
                    return str(data["errors"])
            return str(data)
        except ValueError:
            return response.text or "Неизвестная ошибка"
