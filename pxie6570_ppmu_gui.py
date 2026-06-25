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
- Python 3.10+
- Пакет ``nidigital`` (``pip install -r requirements.txt``)
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
import tkinter as tk
from tkinter import messagebox, ttk

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


class PXIe6570App(tk.Tk):
    """Главное окно приложения для измерения тока PPMU PXIe-6570.

    Измерение выполняется в фоновом потоке, чтобы не блокировать главный
    цикл Tkinter (event loop). Обновление виджетов из рабочего потока
    выполняется через ``self.after(0, ...)`` — потокобезопасный способ
    для Tkinter.

    Attributes:
        resource_var: Имя ресурса прибора (NI MAX).
        simulate_var: Флаг режима симуляции без оборудования.
        status_var: Текстовый статус операции.
        current_var: Отформатированный результат измерения тока.
        measure_btn: Кнопка запуска измерения.
        _worker: Ссылка на текущий поток измерения (или None).
    """

    def __init__(self) -> None:
        super().__init__()
        self.title("PXIe-6570 PPMU — измерение тока")
        self.resizable(False, False)
        self._worker: threading.Thread | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Создаёт и размещает все элементы интерфейса."""
        pad = {"padx": 10, "pady": 5}

        frame = ttk.Frame(self, padding=10)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Resource name:").grid(row=0, column=0, sticky="w", **pad)
        self.resource_var = tk.StringVar(value=DEFAULT_RESOURCE)
        ttk.Entry(frame, textvariable=self.resource_var, width=28).grid(
            row=0, column=1, **pad
        )

        self.simulate_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Режим симуляции (без оборудования)",
            variable=self.simulate_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", **pad)

        params = ttk.LabelFrame(frame, text="Параметры канала 0", padding=8)
        params.grid(row=2, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Label(params, text="Режим: PPMU").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(params, text=f"Напряжение: {VOLTAGE_V} В").grid(
            row=1, column=0, sticky="w", pady=2
        )
        ttk.Label(params, text=f"Лимит тока: {CURRENT_LIMIT_A} А").grid(
            row=2, column=0, sticky="w", pady=2
        )

        self.measure_btn = ttk.Button(
            frame, text="Измерить ток", command=self._on_measure
        )
        self.measure_btn.grid(row=3, column=0, columnspan=2, **pad)

        result_frame = ttk.LabelFrame(frame, text="Результат", padding=8)
        result_frame.grid(row=4, column=0, columnspan=2, sticky="ew", **pad)

        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(result_frame, textvariable=self.status_var).grid(
            row=0, column=0, sticky="w", pady=2
        )

        self.current_var = tk.StringVar(value="—")
        ttk.Label(
            result_frame,
            textvariable=self.current_var,
            font=("Segoe UI", 16, "bold"),
        ).grid(row=1, column=0, sticky="w", pady=4)

        if nidigital is None:
            self.status_var.set(
                "Ошибка: установите пакет nidigital (pip install -r requirements.txt)"
            )
            self.measure_btn.state(["disabled"])

    def _on_measure(self) -> None:
        """Обработчик нажатия кнопки «Измерить ток».

        Проверяет ввод, блокирует повторный запуск и стартует фоновый поток.
        """
        if self._worker and self._worker.is_alive():
            return

        resource = self.resource_var.get().strip()
        if not resource:
            messagebox.showerror("Ошибка", "Укажите resource name прибора.")
            return

        self.measure_btn.state(["disabled"])
        self.status_var.set("Выполняется измерение…")
        self.current_var.set("—")

        self._worker = threading.Thread(
            target=self._measure_worker,
            args=(resource, self.simulate_var.get()),
            daemon=True,
        )
        self._worker.start()

    def _measure_worker(self, resource_name: str, simulate: bool) -> None:
        """Рабочий поток: вызывает ``run_measurement`` и передаёт результат в GUI.

        Args:
            resource_name: Имя ресурса прибора из поля ввода.
            simulate: Значение флага симуляции из чекбокса.

        Note:
            Не обращается к виджетам напрямую — только через ``self.after``.
        """
        try:
            current_a = run_measurement(resource_name, simulate)
        except Exception as exc:
            self.after(0, self._on_measure_failed, str(exc))
            return

        self.after(0, self._on_measure_done, current_a)

    def _on_measure_done(self, current_a: float) -> None:
        """Обновляет GUI после успешного измерения (вызывается из главного потока).

        Args:
            current_a: Измеренный ток в амперах.
        """
        self.current_var.set(f"{current_a * 1e3:.6f} мА  ({current_a:.9f} А)")
        self.status_var.set("Измерение завершено, сессия закрыта")
        self.measure_btn.state(["!disabled"])

    def _on_measure_failed(self, message: str) -> None:
        """Обновляет GUI и показывает диалог при ошибке (главный поток).

        Args:
            message: Текст исключения от драйвера или Python.
        """
        self.status_var.set("Ошибка")
        self.current_var.set("—")
        self.measure_btn.state(["!disabled"])
        messagebox.showerror("Ошибка NI-Digital", message)


def main() -> None:
    """Точка входа: создаёт приложение и запускает главный цикл Tkinter."""
    app = PXIe6570App()
    app.mainloop()


if __name__ == "__main__":
    main()
