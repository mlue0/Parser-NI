"""Главное окно приложения."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from api.client import ApiClient
from config.settings import get_settings, load_last_file_path, save_last_file_path
from logs.setup import get_logger
from models.crystal_data import CrystalData
from parsers.base import ParserError
from parsers.registry import get_parser, supported_extensions
from ui.confirm_dialog import ConfirmDialog
from ui.edit_form import EditFormWidget
from ui.loading_dialog import LoadingDialog
from ui.workers import UploadWorker

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Основное окно: выбор файла, редактирование, отправка."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SimpleMeasure — загрузка данных разбраковки")
        self.resize(720, 640)

        self._settings = get_settings()
        self._api_client = ApiClient(self._settings)
        self._current_file: str | None = None
        self._pending_data: CrystalData | None = None
        self._upload_worker: UploadWorker | None = None
        self._loading_dialog: LoadingDialog | None = None

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._welcome_page = self._build_welcome_page()
        self._stack.addWidget(self._welcome_page)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Готово")

        logger.info("Приложение запущено")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._stack.currentWidget() is self._welcome_page:
            self._open_file_dialog(auto=True)

    def _build_welcome_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()

        title = QLabel("Загрузка данных разбраковки кристаллов")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        hint = QLabel(
            "Выберите файл XLSX, XLS, CSV или TXT для парсинга данных.\n"
            "После проверки данные будут отправлены на сервер через API."
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        open_btn = QPushButton("Выбрать файл...")
        open_btn.clicked.connect(lambda: self._open_file_dialog(auto=False))
        btn_layout.addWidget(open_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        return page

    def _file_filter(self) -> str:
        exts = supported_extensions()
        patterns = " ".join(f"*{ext}" for ext in exts)
        return f"Поддерживаемые файлы ({patterns});;{patterns};;Все файлы (*.*)"

    def _open_file_dialog(self, auto: bool = False) -> None:
        last_dir = ""
        last_file = load_last_file_path()
        if last_file:
            last_dir = str(Path(last_file).parent)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбор файла данных",
            last_dir,
            self._file_filter(),
        )

        if not file_path:
            if auto:
                logger.info("Файл не выбран при автоматическом диалоге")
            return

        self._load_file(file_path)

    def _load_file(self, file_path: str) -> None:
        logger.info("Выбран файл: %s", file_path)
        self._status.showMessage(f"Парсинг: {Path(file_path).name}")

        try:
            parser = get_parser(file_path)
            data = parser.parse(file_path)
        except ParserError as exc:
            logger.error("Ошибка парсинга: %s", exc)
            QMessageBox.critical(self, "Ошибка парсинга", str(exc))
            self._status.showMessage("Ошибка парсинга")
            return
        except Exception as exc:
            logger.exception("Непредвиденная ошибка парсинга")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Непредвиденная ошибка при чтении файла:\n{exc}",
            )
            self._status.showMessage("Ошибка")
            return

        save_last_file_path(file_path)
        self._current_file = file_path
        self._show_edit_form(data)
        self._status.showMessage(f"Файл загружен: {Path(file_path).name}")

    def _show_edit_form(self, data: CrystalData) -> None:
        while self._stack.count() > 1:
            widget = self._stack.widget(1)
            self._stack.removeWidget(widget)
            widget.deleteLater()

        form = EditFormWidget(data)
        form.submit_button.clicked.connect(self._on_submit_clicked)

        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)

        header = QHBoxLayout()
        file_label = QLabel(f"Файл: {self._current_file or ''}")
        file_label.setWordWrap(True)
        header.addWidget(file_label, stretch=1)

        reopen_btn = QPushButton("Открыть другой файл")
        reopen_btn.clicked.connect(lambda: self._open_file_dialog(auto=False))
        header.addWidget(reopen_btn)
        layout.addLayout(header)

        layout.addWidget(form)
        self._stack.addWidget(wrapper)
        self._stack.setCurrentWidget(wrapper)
        self._edit_form = form

    def _on_submit_clicked(self) -> None:
        if not hasattr(self, "_edit_form"):
            return

        data = self._edit_form.collect_data()
        if data is None:
            self._edit_form.highlight_invalid_fields()
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "Заполните все обязательные поля корректными значениями.",
            )
            return

        dialog = ConfirmDialog(data, self)
        if dialog.exec() != ConfirmDialog.DialogCode.Accepted:
            logger.info("Пользователь отменил отправку на этапе подтверждения")
            return

        self._pending_data = data
        self._start_upload()

    def _start_upload(self) -> None:
        if self._pending_data is None:
            return

        if not self._settings.is_configured:
            QMessageBox.warning(
                self,
                "Настройки API",
                "Заполните файл .env (API_URL и учётные данные или API_TOKEN).",
            )
            return

        self._loading_dialog = LoadingDialog("Отправка данных на сервер...", self)
        self._loading_dialog.show()

        self._upload_worker = UploadWorker(self._api_client, self._pending_data, self)
        self._upload_worker.finished_ok.connect(self._on_upload_success)
        self._upload_worker.finished_error.connect(self._on_upload_error)
        self._upload_worker.start()

        if hasattr(self, "_edit_form"):
            self._edit_form.submit_button.setEnabled(False)
        self._status.showMessage("Отправка данных...")

    def _close_loading(self) -> None:
        if self._loading_dialog:
            self._loading_dialog.close()
            self._loading_dialog = None

    def _on_upload_success(self, response) -> None:
        self._close_loading()
        if hasattr(self, "_edit_form"):
            self._edit_form.submit_button.setEnabled(True)

        logger.info("Отправка успешна: %s", response.message)
        self._status.showMessage(response.message)

        QMessageBox.information(self, "Успех", response.message)
        self._pending_data = None

    def _on_upload_error(self, message: str) -> None:
        self._close_loading()
        if hasattr(self, "_edit_form"):
            self._edit_form.submit_button.setEnabled(True)

        logger.error("Ошибка отправки: %s", message)
        self._status.showMessage("Ошибка отправки")

        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Ошибка отправки")
        msg_box.setText(message)

        retry_btn = msg_box.addButton("Повторить", QMessageBox.ButtonRole.AcceptRole)
        msg_box.addButton("Закрыть", QMessageBox.ButtonRole.RejectRole)
        msg_box.exec()

        if msg_box.clickedButton() == retry_btn:
            logger.info("Пользователь запросил повторную отправку")
            self._start_upload()

    def closeEvent(self, event) -> None:
        if self._upload_worker and self._upload_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Выход",
                "Идёт отправка данных. Завершить приложение?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._upload_worker.terminate()
            self._upload_worker.wait(3000)
        logger.info("Приложение закрыто")
        super().closeEvent(event)
