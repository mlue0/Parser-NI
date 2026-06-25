"""Фоновый поток отправки данных в API."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from api.client import ApiClient, ApiResponse
from api.exceptions import ApiError
from logs.setup import get_logger
from models.crystal_data import CrystalData

logger = get_logger(__name__)


class UploadWorker(QThread):
    """Выполняет login + send_data в отдельном потоке."""

    finished_ok = pyqtSignal(object)
    finished_error = pyqtSignal(str)

    def __init__(self, client: ApiClient, data: CrystalData, parent=None) -> None:
        super().__init__(parent)
        self._client = client
        self._data = data

    def run(self) -> None:
        try:
            logger.info("Начало отправки данных в API")
            response: ApiResponse = self._client.send_data(self._data)
            self.finished_ok.emit(response)
        except ApiError as exc:
            logger.error("Ошибка API: %s", exc)
            self.finished_error.emit(str(exc))
        except Exception as exc:
            logger.exception("Непредвиденная ошибка при отправке")
            self.finished_error.emit(f"Непредвиденная ошибка: {exc}")
