"""Диалог подтверждения перед отправкой данных."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from models.crystal_data import CrystalData


class ConfirmDialog(QDialog):
    """Показывает итоговые данные для подтверждения пользователем."""

    def __init__(self, data: CrystalData, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Подтверждение отправки")
        self.setMinimumSize(560, 480)
        self._build_ui(data)

    def _build_ui(self, data: CrystalData) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Проверьте данные перед отправкой на сервер:")
        title.setWordWrap(True)
        layout.addWidget(title)

        table = QTableWidget(len(data.labeled_values()), 2)
        table.setHorizontalHeaderLabels(["Поле", "Значение"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        for row, (label, value) in enumerate(data.labeled_values()):
            label_item = QTableWidgetItem(label)
            value_item = QTableWidgetItem(value)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 0, label_item)
            table.setItem(row, 1, value_item)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Отправить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
