#!/usr/bin/env python3
"""Графическое приложение для измерения тока через PPMU платы PXIe-6570.

Приложение выполняет полный цикл работы с Parametric Measurement Unit (PPMU)
цифрового паттерн-генератора National Instruments PXIe-6570:

    1. Открытие сессии NI-Digital Pattern Driver.
    2. Переключение канала в режим PPMU.
    3. Настройка лимита тока и подача напряжения на DUT.
    4. Измерение тока и отображение результата в GUI.
    5. Отключение канала и закрытие сессии.

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
``session.channels[0]``, а **не** строкой ``"{resource_name}/0"``.

Строка вида ``PXI-6570-1/0`` вызывает ошибку парсера repeated capabilities,
потому что символ ``-`` интерпретируется как диапазон (``0-2``), а в имени
ресурса дефисов несколько.

См. документацию NI-Digital Repeated Capabilities:
https://nidigital.readthedocs.io/en/stable/rep_caps.html

Особенности PXIe-6570
---------------------
На платах PXIe-6570/6571 свойство ``ppmu_current_limit`` не поддерживается;
лимит тока задаётся через ``ppmu_current_limit_range``.
"""

from __future__ import annotations

import threading
import time

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
from kivy.uix.textinput import TextInput

try:
    import nidigital
except ImportError:
    nidigital = None

# Имя ресурса прибора в NI MAX (логическое или физическое, например PXI1Slot2).
DEFAULT_RESOURCE = "PXI-6570-1"

# Индекс канала PPMU (0 — первый канал). Передаётся в session.channels[index].
CHANNEL_INDEX = 0

# Напряжение, подаваемое PPMU на DUT, в вольтах.
VOLTAGE_V = 5.0

# Лимит тока при подаче напряжения, в амперах.
CURRENT_LIMIT_A = 0.01

# Время интегрирования измерения PPMU, в секундах (4 мкс — типичное значение NI).
APERTURE_TIME_S = 4e-6

# Пауза после включения источника перед измерением, в секундах.
SETTLING_TIME_S = 0.01


def configure_ppmu_channel(session: nidigital.Session, channel_index: int) -> None:
    """Настраивает канал PPMU: режим, лимит тока, напряжение и включает источник.

    Последовательность настройки соответствует типовому сценарию «source voltage,
    measure current» из примера NI ``nidigital_ppmu_source_and_measure.py``.

    Args:
        session: Открытая сессия NI-Digital.
        channel_index: Индекс канала (0 … channel_count − 1), не имя ресурса.

    Note:
        ``ppmu_source()`` автоматически переключает ``selected_function`` в PPMU
        и начинает подачу напряжения. Изменения параметров источника вступают
        в силу только после повторного вызова ``ppmu_source()``.
    """
    ch = session.channels[channel_index]

    # Подключить канал к PPMU (отключить цифровой драйвер и active load).
    ch.selected_function = nidigital.SelectedFunction.PPMU

    # Режим источника: постоянное напряжение (DC Voltage).
    ch.ppmu_output_function = nidigital.PPMUOutputFunction.VOLTAGE

    ch.ppmu_aperture_time = APERTURE_TIME_S
    ch.ppmu_aperture_time_units = nidigital.PPMUApertureTimeUnits.SECONDS

    # PXIe-6570/6571: только ppmu_current_limit_range, без ppmu_current_limit.
    if ch.ppmu_current_limit_supported:
        ch.ppmu_current_limit = CURRENT_LIMIT_A
    else:
        ch.ppmu_current_limit_range = CURRENT_LIMIT_A

    ch.ppmu_voltage_level = VOLTAGE_V
    ch.ppmu_source()

    # Дать цепи установиться перед измерением.
    time.sleep(SETTLING_TIME_S)


def measure_channel_current(session: nidigital.Session, channel_index: int) -> float:
    """Выполняет одно измерение тока PPMU на указанном канале.

    Args:
        session: Открытая сессия NI-Digital с уже активным источником PPMU.
        channel_index: Индекс канала для измерения.

    Returns:
        Измеренный ток в амперах.

    Note:
        ``ppmu_measure`` можно вызывать при любом ``selected_function``;
        для измерения тока канал должен быть в режиме подачи напряжения или тока.
    """
    values = session.channels[channel_index].ppmu_measure(
        nidigital.PPMUMeasurementType.CURRENT
    )
    return values[0]


def disconnect_channel(session: nidigital.Session, channel_index: int) -> None:
    """Отключает канал от PPMU и размыкает переключатели прибора.

    Args:
        session: Открытая сессия NI-Digital.
        channel_index: Индекс канала для отключения.

    Note:
        ``DISCONNECT`` останавливает подачу PPMU и электрически отсоединяет
        канал от методов прибора (рекомендуется перед закрытием сессии).
    """
    session.channels[channel_index].selected_function = (
        nidigital.SelectedFunction.DISCONNECT
    )


def build_session_options(simulate: bool) -> str:
    """Формирует строку опций для конструктора ``nidigital.Session``.

    Args:
        simulate: Если True — работа без реального оборудования (встроенный
            симулятор драйвера с моделью 6570).

    Returns:
        Строка опций IVI или пустая строка для работы с реальным прибором.

    Example:
        >>> build_session_options(True)
        'Simulate=1, DriverSetup=Model:6570'
    """
    if simulate:
        return "Simulate=1, DriverSetup=Model:6570"
    return ""


