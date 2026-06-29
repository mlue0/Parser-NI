"""Менеджер конфигурации полей приложения."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from logs.setup import get_logger

logger = get_logger(__name__)


@dataclass
class FieldConfig:
    """Конфигурация одного поля."""

    key: str
    label: str
    type: str  # 'string', 'integer', 'float'
    required: bool = False
    editable: bool = True
    min_value: int | None = None
    max_value: int | None = None
    default_value: Any = None
    order: int = 0
    group: str = ""
    tab: str = ""
    choices: list = field(default_factory=list)
    widget_type: str = ""  # '', 'textarea'
    unit: str = ""          # единица измерения для отображения рядом с полем, напр. «мкА», «В»

    def to_dict(self) -> dict[str, Any]:
        """Преобразует в словарь."""
        d: dict[str, Any] = {
            "key": self.key,
            "label": self.label,
            "type": self.type,
            "required": self.required,
            "editable": self.editable,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "default_value": self.default_value,
            "order": self.order,
        }
        if self.choices:
            d["choices"] = self.choices
        if self.widget_type:
            d["widget_type"] = self.widget_type
        if self.unit:
            d["unit"] = self.unit
        return d


@dataclass
class FieldGroup:
    """Группа полей."""

    name: str
    title: str
    description: str
    plate_type: str | None = None  # 'digital', 'analog', None = оба
    tab: str = ""
    fields: list[FieldConfig] = field(default_factory=list)
    
    def add_field(self, field_config: FieldConfig) -> None:
        """Добавляет поле в группу."""
        field_config.group = self.name
        field_config.tab = self.tab
        self.fields.append(field_config)
        self._sort_fields()
    
    def remove_field(self, key: str) -> bool:
        """Удаляет поле из группы."""
        for i, f in enumerate(self.fields):
            if f.key == key:
                self.fields.pop(i)
                return True
        return False
    
    def move_field(self, key: str, new_order: int) -> bool:
        """Перемещает поле на новую позицию."""
        for f in self.fields:
            if f.key == key:
                f.order = new_order
                self._sort_fields()
                return True
        return False
    
    def _sort_fields(self) -> None:
        """Сортирует поля по order."""
        self.fields.sort(key=lambda f: f.order)


# Sentinel-значение для параметра plate_type_override
# (чтобы отличить "не передано" от None = авто)
_SENTINEL = object()


class FieldsManager:
    """Менеджер конфигурации полей приложения."""

    SCHEMA_VERSION = "1.1.0"

    def __init__(self, config_path: Path | str | None = None):
        if config_path is None:
            from config.settings import BASE_DIR
            config_path = BASE_DIR / "config" / "fields_config.json"

        self.config_path = Path(config_path)
        self.groups: dict[str, FieldGroup] = {}
        self.settings: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Загружает конфигурацию из JSON файла, при необходимости мигрирует."""
        if not self.config_path.exists():
            logger.warning(f"Конфигурация полей не найдена: {self.config_path}")
            self._create_default_config()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Миграция схемы если версия устарела
            file_version = config.get("version", "1.0.0")
            if file_version != self.SCHEMA_VERSION:
                config = self._migrate_config(config, file_version)

            self.settings = config.get("settings", {})
            
            # Загружаем группы полей
            field_groups = config.get("field_groups", {})
            for group_name, group_data in field_groups.items():
                group = FieldGroup(
                    name=group_name,
                    title=group_data.get("title", group_name),
                    description=group_data.get("description", ""),
                    plate_type=group_data.get("plate_type"),
                    tab=group_data.get("tab", ""),
                )
                
                # Загружаем поля группы
                for field_data in group_data.get("fields", []):
                    field_config = FieldConfig(
                        key=field_data["key"],
                        label=field_data["label"],
                        type=field_data.get("type", "string"),
                        required=field_data.get("required", False),
                        editable=field_data.get("editable", True),
                        min_value=field_data.get("min_value"),
                        max_value=field_data.get("max_value"),
                        default_value=field_data.get("default_value"),
                        order=field_data.get("order", 0),
                        choices=field_data.get("choices", []),
                        widget_type=field_data.get("widget_type", ""),
                        unit=field_data.get("unit", ""),
                    )
                    group.add_field(field_config)
                
                self.groups[group_name] = group
            
            logger.info(f"Загружена конфигурация полей из {self.config_path}")
            
        except Exception as exc:
            logger.exception(f"Ошибка загрузки конфигурации: {exc}")
            self._create_default_config()
    
    def _migrate_config(self, config: dict[str, Any], from_version: str) -> dict[str, Any]:
        """Мигрирует конфиг от старой версии к текущей, сохраняя пользовательские поля."""
        logger.info("Миграция конфига полей: %s → %s", from_version, self.SCHEMA_VERSION)

        # Сохраняем бэкап старого конфига
        backup_path = self.config_path.with_suffix(f".{from_version}.bak.json")
        try:
            backup_path.write_text(
                json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info("Бэкап конфига сохранён: %s", backup_path)
        except OSError as exc:
            logger.warning("Не удалось сохранить бэкап конфига: %s", exc)

        # Извлекаем пользовательские поля из старого конфига
        user_fields: list[dict] = []
        old_groups = config.get("field_groups", {})
        if "custom_fields" in old_groups:
            user_fields = old_groups["custom_fields"].get("fields", [])

        # Загружаем свежий конфиг из файла по умолчанию
        default_path = self.config_path.parent / "fields_config.default.json"
        if default_path.exists():
            try:
                with open(default_path, encoding="utf-8") as f:
                    new_config = json.load(f)
            except Exception:
                new_config = config  # fallback
        else:
            # Нет дефолтного файла — обновляем только версию и возвращаем как есть
            config["version"] = self.SCHEMA_VERSION
            # Переносим пользовательские поля
            if user_fields and "custom_fields" in config.get("field_groups", {}):
                config["field_groups"]["custom_fields"]["fields"] = user_fields
            return config

        # Переносим пользовательские поля в новый конфиг
        if user_fields and "custom_fields" in new_config.get("field_groups", {}):
            new_config["field_groups"]["custom_fields"]["fields"] = user_fields
            logger.info("Перенесено %d пользовательских полей", len(user_fields))

        new_config["version"] = self.SCHEMA_VERSION

        # Сохраняем смигрированный конфиг
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(new_config, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.error("Не удалось сохранить смигрированный конфиг: %s", exc)

        return new_config

    def _create_default_config(self) -> None:
        """Создаёт конфигурацию по умолчанию."""
        logger.info("Создание конфигурации по умолчанию")
        # Базовая конфигурация создаётся при первом запуске
    
    def save_config(self) -> None:
        """Сохраняет конфигурацию в JSON файл и сбрасывает синглтон."""
        config = {
            "version": self.SCHEMA_VERSION,
            "description": "Конфигурация полей для SimpleMeasure",
            "field_groups": {},
            "settings": self.settings,
        }

        for group_name, group in self.groups.items():
            config["field_groups"][group_name] = {
                "title": group.title,
                "description": group.description,
                "plate_type": group.plate_type,
                "tab": group.tab,
                "fields": [f.to_dict() for f in group.fields],
            }

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info(f"Конфигурация сохранена в {self.config_path}")
            # Сбрасываем синглтон — при следующем обращении конфиг перечитается
            reset_fields_manager()
        except Exception as exc:
            logger.exception(f"Ошибка сохранения конфигурации: {exc}")
    
    def get_all_fields(self, plate_type: str | None = None) -> list[FieldConfig]:
        """Возвращает все поля, опционально фильтруя по типу пластины.

        Порядок групп соответствует порядку в конфиге (JSON insertion order).
        Внутри каждой группы поля сортируются по полю order.
        """
        fields = []
        for group in self.groups.values():
            # Фильтруем по типу пластины если указан
            if plate_type and group.plate_type and group.plate_type != plate_type:
                continue
            # Сортируем только внутри группы, сохраняя порядок групп из конфига
            fields.extend(sorted(group.fields, key=lambda f: f.order))
        return fields
    
    def get_fields_by_group(self, group_name: str) -> list[FieldConfig]:
        """Возвращает поля конкретной группы."""
        group = self.groups.get(group_name)
        return group.fields if group else []
    
    def get_field(self, key: str) -> FieldConfig | None:
        """Находит поле по ключу."""
        for group in self.groups.values():
            for field_config in group.fields:
                if field_config.key == key:
                    return field_config
        return None
    
    def add_custom_field(
        self,
        key: str,
        label: str,
        field_type: str = "string",
        group: str = "custom_fields",
    ) -> FieldConfig:
        """Добавляет пользовательское поле."""
        if group not in self.groups:
            self.groups[group] = FieldGroup(
                name=group,
                title="Пользовательские поля",
                description="Поля, добавленные пользователем",
            )
        
        # Определяем order как максимальный + 1
        max_order = max(
            (f.order for f in self.groups[group].fields),
            default=0,
        )
        
        field_config = FieldConfig(
            key=key,
            label=label,
            type=field_type,
            required=False,
            editable=True,
            order=max_order + 1,
        )
        
        self.groups[group].add_field(field_config)
        logger.info(f"Добавлено пользовательское поле: {key} ({label})")
        
        return field_config
    
    def remove_field(self, key: str) -> bool:
        """Удаляет поле."""
        for group in self.groups.values():
            if group.remove_field(key):
                logger.info(f"Удалено поле: {key}")
                return True
        return False
    
    def get_fields_from_data(
        self,
        data: dict[str, Any],
        plate_type_override: str | None = _SENTINEL,
    ) -> list[FieldConfig]:
        """Возвращает список полей на основе распарсенных данных.

        Args:
            data: распарсенные данные из файла
            plate_type_override: принудительный тип пластины ("digital" | "analog" | None).
                Если не передан — читает из app_state.json, затем авто-определяет.
        """
        if not self.settings.get("show_only_parsed_fields", True):
            return self.get_all_fields()

        # Определяем тип пластины
        if plate_type_override is _SENTINEL:
            # Приоритет: сохранённый override → авто-определение
            from config.settings import load_plate_type_override
            plate_type_override = load_plate_type_override()

        plate_type = plate_type_override if plate_type_override is not None \
            else self._detect_plate_type(data)
        
        # Собираем поля, которые есть в данных
        result_fields = []
        all_fields = self.get_all_fields(plate_type)
        
        for field_config in all_fields:
            # Обязательные поля всегда включаем
            if field_config.required:
                result_fields.append(field_config)
                continue

            # Редактируемые поля всегда показываем — пользователь заполнит сам
            if field_config.editable:
                result_fields.append(field_config)
                continue

            # Нередактируемые необязательные поля — только если есть в данных
            if field_config.key in data and data[field_config.key] is not None:
                result_fields.append(field_config)
        
        return result_fields
    
    def _detect_plate_type(self, data: dict[str, Any]) -> str | None:
        """Определяет тип пластины по наличию полей.
        
        Если есть аналоговые поля (INL, DNL, etc.) - аналоговая,
        иначе - цифровая.
        """
        if not self.settings.get("auto_detect_plate_type", True):
            return None
        
        analog_indicators = ["defect_inl", "defect_dnl", "defect_burn", "norm_inl", "norm_dnl"]
        
        for key in analog_indicators:
            if key in data and data[key] is not None:
                value = data[key]
                # Проверяем что значение не пустое
                if isinstance(value, str) and value.strip():
                    return "analog"
                elif isinstance(value, (int, float)) and value != 0:
                    return "analog"
        
        return "digital"


# Глобальный экземпляр менеджера
_fields_manager: FieldsManager | None = None


def get_fields_manager() -> FieldsManager:
    """Возвращает глобальный экземпляр менеджера полей."""
    global _fields_manager
    if _fields_manager is None:
        _fields_manager = FieldsManager()
    return _fields_manager


def reset_fields_manager() -> None:
    """Сбрасывает синглтон — при следующем вызове get_fields_manager конфиг перечитается."""
    global _fields_manager
    _fields_manager = None
