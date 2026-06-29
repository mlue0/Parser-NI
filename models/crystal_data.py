"""Pydantic-модель данных о разбраковке кристаллов."""

from __future__ import annotations

from typing import ClassVar

PLATE_MARKINGS: tuple[str, ...] = (
    "M3RV",
    "M1RV",
    "K03R",
    "K04",
    "K03",
    "K02",
    "K01",
    "HV101M",
    "HV232",
    "HV231",
    "HV252",
    "HV251",
    "HV24",
    "HV214",
    "HV222",
    "HV221",
    "HV212",
    "HV211",
    "HV19",
    "HV18",
    "HV174",
    "HV173",
    "HV172",
    "HV171",
    "HV16",
    "HV154",
    "HV153",
    "HV152",
    "HV151",
    "HV14",
    "HV13",
    "HV124",
    "HV121",
    "HV114",
    "HV113",
    "HV112",
    "HV111",
    "HV104",
    "HV103",
    "HV102",
    "HV101",
    "HV91",
    "HV84",
    "HV83",
    "HV82",
    "HV81",
    "HV74",
    "HV73",
    "HV72",
    "HV71",
    "HV64",
    "HV63",
    "HV62",
    "HV61",
)

HV_SUFFIXES: tuple[str, ...] = (
    "232",
    "231",
    "252",
    "251",
    "24",
    "214",
    "222",
    "221",
    "212",
    "211",
    "19",
    "18",
    "174",
    "173",
    "172",
    "171",
    "16",
    "154",
    "153",
    "152",
    "151",
    "14",
    "13",
    "124",
    "121",
    "114",
    "113",
    "112",
    "111",
    "104",
    "103",
    "102",
    "101",
    "91",
    "84",
    "83",
    "82",
    "81",
    "74",
    "73",
    "72",
    "71",
    "64",
    "63",
    "62",
    "61",
)

from pydantic import BaseModel, ConfigDict, Field, field_validator


SORTING_TARGETS: tuple[str, ...] = ("ПР-ОВ", "ОКР")

SORTING_TYPES: tuple[str, ...] = (
    "Разбраковка NI",
    "Разбраковка FORM",
)


FIELD_LABELS: dict[str, str] = {
    "good_crystals": "Годные кристаллы",
    "defective_crystals": "Бракованные кристаллы",
    "total_crystals": "Общее количество кристаллов",
    "defect_contact": "Брак по Contact",
    "defect_icc": "Брак по ICC",
    "defect_fc": "Брак по FC",
    "defect_static": "Брак по Static",
    "defect_inl": "Брак по INL",
    "defect_dnl": "Брак по DNL",
    "defect_burn": "Брак по Burn",
    "defect_u0_adc": "Брак по U0 в режиме АЦП",
    "norm_inl": "Норма INL",
    "norm_dnl": "Норма DNL",
    "norm_ufs": "Норма Ufs",
    "norm_u0": "Норма U0",
    "norm_u_perzhiganiya": "Норма U пережигания",
    "norm_u0_adc": "Норма U0 в режиме АЦП",
    "plate_marking": "Маркировка пластины",
    "firmware_number": "Номер зашивки",
    "correction_number": "Номер коррекции",
    "bmk_batch_number": "Номер партии БМК",
    "plate_number": "Номер пластины",
    "initial_crystals": "Исходное количество кристаллов",
    "sorting_type": "Тип разбраковки",
    "sorting_target": "Цель разбраковки (ПР-ОВ или ОКР)",
    "comment": "Комментарий",
}


# Соответствие русских заголовков в файлах и имён полей модели
HEADER_ALIASES: dict[str, str] = {label: key for key, label in FIELD_LABELS.items()}
HEADER_ALIASES.update(
    {
        "Цель разбраковки": "sorting_target",
        "Тип разбраковки": "sorting_type",
        "Брак по INL": "defect_inl",
        "Брак по DNL": "defect_dnl",
        "Брак по Burn": "defect_burn",
        "Брак по U0 в режиме АЦП": "defect_u0_adc",
        "Норма INL": "norm_inl",
        "Норма DNL": "norm_dnl",
        "Норма Ufs": "norm_ufs",
        "Норма U0": "norm_u0",
        "Норма U пережигания": "norm_u_perzhiganiya",
        "Норма U0 в режиме АЦП": "norm_u0_adc",
    }
)


