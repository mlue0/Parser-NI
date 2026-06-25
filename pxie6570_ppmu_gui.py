#!/usr/bin/env python3
"""Графическое приложение для измерения тока через PPMU платы PXIe-6570.

Приложение выполняет полный цикл работы с Parametric Measurement Unit (PPMU)
цифрового паттерн-генератора National Instruments PXIe-6570:

    1. Открытие сессии NI-Digital Pattern Driver.
    2. Переключение выбранных каналов в режим PPMU.
    3. Настройка лимита тока и подача напряжения на DUT.
    4. Измерение тока на каждом канале и отображение результатов в GUI.
    5. Отключение каналов и закрытие сессии.

Зависимости
-----------
- Python 3.10–3.13 (Kivy; на Windows нет wheel для 3.14)
- Пакет ``nidigital`` (``pip install -r requirements.txt``)
- Пакет ``kivy`` (GUI)
- Установленный NI-Digital Pattern Driver (см. ni.com/downloads)
- Плата PXIe-6570, видимая в NI MAX

Запуск
------
::

    pip install -r requirements.txt
    python pxie6570_ppmu_gui.py

Важно: именование каналов
-------------------------
``resource_name`` (например ``PXI-6570-1``) используется **только** при
создании ``nidigital.Session``. Каналы в API задаются **индексом** —
``session.channels[0]`` или ``session.channels[[0, 1, 2]]``, а **не** строкой
``"{resource_name}/0"``.

Формат поля «Каналы»: ``0``, ``0,2,5``, ``0-3``, ``0:3`` (как в NI-Digital
Repeated Capabilities).

См. документацию NI-Digital Repeated Capabilities:
https://nidigital.readthedocs.io/en/stable/rep_caps.html

Особенности PXIe-6570
---------------------
На платах PXIe-6570/6571 свойство ``ppmu_current_limit`` не поддерживается;
лимит тока задаётся через ``ppmu_current_limit_range``.
"""

from __future__ import annotations

import re
import threading
import time
from typing import TYPE_CHECKING

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

try:
    import nidigital
except ImportError:
    nidigital = None

if TYPE_CHECKING:
    from nidigital import Session

# Имя ресурса прибора в NI MAX (логическое или физическое, например PXI1Slot2).
DEFAULT_RESOURCE = "PXI-6570-1"

# Значения по умолчанию для полей ввода.
DEFAULT_CHANNELS = "0"
DEFAULT_VOLTAGE = "5.0"
DEFAULT_CURRENT_LIMIT = "0.01"

# Время интегрирования измерения PPMU, в секундах (4 мкс — типичное значение NI).
APERTURE_TIME_S = 4e-6

# Пауза после включения источника перед измерением, в секундах.
SETTLING_TIME_S = 0.01

# Результат измерения: (номер канала, ток в амперах).
ChannelMeasurement = tuple[int, float]


def parse_channels(text: str) -> list[int]:
    """Разбирает строку с номерами каналов в список индексов.

    Поддерживаемые форматы (как в nidigital repeated capabilities):

    - один канал: ``0``
    - список: ``0,2,5``
    - диапазон через дефис: ``0-3`` → 0, 1, 2, 3
    - диапазон через двоеточие: ``0:3`` → 0, 1, 2, 3

    Args:
        text: Строка из поля ввода каналов.

    Returns:
        Отсортированный список уникальных индексов каналов.

    Raises:
        ValueError: Пустая строка или неверный формат.
    """
    text = text.strip()
    if not text:
        raise ValueError("Укажите номера каналов (например: 0 или 0,1,2 или 0-3).")

    channels: list[int] = []
    for part in re.split(r"\s*,\s*", text):
        part = part.strip()
        if not part:
            continue

        range_match = re.fullmatch(r"(\d+)\s*[-:]\s*(\d+)", part)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            if end < start:
                raise ValueError(f"Неверный диапазон каналов: {part}")
            channels.extend(range(start, end + 1))
            continue

        if not part.isdigit():
            raise ValueError(f"Неверный номер канала: {part!r}")
        channels.append(int(part))

    if not channels:
        raise ValueError("Укажите хотя бы один канал.")

    return sorted(set(channels))


