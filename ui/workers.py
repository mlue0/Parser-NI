"""Фоновый поток отправки данных в API."""

from __future__ import annotations

from pydantic import BaseModel
from PyQt6.QtCore import QThread, pyqtSignal

from api.client import ApiClient, ApiResponse
from api.exceptions import ApiError
from logs.setup import get_logger

logger = get_logger(__name__)


class UploadWorker(QThread):
    """Выполняет login + отправку данных в отдельном потоке.

    mode="sorting" → send_data (разбраковка); mode="plate" → send_plate (новая пластина).
    """

    finished_ok = pyqtSignal(object)
    finished_error = pyqtSignal(str)

    def __init__(
        self,
        client: ApiClient,
        data: BaseModel,
        parent=None,
        mode: str = "sorting",
    ) -> None:
        super().__init__(parent)
        self._client = client
        self._data = data
        self._mode = mode

    def run(self) -> None:
        try:
            logger.info("Начало отправки данных в API (режим=%s)", self._mode)
            if self._mode == "plate":
                response: ApiResponse = self._client.send_plate(self._data)
            else:
                response = self._client.send_data(self._data)
            self.finished_ok.emit(response)
        except ApiError as exc:
            logger.error("Ошибка API: %s", exc)
            self.finished_error.emit(str(exc))
        except Exception as exc:
            logger.exception("Непредвиденная ошибка при отправке")
            self.finished_error.emit(f"Непредвиденная ошибка: {exc}")


class FlushQueueWorker(QThread):
    """Фоновый сброс офлайн-очереди (login + send_data по каждой записи)."""

    finished_flush = pyqtSignal(int, int)  # (sent, failed)

    def __init__(self, client: ApiClient, parent=None) -> None:
        super().__init__(parent)
        self._client = client

    def run(self) -> None:
        try:
            from ui.offline_queue import flush_queue
            sent, failed = flush_queue(self._client)
            self.finished_flush.emit(sent, failed)
        except Exception as exc:
            logger.warning("Ошибка при сбросе офлайн-очереди: %s", exc)
            self.finished_flush.emit(0, -1)
