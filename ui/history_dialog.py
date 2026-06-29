"""Диалог просмотра истории загрузок."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from config.settings import clear_upload_history, load_upload_history
from logs.setup import get_logger

logger = get_logger(__name__)

_COLUMNS = ["Дата", "Файл", "Маркировка", "Статус", "Сообщение"]


class HistoryDialog(QDialog):
    """Таблица истории загрузок с поиском, очисткой и повторной отправкой."""

    resend_requested: tuple[str, str] | None = None

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("История загрузок")
        self.setMinimumSize(900, 480)
        self._all_history: list[dict] = load_upload_history()
        self._build_ui()
        self._populate(self._all_history)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        self._title_label = QLabel("История загрузок")
        self._title_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        header_row.addWidget(self._title_label)
        header_row.addStretch()
        clear_btn = QPushButton("Очистить всё")
        clear_btn.clicked.connect(self._clear_history)
        header_row.addWidget(clear_btn)
        layout.addLayout(header_row)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Поиск:"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Маркировка, файл или сообщение...")
        self._search_edit.textChanged.connect(self._filter)
        search_row.addWidget(self._search_edit)
        layout.addLayout(search_row)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 140)
        self._table.setColumnWidth(1, 240)
        self._table.setColumnWidth(2, 110)
        self._table.setColumnWidth(3, 90)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        self._resend_btn = QPushButton("Отправить снова")
        self._resend_btn.setEnabled(False)
        self._resend_btn.setToolTip(
            "Загрузить файл из выбранной строки и открыть форму для редактирования"
        )
        self._resend_btn.clicked.connect(self._resend_selected)
        btn_row.addWidget(self._resend_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Закрыть")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, history: list[dict]) -> None:
        self._table.setRowCount(0)
        for entry in history:
            row = self._table.rowCount()
            self._table.insertRow(row)
            status = entry.get("status", "")
            status_text = "OK" if status == "ok" else ("Ошибка" if status == "error" else status)
            cells = [
                entry.get("date", ""),
                entry.get("file", ""),
                entry.get("plate_marking", ""),
                status_text,
                entry.get("message", ""),
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, entry)
                if col == 3:
                    if status == "error":
                        item.setForeground(Qt.GlobalColor.red)
                    elif status == "ok":
                        item.setForeground(Qt.GlobalColor.darkGreen)
                self._table.setItem(row, col, item)

        count = self._table.rowCount()
        self._title_label.setText(f"История загрузок ({count} записей)")

    def _filter(self, text: str) -> None:
        query = text.strip().lower()
        if not query:
            self._populate(self._all_history)
            return
        filtered = [
            e for e in self._all_history
            if query in e.get("plate_marking", "").lower()
            or query in e.get("file", "").lower()
            or query in e.get("message", "").lower()
        ]
        self._populate(filtered)

    def _on_selection_changed(self) -> None:
        self._resend_btn.setEnabled(bool(self._table.selectedItems()))

    def _resend_selected(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        entry_item = self._table.item(row, 0)
        if not entry_item:
            return
        entry: dict = entry_item.data(Qt.ItemDataRole.UserRole)
        file_path: str = entry.get("file", "")
        plate_marking: str = entry.get("plate_marking", "")

        if not file_path:
            QMessageBox.warning(self, "Ошибка", "Путь к файлу не сохранён в истории")
            return

        from pathlib import Path
        if not Path(file_path).exists():
            QMessageBox.critical(
                self,
                "Файл не найден",
                f"Файл не найден по пути:\n{file_path}\n\nВозможно, он был перемещён или удалён.",
            )
            return

        self.resend_requested = (file_path, plate_marking)
        self.accept()

    def _clear_history(self) -> None:
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Очистить всю историю загрузок?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            clear_upload_history()
            self._all_history = []
            self._populate([])
            logger.info("История загрузок очищена")