def parse_positive_float(text: str, field_name: str) -> float:
    """Разбирает положительное число с плавающей точкой из поля ввода.

    Args:
        text: Строка из TextInput.
        field_name: Имя поля для сообщения об ошибке.

    Returns:
        Разобранное значение.

    Raises:
        ValueError: Пустая строка, не число или значение ≤ 0.
    """
    text = text.strip().replace(",", ".")
    if not text:
        raise ValueError(f"Укажите {field_name}.")
    try:
        value = float(text)
    except ValueError as exc:
        raise ValueError(f"{field_name}: ожидается число, получено {text!r}.") from exc
    if value <= 0:
        raise ValueError(f"{field_name} должно быть больше нуля.")
    return value


def configure_ppmu_channels(
    session: Session,
    channel_indices: list[int],
    voltage_v: float,
    current_limit_a: float,
) -> None:
    """Настраивает PPMU на указанных каналах и включает источник напряжения.

    Args:
        session: Открытая сессия NI-Digital.
        channel_indices: Индексы каналов (не имена ресурса).
        voltage_v: Подаваемое напряжение, В.
        current_limit_a: Лимит тока, А.

    Note:
        Свойства задаются пакетно через ``session.channels[indices]``.
        ``ppmu_source()`` применяет настройки ко всем указанным каналам.
    """
    ch = session.channels[channel_indices]

    ch.selected_function = nidigital.SelectedFunction.PPMU
    ch.ppmu_output_function = nidigital.PPMUOutputFunction.VOLTAGE
    ch.ppmu_aperture_time = APERTURE_TIME_S
    ch.ppmu_aperture_time_units = nidigital.PPMUApertureTimeUnits.SECONDS

    # Проверка поддержки — по первому каналу (одинакова для всей платы).
    if session.channels[channel_indices[0]].ppmu_current_limit_supported:
        ch.ppmu_current_limit = current_limit_a
    else:
        ch.ppmu_current_limit_range = current_limit_a

    ch.ppmu_voltage_level = voltage_v
    ch.ppmu_source()
    time.sleep(SETTLING_TIME_S)


def measure_channels_current(
    session: Session,
    channel_indices: list[int],
) -> list[ChannelMeasurement]:
    """Измеряет ток PPMU на каждом из указанных каналов.

    Args:
        session: Открытая сессия с активным источником PPMU.
        channel_indices: Индексы каналов для измерения.

    Returns:
        Список пар (номер канала, ток в амперах) в порядке ``channel_indices``.
    """
    values = session.channels[channel_indices].ppmu_measure(
        nidigital.PPMUMeasurementType.CURRENT
    )
    return list(zip(channel_indices, values))


def disconnect_channels(session: Session, channel_indices: list[int]) -> None:
    """Отключает указанные каналы от PPMU.

    Args:
        session: Открытая сессия NI-Digital.
        channel_indices: Индексы каналов для отключения.
    """
    session.channels[channel_indices].selected_function = (
        nidigital.SelectedFunction.DISCONNECT
    )


def build_session_options(simulate: bool) -> str:
    """Формирует строку опций для конструктора ``nidigital.Session``.

    Args:
        simulate: Если True — работа без реального оборудования.

    Returns:
        Строка опций IVI или пустая строка для работы с реальным прибором.
    """
    if simulate:
        return "Simulate=1, DriverSetup=Model:6570"
    return ""


def run_measurement(
    resource_name: str,
    simulate: bool,
    channel_indices: list[int],
    voltage_v: float,
    current_limit_a: float,
) -> list[ChannelMeasurement]:
    """Выполняет полный цикл измерения на всех указанных каналах.

    Args:
        resource_name: Имя ресурса из NI MAX.
        simulate: Режим симуляции драйвера.
        channel_indices: Список индексов каналов.
        voltage_v: Подаваемое напряжение, В.
        current_limit_a: Лимит тока, А.

    Returns:
        Результаты измерения для каждого канала.

    Raises:
        nidigital.errors.DriverError: Ошибка драйвера NI-Digital.
    """
    options = build_session_options(simulate)

    with nidigital.Session(resource_name=resource_name, options=options) as session:
        configure_ppmu_channels(
            session, channel_indices, voltage_v, current_limit_a
        )
        results = measure_channels_current(session, channel_indices)
        disconnect_channels(session, channel_indices)
        return results


