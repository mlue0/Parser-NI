"""Динамическая модель данных о разбраковке кристаллов."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, create_model, field_validator, model_validator

from config.fields_manager import get_fields_manager
from logs.setup import get_logger

logger = get_logger(__name__)

# Константы остаются для обратной совместимости
PLATE_MARKINGS: tuple[str, ...] = (
    "M3RV", "M1RV", "K03R", "K04", "K03", "K02", "K01", "HV101M",
    "HV232", "HV231", "HV252", "HV251", "HV24", "HV214", "HV222", "HV221",
    "HV212", "HV211", "HV19", "HV18", "HV174", "HV173", "HV172", "HV171",
    "HV16", "HV154", "HV153", "HV152", "HV151", "HV14", "HV13", "HV124",
    "HV121", "HV114", "HV113", "HV112", "HV111", "HV104", "HV103", "HV102",
    "HV101", "HV91", "HV84", "HV83", "HV82", "HV81", "HV74", "HV73",
    "HV72", "HV71", "HV64", "HV63", "HV62", "HV61",
)

SORTING_TARGETS: tuple[str, ...] = ("ПР-ОВ", "ОКР")
SORTING_TYPES: tuple[str, ...] = ("Разбраковка NI", "Разбраковка FORM")


def create_dynamic_crystal_data_model(data: dict[str, Any]) -> type[BaseModel]:
    """Создаёт динамическую Pydantic модель на основе данных.
    
    Args:
        data: Словарь с данными, полученными из парсера
        
    Returns:
        Класс Pydantic модели с полями на основе данных
    """
    fields_manager = get_fields_manager()
    
    # Получаем конфигурацию полей на основе данных
    field_configs = fields_manager.get_fields_from_data(data)
    
    # Создаём словарь полей для Pydantic
    model_fields: dict[str, Any] = {}
    
    for field_config in field_configs:
        # Определяем тип поля
        if field_config.type == "integer":
            field_type = int
            field_params = {"ge": field_config.min_value or 0}
        elif field_config.type == "float":
            field_type = float
            field_params = {"ge": field_config.min_value or 0.0}
        else:  # string
            field_type = str
            field_params = {}
        
        # Определяем дефолтное значение
        if field_config.required:
            # Обязательное поле без дефолта → ... (Pydantic «required»)
            default = field_config.default_value if field_config.default_value is not None else ...
        else:
            # Для опциональных полей используем дефолт или 0/""
            if field_config.default_value is not None:
                default = field_config.default_value
            elif field_config.type == "integer":
                default = 0
            elif field_config.type == "float":
                default = 0.0
            else:
                default = ""
        
        # Создаём Field
        if default == ...:
            model_fields[field_config.key] = (
                field_type,
                Field(..., description=field_config.label, **field_params),
            )
        else:
            model_fields[field_config.key] = (
                field_type,
                Field(default=default, description=field_config.label, **field_params),
            )
    
    # Эти поля всегда имеют дефолт — перезаписываем даже если пришли из field_configs,
    # чтобы пустая строка из формы не вызывала ValidationError
    model_fields["sorting_type"] = (
        str,
        Field(default="Разбраковка NI", description="Тип разбраковки"),
    )
    model_fields["sorting_target"] = (
        str,
        Field(default="ПР-ОВ", description="Цель разбраковки"),
    )
    if "comment" not in model_fields:
        model_fields["comment"] = (
            str,
            Field(default="", description="Комментарий"),
        )
    
    # Базовый класс с валидаторами — единственный надёжный способ в Pydantic v2
    # для добавления валидаторов к динамическим моделям
    class _CrystalBase(BaseModel):
        # coerce_numbers_to_str: парсеры теперь возвращают числа типизированно
        # (напр. номер партии 240711 как int), а строковые поля должны их принять.
        model_config = {
            "arbitrary_types_allowed": True,
            "coerce_numbers_to_str": True,
        }

        @field_validator("sorting_type", mode="before", check_fields=False)
        @classmethod
        def _val_sorting_type(cls, value: Any) -> str:
            if not value or not str(value).strip():
                return "Разбраковка NI"
            return str(value).strip()

        @field_validator("sorting_target", mode="before", check_fields=False)
        @classmethod
        def _val_sorting_target(cls, value: Any) -> str:
            v = str(value).strip() if value else ""
            if not v:
                return "ПР-ОВ"
            if v not in SORTING_TARGETS:
                return "ПР-ОВ"  # мягкий фолбэк вместо ошибки
            return v

        @model_validator(mode="after")
        def _val_crystal_sums(self) -> _CrystalBase:
            data = self.__dict__
            good = data.get("good_crystals")
            bad = data.get("defective_crystals")
            total = data.get("total_crystals")
            warnings: list[str] = []
            if None not in (good, bad, total) and good + bad != total:
                warnings.append(
                    f"Годные ({good}) + Бракованные ({bad}) ≠ Общее ({total})"
                )
            defect_keys = [
                "defect_contact", "defect_icc", "defect_fc", "defect_static",
                "defect_inl", "defect_dnl", "defect_burn", "defect_u0_adc",
            ]
            defect_sum = sum(data.get(k) or 0 for k in defect_keys if k in data)
            if bad is not None and defect_sum > bad:
                warnings.append(
                    f"Сумма видов брака ({defect_sum}) > Бракованных кристаллов ({bad})"
                )
            if warnings:
                self.__dict__["_cross_field_warnings"] = warnings
            return self

    # Создаём динамическую модель с валидаторами из базового класса
    DynamicModel = create_model(
        "DynamicCrystalData",
        __base__=_CrystalBase,
        **model_fields,
    )
    
    # Добавляем метод to_api_payload
    def to_api_payload(self) -> dict:
        """Преобразует модель в JSON для REST API."""
        return self.model_dump(mode="json")
    
    DynamicModel.to_api_payload = to_api_payload
    
    # Добавляем метод labeled_values
    def labeled_values(self) -> list[tuple[str, str]]:
        """Возвращает пары (метка, значение) для отображения."""
        result = []
        data_dict = self.model_dump()
        
        for field_config in field_configs:
            if field_config.key in data_dict:
                value = data_dict[field_config.key]
                result.append((field_config.label, str(value)))
        
        # Добавляем стандартные поля
        if "sorting_type" in data_dict:
            result.append(("Тип разбраковки", str(data_dict["sorting_type"])))
        if "sorting_target" in data_dict:
            result.append(("Цель разбраковки", str(data_dict["sorting_target"])))
        if "comment" in data_dict:
            result.append(("Комментарий", str(data_dict["comment"])))
        
        return result
    
    DynamicModel.labeled_values = labeled_values

    # Доступ к предупреждениям кросс-валидации (заполняются в _val_crystal_sums)
    def cross_field_warnings(self) -> list[str]:
        """Возвращает предупреждения кросс-валидации (может быть пустым)."""
        return list(self.__dict__.get("_cross_field_warnings", []))

    DynamicModel.cross_field_warnings = cross_field_warnings

    logger.info(f"Создана динамическая модель с {len(model_fields)} полями")

    return DynamicModel


def get_field_label(key: str) -> str:
    """Возвращает label поля по ключу."""
    fields_manager = get_fields_manager()
    field_config = fields_manager.get_field(key)
    
    if field_config:
        return field_config.label
    
    # Fallback на старую систему
    from models.crystal_data import FIELD_LABELS
    return FIELD_LABELS.get(key, key)


# Кэш алиасов. Привязан к экземпляру FieldsManager: после reset_fields_manager()
# создаётся новый экземпляр, и кэш автоматически считается недействительным.
_aliases_cache: dict[str, str] | None = None
_aliases_cache_owner: object | None = None


def get_field_aliases() -> dict[str, str]:
    """Возвращает словарь {русское_название: key} для парсинга.

    Включает:
    - метки полей из fields_config.json (label → key)
    - дополнительные синонимы для норм (файлы используют «Норма по X» и «Норма X»)
    - стандартные системные поля

    Результат кэшируется до пересоздания менеджера полей.
    """
    global _aliases_cache, _aliases_cache_owner
    fields_manager = get_fields_manager()
    if _aliases_cache is not None and _aliases_cache_owner is fields_manager:
        return _aliases_cache

    all_fields = fields_manager.get_all_fields()

    aliases: dict[str, str] = {}
    for field_config in all_fields:
        aliases[field_config.label] = field_config.key

    # ── Алиасы для норм ──────────────────────────────────────────────────────
    # Файлы пишут «Норма по ICC» или «Норма ICC»; label в конфиге — «Норма Icc».
    # Перечисляем все реальные варианты написания.
    _NORM_ALIASES: dict[str, str] = {
        # Цифровые
        "Норма по ICC":              "norm_icc",
        "Норма ICC":                 "norm_icc",
        "Норма Icc":                 "norm_icc",
        "Норма по Icc":              "norm_icc",
        # Аналоговые
        "Норма по INL":              "norm_inl",
        "Норма INL":                 "norm_inl",
        "Норма по DNL":              "norm_dnl",
        "Норма DNL":                 "norm_dnl",
        "Норма по Ufs":              "norm_ufs",
        "Норма Ufs":                 "norm_ufs",
        "Норма по U0":               "norm_u0",
        "Норма U0":                  "norm_u0",
        "Норма по U пережигания":    "norm_u_perzhiganiya",
        "Норма U пережигания":       "norm_u_perzhiganiya",
        "Норма по U0 в режиме АЦП":  "norm_u0_adc",
        "Норма U0 АЦП":              "norm_u0_adc",
        "Норма U0 в режиме АЦП":     "norm_u0_adc",
        "Норма по IoCC":             "norm_iocc",
        "Норма IoCC":                "norm_iocc",
        "Норма по IIL":              "norm_iil",
        "Норма IIL":                 "norm_iil",
        "Норма по IIH":              "norm_iih",
        "Норма IIH":                 "norm_iih",
        "Норма по IOH":              "norm_ioh",
        "Норма IOH":                 "norm_ioh",
        "Норма по IOL":              "norm_iol",
        "Норма IOL":                 "norm_iol",
        "Норма по UoL":              "norm_uol",
        "Норма UoL":                 "norm_uol",
        "Норма по UoH":              "norm_uoh",
        "Норма UoH":                 "norm_uoh",
        "Норма по Ro":               "norm_ro",
        "Норма Ro":                  "norm_ro",
    }
    aliases.update(_NORM_ALIASES)

    # ── Стандартные системные поля ───────────────────────────────────────────
    aliases.update({
        "Тип разбраковки": "sorting_type",
        "Цель разбраковки": "sorting_target",
        "Комментарий": "comment",
    })

    _aliases_cache = aliases
    _aliases_cache_owner = fields_manager
    return aliases
