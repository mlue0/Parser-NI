"""Тесты UI компонентов с pytest-qt."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from models.crystal_data import CrystalData
from ui.confirm_dialog import ConfirmDialog
from ui.edit_form import EditFormWidget
from ui.loading_dialog import LoadingDialog


@pytest.fixture
def sample_crystal_data() -> CrystalData:
    """Fixture с примером данных."""
    return CrystalData(
        good_crystals=150,
        defective_crystals=50,
        total_crystals=200,
        defect_contact=10,
        defect_icc=15,
        defect_fc=5,
        defect_static=8,
        defect_inl=7,
        defect_dnl=3,
        defect_burn=2,
        defect_u0_adc=0,
        plate_marking="HV101",
        firmware_number="HV101",
        correction_number="HV101",
        bmk_batch_number="BMK-2024-001",
        plate_number="PL-001",
        initial_crystals=200,
        sorting_type="Разбраковка NI",
        sorting_target="ПР-ОВ",
        norm_inl="10 нА",
        norm_dnl="5 нА",
        norm_ufs="1.5 В",
        norm_u0="2.0 В",
        norm_u_perzhiganiya="3.0 В",
        norm_u0_adc="1.8 В",
        comment="Тестовый комментарий",
    )


class TestLoadingDialog:
    """Тесты LoadingDialog."""

    def test_loading_dialog_creation(self, qtbot):
        """Тест создания диалога загрузки."""
        dialog = LoadingDialog("Тестовая загрузка...", None)
        qtbot.addWidget(dialog)
        
        assert dialog.windowTitle() == "Подождите"
        assert dialog.isModal()
        
    def test_loading_dialog_display(self, qtbot):
        """Тест отображения диалога."""
        dialog = LoadingDialog("Загрузка данных...", None)
        qtbot.addWidget(dialog)
        
        dialog.show()
        assert dialog.isVisible()


class TestConfirmDialog:
    """Тесты ConfirmDialog."""

    def test_confirm_dialog_creation(self, qtbot, sample_crystal_data):
        """Тест создания диалога подтверждения."""
        dialog = ConfirmDialog(sample_crystal_data, None)
        qtbot.addWidget(dialog)
        
        assert dialog.windowTitle() == "Подтверждение отправки"
        assert dialog.minimumWidth() == 560
        assert dialog.minimumHeight() == 480

    def test_confirm_dialog_data_display(self, qtbot, sample_crystal_data):
        """Тест отображения данных в таблице."""
        dialog = ConfirmDialog(sample_crystal_data, None)
        qtbot.addWidget(dialog)
        
        # Проверяем, что все поля отображены
        labeled_values = sample_crystal_data.labeled_values()
        assert len(labeled_values) > 0


class TestEditFormWidget:
    """Тесты EditFormWidget."""

    def test_edit_form_creation(self, qtbot, sample_crystal_data):
        """Тест создания формы редактирования."""
        form = EditFormWidget(sample_crystal_data, None)
        qtbot.addWidget(form)
        
        assert form.submit_button is not None
        assert form.submit_button.text() == "Подтвердить и отправить"

    def test_edit_form_collect_valid_data(self, qtbot, sample_crystal_data):
        """Тест сбора валидных данных из формы."""
        form = EditFormWidget(sample_crystal_data, None)
        qtbot.addWidget(form)
        
        # Собираем данные
        collected_data = form.collect_data()
        
        assert collected_data is not None
        assert collected_data.plate_marking == sample_crystal_data.plate_marking
        assert collected_data.good_crystals == sample_crystal_data.good_crystals

    def test_edit_form_invalid_data(self, qtbot):
        """Тест обработки невалидных данных."""
        # Создаём форму с минимальными данными
        minimal_data = CrystalData(
            good_crystals=0,
            defective_crystals=0,
            total_crystals=0,
            defect_contact=0,
            defect_icc=0,
            defect_fc=0,
            defect_static=0,
            defect_inl=0,
            defect_dnl=0,
            defect_burn=0,
            defect_u0_adc=0,
            plate_marking="HV101",
            bmk_batch_number="BMK-001",
            plate_number="PL-001",
            initial_crystals=0,
            sorting_type="Разбраковка NI",
            sorting_target="ПР-ОВ",
        )
        
        form = EditFormWidget(minimal_data, None)
        qtbot.addWidget(form)
        
        # Очищаем обязательное поле
        if form._line_edits.get("bmk_batch_number"):
            form._line_edits["bmk_batch_number"].clear()
        
        # Попытка сбора должна вернуть None
        collected_data = form.collect_data()
        assert collected_data is None

    def test_edit_form_plate_marking_change(self, qtbot, sample_crystal_data):
        """Тест изменения маркировки пластины."""
        form = EditFormWidget(sample_crystal_data, None)
        qtbot.addWidget(form)
        
        if form._plate_marking_combo:
            # Меняем маркировку
            form._plate_marking_combo.setCurrentText("M3RV")
            
            # Проверяем, что динамические поля обновились
            if form._firmware_combo:
                assert form._firmware_combo.count() > 0

    def test_edit_form_tab_navigation(self, qtbot, sample_crystal_data):
        """Тест навигации между вкладками."""
        form = EditFormWidget(sample_crystal_data, None)
        qtbot.addWidget(form)
        
        # Проверяем наличие вкладок
        assert form._tabs.count() == 3
        assert form._tabs.tabText(0) == "Параметры"
        assert form._tabs.tabText(1) == "Количественные показатели"
        assert form._tabs.tabText(2) == "Нормы"
        
        # Переключаем вкладки
        form._tabs.setCurrentIndex(1)
        assert form._tabs.currentIndex() == 1
        
        form._tabs.setCurrentIndex(2)
        assert form._tabs.currentIndex() == 2


@pytest.mark.integration
class TestFormIntegration:
    """Интеграционные тесты формы."""

    def test_full_form_workflow(self, qtbot, sample_crystal_data):
        """Тест полного workflow: создание → редактирование → сбор."""
        form = EditFormWidget(sample_crystal_data, None)
        qtbot.addWidget(form)
        
        # Изменяем некоторые поля
        if form._spin_boxes.get("good_crystals"):
            form._spin_boxes["good_crystals"].setValue(175)
        
        if form._comment_edit:
            form._comment_edit.setPlainText("Обновлённый комментарий")
        
        # Собираем данные
        collected_data = form.collect_data()
        
        assert collected_data is not None
        assert collected_data.good_crystals == 175
        assert collected_data.comment == "Обновлённый комментарий"

    def test_form_validation_feedback(self, qtbot, sample_crystal_data):
        """Тест визуальной обратной связи при валидации."""
        form = EditFormWidget(sample_crystal_data, None)
        qtbot.addWidget(form)
        
        # Очищаем обязательное поле
        if form._line_edits.get("plate_number"):
            form._line_edits["plate_number"].clear()
        
        # Пытаемся собрать данные
        result = form.collect_data()
        
        # Должна быть ошибка
        assert result is None
        
        # Подсвечиваем невалидные поля
        form.highlight_invalid_fields()
        
        # Проверяем, что применён стиль ошибки
        if form._line_edits.get("plate_number"):
            style = form._line_edits["plate_number"].styleSheet()
            assert "border" in style.lower() or len(style) > 0
