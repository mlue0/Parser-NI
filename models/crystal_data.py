"""Pydantic-модель данных о разбраковке кристаллов."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


SORTING_TARGETS: tuple[str, ...] = ("ПР-ОВ", "ОКР")

SORTING_TYPES: tuple[str, ...] = (
    "Полная",
    "Частичная",
    "Контрольная",
    "Повторная",
)


FIELD_LABELS: dict[str, str] = {
    "good_crystals": "Годные кристаллы",
    "defective_crystals": "Бракованные кристаллы",
    "total_crystals": "Общее количество кристаллов",
    "defect_contact": "Брак по Contact",
    "defect_icc": "Брак по Icc",
    "defect_fc": "Брак по FC",
    "defect_static": "Брак по Static",
    "plate_marking": "Маркировка пластины",
    "firmware_number": "Номер зашивки",
    "correction_number": "Номер коррекции",
    "bmk_batch_number": "Номер партии БМК",
    "plate_number": "Номер пластины",
    "initial_crystals": "Исходное количество кристаллов",
    "sorting_type": "Тип разбраковки",
    "sorting_target": "Цель разбраковки (ПР-ОВ или ОКР)",
}


# Соответствие русских заголовков в файлах и имён полей модели
HEADER_ALIASES: dict[str, str] = {label: key for key, label in FIELD_LABELS.items()}
HEADER_ALIASES.update(
    {
        "Цель разбраковки": "sorting_target",
        "Тип разбраковки": "sorting_type",
    }
)


class CrystalData(BaseModel):
    """Данные разбраковки кристаллов для отправки в API."""

    model_config = ConfigDict(str_strip_whitespace=True)

    good_crystals: int = Field(..., ge=0, description="Годные кристаллы")
    defective_crystals: int = Field(..., ge=0, description="Бракованные кристаллы")
    total_crystals: int = Field(..., ge=0, description="Общее количество кристаллов")
    defect_contact: int = Field(..., ge=0, description="Брак по Contact")
    defect_icc: int = Field(..., ge=0, description="Брак по Icc")
    defect_fc: int = Field(..., ge=0, description="Брак по FC")
    defect_static: int = Field(..., ge=0, description="Брак по Static")
    plate_marking: str = Field(..., min_length=1, description="Маркировка пластины")
    firmware_number: str = Field(..., min_length=1, description="Номер зашивки")
    correction_number: str = Field(..., min_length=1, description="Номер коррекции")
    bmk_batch_number: str = Field(..., min_length=1, description="Номер партии БМК")
    plate_number: str = Field(..., min_length=1, description="Номер пластины")
    initial_crystals: int = Field(..., ge=0, description="Исходное количество кристаллов")
    sorting_type: str = Field(..., min_length=1, description="Тип разбраковки")
    sorting_target: str = Field(..., description="Цель разбраковки")

    REQUIRED_STRING_FIELDS: ClassVar[tuple[str, ...]] = (
        "plate_marking",
        "firmware_number",
        "correction_number",
        "bmk_batch_number",
        "plate_number",
        "sorting_type",
        "sorting_target",
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
        if not value.strip():
            raise ValueError("Тип разбраковки обязателен")
        return value

    def to_api_payload(self) -> dict:
        """Преобразует модель в JSON для REST API."""
        return self.model_dump(mode="json")

    def labeled_values(self) -> list[tuple[str, str]]:
        """Возвращает пары (метка, значение) для отображения пользователю."""
        data = self.model_dump()
        return [(FIELD_LABELS[key], str(data[key])) for key in FIELD_LABELS]
