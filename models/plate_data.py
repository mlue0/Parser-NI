"""Pydantic-модель данных пластины (режим «Добавить пластину»)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.crystal_data import SORTING_TARGETS

# Поля формы добавления пластины в требуемом порядке (key → подпись).
PLATE_FIELD_LABELS: dict[str, str] = {
    "plate_marking": "Маркировка пластины",
    "firmware_number": "Номер зашивки",
    "correction_number": "Номер коррекции",
    "sorting_target": "Цель разбраковки",
    "bmk_batch_number": "Номер партии БМК",
    "plate_number": "Номер пластины",
    "initial_crystals": "Исходное количество кристаллов",
    "sorting_type": "Тип разбраковки",
    "comment": "Комментарий",
}


class PlateData(BaseModel):
    """Данные новой пластины для занесения в базу."""

    # coerce_numbers_to_str — на случай, если номера пришли числами.
    model_config = ConfigDict(str_strip_whitespace=True, coerce_numbers_to_str=True)

    plate_marking: str = Field(..., min_length=1, description="Маркировка пластины")
    firmware_number: str = Field(default="", description="Номер зашивки")
    correction_number: str = Field(default="", description="Номер коррекции")
    sorting_target: str = Field(default="ПР-ОВ", description="Цель разбраковки")
    bmk_batch_number: str = Field(..., min_length=1, description="Номер партии БМК")
    plate_number: str = Field(..., min_length=1, description="Номер пластины")
    initial_crystals: int = Field(default=0, ge=0, description="Исходное количество кристаллов")
    sorting_type: str = Field(default="Разбраковка NI", description="Тип разбраковки")
    comment: str = Field(default="", description="Комментарий")

    @field_validator("sorting_target")
    @classmethod
    def _validate_sorting_target(cls, value: str) -> str:
        # Мягкий фолбэк к значению по умолчанию, если пришло что-то иное.
        return value if value in SORTING_TARGETS else "ПР-ОВ"

    @field_validator("sorting_type")
    @classmethod
    def _validate_sorting_type(cls, value: str) -> str:
        return value.strip() or "Разбраковка NI"

    def to_api_payload(self) -> dict:
        """Преобразует модель в JSON для REST API."""
        return self.model_dump(mode="json")

    def labeled_values(self) -> list[tuple[str, str]]:
        """Пары (метка, значение) для отображения пользователю."""
        data = self.model_dump()
        return [(label, str(data[key])) for key, label in PLATE_FIELD_LABELS.items()]
