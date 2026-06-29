"""Диалог просмотра последних записей лога."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from config.settings import LOGS_DIR
from logs.setup import get_logger

logger = get_logger(__name__)

_LEVEL_COLORS: dict[str, str] = {
    "DEBUG": "#888888",
    "INFO": "#1a6e1a",
    "WARNING": "#b07800",
    "ERROR": "#c00000",
    "CRITICAL": "#800080",
}

_DEFAULT_LINES = 200


def _read_last_lines(log_path: Path, n: int) -> list[str]:
    """Читает последние n строк из файла."""
    if not log_path.exists():
        return []
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        return lines[-n:] if len(lines) > n else lines
    except OSError:
        return []


def _find_log_file() -> Path | None:
    """Ищет актуальный файл лога в папке logs."""
    if not LOGS_DIR.exists():
        return None
    candidates = sorted(LOGS_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


class LogViewerDialog(QDialog):
    """Просмотр последних строк лог-файла с цветовой подсветкой."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Просмотр логов")
        self.setMinimumSize(820, 520)
        self._log_path = _find_log_file()
        self._auto_refresh = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._reload)
        self._build_ui()
        self._reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Верхняя панель управления
        ctrl_row = QHBoxLayout()

        ctrl_row.addWidget(QLabel("Строк:"))
        self._lines_spin = QSpinBox()
        self._lines_spin.setRange(10, 2000)
        self._lines_spin.setValue(_DEFAULT_LINES)
        self._lines_spin.setSingleStep(50)
        ctrl_row.addWidget(self._lines_spin)

        reload_btn = QPushButton("🔄 Обновить")
        reload_btn.clicked.connect(self._reload)
        ctrl_row.addWidget(reload_btn)

        self._auto_cb = QCheckBox("Авто-обновление (3 сек)")
        self._auto_cb.toggled.connect(self._toggle_auto)
        ctrl_row.addWidget(self._auto_cb)

        ctrl_row.addStretch()

        self._path_label = QLabel("")
        self._path_label.setStyleSheet("color: #666; font-size: 11px;")
        ctrl_row.addWidget(self._path_label)

        layout.addLayout(ctrl_row)

        # Текстовое поле
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._text.setFont(font)
        layout.addWidget(self._text)

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Закрыть")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _reload(self) -> None:
        if self._log_path is None:
            self._log_path = _find_log_file()

        if self._log_path is None:
            self._text.setPlainText("Файл лога не найден.")
            self._path_label.setText("")
            return

        self._path_label.setText(str(self._log_path))
        lines = _read_last_lines(self._log_path, self._lines_spin.value())

        self._text.clear()
        cursor = self._text.textCursor()

        for line in lines:
            fmt = QTextCharFormat()
            for level, color in _LEVEL_COLORS.items():
                if f" {level} " in line or line.startswith(level):
                    fmt.setForeground(QColor(color))
                    break

            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(line + "\n", fmt)

        # Прокручиваем в конец
        self._text.moveCursor(QTextCursor.MoveOperation.End)

    def _toggle_auto(self, checked: bool) -> None:
        if checked:
            self._timer.start(3000)
        else:
            self._timer.stop()

    def closeEvent(self, event) -> None:
        self._timer.stop()
        super().closeEvent(event)

    def reject(self) -> None:
        self._timer.stop()
        super().reject()