def run_measurement(resource_name: str, simulate: bool) -> float:
    """Выполняет полный цикл измерения: сессия → PPMU → измерение → закрытие.

    Контекстный менеджер ``with nidigital.Session(...)`` гарантирует закрытие
    сессии и освобождение ресурсов драйвера даже при исключении.

    Args:
        resource_name: Имя ресурса из NI MAX (например ``PXI-6570-1``).
        simulate: Использовать режим симуляции драйвера.

    Returns:
        Измеренный ток на канале ``CHANNEL_INDEX``, в амперах.

    Raises:
        nidigital.errors.DriverError: Ошибка драйвера (прибор не найден,
            неверные параметры, занят другим процессом и т.д.).
        Exception: Любые прочие ошибки Python/NI (пробрасываются в GUI).
    """
    options = build_session_options(simulate)

    with nidigital.Session(resource_name=resource_name, options=options) as session:
        configure_ppmu_channel(session, CHANNEL_INDEX)
        current_a = measure_channel_current(session, CHANNEL_INDEX)
        disconnect_channel(session, CHANNEL_INDEX)
        return current_a


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
    """Kivy-приложение для измерения тока PPMU PXIe-6570.

    Измерение выполняется в фоновом потоке, чтобы не блокировать главный
    цикл Kivy. Обновление виджетов из рабочего потока выполняется через
    ``Clock.schedule_once`` — потокобезопасный способ для Kivy.

    Attributes:
        resource_input: Поле ввода имени ресурса (NI MAX).
        simulate_checkbox: Флаг режима симуляции без оборудования.
        status_label: Текстовый статус операции.
        current_label: Отформатированный результат измерения тока.
        measure_btn: Кнопка запуска измерения.
        _worker: Ссылка на текущий поток измерения (или None).
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.title = "PXIe-6570 PPMU — измерение тока"
        self._worker: threading.Thread | None = None

    def build(self):
        """Создаёт корневой виджет и возвращает его Kivy."""
        Window.size = (dp(480), dp(420))
        Window.minimum_width = dp(400)
        Window.minimum_height = dp(380)

        root = BoxLayout(
            orientation="vertical",
            padding=dp(16),
            spacing=dp(12),
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
            Label(
                text="Режим симуляции (без оборудования)",
                halign="left",
                valign="middle",
            )
        )
        root.add_widget(simulate_row)

        params_section = SectionBox(title="Параметры канала 0", size_hint_y=None)
        params_section.height = dp(120)
        for line in (
            "Режим: PPMU",
            f"Напряжение: {VOLTAGE_V} В",
            f"Лимит тока: {CURRENT_LIMIT_A} А",
        ):
            params_section.content.add_widget(
                Label(text=line, size_hint_y=None, height=dp(24), halign="left")
            )
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
        self.current_label = Label(
            text="—",
            size_hint_y=None,
            height=dp(40),
            font_size=dp(18),
            bold=True,
            halign="left",
        )
        result_section.content.add_widget(self.status_label)
        result_section.content.add_widget(self.current_label)
        root.add_widget(result_section)

        if nidigital is None:
            self.status_label.text = (
                "Ошибка: установите пакет nidigital (pip install -r requirements.txt)"
            )
            self.measure_btn.disabled = True

        return root

    def _on_measure(self, *_args) -> None:
        """Обработчик нажатия кнопки «Измерить ток».

        Проверяет ввод, блокирует повторный запуск и стартует фоновый поток.
        """
        if self._worker and self._worker.is_alive():
            return

        resource = self.resource_input.text.strip()
        if not resource:
            self._show_error("Ошибка", "Укажите resource name прибора.")
            return

        self.measure_btn.disabled = True
        self.status_label.text = "Выполняется измерение…"
        self.current_label.text = "—"

        simulate = self.simulate_checkbox.active
        self._worker = threading.Thread(
            target=self._measure_worker,
            args=(resource, simulate),
            daemon=True,
        )
        self._worker.start()

    def _measure_worker(self, resource_name: str, simulate: bool) -> None:
        """Рабочий поток: вызывает ``run_measurement`` и передаёт результат в GUI.

        Args:
            resource_name: Имя ресурса прибора из поля ввода.
            simulate: Значение флага симуляции из чекбокса.

        Note:
            Не обращается к виджетам напрямую — только через ``Clock.schedule_once``.
        """
        try:
            current_a = run_measurement(resource_name, simulate)
        except Exception as exc:
            Clock.schedule_once(lambda _dt: self._on_measure_failed(str(exc)), 0)
            return

        Clock.schedule_once(lambda _dt, value=current_a: self._on_measure_done(value), 0)

    def _on_measure_done(self, current_a: float) -> None:
        """Обновляет GUI после успешного измерения (вызывается из главного потока).

        Args:
            current_a: Измеренный ток в амперах.
        """
        self.current_label.text = f"{current_a * 1e3:.6f} мА  ({current_a:.9f} А)"
        self.status_label.text = "Измерение завершено, сессия закрыта"
        self.measure_btn.disabled = False

    def _on_measure_failed(self, message: str) -> None:
        """Обновляет GUI и показывает диалог при ошибке (главный поток).

        Args:
            message: Текст исключения от драйвера или Python.
        """
        self.status_label.text = "Ошибка"
        self.current_label.text = "—"
        self.measure_btn.disabled = False
        self._show_error("Ошибка NI-Digital", message)

    @staticmethod
    def _show_error(title: str, message: str) -> None:
        """Показывает модальное окно с текстом ошибки.

        Args:
            title: Заголовок всплывающего окна.
            message: Текст сообщения об ошибке.
        """
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
