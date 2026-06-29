"""Главное окно приложения."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QComboBox,
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
from config.settings import (
    clear_draft,
    get_settings,
    load_draft,
    load_hotkeys,
    load_last_file_path,
    load_plate_type_override,
    load_template,
    save_last_file_path,
    save_template,
    save_upload_entry,
)
from logs.setup import get_logger
from models.dynamic_crystal_data import create_dynamic_crystal_data_model
from parsers.base import ParserError
from parsers.registry import get_parser, supported_extensions
from ui.confirm_dialog import ConfirmDialog
from ui.dynamic_edit_form import DynamicEditFormWidget
from ui.loading_dialog import LoadingDialog
from ui.workers import UploadWorker

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Основное окно: выбор файла, редактирование, отправка."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SimpleMeasure — загрузка данных разбраковки")
        self.resize(540, 960)
        self.setMinimumSize(360, 640)
        self._resizing = False

        self._settings = get_settings()
        self._api_client = ApiClient(self._settings)
        self._current_file: str | None = None
        self._current_raw_data: dict | None = None  # Сырые данные для перестройки формы
        self._pending_data = None  # Может быть BaseModel или None
        self._upload_worker: UploadWorker | None = None
        self._loading_dialog: LoadingDialog | None = None
        # Очередь файлов для пакетной загрузки
        self._batch_queue: list[str] = []

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)
        self.setAcceptDrops(True)

        self._welcome_page = self._build_welcome_page()
        self._stack.addWidget(self._welcome_page)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Готово")

        # Индикатор статуса API справа в строке состояния
        from ui.api_status_widget import ApiStatusWidget
        self._api_status = ApiStatusWidget()
        self._status.addPermanentWidget(self._api_status)
        self._api_status.ping(self._settings)

        # Горячие клавиши
        self._shortcuts: list[QShortcut] = []
        self._register_shortcuts()

        logger.info("Приложение запущено")

        # Пробуем отправить офлайн-очередь в фоне
        self._try_flush_offline_queue()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._stack.currentWidget() is self._welcome_page:
            self._open_file_dialog(auto=True)

    def _build_welcome_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Верхняя панель с кнопками инструментов
        outer.addWidget(self._build_toolbar())

        # Центральная часть
        layout = QVBoxLayout()
        layout.addStretch()

        title = QLabel("Загрузка данных разбраковки кристаллов")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 700; color: #212121;")
        layout.addWidget(title)

        hint = QLabel(
            "Выберите файл XLSX, XLS, CSV или TXT для парсинга данных.\n"
            "После проверки данные будут отправлены на сервер через API."
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 13px; color: #666666;")
        layout.addWidget(hint)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        open_btn = QPushButton("📂 Выбрать файл...")
        open_btn.clicked.connect(lambda: self._open_file_dialog(auto=False))
        btn_layout.addWidget(open_btn)

        batch_btn = QPushButton("📂 Выбрать несколько файлов...")
        batch_btn.clicked.connect(self._open_batch_dialog)
        btn_layout.addWidget(batch_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        drop_hint = QLabel("или перетащите файл(ы) сюда")
        drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_hint.setStyleSheet("font-size: 12px; color: #aaaaaa; padding-top: 4px;")
        layout.addWidget(drop_hint)

        layout.addStretch()
        outer.addLayout(layout)
        page.setStyleSheet("background: transparent;")
        return page

    def _build_toolbar(self) -> QWidget:
        """Верхняя панель с кнопками: API-настройки, история, лог."""
        bar = QWidget()
        bar.setObjectName("AppToolBar")
        bar.setStyleSheet(
            "QWidget#AppToolBar { background: palette(button); border-bottom: 1px solid palette(mid); }"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(6)
        row.addStretch()

        api_btn = QPushButton("⚙ API")
        api_btn.setToolTip("Настройки подключения к API")
        api_btn.clicked.connect(self._open_api_settings)
        row.addWidget(api_btn)

        hist_btn = QPushButton("📋 История")
        hist_btn.setToolTip("История загрузок")
        hist_btn.clicked.connect(self._open_history)
        row.addWidget(hist_btn)

        log_btn = QPushButton("📄 Лог")
        log_btn.setToolTip("Просмотр лога приложения")
        log_btn.clicked.connect(self._open_log_viewer)
        row.addWidget(log_btn)

        theme_btn = QPushButton("🌙")
        theme_btn.setToolTip("Переключить тёмную / светлую тему")
        theme_btn.setFixedWidth(36)
        theme_btn.clicked.connect(self._toggle_theme)
        row.addWidget(theme_btn)

        return bar

    def _toggle_theme(self) -> None:
        from ui.theme import toggle_theme
        app = self.__class__.__bases__  # не используем напрямую
        from PyQt6.QtWidgets import QApplication
        dark = toggle_theme(QApplication.instance())
        self._status.showMessage("Тёмная тема" if dark else "Светлая тема", 3000)

    def _file_filter(self) -> str:
        exts = supported_extensions()
        patterns = " ".join(f"*{ext}" for ext in exts)
        return f"Поддерживаемые файлы ({patterns});;{patterns};;Все файлы (*.*)"

    def _last_dir(self) -> str:
        last_file = load_last_file_path()
        return str(Path(last_file).parent) if last_file else ""

    def _open_file_dialog(self, auto: bool = False) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбор файла данных",
            self._last_dir(),
            self._file_filter(),
        )

        if not file_path:
            if auto:
                logger.info("Файл не выбран при автоматическом диалоге")
            return

        self._load_file(file_path)

    def _open_batch_dialog(self) -> None:
        """Выбор нескольких файлов для последовательной загрузки."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выбор нескольких файлов",
            self._last_dir(),
            self._file_filter(),
        )
        if not file_paths:
            return

        if len(file_paths) == 1:
            self._load_file(file_paths[0])
            return

        # Кладём остаток в очередь, первый — открываем сразу
        self._batch_queue = list(file_paths[1:])
        self._load_file(file_paths[0])
        logger.info("Пакетная загрузка: %d файлов в очереди", len(self._batch_queue))

    def _load_file(self, file_path: str, skip_preview: bool = False) -> None:
        logger.info("Выбран файл: %s", file_path)

        # Предпросмотр (если не пропущен и включён в настройках)
        if not skip_preview and self._preview_enabled():
            from ui.file_preview_dialog import FilePreviewDialog
            dlg = FilePreviewDialog(file_path, self)
            if dlg.exec() != FilePreviewDialog.DialogCode.Accepted:
                logger.info("Пользователь отменил загрузку на этапе предпросмотра")
                return

        file_size = Path(file_path).stat().st_size

        # Показываем прогресс-бар для файлов больше 1 MB
        if file_size > 1024 * 1024:
            self._loading_dialog = LoadingDialog(f"Загрузка файла...\n{Path(file_path).name}", self)
            self._loading_dialog.show()

        self._status.showMessage(f"Парсинг: {Path(file_path).name}")

        try:
            parser = get_parser(file_path)
            raw_data = parser.parse(file_path)
        except ParserError as exc:
            logger.error("Ошибка парсинга: %s", exc)
            self._close_loading()
            QMessageBox.critical(self, "Ошибка парсинга", str(exc))
            self._status.showMessage("Ошибка парсинга")
            return
        except Exception as exc:
            logger.exception("Непредвиденная ошибка парсинга")
            self._close_loading()
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Непредвиденная ошибка при чтении файла:\n{exc}",
            )
            self._status.showMessage("Ошибка")
            return
        finally:
            self._close_loading()

        # Создаём динамическую модель на основе распарсенных данных
        try:
            DynamicModel = create_dynamic_crystal_data_model(raw_data)
            data = DynamicModel.model_validate(raw_data)
        except Exception as exc:
            logger.exception("Ошибка валидации данных")
            QMessageBox.critical(
                self,
                "Ошибка валидации",
                f"Не удалось валидировать данные из файла:\n{exc}",
            )
            self._status.showMessage("Ошибка валидации")
            return

        save_last_file_path(file_path)
        self._current_file = file_path
        self._current_raw_data = raw_data  # Сохраняем для перестройки при смене типа пластины
        self._show_edit_form(data)
        self._status.showMessage(f"Файл загружен: {Path(file_path).name}")

    def _show_edit_form(
        self,
        data,
        plate_type_override: str | None = None,
        skip_draft_restore: bool = False,
    ) -> None:
        while self._stack.count() > 1:
            widget = self._stack.widget(1)
            self._stack.removeWidget(widget)
            widget.deleteLater()

        form = DynamicEditFormWidget(
            data,
            file_path=self._current_file,
            plate_type_override=plate_type_override,
        )
        form.submit_button.clicked.connect(self._on_submit_clicked)

        # Если пришли из «Отправить снова» — подставляем маркировку из истории
        resend_marking = getattr(self, "_resend_plate_marking", None)
        if resend_marking:
            form.apply_template({"plate_marking": resend_marking})
            self._resend_plate_marking = None

        # Предлагаем восстановить черновик, если он есть (пропускаем при перестройке формы)
        draft_applied = False
        if not skip_draft_restore and self._current_file:
            draft = load_draft(self._current_file)
            if draft:
                reply = QMessageBox.question(
                    self,
                    "Восстановить черновик?",
                    "Найден несохранённый черновик для этого файла.\n"
                    "Восстановить введённые ранее значения?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    form.apply_template(draft)
                    draft_applied = True

        # Применяем шаблон, если черновик не восстанавливался
        if not draft_applied:
            try:
                template = load_template()
                if template:
                    form.apply_template(template)
            except Exception as exc:
                logger.warning("Не удалось применить шаблон: %s", exc)

        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Верхняя панель инструментов (та же, что на стартовом экране)
        layout.addWidget(self._build_toolbar())

        # Строка с именем файла и кнопками
        header_widget = QWidget()
        header = QHBoxLayout(header_widget)
        header.setContentsMargins(8, 4, 8, 4)
        file_label = QLabel(f"📄 {Path(self._current_file).name}" if self._current_file else "")
        file_label.setWordWrap(True)
        header.addWidget(file_label, stretch=1)

        # Быстрое переключение типа пластины
        header.addWidget(QLabel("Тип:"))
        plate_combo = QComboBox()
        plate_combo.addItems(["Авто", "Цифровая", "Аналоговая"])
        plate_combo.setToolTip(
            "Переключить набор полей для цифровой или аналоговой пластины.\n"
            "«Авто» — определяется по содержимому файла.\n"
            "Значение по умолчанию задаётся в Настройках."
        )
        # Выбираем текущий вариант
        current_override = plate_type_override if plate_type_override is not None \
            else load_plate_type_override()
        if current_override == "digital":
            plate_combo.setCurrentIndex(1)
        elif current_override == "analog":
            plate_combo.setCurrentIndex(2)
        else:
            plate_combo.setCurrentIndex(0)
        plate_combo.currentIndexChanged.connect(
            lambda idx: self._on_plate_type_combo_changed(idx)
        )
        header.addWidget(plate_combo)
        self._plate_combo = plate_combo  # сохраняем ссылку

        fields_btn = QPushButton("⚙️ Поля")
        fields_btn.setToolTip("Редактор конфигурации полей")
        fields_btn.clicked.connect(self._open_fields_editor)
        header.addWidget(fields_btn)

        reopen_btn = QPushButton("📂 Другой файл")
        reopen_btn.clicked.connect(lambda: self._open_file_dialog(auto=False))
        header.addWidget(reopen_btn)

        if self._batch_queue:
            batch_info = QLabel(f"В очереди: {len(self._batch_queue)} файл(ов)")
            batch_info.setStyleSheet("color: #1565c0; font-weight: bold;")
            header.addWidget(batch_info)

        layout.addWidget(header_widget)
        layout.addWidget(form)
        self._stack.addWidget(wrapper)
        self._stack.setCurrentWidget(wrapper)
        self._edit_form = form

    def _on_plate_type_combo_changed(self, index: int) -> None:
        """Перестраивает форму с новым типом пластины без перечитывания файла."""
        if self._current_raw_data is None:
            return
        override_map = {0: None, 1: "digital", 2: "analog"}
        plate_type_override = override_map.get(index)

        try:
            DynamicModel = create_dynamic_crystal_data_model(self._current_raw_data)
            data = DynamicModel.model_validate(self._current_raw_data)
        except Exception as exc:
            logger.exception("Ошибка перестройки формы для типа пластины: %s", exc)
            return

        self._show_edit_form(data, plate_type_override=plate_type_override, skip_draft_restore=True)
        label = {None: "авто", "digital": "цифровая", "analog": "аналоговая"}.get(plate_type_override, "")
        self._status.showMessage(f"Тип пластины: {label}", 3000)

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

    def _try_flush_offline_queue(self) -> None:
        """Фоновая попытка отправить накопленные офлайн-данные."""
        from ui.offline_queue import flush_queue, queue_size
        if queue_size() == 0:
            return
        if not self._settings.is_configured:
            return
        try:
            sent, failed = flush_queue(self._api_client)
            if sent:
                self._status.showMessage(
                    f"Офлайн-очередь: отправлено {sent} записей"
                    + (f", осталось {failed}" if failed else ""),
                    6000,
                )
                logger.info("Офлайн-очередь: отправлено %d, осталось %d", sent, failed)
        except Exception as exc:
            logger.warning("Ошибка при сбросе офлайн-очереди: %s", exc)

    def _register_shortcuts(self) -> None:
        """Создаёт QShortcut из текущих настроек горячих клавиш."""
        for sc in self._shortcuts:
            sc.setEnabled(False)
        self._shortcuts.clear()

        hk = load_hotkeys()
        bindings = {
            "open_file":     lambda: self._open_file_dialog(auto=False),
            "open_batch":    self._open_batch_dialog,
            "submit":        self._on_submit_clicked,
            "api_settings":  self._open_api_settings,
            "history":       self._open_history,
            "log":           self._open_log_viewer,
            "fields_editor": self._open_fields_editor,
        }
        for action, seq_str in hk.items():
            if not seq_str or action not in bindings:
                continue
            sc = QShortcut(QKeySequence(seq_str), self)
            sc.activated.connect(bindings[action])
            self._shortcuts.append(sc)

    def _preview_enabled(self) -> bool:
        """Возвращает True если предпросмотр файла включён в настройках."""
        from config.settings import _load_state
        return _load_state().get("show_file_preview", True)

    def _open_fields_editor(self) -> None:
        from ui.fields_editor import FieldsEditorWindow
        editor = FieldsEditorWindow(self)
        editor.exec()
        logger.info("Редактор полей закрыт")

    def _open_api_settings(self) -> None:
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self)
        if dlg.exec():
            from config.settings import get_settings, reset_settings_cache
            reset_settings_cache()
            self._settings = get_settings()
            self._api_client = ApiClient(self._settings)
            self._api_status.ping(self._settings)
            self._register_shortcuts()
            logger.info("API-клиент пересоздан с новыми настройками")

    def _open_history(self) -> None:
        from ui.history_dialog import HistoryDialog
        dlg = HistoryDialog(self)
        if dlg.exec() == HistoryDialog.DialogCode.Accepted and dlg.resend_requested:
            file_path, plate_marking = dlg.resend_requested
            logger.info("Повторная отправка из истории: %s (маркировка: %s)", file_path, plate_marking)
            # Загружаем файл без предпросмотра (пользователь уже видел его раньше)
            self._resend_plate_marking = plate_marking
            self._load_file(file_path, skip_preview=True)

    def _open_log_viewer(self) -> None:
        from ui.log_viewer import LogViewerDialog
        LogViewerDialog(self).exec()

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

    def resizeEvent(self, event) -> None:
        if getattr(self, "_resizing", False):
            super().resizeEvent(event)
            return

        self._resizing = True
        new_size = event.size()
        target_height = int(new_size.width() * 16 / 9)
        target_width = int(new_size.height() * 9 / 16)
        if abs(target_height - new_size.height()) < abs(target_width - new_size.width()):
            self.resize(new_size.width(), target_height)
        else:
            self.resize(target_width, new_size.height())
        self._resizing = False
        super().resizeEvent(event)

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

        # Сохраняем запись в историю
        if self._pending_data is not None:
            plate_marking = getattr(self._pending_data, "plate_marking", "")
            save_upload_entry(
                file_path=self._current_file or "",
                plate_marking=str(plate_marking),
                status="ok",
                message=response.message,
            )
            # Сохраняем редактируемые поля как шаблон для следующего файла
            try:
                if hasattr(self, "_edit_form"):
                    template_vals = self._edit_form.collect_editable_values()
                    if template_vals:
                        save_template(template_vals)
            except Exception as exc:
                logger.warning("Не удалось сохранить шаблон: %s", exc)

        # Очищаем черновик — данные успешно отправлены
        if self._current_file:
            try:
                clear_draft(self._current_file)
            except Exception:
                pass

        QMessageBox.information(self, "Успех", response.message)
        self._pending_data = None

        # Если есть очередь файлов — переходим к следующему
        if self._batch_queue:
            next_file = self._batch_queue.pop(0)
            logger.info("Пакетная загрузка: следующий файл %s", next_file)
            self._load_file(next_file)

    def _on_upload_error(self, message: str) -> None:
        self._close_loading()
        if hasattr(self, "_edit_form"):
            self._edit_form.submit_button.setEnabled(True)

        logger.error("Ошибка отправки: %s", message)
        self._status.showMessage("Ошибка отправки")

        # Сохраняем ошибку в историю
        if self._current_file:
            plate_marking = ""
            if self._pending_data is not None:
                plate_marking = str(getattr(self._pending_data, "plate_marking", ""))
            save_upload_entry(
                file_path=self._current_file,
                plate_marking=plate_marking,
                status="error",
                message=message,
            )

        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Ошибка отправки")
        msg_box.setText(message)

        retry_btn = msg_box.addButton("Повторить", QMessageBox.ButtonRole.AcceptRole)
        queue_btn = msg_box.addButton("📥 В очередь", QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton("Закрыть", QMessageBox.ButtonRole.RejectRole)
        msg_box.exec()

        clicked = msg_box.clickedButton()
        if clicked == retry_btn:
            logger.info("Пользователь запросил повторную отправку")
            self._start_upload()
        elif clicked == queue_btn and self._pending_data is not None:
            from ui.offline_queue import enqueue
            enqueue(self._pending_data.model_dump(), self._current_file or "")
            self._pending_data = None
            self._status.showMessage("Данные сохранены в офлайн-очередь")
            logger.info("Данные добавлены в офлайн-очередь")

    # ── Drag & Drop ────────────────────────────────────────────

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            exts = supported_extensions()
            if any(Path(u.toLocalFile()).suffix.lower() in exts for u in urls):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        exts = supported_extensions()
        files = [
            u.toLocalFile()
            for u in urls
            if Path(u.toLocalFile()).suffix.lower() in exts
        ]
        if not files:
            return
        if len(files) == 1:
            self._load_file(files[0])
        else:
            self._batch_queue = files[1:]
            self._load_file(files[0])
            logger.info("Drag & Drop: %d файлов, %d в очереди", len(files), len(self._batch_queue))

    # ── Закрытие ───────────────────────────────────────────────

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
