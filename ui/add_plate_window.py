"""Окно режима «Добавить пластину»: форма метаданных пластины + занесение в базу."""

from __future__ import annotations

from pydantic import ValidationError
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from api.client import ApiClient
from config.settings import get_settings, save_upload_entry
from logs.setup import get_logger
from models.crystal_data import PLATE_MARKINGS, SORTING_TARGETS, SORTING_TYPES
from models.plate_data import PlateData
from ui.confirm_dialog import ConfirmDialog
from ui.loading_dialog import LoadingDialog
from ui.workers import UploadWorker

logger = get_logger(__name__)


class AddPlateWindow(QMainWindow):
    """Форма добавления новой пластины в базу."""

    def __init__(self, parent=None, on_back=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("SimpleMeasure — добавление пластины")
        self.resize(520, 640)
        self.setMinimumSize(420, 560)

        self._on_back = on_back  # колбэк возврата на экран выбора режима
        self._settings = get_settings()
        self._api_client = ApiClient(self._settings)
        self._pending_data: PlateData | None = None
        self._loading_dialog: LoadingDialog | None = None
        self._upload_worker: UploadWorker | None = None

        self._build_ui()

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Готово")
        logger.info("Открыт режим «Добавить пластину»")

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        if self._on_back is not None:
            top = QHBoxLayout()
            back_btn = QPushButton("← Назад")
            back_btn.setToolTip("Вернуться к выбору режима")
            back_btn.clicked.connect(self._go_back)
            top.addWidget(back_btn)
            top.addStretch()
            root.addLayout(top)

        title = QLabel("Добавление пластины")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        root.addWidget(title)

        form = QFormLayout()
        form.setVerticalSpacing(10)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        # 1. Маркировка пластины (с подсказками-вариантами)
        self._plate_marking = QComboBox()
        self._plate_marking.setEditable(True)
        self._plate_marking.addItems(list(PLATE_MARKINGS))
        self._plate_marking.setCurrentText("")
        form.addRow("Маркировка пластины:", self._plate_marking)

        # 2. Номер зашивки
        self._firmware = QLineEdit()
        form.addRow("Номер зашивки:", self._firmware)

        # 3. Номер коррекции
        self._correction = QLineEdit()
        form.addRow("Номер коррекции:", self._correction)

        # 4. Цель разбраковки (по умолчанию ПР-ОВ, редактируемо)
        self._sorting_target = QComboBox()
        self._sorting_target.addItems(list(SORTING_TARGETS))
        self._sorting_target.setCurrentText("ПР-ОВ")
        form.addRow("Цель разбраковки:", self._sorting_target)

        # 5. Номер партии БМК (обязательное)
        self._bmk = QLineEdit()
        self._bmk.setPlaceholderText("Обязательное поле")
        form.addRow("Номер партии БМК:", self._bmk)

        # 6. Номер пластины (обязательное)
        self._plate_number = QLineEdit()
        self._plate_number.setPlaceholderText("Обязательное поле")
        form.addRow("Номер пластины:", self._plate_number)

        # 7. Исходное количество кристаллов
        self._initial = QSpinBox()
        self._initial.setRange(0, 10_000_000)
        form.addRow("Исходное количество кристаллов:", self._initial)

        # 8. Тип разбраковки (по умолчанию «Разбраковка NI», редактируемо)
        self._sorting_type = QComboBox()
        self._sorting_type.setEditable(True)
        self._sorting_type.addItems(list(SORTING_TYPES))
        self._sorting_type.setCurrentText("Разбраковка NI")
        form.addRow("Тип разбраковки:", self._sorting_type)

        # 9. Комментарий
        self._comment = QPlainTextEdit()
        self._comment.setFixedHeight(80)
        form.addRow("Комментарий:", self._comment)

        root.addLayout(form)

        self._error_label = QLabel("")
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(
            "color: #b00020; background: #fff0f0;"
            "border: 1px solid rgba(176, 0, 32, 0.2); border-radius: 8px; padding: 8px;"
        )
        self._error_label.setVisible(False)
        root.addWidget(self._error_label)

        root.addStretch()

        self._submit_btn = QPushButton("Занести в базу")
        self._submit_btn.setMinimumHeight(40)
        self._submit_btn.clicked.connect(self._on_submit)
        root.addWidget(self._submit_btn)

    # ── Сбор и валидация ──────────────────────────────────────────────────

    def _collect(self) -> PlateData | None:
        self._error_label.setVisible(False)
        raw = {
            "plate_marking": self._plate_marking.currentText().strip(),
            "firmware_number": self._firmware.text().strip(),
            "correction_number": self._correction.text().strip(),
            "sorting_target": self._sorting_target.currentText().strip(),
            "bmk_batch_number": self._bmk.text().strip(),
            "plate_number": self._plate_number.text().strip(),
            "initial_crystals": self._initial.value(),
            "sorting_type": self._sorting_type.currentText().strip(),
            "comment": self._comment.toPlainText().strip(),
        }
        try:
            return PlateData.model_validate(raw)
        except ValidationError as exc:
            messages = []
            for error in exc.errors():
                loc = error.get("loc", ())
                key = str(loc[0]) if loc else "поле"
                from models.plate_data import PLATE_FIELD_LABELS
                label = PLATE_FIELD_LABELS.get(key, key)
                messages.append(f"{label}: {error.get('msg', 'ошибка')}")
            self._error_label.setText("\n".join(messages))
            self._error_label.setVisible(True)
            logger.warning("Ошибка валидации формы пластины: %s", messages)
            return None

    # ── Отправка ──────────────────────────────────────────────────────────

    def _on_submit(self) -> None:
        data = self._collect()
        if data is None:
            QMessageBox.warning(
                self,
                "Проверьте данные",
                "Заполните обязательные поля (маркировка, номер партии БМК, номер пластины).",
            )
            return

        if not self._settings.is_configured:
            QMessageBox.warning(
                self,
                "Настройки API",
                "Заполните настройки API (URL и учётные данные или токен), чтобы заносить данные в базу.",
            )
            return

        dialog = ConfirmDialog(data, self)
        if dialog.exec() != ConfirmDialog.DialogCode.Accepted:
            logger.info("Добавление пластины отменено пользователем")
            return

        self._pending_data = data
        self._submit_btn.setEnabled(False)
        self._loading_dialog = LoadingDialog("Занесение пластины в базу...", self)
        self._loading_dialog.show()

        self._upload_worker = UploadWorker(self._api_client, data, self, mode="plate")
        self._upload_worker.finished_ok.connect(self._on_success)
        self._upload_worker.finished_error.connect(self._on_error)
        self._upload_worker.start()
        self._status.showMessage("Отправка данных...")

    def _close_loading(self) -> None:
        if self._loading_dialog:
            self._loading_dialog.close()
            self._loading_dialog = None

    def _on_success(self, response) -> None:
        self._close_loading()
        self._submit_btn.setEnabled(True)
        marking = self._pending_data.plate_marking if self._pending_data else ""
        save_upload_entry(
            file_path="(добавление пластины)",
            plate_marking=str(marking),
            status="ok",
            message=response.message,
        )
        self._status.showMessage(response.message, 5000)
        logger.info("Пластина добавлена: %s", marking)
        QMessageBox.information(self, "Готово", response.message)
        self._pending_data = None
        self._clear_form()

    def _on_error(self, message: str) -> None:
        self._close_loading()
        self._submit_btn.setEnabled(True)
        marking = self._pending_data.plate_marking if self._pending_data else ""
        save_upload_entry(
            file_path="(добавление пластины)",
            plate_marking=str(marking),
            status="error",
            message=message,
        )
        self._status.showMessage("Ошибка отправки", 5000)
        logger.error("Ошибка добавления пластины: %s", message)

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Ошибка отправки")
        box.setText(message)
        retry_btn = box.addButton("Повторить", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Закрыть", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() == retry_btn and self._pending_data is not None:
            self._resubmit()

    def _resubmit(self) -> None:
        if self._pending_data is None:
            return
        self._submit_btn.setEnabled(False)
        self._loading_dialog = LoadingDialog("Занесение пластины в базу...", self)
        self._loading_dialog.show()
        self._upload_worker = UploadWorker(self._api_client, self._pending_data, self, mode="plate")
        self._upload_worker.finished_ok.connect(self._on_success)
        self._upload_worker.finished_error.connect(self._on_error)
        self._upload_worker.start()

    def _go_back(self) -> None:
        """Возврат на экран выбора режима."""
        from ui.launcher import navigate_back
        navigate_back(self, self._on_back)

    def _clear_form(self) -> None:
        self._plate_marking.setCurrentText("")
        self._firmware.clear()
        self._correction.clear()
        self._sorting_target.setCurrentText("ПР-ОВ")
        self._bmk.clear()
        self._plate_number.clear()
        self._initial.setValue(0)
        self._sorting_type.setCurrentText("Разбраковка NI")
        self._comment.clear()

    def closeEvent(self, event) -> None:
        if self._upload_worker and self._upload_worker.isRunning():
            try:
                self._upload_worker.finished_ok.disconnect()
                self._upload_worker.finished_error.disconnect()
            except (TypeError, RuntimeError):
                pass
            self._upload_worker.wait(3000)
        super().closeEvent(event)
