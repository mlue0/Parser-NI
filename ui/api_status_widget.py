"""Виджет-индикатор статуса соединения с API для строки состояния."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from logs.setup import get_logger

logger = get_logger(__name__)


class _PingWorker(QThread):
    """Фоновый поток: проверяет доступность API."""
    result = pyqtSignal(bool, str)  # (ok, message)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings

    def run(self) -> None:
        try:
            from api.client import ApiClient
            from api.exceptions import ApiError
            client = ApiClient(self._settings, timeout=5.0, max_retries=1)
            client.login()
            self.result.emit(True, self._settings.api_url)
        except Exception as exc:
            self.result.emit(False, str(exc))


class ApiStatusWidget(QWidget):
    """Компактный индикатор 🟢/🔴 + URL для статус-бара."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(4)

        self._dot = QLabel("⚪")
        self._dot.setToolTip("Статус API")
        layout.addWidget(self._dot)

        self._url_label = QLabel("—")
        self._url_label.setStyleSheet("font-size: 11px; color: #666;")
        layout.addWidget(self._url_label)

        self._worker: _PingWorker | None = None

    def ping(self, settings) -> None:
        """Запускает фоновую проверку соединения."""
        if self._worker and self._worker.isRunning():
            return
        url = settings.api_url
        self._url_label.setText(url or "—")
        self._dot.setText("⏳")
        self._worker = _PingWorker(settings, self)
        self._worker.result.connect(self._on_result)
        self._worker.start()

    def _on_result(self, ok: bool, message: str) -> None:
        if ok:
            self._dot.setText("🟢")
            self._dot.setToolTip(f"API доступен: {message}")
        else:
            self._dot.setText("🔴")
            self._dot.setToolTip(f"API недоступен: {message}")
        logger.debug("API ping: ok=%s %s", ok, message)

    def set_unknown(self) -> None:
        self._dot.setText("⚪")
        self._dot.setToolTip("Статус неизвестен")
