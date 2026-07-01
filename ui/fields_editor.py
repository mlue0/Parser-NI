"""Редактор конфигурации полей."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config.fields_manager import FieldConfig, get_fields_manager
from logs.setup import get_logger

logger = get_logger(__name__)


class FieldEditorDialog(QDialog):
    """Диалог редактирования одного поля."""
    
    def __init__(self, field_config: FieldConfig | None = None, parent=None):
        super().__init__(parent)
        self.field_config = field_config
        self.setWindowTitle("Редактирование поля" if field_config else "Новое поле")
        self.setMinimumWidth(400)
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Ключ поля
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("Ключ (англ.):"))
        self.key_edit = QLineEdit()
        if self.field_config:
            self.key_edit.setText(self.field_config.key)
            self.key_edit.setEnabled(False)  # Ключ нельзя менять
        self.key_edit.setPlaceholderText("например: defect_new_param")
        key_layout.addWidget(self.key_edit)
        layout.addLayout(key_layout)
        
        # Метка поля
        label_layout = QHBoxLayout()
        label_layout.addWidget(QLabel("Название:"))
        self.label_edit = QLineEdit()
        if self.field_config:
            self.label_edit.setText(self.field_config.label)
        self.label_edit.setPlaceholderText("например: Брак по новому параметру")
        label_layout.addWidget(self.label_edit)
        layout.addLayout(label_layout)
        
        # Тип поля
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Тип данных:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["string", "integer", "float"])
        if self.field_config:
            index = self.type_combo.findText(self.field_config.type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # Порядок
        order_layout = QHBoxLayout()
        order_layout.addWidget(QLabel("Порядок:"))
        self.order_spin = QSpinBox()
        self.order_spin.setRange(0, 1000)
        if self.field_config:
            self.order_spin.setValue(self.field_config.order)
        order_layout.addWidget(self.order_spin)
        order_layout.addStretch()
        layout.addLayout(order_layout)
        
        # Обязательное поле
        # self.required_check = QCheckBox("Обязательное поле")
        # if self.field_config:
        #     self.required_check.setChecked(self.field_config.required)
        # layout.addWidget(self.required_check)
        
        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_field_config(self) -> FieldConfig | None:
        """Возвращает конфигурацию поля из формы."""
        key = self.key_edit.text().strip()
        label = self.label_edit.text().strip()
        
        if not key or not label:
            QMessageBox.warning(self, "Ошибка", "Заполните ключ и название поля")
            return None
        
        return FieldConfig(
            key=key,
            label=label,
            type=self.type_combo.currentText(),
            required=False,
            editable=True,
            order=self.order_spin.value(),
        )


class FieldsEditorWindow(QDialog):
    """Главное окно редактора полей."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактор полей SimpleMeasure")
        self.setMinimumSize(800, 600)
        self.fields_manager = get_fields_manager()
        self._build_ui()
        self._load_fields()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # Заголовок
        title = QLabel("Настройка полей приложения")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        desc = QLabel(
            "Здесь вы можете добавлять, удалять и изменять порядок полей.\n"
            "Изменения вступят в силу после перезапуска приложения."
        )
        desc.setStyleSheet("color: #666; padding: 5px 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Вкладки для разных групп
        self.tabs = QTabWidget()

        # Вкладка: Параметры (идентификация + разбраковка)
        self.params_tab = self._create_group_tab("params_identity", "params_output")
        self.tabs.addTab(self.params_tab, "Параметры")

        # Вкладка: Количественные показатели (кол-ва + браки)
        self.quantities_tab = self._create_group_tab("quantities_base", "defects_common", "defects_analog")
        self.tabs.addTab(self.quantities_tab, "Количественные показатели")

        # Вкладка: Нормы
        self.norms_tab = self._create_group_tab("norms_digital", "norms_analog")
        self.tabs.addTab(self.norms_tab, "Нормы")

        # Вкладка: Пользовательские поля
        self.custom_tab = self._create_group_tab(
            "custom_fields",
            hint=(
                "Здесь появляются добавленные вами поля. Нажмите «➕ Добавить поле», "
                "чтобы создать новое — его можно редактировать, удалять и менять порядок. "
                "Пользовательские поля отображаются в форме разбраковки на вкладке «Параметры»."
            ),
        )
        self.tabs.addTab(self.custom_tab, "Пользовательские поля")
        
        layout.addWidget(self.tabs)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Добавить поле")
        self.add_btn.clicked.connect(self._add_field)
        buttons_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️ Редактировать")
        self.edit_btn.clicked.connect(self._edit_field)
        buttons_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.clicked.connect(self._delete_field)
        buttons_layout.addWidget(self.delete_btn)
        
        self.move_up_btn = QPushButton("⬆️ Вверх")
        self.move_up_btn.clicked.connect(self._move_up)
        buttons_layout.addWidget(self.move_up_btn)
        
        self.move_down_btn = QPushButton("⬇️ Вниз")
        self.move_down_btn.clicked.connect(self._move_down)
        buttons_layout.addWidget(self.move_down_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Кнопки сохранения
        save_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save_buttons.button(QDialogButtonBox.StandardButton.Save).setText("💾 Сохранить")
        save_buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("❌ Отмена")
        save_buttons.accepted.connect(self._save_and_close)
        save_buttons.rejected.connect(self.reject)
        layout.addWidget(save_buttons)
    
    def _create_group_tab(self, *group_names: str, hint: str | None = None) -> QWidget:
        """Создаёт вкладку для группы полей."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        if hint:
            hint_label = QLabel(hint)
            hint_label.setWordWrap(True)
            hint_label.setStyleSheet("color: #888; font-size: 12px; padding: 4px 2px;")
            layout.addWidget(hint_label)

        # Создаём список для каждой группы
        for group_name in group_names:
            group = self.fields_manager.groups.get(group_name)
            if not group:
                continue
            
            group_box = QGroupBox(group.title)
            group_layout = QVBoxLayout(group_box)
            # Верхний отступ, чтобы список не перекрывал заголовок группы
            group_layout.setContentsMargins(10, 18, 10, 10)

            list_widget = QListWidget()
            list_widget.setProperty("group_name", group_name)
            list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
            
            group_layout.addWidget(list_widget)
            layout.addWidget(group_box)
        
        layout.addStretch()
        return widget
    
    def _load_fields(self):
        """Загружает поля в списки."""
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            for group_box in tab.findChildren(QGroupBox):
                for list_widget in group_box.findChildren(QListWidget):
                    group_name = list_widget.property("group_name")
                    if not group_name:
                        continue
                    
                    group = self.fields_manager.groups.get(group_name)
                    if not group:
                        continue
                    
                    list_widget.clear()
                    for field_config in group.fields:
                        item = QListWidgetItem(f"{field_config.label} ({field_config.key})")
                        item.setData(Qt.ItemDataRole.UserRole, field_config.key)
                        list_widget.addItem(item)
    
    def _get_current_list(self) -> QListWidget | None:
        """Возвращает текущий активный список."""
        current_tab = self.tabs.currentWidget()
        for group_box in current_tab.findChildren(QGroupBox):
            for list_widget in group_box.findChildren(QListWidget):
                if list_widget.currentItem():
                    return list_widget
        return None
    
    def _add_field(self):
        """Добавляет новое поле."""
        dialog = FieldEditorDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            field_config = dialog.get_field_config()
            if field_config:
                # Всегда добавляем пользовательские поля в custom_fields
                group_name = "custom_fields"
                
                self.fields_manager.add_custom_field(
                    field_config.key,
                    field_config.label,
                    field_config.type,
                    group_name,
                )
                self._load_fields()
                logger.info(f"Добавлено поле: {field_config.key}")
    
    def _edit_field(self):
        """Редактирует выбранное поле."""
        list_widget = self._get_current_list()
        if not list_widget:
            QMessageBox.warning(self, "Ошибка", "Выберите поле для редактирования")
            return
        
        item = list_widget.currentItem()
        if not item:
            return
        
        key = item.data(Qt.ItemDataRole.UserRole)
        field_config = self.fields_manager.get_field(key)
        
        if not field_config:
            return
        
        if not field_config.editable:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Это системное поле нельзя редактировать"
            )
            return
        
        dialog = FieldEditorDialog(field_config, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_config = dialog.get_field_config()
            if new_config:
                # Обновляем конфигурацию
                field_config.label = new_config.label
                field_config.type = new_config.type
                field_config.order = new_config.order
                self._load_fields()
                logger.info(f"Изменено поле: {key}")
    
    def _delete_field(self):
        """Удаляет выбранное поле."""
        list_widget = self._get_current_list()
        if not list_widget:
            QMessageBox.warning(self, "Ошибка", "Выберите поле для удаления")
            return
        
        item = list_widget.currentItem()
        if not item:
            return
        
        key = item.data(Qt.ItemDataRole.UserRole)
        field_config = self.fields_manager.get_field(key)
        
        if not field_config:
            return
        
        if not field_config.editable:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Это системное поле нельзя удалить"
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить поле '{field_config.label}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.fields_manager.remove_field(key)
            self._load_fields()
            logger.info(f"Удалено поле: {key}")
    
    def _move_up(self):
        """Перемещает поле вверх."""
        self._move_field(-1)
    
    def _move_down(self):
        """Перемещает поле вниз."""
        self._move_field(1)
    
    def _move_field(self, direction: int):
        """Перемещает поле в указанном направлении."""
        list_widget = self._get_current_list()
        if not list_widget:
            return
        
        current_row = list_widget.currentRow()
        if current_row < 0:
            return
        
        new_row = current_row + direction
        if new_row < 0 or new_row >= list_widget.count():
            return
        
        # Получаем ключи полей
        current_item = list_widget.item(current_row)
        target_item = list_widget.item(new_row)
        
        current_key = current_item.data(Qt.ItemDataRole.UserRole)
        target_key = target_item.data(Qt.ItemDataRole.UserRole)
        
        # Меняем order
        current_field = self.fields_manager.get_field(current_key)
        target_field = self.fields_manager.get_field(target_key)
        
        if current_field and target_field:
            current_field.order, target_field.order = target_field.order, current_field.order
            
            # Пересортировываем группу
            group_name = list_widget.property("group_name")
            group = self.fields_manager.groups.get(group_name)
            if group:
                group._sort_fields()
            
            self._load_fields()
            
            # Восстанавливаем выбор
            list_widget.setCurrentRow(new_row)
    
    def reject(self):
        """Отмена: откатываем правки, сделанные в живом синглтоне.

        Диалог редактирует объекты FieldsManager «на месте» (label/order/...),
        поэтому при отмене сбрасываем синглтон — конфиг перечитается с диска
        и несохранённые изменения не «протекут» в остальное приложение.
        """
        from config.fields_manager import reset_fields_manager
        reset_fields_manager()
        super().reject()

    def _save_and_close(self):
        """Сохраняет изменения и закрывает окно."""
        try:
            self.fields_manager.save_config()
            QMessageBox.information(
                self,
                "Успех",
                "Конфигурация сохранена.\nИзменения вступят в силу после перезапуска приложения."
            )
            self.accept()
        except Exception as exc:
            logger.exception("Ошибка сохранения конфигурации")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось сохранить конфигурацию:\n{exc}"
            )
