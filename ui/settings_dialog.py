"""Диалог настроек: API, горячие клавиши, предпросмотр."""

from __future__ import annotations

from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config.credentials import (
    get_login,
    get_password,
    get_token,
    save_credentials,
    save_token,
)
from config.settings import (
    DEFAULT_HOTKEYS,
    ENV_PATH,
    _load_state,
    _save_state,
    get_settings,
    load_hotkeys,
    load_plate_type_override,
    reset_settings_cache,
    save_hotkeys,
    save_plate_type_override,
)
from logs.setup import get_logger

logger = get_logger(__name__)

_HOTKEY_LABELS: dict[str, str] = {
    "open_file": "Открыть файл",
    "open_batch": "Открыть несколько файлов",
    "submit": "Подтвердить и отправить",
    "api_settings": "Настройки API",
    "history": "История загрузок",
    "log": "Просмотр лога",
    "fields_editor": "Редактор полей",
}


class SettingsDialog(QDialog):
    """Диалог настроек: API, горячие клавиши, прочее."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(520)
        self._build_ui()
        self._load_current_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_api_tab(), "🔌 API")
        self._tabs.addTab(self._build_hotkeys_tab(), "⌨ Горячие клавиши")
        self._tabs.addTab(self._build_misc_tab(), "⚙ Прочее")
        layout.addWidget(self._tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("💾 Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── Вкладка API ──────────────────────────────────────────

    def _build_api_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        url_group = QGroupBox("Адрес сервера")
        url_form = QFormLayout(url_group)
        # Верхний отступ, чтобы первая строка не перекрывала заголовок группы
        url_form.setContentsMargins(12, 18, 12, 12)
        self._url_edit = QLineEdit()
        self._url_edit.setPlaceholderText("https://api.example.com")
        url_form.addRow("API URL:", self._url_edit)
        layout.addWidget(url_group)

        auth_group = QGroupBox("Авторизация")
        auth_layout = QVBoxLayout(auth_group)
        auth_layout.setContentsMargins(12, 18, 12, 12)

        self._radio_token = QRadioButton("API-токен (Bearer)")
        self._radio_token.setChecked(True)
        auth_layout.addWidget(self._radio_token)

        token_row = QHBoxLayout()
        self._token_edit = QLineEdit()
        self._token_edit.setPlaceholderText("Вставьте токен")
        self._token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        token_row.addWidget(self._token_edit)
        show_token_btn = QPushButton("👁")
        show_token_btn.setFixedWidth(36)
        show_token_btn.setCheckable(True)
        show_token_btn.toggled.connect(
            lambda checked: self._token_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        token_row.addWidget(show_token_btn)
        auth_layout.addLayout(token_row)

        self._radio_login = QRadioButton("Логин и пароль")
        auth_layout.addWidget(self._radio_login)

        login_form = QFormLayout()
        self._login_edit = QLineEdit()
        self._login_edit.setPlaceholderText("Логин")
        login_form.addRow("Логин:", self._login_edit)

        pw_row = QHBoxLayout()
        self._password_edit = QLineEdit()
        self._password_edit.setPlaceholderText("Пароль")
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        pw_row.addWidget(self._password_edit)
        show_pw_btn = QPushButton("👁")
        show_pw_btn.setFixedWidth(36)
        show_pw_btn.setCheckable(True)
        show_pw_btn.toggled.connect(
            lambda checked: self._password_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        pw_row.addWidget(show_pw_btn)
        login_form.addRow("Пароль:", pw_row)
        auth_layout.addLayout(login_form)
        layout.addWidget(auth_group)

        self._radio_token.toggled.connect(self._update_auth_fields)
        self._radio_login.toggled.connect(self._update_auth_fields)
        self._update_auth_fields()

        test_btn = QPushButton("🔌 Проверить соединение")
        test_btn.clicked.connect(self._test_connection)
        layout.addWidget(test_btn)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        layout.addStretch()
        return page

    # ── Вкладка горячих клавиш ────────────────────────────────

    def _build_hotkeys_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        hint = QLabel("Нажмите на поле и введите нужное сочетание клавиш.")
        hint.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(hint)

        form = QFormLayout()
        self._hotkey_edits: dict[str, QKeySequenceEdit] = {}
        current = load_hotkeys()

        for action, label in _HOTKEY_LABELS.items():
            editor = QKeySequenceEdit(QKeySequence(current.get(action, "")))
            self._hotkey_edits[action] = editor
            form.addRow(label + ":", editor)

        layout.addLayout(form)

        reset_btn = QPushButton("↩ Сбросить к стандартным")
        reset_btn.clicked.connect(self._reset_hotkeys)
        layout.addWidget(reset_btn)

        layout.addStretch()
        return page

    # ── Вкладка «Прочее» ────────────────────────────────────

    def _build_misc_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # ── Тип пластины ──
        plate_group = QGroupBox("Тип пластины по умолчанию")
        plate_layout = QVBoxLayout(plate_group)
        plate_layout.setContentsMargins(12, 18, 12, 12)

        hint = QLabel(
            "Определяет, какой набор полей (цифровой или аналоговый) показывать в форме.\n"
            "«Авто» — определяется по содержимому файла."
        )
        hint.setStyleSheet("color: #888; font-size: 11px;")
        hint.setWordWrap(True)
        plate_layout.addWidget(hint)

        self._plate_auto = QRadioButton("Авто-определение по файлу")
        self._plate_digital = QRadioButton("Цифровая пластина")
        self._plate_analog = QRadioButton("Аналоговая пластина")

        current_override = load_plate_type_override()
        if current_override == "digital":
            self._plate_digital.setChecked(True)
        elif current_override == "analog":
            self._plate_analog.setChecked(True)
        else:
            self._plate_auto.setChecked(True)

        plate_layout.addWidget(self._plate_auto)
        plate_layout.addWidget(self._plate_digital)
        plate_layout.addWidget(self._plate_analog)
        layout.addWidget(plate_group)

        # ── Поведение ──
        misc_group = QGroupBox("Поведение")
        misc_form = QFormLayout(misc_group)
        misc_form.setContentsMargins(12, 18, 12, 12)

        state = _load_state()

        self._preview_cb = QCheckBox("Показывать предпросмотр файла перед загрузкой")
        self._preview_cb.setChecked(state.get("show_file_preview", True))
        misc_form.addRow("Предпросмотр:", self._preview_cb)

        self._dark_theme_cb = QCheckBox("Тёмная тема")
        self._dark_theme_cb.setChecked(state.get("dark_theme", False))
        misc_form.addRow("Тема:", self._dark_theme_cb)

        layout.addWidget(misc_group)
        layout.addStretch()
        return page

    # ── Вспомогательные методы ────────────────────────────────

    def _update_auth_fields(self) -> None:
        use_token = self._radio_token.isChecked()
        self._token_edit.setEnabled(use_token)
        self._login_edit.setEnabled(not use_token)
        self._password_edit.setEnabled(not use_token)

    def _load_current_values(self) -> None:
        try:
            settings = get_settings()
            self._url_edit.setText(settings.api_url)
            token = get_token() or settings.api_token
            login = get_login() or settings.api_login
            password = get_password() or settings.api_password
            if token:
                self._radio_token.setChecked(True)
                self._token_edit.setText(token)
            else:
                self._radio_login.setChecked(True)
                self._login_edit.setText(login)
                self._password_edit.setText(password)
        except Exception as exc:
            logger.warning("Не удалось загрузить текущие настройки: %s", exc)

    def _reset_hotkeys(self) -> None:
        for action, seq in DEFAULT_HOTKEYS.items():
            if action in self._hotkey_edits:
                self._hotkey_edits[action].setKeySequence(QKeySequence(seq))

    def _save_and_close(self) -> None:
        # ── Сохранение API ──
        url = self._url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Укажите API URL")
            return
        self._write_env("API_URL", url)

        try:
            if self._radio_token.isChecked():
                token = self._token_edit.text().strip()
                if not token:
                    QMessageBox.warning(self, "Ошибка", "Укажите токен")
                    return
                save_token(token)
                self._write_env("API_LOGIN", "")
                self._write_env("API_PASSWORD", "")
                self._write_env("API_TOKEN", "")
            else:
                login = self._login_edit.text().strip()
                password = self._password_edit.text().strip()
                if not login or not password:
                    QMessageBox.warning(self, "Ошибка", "Укажите логин и пароль")
                    return
                save_credentials(login, password)
                self._write_env("API_TOKEN", "")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить credentials:\n{exc}")
            return

        # ── Сохранение горячих клавиш ──
        hotkeys = {
            action: editor.keySequence().toString()
            for action, editor in self._hotkey_edits.items()
        }
        save_hotkeys(hotkeys)

        # ── Сохранение типа пластины ──
        if self._plate_digital.isChecked():
            save_plate_type_override("digital")
        elif self._plate_analog.isChecked():
            save_plate_type_override("analog")
        else:
            save_plate_type_override(None)

        # ── Сохранение прочего ──
        state = _load_state()
        state["show_file_preview"] = self._preview_cb.isChecked()
        dark = self._dark_theme_cb.isChecked()
        state["dark_theme"] = dark
        _save_state(state)

        # Применяем тему немедленно
        from PyQt6.QtWidgets import QApplication

        from ui.theme import apply_dark_theme, apply_light_theme
        if dark:
            apply_dark_theme(QApplication.instance())
        else:
            apply_light_theme(QApplication.instance())

        reset_settings_cache()
        logger.info("Настройки сохранены")
        QMessageBox.information(self, "Готово", "Настройки сохранены.")
        self.accept()

    def _test_connection(self) -> None:
        from api.client import ApiClient
        from api.exceptions import ApiError
        from config.settings import Settings

        url = self._url_edit.text().strip()
        if not url:
            self._set_status("⚠ Укажите API URL", error=True)
            return

        if self._radio_token.isChecked():
            token = self._token_edit.text().strip()
            tmp = Settings(api_url=url, api_login="", api_password="", api_token=token)
        else:
            login = self._login_edit.text().strip()
            password = self._password_edit.text().strip()
            tmp = Settings(api_url=url, api_login=login, api_password=password, api_token="")

        self._set_status("Проверяю соединение…", error=False)
        try:
            client = ApiClient(tmp, timeout=10.0, max_retries=1)
            client.login()
            self._set_status("✅ Соединение успешно", error=False)
            logger.info("Проверка соединения: успех")
        except ApiError as exc:
            self._set_status(f"❌ Ошибка: {exc}", error=True)
            logger.warning("Проверка соединения: %s", exc)
        except Exception as exc:
            self._set_status(f"❌ Непредвиденная ошибка: {exc}", error=True)

    def _set_status(self, text: str, *, error: bool) -> None:
        color = "#b00020" if error else "#2e7d32"
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color};")

    @staticmethod
    def _write_env(key: str, value: str) -> None:
        try:
            lines: list[str] = []
            if ENV_PATH.exists():
                lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
            found = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
                    lines[i] = f"{key}={value}"
                    found = True
                    break
            if not found:
                lines.append(f"{key}={value}")
            ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError as exc:
            logger.warning("Не удалось обновить .env: %s", exc)
