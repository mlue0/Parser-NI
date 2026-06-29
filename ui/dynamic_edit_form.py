"""Динамическая форма редактирования распарсенных данных."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import BaseModel, ValidationError
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config.fields_manager import FieldConfig, get_fields_manager
from logs.setup import get_logger

logger = get_logger(__name__)

# Желаемый порядок табов
TAB_ORDER = ["Параметры", "Количественные показатели", "Нормы"]

# ── Расшифровка SI-суффиксов ──────────────────────────────────────────────────
_SI_PREFIX: dict[str, tuple[str, str]] = {
    # суффикс → (русский префикс, степень)
    "p":  ("пико",  "× 10⁻¹²"),
    "n":  ("нано",  "× 10⁻⁹"),
    "u":  ("микро", "× 10⁻⁶"),
    "µ":  ("микро", "× 10⁻⁶"),
    "mk": ("микро", "× 10⁻⁶"),
    "мк": ("микро", "× 10⁻⁶"),
    "m":  ("милли", "× 10⁻³"),
    "м":  ("милли", "× 10⁻³"),
    "k":  ("кило",  "× 10³"),
    "к":  ("кило",  "× 10³"),
    "M":  ("мега",  "× 10⁶"),
    "G":  ("гига",  "× 10⁹"),
}
# Расшифровки базовых единиц
_UNIT_FULL: dict[str, str] = {
    "А":   "ампер",
    "мкА": "микроампер",
    "мА":  "миллиампер",
    "В":   "вольт",
    "мВ":  "милливольт",
    "МЗР": "младший значащий разряд (LSB)",
    "Ом":  "ом",
    "Гц":  "герц",
}

# Краткие русские символы SI-префиксов для метки рядом с полем
_SI_SYMBOL: dict[str, str] = {
    "p":  "п",   # пико
    "n":  "н",   # нано
    "u":  "мк",  # микро
    "µ":  "мк",
    "mk": "мк",
    "мк": "мк",
    "m":  "м",   # милли
    "м":  "м",
    "k":  "к",   # кило
    "к":  "к",
    "M":  "М",   # мега
    "G":  "Г",   # гига
}

# Составные единицы, которые файл пишет как суффикс к числу ("5mA", "11A", ...)
_VALUE_UNITS: dict[str, str] = {
    "A":  "А",   "mA": "мА",  "uA": "мкА", "µA": "мкА",
    "V":  "В",   "mV": "мВ",  "kV": "кВ",
    "Hz": "Гц",  "kHz": "кГц",
}


def _make_unit_tooltip(value: str, base_unit: str) -> str:
    """Строит подсказку: расшифровывает SI-суффикс в значении + полное имя единицы.

    Пример: value='25u', base_unit='мкА'  →  '25 мкА — микроампер'
            value='25u', base_unit='А'    →  '25u А — 25 микро-ампер (× 10⁻⁶)'
    """
    full = _UNIT_FULL.get(base_unit, base_unit)
    if not value:
        return f"Единица: {base_unit} ({full})"

    # Пытаемся разобрать число + SI-суффикс из строки значения
    import re
    m = re.fullmatch(r"([+-]?[0-9]*\.?[0-9]+)\s*([a-zA-Zмкµ]*)", value.strip())
    if m:
        num_str, suffix = m.group(1), m.group(2).lower()
        if suffix in _SI_PREFIX:
            prefix_name, power = _SI_PREFIX[suffix]
            return (
                f"{num_str} {prefix_name}{base_unit.lower()} ({power} {base_unit})\n"
                f"Единица: {base_unit} — {full}"
            )

    return f"Единица: {base_unit} — {full}"


def _split_value_unit(raw_val: str, base_unit: str) -> tuple[str, str]:
    """Разбивает строку вида '17p', '5mA', '3.12 mA' на (число, метка_единицы).

    Возвращает:
        display_val  — числовая часть для подстановки в поле ввода
        display_unit — метка единицы для показа рядом с полем
                       (например 'пМЗР', 'мА', 'мкВ')
    """
    import re
    val = raw_val.strip()
    m = re.fullmatch(r"([+-]?[0-9]*\.?[0-9]+)\s*([a-zA-Zмкµ]+)?", val)
    if not m:
        return val, base_unit
    num_str = m.group(1)
    suffix = m.group(2) or ""
    if not suffix:
        return num_str, base_unit

    # 1. Известная составная единица ("mA", "uA", "V", ...)
    if suffix in _VALUE_UNITS:
        return num_str, _VALUE_UNITS[suffix]

    # 2. Одиночный SI-префикс → соединяем с базовой единицей конфига
    if suffix in _SI_SYMBOL:
        return num_str, _SI_SYMBOL[suffix] + base_unit

    # 3. Ничего не распознали — оставляем как есть, просто убираем суффикс из поля
    return num_str, suffix + " " + base_unit  # nbsp-пробел для читаемости


class DynamicEditFormWidget(QWidget):
    """Динамическая форма для редактирования данных на основе FieldConfigs."""

    def __init__(
        self,
        data: BaseModel,
        file_path: str | None = None,
        plate_type_override: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._data = data
        self._data_type = type(data)
        self._fields_manager = get_fields_manager()
        self._file_path = file_path
        self._plate_type_override = plate_type_override  # "digital" | "analog" | None

        # Словари для хранения виджетов по ключам полей
        self._widgets: dict[str, QWidget] = {}

        # Получаем field_configs с учётом типа пластины
        raw_data = data.model_dump()
        self._field_configs = self._fields_manager.get_fields_from_data(
            raw_data, plate_type_override=plate_type_override
        )

        # Группируем поля по табам (с учётом желаемого порядка)
        self._grouped_fields = self._group_fields_by_category()

        self._build_ui(data)

        # Таймер автосохранения черновика (5 сек после последнего изменения)
        self._draft_timer = QTimer(self)
        self._draft_timer.setSingleShot(True)
        self._draft_timer.setInterval(5000)
        self._draft_timer.timeout.connect(self._autosave_draft)
        self._connect_change_signals()

    def _group_fields_by_category(self) -> dict[str, list[FieldConfig]]:
        """Группирует field_configs по табам, соблюдая TAB_ORDER."""
        grouped: dict[str, list[FieldConfig]] = {}

        for field_config in self._field_configs:
            tab = field_config.tab or field_config.group or "Прочее"
            if tab not in grouped:
                grouped[tab] = []
            grouped[tab].append(field_config)

        # Сортируем по TAB_ORDER, затем остальные в алфавитном порядке
        ordered: dict[str, list[FieldConfig]] = {}
        for tab_name in TAB_ORDER:
            if tab_name in grouped:
                ordered[tab_name] = grouped[tab_name]
        for tab_name, fields in grouped.items():
            if tab_name not in ordered:
                ordered[tab_name] = fields

        return ordered

    def _build_ui(self, data: BaseModel) -> None:
        """Создаёт UI на основе field_configs."""
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        self.setObjectName("DynamicEditForm")
        self.setStyleSheet(
            "QWidget#DynamicEditForm { background: transparent; }"
            "QScrollArea { background: transparent; border: none; }"
        )

        scroll = QScrollArea()
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidgetResizable(True)

        # Фильтруем пустые табы
        non_empty = {k: v for k, v in self._grouped_fields.items() if v}

        if len(non_empty) == 1:
            content_widget = self._build_single_group(non_empty)
            scroll.setWidget(content_widget)
        else:
            tabs = QTabWidget()
            tabs.setTabPosition(QTabWidget.TabPosition.North)
            # Стили вкладок управляются темой приложения (theme.py)
            tabs.setStyleSheet("QTabWidget::pane { background-color: transparent; border: none; }")
            for tab_name, fields in non_empty.items():
                tab_widget = self._build_group_form(tab_name, fields, data)
                tabs.addTab(tab_widget, tab_name)
            scroll.setWidget(tabs)

        root.addWidget(scroll)

        # Плашка предупреждений кросс-валидации (жёлтая)
        self._warning_label = QLabel("")
        self._warning_label.setStyleSheet(
            "color: #7a5c00; background: #fff8e1;"
            "border: 1px solid #ffe082; border-radius: 8px; padding: 8px;"
        )
        self._warning_label.setWordWrap(True)
        self._warning_label.setVisible(False)
        root.addWidget(self._warning_label)

        # Метка ошибок (красная)
        self._error_label = QLabel("")
        self._error_label.setStyleSheet(
            "color: #b00020; background: #fff0f0;"
            "border: 1px solid rgba(176, 0, 32, 0.2); border-radius: 8px;"
            "padding: 8px;"
        )
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        root.addWidget(self._error_label)

        # Кнопки действий
        buttons = QHBoxLayout()

        export_btn = QPushButton("💾 Сохранить копию")
        export_btn.setToolTip("Сохранить данные в файл Excel или PDF")
        export_btn.clicked.connect(self._export_data)
        buttons.addWidget(export_btn)

        buttons.addStretch()
        self.submit_button = QPushButton("Подтвердить и отправить")
        self.submit_button.setMinimumWidth(220)
        buttons.addWidget(self.submit_button)

        # Показываем предупреждения кросс-валидации сразу при открытии
        self._show_cross_field_warnings(data)
        root.addLayout(buttons)

    def _build_single_group(self, non_empty: dict[str, list[FieldConfig]]) -> QWidget:
        """Одиночный контейнер без табов."""
        container = QWidget()
        layout = QVBoxLayout(container)
        for tab_name, fields in non_empty.items():
            form = self._build_group_form(tab_name, fields, self._data)
            layout.addWidget(form)
        layout.addStretch()
        return container

    def _build_group_form(
        self,
        group_name: str,
        field_configs: list[FieldConfig],
        data: BaseModel,
    ) -> QWidget:
        """Создаёт форму для одного таба."""
        container = QWidget()
        layout = QVBoxLayout(container)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setVerticalSpacing(10)

        raw_data = data.model_dump()

        for field_config in field_configs:
            value = raw_data.get(field_config.key, field_config.default_value or "")
            raw_val = str(value) if value not in (None, "") else ""

            if field_config.unit and raw_val:
                # Разбиваем «17p» → display_val='17', display_unit='пМЗР'
                display_val, display_unit = _split_value_unit(raw_val, field_config.unit)
            else:
                display_val, display_unit = raw_val, field_config.unit

            widget = self._create_widget_for_field(field_config, display_val)
            self._widgets[field_config.key] = widget

            if field_config.unit:
                # Оборачиваем виджет + метка единицы измерения
                row_widget = QWidget()
                row_lay = QHBoxLayout(row_widget)
                row_lay.setContentsMargins(0, 0, 0, 0)
                row_lay.setSpacing(6)
                row_lay.addWidget(widget, stretch=1)
                unit_lbl = QLabel(display_unit)
                unit_lbl.setMinimumWidth(36)
                unit_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                unit_lbl.setStyleSheet("color: #888; font-size: 11px;")
                # Тултип: расшифровка SI-суффикса из исходного (необработанного) значения
                tip = _make_unit_tooltip(raw_val, field_config.unit)
                unit_lbl.setToolTip(tip)
                widget.setToolTip(tip)
                row_lay.addWidget(unit_lbl)
                form.addRow(field_config.label + ":", row_widget)
            else:
                form.addRow(field_config.label + ":", widget)

        layout.addLayout(form)
        layout.addStretch()
        return container

    def _create_widget_for_field(self, field_config: FieldConfig, value: Any) -> QWidget:
        """Создаёт подходящий виджет для поля."""

        # --- Комбобокс (если заданы choices) ---
        if field_config.choices:
            combo = QComboBox()
            combo.addItems(field_config.choices)
            if field_config.editable:
                # Разрешаем ручной ввод
                combo.setEditable(True)
                combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            current = str(value).strip() if value is not None else ""
            idx = combo.findText(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            elif field_config.editable and current:
                combo.setCurrentText(current)
            elif not field_config.editable and combo.count() > 0:
                # Нет значения — оставляем первый пункт
                combo.setCurrentIndex(0)
            return combo

        # --- Многострочный текст ---
        if field_config.widget_type == "textarea":
            edit = QPlainTextEdit()
            edit.setPlainText(str(value) if value else "")
            edit.setFixedHeight(70)
            return edit

        # --- Целое число ---
        if field_config.type == "integer":
            spin = QSpinBox()
            spin.setRange(field_config.min_value or 0, field_config.max_value or 10_000_000)
            try:
                spin.setValue(int(value) if value not in (None, "") else 0)
            except (TypeError, ValueError):
                spin.setValue(0)
            if not field_config.editable:
                spin.setReadOnly(True)
                spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
            return spin

        # --- Число с плавающей точкой ---
        if field_config.type == "float":
            edit = QLineEdit()
            edit.setText(str(value) if value not in (None, "") else "")
            if not field_config.editable:
                edit.setReadOnly(True)
            return edit

        # --- Строка (по умолчанию) ---
        edit = QLineEdit()
        if not field_config.editable:
            edit.setReadOnly(True)
        # Убираем плейсхолдер "Опциональное поле" — оставляем только для обязательных
        if field_config.required:
            edit.setPlaceholderText("Обязательное поле")
        edit.setText(str(value) if value not in (None, "") else "")
        return edit

    def collect_data(self) -> BaseModel | None:
        """Собирает и валидирует данные из формы."""
        self._hide_error()
        raw: dict[str, Any] = {}

        for field_config in self._field_configs:
            widget = self._widgets.get(field_config.key)
            if widget is None:
                continue

            if isinstance(widget, QSpinBox):
                raw[field_config.key] = widget.value()

            elif isinstance(widget, QComboBox):
                raw[field_config.key] = widget.currentText().strip()

            elif isinstance(widget, QPlainTextEdit):
                raw[field_config.key] = widget.toPlainText().strip()

            elif isinstance(widget, QLineEdit):
                text = widget.text().strip()
                if field_config.type == "float":
                    try:
                        raw[field_config.key] = float(text) if text else 0.0
                    except ValueError:
                        raw[field_config.key] = 0.0
                elif field_config.type == "integer":
                    try:
                        raw[field_config.key] = int(text) if text else 0
                    except ValueError:
                        raw[field_config.key] = 0
                else:
                    raw[field_config.key] = text

        # Добавляем стандартные поля только если виджет для них не создан
        raw_data = self._data.model_dump()
        for key in ["sorting_type", "sorting_target", "comment"]:
            if key not in raw and key in raw_data:
                raw[key] = raw_data[key]

        try:
            model = self._data_type.model_validate(raw)
            self._show_cross_field_warnings(model)
            logger.info("Данные формы успешно прошли валидацию")
            return model
        except ValidationError as exc:
            messages = []
            for error in exc.errors():
                loc = error.get("loc", ())
                field_name = str(loc[0]) if loc else "поле"
                fc = self._fields_manager.get_field(field_name)
                label = fc.label if fc else field_name
                messages.append(f"{label}: {error.get('msg', 'ошибка')}")
            self._show_error("\n".join(messages))
            logger.warning("Ошибка валидации формы: %s", messages)
            return None

    def _export_data(self) -> None:
        """Открывает диалог сохранения и экспортирует текущие данные формы."""
        from ui.export_utils import export_to_excel, export_to_pdf

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Сохранить копию данных",
            "",
            "Excel (*.xlsx);;PDF (*.pdf)",
        )
        if not file_path:
            return

        # Собираем пары (label, value) из всех полей
        labeled: list[tuple[str, str]] = []
        raw = self._data.model_dump()
        for fc in self._field_configs:
            widget = self._widgets.get(fc.key)
            if widget is None:
                continue
            if isinstance(widget, QSpinBox):
                val = str(widget.value())
            elif isinstance(widget, QComboBox):
                val = widget.currentText()
            elif isinstance(widget, QPlainTextEdit):
                val = widget.toPlainText()
            elif isinstance(widget, QLineEdit):
                val = widget.text()
            else:
                val = str(raw.get(fc.key, ""))
            labeled.append((fc.label, val))

        try:
            if file_path.endswith(".xlsx"):
                export_to_excel(labeled, file_path)
            else:
                export_to_pdf(labeled, file_path)
            QMessageBox.information(self, "Готово", f"Файл сохранён:\n{file_path}")
        except Exception as exc:
            logger.error("Ошибка экспорта: %s", exc)
            QMessageBox.critical(self, "Ошибка экспорта", str(exc))

    def _show_cross_field_warnings(self, model: BaseModel) -> None:
        """Показывает предупреждения кросс-валидации из модели (жёлтая плашка)."""
        warnings = model.__dict__.get("_cross_field_warnings", [])
        if warnings:
            self._warning_label.setText("⚠ " + "\n⚠ ".join(warnings))
            self._warning_label.setVisible(True)
        else:
            self._warning_label.setVisible(False)

    def _show_error(self, message: str) -> None:
        if self._error_label:
            self._error_label.setText(message)
            self._error_label.setVisible(True)

    def _hide_error(self) -> None:
        if self._error_label:
            self._error_label.clear()
            self._error_label.setVisible(False)

    def highlight_invalid_fields(self) -> None:
        """Подсвечивает пустые обязательные поля."""
        err_style = (
            "background-color: rgba(255,255,255,0.05);"
            "border: 1px solid #ff5a5a;"
            "color: #fefefe;"
        )
        for field_config in self._field_configs:
            if not field_config.required:
                continue
            widget = self._widgets.get(field_config.key)
            if widget is None:
                continue
            if isinstance(widget, QLineEdit):
                widget.setStyleSheet(err_style if not widget.text().strip() else "")
            elif isinstance(widget, QComboBox):
                widget.setStyleSheet(err_style if not widget.currentText().strip() else "")

    def _connect_change_signals(self) -> None:
        """Подключает сигналы изменения виджетов к таймеру автосохранения."""
        for widget in self._widgets.values():
            if isinstance(widget, QSpinBox):
                widget.valueChanged.connect(self._draft_timer.start)
            elif isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(self._draft_timer.start)
            elif isinstance(widget, QPlainTextEdit):
                widget.textChanged.connect(self._draft_timer.start)
            elif isinstance(widget, QLineEdit):
                widget.textChanged.connect(self._draft_timer.start)

    def _autosave_draft(self) -> None:
        """Сохраняет все значения формы как черновик."""
        if not self._file_path:
            return
        try:
            from config.settings import save_draft
            values = self.collect_editable_values()
            if values:
                save_draft(self._file_path, values)
                logger.debug("Черновик автосохранён для %s", self._file_path)
        except Exception as exc:
            logger.warning("Не удалось автосохранить черновик: %s", exc)

    def apply_template(self, template: dict[str, Any]) -> None:
        """Применяет шаблон — заполняет редактируемые поля из словаря template.

        Перезаписывает только те поля, где widget editable=True и значение
        в форме пустое/нулевое (чтобы не перетирать данные из файла).
        """
        for field_config in self._field_configs:
            if not field_config.editable or field_config.key not in template:
                continue
            widget = self._widgets.get(field_config.key)
            if widget is None:
                continue
            tpl_value = template[field_config.key]

            if isinstance(widget, QLineEdit):
                if not widget.text().strip():
                    widget.setText(str(tpl_value))
            elif isinstance(widget, QComboBox):
                if not widget.currentText().strip():
                    idx = widget.findText(str(tpl_value))
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
                    elif widget.isEditable():
                        widget.setCurrentText(str(tpl_value))
            elif isinstance(widget, QPlainTextEdit):
                if not widget.toPlainText().strip():
                    widget.setPlainText(str(tpl_value))

    def collect_editable_values(self) -> dict[str, Any]:
        """Возвращает только значения редактируемых полей — для сохранения шаблона."""
        result: dict[str, Any] = {}
        for field_config in self._field_configs:
            if not field_config.editable:
                continue
            widget = self._widgets.get(field_config.key)
            if widget is None:
                continue
            if isinstance(widget, QSpinBox):
                result[field_config.key] = widget.value()
            elif isinstance(widget, QComboBox):
                result[field_config.key] = widget.currentText().strip()
            elif isinstance(widget, QPlainTextEdit):
                result[field_config.key] = widget.toPlainText().strip()
            elif isinstance(widget, QLineEdit):
                result[field_config.key] = widget.text().strip()
        return result