def get_correction_options(plate_marking: str) -> tuple[str, ...]:
    """Возвращает список вариантов номера коррекции для маркировки."""
    normalized = plate_marking.strip().upper()
    # Handle HV-prefixed or HV-suffixed markings and explicit known markings.
    if normalized.startswith("HV") or normalized.endswith("HV"):
        return (normalized,)
    if normalized in {"M3RV", "M1RV", "K03R", "K04", "K03", "K02", "K01", "HV101M"}:
        return (normalized,)
    return (normalized, "")


def get_firmware_options(plate_marking: str) -> tuple[str, ...]:
    """Возвращает список вариантов номера зашивки для маркировки."""
    normalized = plate_marking.strip().upper()
    if normalized.startswith("HV") or normalized.endswith("HV"):
        return (normalized,)
    if normalized in {"M3RV", "M1RV", "K03R", "K04", "K03", "K02", "K01", "HV101M"}:
        return (normalized,)
    return (normalized,)


def get_initial_crystals_default(plate_marking: str) -> int:
    """Возвращает рекомендуемое исходное количество кристаллов по маркировке."""
    normalized = plate_marking.strip().upper()
    defaults = {
        "M3RV": 200,
        "M1RV": 250,
        "K03R": 300,
        "K04": 320,
        "K03": 350,
        "K02": 360,
        "K01": 380,
        "HV101M": 400,
    }
    return defaults.get(normalized, 0)


class CrystalData(BaseModel):
    """Данные разбраковки кристаллов для отправки в API."""

    model_config = ConfigDict(str_strip_whitespace=True)

    good_crystals: int = Field(..., ge=0, description="Годные кристаллы")
    defective_crystals: int = Field(..., ge=0, description="Бракованные кристаллы")
    total_crystals: int = Field(..., ge=0, description="Общее количество кристаллов")
    defect_contact: int = Field(..., ge=0, description="Брак по Contact")
    defect_icc: int = Field(..., ge=0, description="Брак по ICC")
    defect_fc: int = Field(..., ge=0, description="Брак по FC")
    defect_static: int = Field(..., ge=0, description="Брак по Static")
    defect_inl: int = Field(..., ge=0, description="Брак по INL")
    defect_dnl: int = Field(..., ge=0, description="Брак по DNL")
    defect_burn: int = Field(..., ge=0, description="Брак по Burn")
    defect_u0_adc: int = Field(..., ge=0, description="Брак по U0 в режиме АЦП")
    plate_marking: str = Field(..., min_length=1, description="Маркировка пластины")
    firmware_number: str = Field(default="", description="Номер зашивки")
    correction_number: str = Field(default="", description="Номер коррекции")
    bmk_batch_number: str = Field(..., min_length=1, description="Номер партии БМК")
    plate_number: str = Field(..., min_length=1, description="Номер пластины")
    initial_crystals: int = Field(..., ge=0, description="Исходное количество кристаллов")
    sorting_type: str = Field(default="Разбраковка NI", min_length=1, description="Тип разбраковки")
    sorting_target: str = Field(default="ПР-ОВ", description="Цель разбраковки")
    norm_inl: str = Field(default="", description="Норма INL")
    norm_dnl: str = Field(default="", description="Норма DNL")
    norm_ufs: str = Field(default="", description="Норма Ufs")
    norm_u0: str = Field(default="", description="Норма U0")
    norm_u_perzhiganiya: str = Field(default="", description="Норма U пережигания")
    norm_u0_adc: str = Field(default="", description="Норма U0 в режиме АЦП")
    comment: str = Field(default="", description="Комментарий")

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "plate_marking",
        "bmk_batch_number",
        "plate_number",
    )

    @field_validator("sorting_target")
    @classmethod
    def validate_sorting_target(cls, value: str) -> str:
        if value not in SORTING_TARGETS:
            allowed = ", ".join(SORTING_TARGETS)
            raise ValueError(f"Допустимые значения: {allowed}")
        return value

    @field_validator("sorting_type")
    @classmethod
    def validate_sorting_type(cls, value: str) -> str:
        # Разрешаем любое непустое значение, но проверяем что оно не пустое
        if not value or not value.strip():
            # Если пустое - используем дефолт
            return "Разбраковка NI"
        return value.strip()

    def to_api_payload(self) -> dict:
        """Преобразует модель в JSON для REST API."""
        return self.model_dump(mode="json")

    def labeled_values(self) -> list[tuple[str, str]]:
        """Возвращает пары (метка, значение) для отображения пользователю."""
        data = self.model_dump()
        return [(FIELD_LABELS[key], str(data[key])) for key in FIELD_LABELS]
