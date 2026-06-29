"""Форма редактирования распарсенных данных."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from logs.setup import get_logger
from models.crystal_data import (
    FIELD_LABELS,
    PLATE_MARKINGS,
    SORTING_TARGETS,
    SORTING_TYPES,
    CrystalData,
    get_correction_options,
    get_firmware_options,
    get_initial_crystals_default,
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
    "defect_inl",
    "defect_dnl",
    "defect_burn",
    "defect_u0_adc",
    "initial_crystals",
)

STRING_FIELDS: tuple[str, ...] = (
    "bmk_batch_number",
    "plate_number",
)

NORM_FIELDS: tuple[tuple[str, str], ...] = (
    ("norm_inl", "Норма INL"),
    ("norm_dnl", "Норма DNL"),
    ("norm_ufs", "Норма Ufs"),
    ("norm_u0", "Норма U0"),
    ("norm_u_perzhiganiya", "Норма U пережигания"),
    ("norm_u0_adc", "Норма U0 в режиме АЦП"),
)

UNIT_OPTIONS: tuple[str, ...] = ("нА", "мкА", "мА", "А", "мВ", "В", "кВ")


class EditFormWidget(QWidget):
    """Форма с полями для проверки и редактирования данных."""

    def __init__(self, data: CrystalData, parent=None) -> None:
        super().__init__(parent)
        self._spin_boxes: dict[str, QSpinBox] = {}
        self._line_edits: dict[str, QLineEdit] = {}
        self._norm_line_edits: dict[str, QLineEdit] = {}
        self._norm_unit_combos: dict[str, QComboBox] = {}
        self._plate_marking_combo: QComboBox | None = None
        self._firmware_combo: QComboBox | None = None
        self._correction_combo: QComboBox | None = None
        self._comment_edit: QPlainTextEdit | None = None
        self._sorting_type_combo: QComboBox | None = None
        self._sorting_target_combo: QComboBox | None = None
        self._error_label: QLabel | None = None
        self._build_ui(data)

    def _build_ui(self, data: CrystalData) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        self.setObjectName("EditForm")
        self.setStyleSheet(
            "QWidget#EditForm { background: transparent; }"
            "QScrollArea { background: transparent; border: none; }"
            "QGroupBox { background: transparent; border: 1px solid #f0f0f0; border-radius: 12px; }"
        )

        scroll = QScrollArea()
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)
        self._tabs.setStyleSheet(
            "QTabBar::tab { background-color: transparent; min-width: 100px; margin: 2px; padding: 8px 12px; border-radius: 8px; color: #424242; }"
            "QTabBar::tab:selected { background-color: #f5f5f5; color: #212121; }"
            "QTabWidget::pane { background-color: transparent; border: none; }")

        values = data.model_dump()

        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_form = QFormLayout()
        general_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        general_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self._plate_marking_combo = QComboBox()
        self._plate_marking_combo.setEditable(True)
        self._plate_marking_combo.addItems(list(PLATE_MARKINGS))
        self._plate_marking_combo.setCurrentText(str(values["plate_marking"]))
        self._plate_marking_combo.currentTextChanged.connect(self._update_dynamic_fields)
        general_form.addRow(FIELD_LABELS["plate_marking"], self._plate_marking_combo)

        self._firmware_combo = QComboBox()
        self._firmware_combo.setEditable(True)
        general_form.addRow(FIELD_LABELS["firmware_number"], self._firmware_combo)

        self._correction_combo = QComboBox()
        self._correction_combo.setEditable(True)
        general_form.addRow(FIELD_LABELS["correction_number"], self._correction_combo)

        plate_edit = QLineEdit(str(values["plate_number"]))
        plate_edit.setPlaceholderText("Обязательное поле")
        general_form.addRow(FIELD_LABELS["plate_number"], plate_edit)
        self._line_edits["plate_number"] = plate_edit

        bmk_edit = QLineEdit(str(values["bmk_batch_number"]))
        bmk_edit.setPlaceholderText("Обязательное поле")
        general_form.addRow(FIELD_LABELS["bmk_batch_number"], bmk_edit)
        self._line_edits["bmk_batch_number"] = bmk_edit

        self._sorting_target_combo = QComboBox()
        self._sorting_target_combo.addItems(list(SORTING_TARGETS))
        # Устанавливаем значение из данных или дефолт
        target_value = str(values["sorting_target"]) if values.get("sorting_target") else "ПР-ОВ"
        target_index = self._sorting_target_combo.findText(target_value)
        if target_index >= 0:
            self._sorting_target_combo.setCurrentIndex(target_index)
        else:
            # Если не найдено - ставим первое значение
            self._sorting_target_combo.setCurrentIndex(0)
        general_form.addRow(FIELD_LABELS["sorting_target"], self._sorting_target_combo)

        self._sorting_type_combo = QComboBox()
        self._sorting_type_combo.setEditable(True)
        self._sorting_type_combo.addItems(list(SORTING_TYPES))
        # Устанавливаем значение из данных или дефолт
        current_type = str(values.get("sorting_type", "Разбраковка NI"))
        type_index = self._sorting_type_combo.findText(current_type)
        if type_index >= 0:
            self._sorting_type_combo.setCurrentIndex(type_index)
        else:
            self._sorting_type_combo.setEditText(current_type)
        general_form.addRow(FIELD_LABELS["sorting_type"], self._sorting_type_combo)

        self._comment_edit = QPlainTextEdit(str(values.get("comment", "")))
        self._comment_edit.setPlaceholderText("Добавьте комментарий перед отправкой")
        self._comment_edit.setMaximumHeight(90)
        general_form.addRow(FIELD_LABELS["comment"], self._comment_edit)

        general_layout.addLayout(general_form)
        self._tabs.addTab(general_tab, "Параметры")

        self._update_dynamic_fields(str(values["plate_marking"]))

        quantities_tab = QWidget()
        quantities_layout = QVBoxLayout(quantities_tab)
        quantities_form = QFormLayout()
        quantities_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        for field in INT_FIELDS:
            spin = QSpinBox()
            spin.setRange(0, 10_000_000)
            spin.setValue(int(values.get(field, 0)))
            quantities_form.addRow(FIELD_LABELS[field], spin)
            self._spin_boxes[field] = spin

        quantities_layout.addLayout(quantities_form)
        quantities_layout.addStretch()
        self._tabs.addTab(quantities_tab, "Количественные показатели")

        norms_tab = QWidget()
        norms_layout = QVBoxLayout(norms_tab)
        norms_form = QFormLayout()
        norms_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._norm_line_edits = {}
        self._norm_unit_combos = {}

        for field, label_text in NORM_FIELDS:
            field_container = QWidget()
            field_layout = QHBoxLayout(field_container)
            field_layout.setContentsMargins(0, 0, 0, 0)

            edit = QLineEdit(str(values.get(field, "")))
            edit.setPlaceholderText("Значение")
            field_layout.addWidget(edit)
            self._norm_line_edits[field] = edit

            unit_combo = QComboBox()
            unit_combo.addItems(list(UNIT_OPTIONS))
            unit_combo.setCurrentIndex(0)
            field_layout.addWidget(unit_combo)
            self._norm_unit_combos[field] = unit_combo

            norms_form.addRow(label_text, field_container)

        norms_layout.addLayout(norms_form)
        norms_layout.addStretch()
        self._tabs.addTab(norms_tab, "Нормы")

        scroll.setWidget(self._tabs)
        root.addWidget(scroll)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet(
            "color: #b00020; background: transparent;"
            "border: 1px solid rgba(176, 0, 32, 0.08); border-radius: 8px;"
            "padding: 8px;"
        )
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        root.addWidget(self._error_label)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.submit_button = QPushButton("Подтвердить и отправить")
        self.submit_button.setMinimumWidth(220)
        self.submit_button.setStyleSheet(
            "QPushButton { background-color: #ffffff; color: #212121; border: 1px solid #e0e0e0; border-radius: 10px; padding: 10px 20px; }"
            "QPushButton:hover { background-color: #f5f5f5; }"
        )
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
            if not raw[field] and field in STRING_FIELDS:
                edit.setStyleSheet(
                    "background-color: rgba(255,255,255,0.05);"
                    "border: 1px solid rgba(255, 114, 114, 0.75);"
                    "color: #f8f9fb;"
                )

        assert self._plate_marking_combo is not None
        assert self._firmware_combo is not None
        assert self._correction_combo is not None
        assert self._comment_edit is not None
        assert self._sorting_type_combo is not None
        assert self._sorting_target_combo is not None
        raw["plate_marking"] = self._plate_marking_combo.currentText().strip()
        raw["firmware_number"] = self._firmware_combo.currentText().strip()
        raw["correction_number"] = self._correction_combo.currentText().strip()
        raw["comment"] = self._comment_edit.toPlainText().strip()
        raw["sorting_type"] = self._sorting_type_combo.currentText().strip()
        raw["sorting_target"] = self._sorting_target_combo.currentText().strip()
        for field, edit in self._norm_line_edits.items():
            unit = self._norm_unit_combos[field].currentText() if self._norm_unit_combos.get(field) else ""
            raw[field] = f"{edit.text().strip()} {unit}".strip()

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

    def _update_dynamic_fields(self, plate_marking: str | None = None) -> None:
        if self._plate_marking_combo is None:
            return
        current_marking = (plate_marking or self._plate_marking_combo.currentText()).strip().upper()
        if self._firmware_combo is not None:
            firmware_options = list(get_firmware_options(current_marking))
            self._firmware_combo.clear()
            self._firmware_combo.addItems(firmware_options)
            current_firmware = self._firmware_combo.currentText().strip() if self._firmware_combo.count() else ""
            if current_firmware and current_firmware in firmware_options:
                self._firmware_combo.setCurrentText(current_firmware)
            else:
                self._firmware_combo.setEditText(firmware_options[0] if firmware_options else "")

        if self._correction_combo is not None:
            correction_options = list(get_correction_options(current_marking))
            self._correction_combo.clear()
            self._correction_combo.addItems(correction_options)
            current_correction = self._correction_combo.currentText().strip() if self._correction_combo.count() else ""
            if current_correction and current_correction in correction_options:
                self._correction_combo.setCurrentText(current_correction)
            else:
                self._correction_combo.setEditText(correction_options[0] if correction_options else "")

        if self._spin_boxes.get("initial_crystals") is not None:
            default_initial = get_initial_crystals_default(current_marking)
            if default_initial > 0:
                self._spin_boxes["initial_crystals"].setValue(default_initial)

    def highlight_invalid_fields(self) -> None:
        """Подсвечивает пустые обязательные текстовые поля."""
        for field, edit in self._line_edits.items():
            if not edit.text().strip():
                edit.setStyleSheet(
                    "background-color: rgba(255,255,255,0.05);"
                    "border: 1px solid #ff5a5a;"
                    "color: #fefefe;"
                )
            else:
                edit.setStyleSheet("")

        if self._plate_marking_combo and not self._plate_marking_combo.currentText().strip():
            self._plate_marking_combo.setStyleSheet(
                "background-color: rgba(255,255,255,0.05);"
                "border: 1px solid #ff5a5a;"
                "color: #fefefe;"
            )
        else:
            self._plate_marking_combo.setStyleSheet("")
