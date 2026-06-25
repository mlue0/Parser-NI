"""Форма редактирования распарсенных данных."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from logs.setup import get_logger
from models.crystal_data import (
    FIELD_LABELS,
    SORTING_TARGETS,
    SORTING_TYPES,
    CrystalData,
)

logger = get_logger(__name__)

INT_FIELDS: tuple[str, ...] = (
    "good_crystals",
    "defective_crystals",
    "total_crystals",
    "defect_contact",
    "defect_icc",
    "defect_fc",
    "defect_static",
    "initial_crystals",
)

STRING_FIELDS: tuple[str, ...] = (
    "plate_marking",
    "firmware_number",
    "correction_number",
    "bmk_batch_number",
    "plate_number",
)


class EditFormWidget(QWidget):
    """Форма с полями для проверки и редактирования данных."""

    def __init__(self, data: CrystalData, parent=None) -> None:
        super().__init__(parent)
        self._spin_boxes: dict[str, QSpinBox] = {}
        self._line_edits: dict[str, QLineEdit] = {}
        self._sorting_type_combo: QComboBox | None = None
        self._sorting_target_combo: QComboBox | None = None
        self._error_label: QLabel | None = None
        self._build_ui(data)

    def _build_ui(self, data: CrystalData) -> None:
        root = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        form_layout = QFormLayout(container)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        values = data.model_dump()

        numbers_group = QGroupBox("Количественные показатели")
        numbers_layout = QFormLayout(numbers_group)
        for field in INT_FIELDS:
            spin = QSpinBox()
            spin.setRange(0, 10_000_000)
            spin.setValue(int(values[field]))
            numbers_layout.addRow(FIELD_LABELS[field], spin)
            self._spin_boxes[field] = spin
        form_layout.addRow(numbers_group)

        text_group = QGroupBox("Идентификаторы")
        text_layout = QFormLayout(text_group)
        for field in STRING_FIELDS:
            edit = QLineEdit(str(values[field]))
            edit.setPlaceholderText("Обязательное поле")
            text_layout.addRow(FIELD_LABELS[field], edit)
            self._line_edits[field] = edit
        form_layout.addRow(text_group)

        sorting_group = QGroupBox("Параметры разбраковки")
        sorting_layout = QFormLayout(sorting_group)

        self._sorting_type_combo = QComboBox()
        self._sorting_type_combo.setEditable(True)
        self._sorting_type_combo.addItems(list(SORTING_TYPES))
        current_type = str(values["sorting_type"])
        index = self._sorting_type_combo.findText(current_type)
        if index >= 0:
            self._sorting_type_combo.setCurrentIndex(index)
        else:
            self._sorting_type_combo.setEditText(current_type)
        sorting_layout.addRow(FIELD_LABELS["sorting_type"], self._sorting_type_combo)

        self._sorting_target_combo = QComboBox()
        self._sorting_target_combo.addItems(list(SORTING_TARGETS))
        target_index = self._sorting_target_combo.findText(str(values["sorting_target"]))
        if target_index >= 0:
            self._sorting_target_combo.setCurrentIndex(target_index)
        sorting_layout.addRow(FIELD_LABELS["sorting_target"], self._sorting_target_combo)

        form_layout.addRow(sorting_group)

        scroll.setWidget(container)
        root.addWidget(scroll)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #c0392b;")
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        root.addWidget(self._error_label)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.submit_button = QPushButton("Подтвердить и отправить")
        self.submit_button.setMinimumWidth(220)
        buttons.addWidget(self.submit_button)
        root.addLayout(buttons)

    def collect_data(self) -> CrystalData | None:
        """Собирает и валидирует данные из формы."""
        self._hide_error()
        raw: dict[str, Any] = {}

        for field, spin in self._spin_boxes.items():
            raw[field] = spin.value()

        for field, edit in self._line_edits.items():
            raw[field] = edit.text().strip()

        assert self._sorting_type_combo is not None
        assert self._sorting_target_combo is not None
        raw["sorting_type"] = self._sorting_type_combo.currentText().strip()
        raw["sorting_target"] = self._sorting_target_combo.currentText().strip()

        try:
            model = CrystalData.model_validate(raw)
            logger.info("Данные формы успешно прошли валидацию")
            return model
        except ValidationError as exc:
            messages = []
            for error in exc.errors():
                loc = error.get("loc", ())
                field_name = str(loc[0]) if loc else "поле"
                label = FIELD_LABELS.get(field_name, field_name)
                messages.append(f"{label}: {error.get('msg', 'ошибка')}")
            self._show_error("\n".join(messages))
            logger.warning("Ошибка валидации формы: %s", messages)
            return None

    def _show_error(self, message: str) -> None:
        if self._error_label:
            self._error_label.setText(message)
            self._error_label.setVisible(True)

    def _hide_error(self) -> None:
        if self._error_label:
            self._error_label.clear()
            self._error_label.setVisible(False)

    def highlight_invalid_fields(self) -> None:
        """Подсвечивает пустые обязательные текстовые поля."""
        for field, edit in self._line_edits.items():
            if not edit.text().strip():
                edit.setStyleSheet("border: 1px solid #c0392b;")
            else:
                edit.setStyleSheet("")