def format_measurements(results: list[ChannelMeasurement]) -> str:
    """Форматирует результаты измерений для отображения в GUI.

    Args:
        results: Список пар (канал, ток в амперах).

    Returns:
        Многострочная строка с результатами по каждому каналу.
    """
    lines = []
    for channel, current_a in results:
        lines.append(
            f"Канал {channel}: {current_a * 1e3:.6f} мА  ({current_a:.9f} А)"
        )
    return "\n".join(lines)


class SectionBox(BoxLayout):
    """Вертикальный блок с заголовком секции (аналог LabelFrame в Tkinter)."""

    def __init__(self, title: str, **kwargs) -> None:
        super().__init__(orientation="vertical", spacing=dp(6), **kwargs)
        self.add_widget(
            Label(
                text=title,
                size_hint_y=None,
                height=dp(28),
                bold=True,
                color=(0.85, 0.85, 0.9, 1),
            )
        )
        self.content = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            padding=(dp(8), dp(4), dp(8), dp(8)),
        )
        self.add_widget(self.content)


class PXIe6570App(App):
    """Kivy-приложение для измерения тока PPMU PXIe-6570."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.title = "PXIe-6570 PPMU — измерение тока"
        self._worker: threading.Thread | None = None

    def build(self):
        """Создаёт корневой виджет и возвращает его Kivy."""
        Window.size = (dp(500), dp(560))
        Window.minimum_width = dp(420)
        Window.minimum_height = dp(480)

        root = BoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(10),
        )

        root.add_widget(
            Label(
                text="PXIe-6570 PPMU",
                size_hint_y=None,
                height=dp(36),
                font_size=dp(20),
                bold=True,
            )
        )

        resource_row = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(40))
        resource_row.add_widget(
            Label(text="Resource name:", size_hint_x=None, width=dp(130), halign="left")
        )
        self.resource_input = TextInput(
            text=DEFAULT_RESOURCE,
            multiline=False,
            size_hint_x=1,
        )
        resource_row.add_widget(self.resource_input)
        root.add_widget(resource_row)

        simulate_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(36),
        )
        self.simulate_checkbox = CheckBox(active=False, size_hint_x=None, width=dp(32))
        simulate_row.add_widget(self.simulate_checkbox)
        simulate_row.add_widget(
            Label(text="Режим симуляции (без оборудования)", halign="left", valign="middle")
        )
        root.add_widget(simulate_row)

        params_section = SectionBox(title="Параметры PPMU", size_hint_y=None)
        params_section.height = dp(200)
        params_grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
        params_grid.bind(minimum_height=params_grid.setter("height"))

        params_grid.add_widget(Label(text="Каналы:", halign="left", size_hint_y=None, height=dp(36)))
        self.channels_input = TextInput(
            text=DEFAULT_CHANNELS,
            multiline=False,
            size_hint_y=None,
            height=dp(36),
            hint_text="0,1,2 или 0-3",
        )
        params_grid.add_widget(self.channels_input)

        params_grid.add_widget(Label(text="Напряжение, В:", halign="left", size_hint_y=None, height=dp(36)))
        self.voltage_input = TextInput(
            text=DEFAULT_VOLTAGE,
            multiline=False,
            size_hint_y=None,
            height=dp(36),
        )
        params_grid.add_widget(self.voltage_input)

        params_grid.add_widget(
            Label(text="Лимит тока, А:", halign="left", size_hint_y=None, height=dp(36))
        )
        self.current_limit_input = TextInput(
            text=DEFAULT_CURRENT_LIMIT,
            multiline=False,
            size_hint_y=None,
            height=dp(36),
        )
        params_grid.add_widget(self.current_limit_input)

        params_section.content.add_widget(
            Label(text="Режим: PPMU (source voltage, measure current)", size_hint_y=None, height=dp(24))
        )
        params_section.content.add_widget(params_grid)
        root.add_widget(params_section)

        self.measure_btn = Button(
            text="Измерить ток",
            size_hint_y=None,
            height=dp(44),
            background_color=(0.2, 0.55, 0.85, 1),
        )
        self.measure_btn.bind(on_press=self._on_measure)
        root.add_widget(self.measure_btn)

        result_section = SectionBox(title="Результат", size_hint_y=1)
        self.status_label = Label(
            text="Готово",
            size_hint_y=None,
            height=dp(24),
            halign="left",
            color=(0.75, 0.75, 0.8, 1),
        )
        self.results_label = Label(
            text="—",
            size_hint_y=None,
            halign="left",
            valign="top",
            font_size=dp(15),
            bold=True,
        )
        self.results_label.bind(
            texture_size=lambda inst, _size: setattr(inst, "height", inst.texture_size[1])
        )
        self.results_label.bind(
            size=lambda inst, val: setattr(inst, "text_size", (val[0], None))
        )

        results_scroll = ScrollView(size_hint_y=1)
        results_scroll.add_widget(self.results_label)

        result_section.content.add_widget(self.status_label)
        result_section.content.add_widget(results_scroll)
        root.add_widget(result_section)

        if nidigital is None:
            self.status_label.text = (
                "Ошибка: установите пакет nidigital (pip install -r requirements.txt)"
            )
            self.measure_btn.disabled = True

        return root

    def _collect_inputs(self) -> tuple[str, list[int], float, float]:
        """Читает и проверяет все поля ввода перед измерением.

        Returns:
            Кортеж (resource_name, channel_indices, voltage_v, current_limit_a).

        Raises:
            ValueError: Некорректные данные в любом из полей.
        """
        resource = self.resource_input.text.strip()
        if not resource:
            raise ValueError("Укажите resource name прибора.")

        channels = parse_channels(self.channels_input.text)
        voltage_v = parse_positive_float(self.voltage_input.text, "напряжение")
        current_limit_a = parse_positive_float(
            self.current_limit_input.text, "лимит тока"
        )
        return resource, channels, voltage_v, current_limit_a

    def _on_measure(self, *_args) -> None:
        """Обработчик нажатия кнопки «Измерить ток»."""
        if self._worker and self._worker.is_alive():
            return

        try:
            resource, channels, voltage_v, current_limit_a = self._collect_inputs()
        except ValueError as exc:
            self._show_error("Ошибка ввода", str(exc))
            return

        self.measure_btn.disabled = True
        self.status_label.text = "Выполняется измерение…"
        self.results_label.text = "—"

        simulate = self.simulate_checkbox.active
        self._worker = threading.Thread(
            target=self._measure_worker,
            args=(resource, simulate, channels, voltage_v, current_limit_a),
            daemon=True,
        )
        self._worker.start()

    def _measure_worker(
        self,
        resource_name: str,
        simulate: bool,
        channel_indices: list[int],
        voltage_v: float,
        current_limit_a: float,
    ) -> None:
        """Фоновый поток измерения."""
        try:
            results = run_measurement(
                resource_name,
                simulate,
                channel_indices,
                voltage_v,
                current_limit_a,
            )
        except Exception as exc:
            Clock.schedule_once(lambda _dt: self._on_measure_failed(str(exc)), 0)
            return

        Clock.schedule_once(lambda _dt, r=results: self._on_measure_done(r), 0)

    def _on_measure_done(self, results: list[ChannelMeasurement]) -> None:
        """Обновляет GUI после успешного измерения."""
        self.results_label.text = format_measurements(results)
        self.status_label.text = "Измерение завершено, сессия закрыта"
        self.measure_btn.disabled = False

    def _on_measure_failed(self, message: str) -> None:
        """Обновляет GUI и показывает диалог при ошибке."""
        self.status_label.text = "Ошибка"
        self.results_label.text = "—"
        self.measure_btn.disabled = False
        self._show_error("Ошибка NI-Digital", message)

    @staticmethod
    def _show_error(title: str, message: str) -> None:
        """Показывает модальное окно с текстом ошибки."""
        content = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(12))
        content.add_widget(Label(text=message, text_size=(dp(360), None)))
        close_btn = Button(text="OK", size_hint_y=None, height=dp(40))
        popup = Popup(
            title=title,
            content=content,
            size_hint=(None, None),
            size=(dp(400), dp(200)),
            auto_dismiss=False,
        )
        close_btn.bind(on_press=popup.dismiss)
        content.add_widget(close_btn)
        popup.open()


def main() -> None:
    """Точка входа: создаёт приложение и запускает главный цикл Kivy."""
    PXIe6570App().run()


if __name__ == "__main__":
    main()
