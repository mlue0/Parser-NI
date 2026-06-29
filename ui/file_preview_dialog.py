"""Диалог предпросмотра файла перед парсингом."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
)

from logs.setup import get_logger

logger = get_logger(__name__)

_MAX_BYTES = 32 * 1024   # 32 KB достаточно для предпросмотра
_MAX_LINES = 200


class FilePreviewDialog(QDialog):
    """Показывает первые N строк файла; пользователь решает — загружать или нет."""

    def __init__(self, file_path: str | Path, parent=None) -> None:
        super().__init__(parent)
        path = Path(file_path)
        self.setWindowTitle(f"Предпросмотр: {path.name}")
        self.setMinimumSize(700, 480)
        self._build_ui(path)

    def _build_ui(self, path: Path) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        info = QLabel(
            f"<b>{path.name}</b> — {path.stat().st_size / 1024:.1f} KB  |  "
            f"Показаны первые {_MAX_LINES} строк"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        text_edit.setFont(font)
        text_edit.setPlainText(self._read_preview(path))
        layout.addWidget(text_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("✅ Загрузить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _read_preview(path: Path) -> str:
        """Читает первые _MAX_LINES строк или _MAX_BYTES байт."""
        try:
            raw = path.read_bytes()[:_MAX_BYTES]
            for enc in ("utf-8-sig", "cp1251", "latin-1"):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return "(Бинарный файл — предпросмотр недоступен)"

            lines = text.splitlines()[:_MAX_LINES]
            suffix = f"\n… (ещё {len(text.splitlines()) - _MAX_LINES} строк)" \
                if len(text.splitlines()) > _MAX_LINES else ""
            return "\n".join(lines) + suffix
        except OSError as exc:
            return f"Не удалось прочитать файл: {exc}"
