"""Управление темами приложения (светлая / тёмная)."""

from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from logs.setup import get_logger

logger = get_logger(__name__)

_DARK_PALETTE = {
    QPalette.ColorRole.Window:          "#1e1e1e",
    QPalette.ColorRole.WindowText:      "#e0e0e0",
    QPalette.ColorRole.Base:            "#2d2d2d",
    QPalette.ColorRole.AlternateBase:   "#252525",
    QPalette.ColorRole.ToolTipBase:     "#2d2d2d",
    QPalette.ColorRole.ToolTipText:     "#e0e0e0",
    QPalette.ColorRole.Text:            "#e0e0e0",
    QPalette.ColorRole.Button:          "#3a3a3a",
    QPalette.ColorRole.ButtonText:      "#e0e0e0",
    QPalette.ColorRole.BrightText:      "#ffffff",
    QPalette.ColorRole.Highlight:       "#0d6efd",
    QPalette.ColorRole.HighlightedText: "#ffffff",
    QPalette.ColorRole.Link:            "#58a6ff",
    QPalette.ColorRole.LinkVisited:     "#9f7aea",
}


def apply_dark_theme(app: QApplication) -> None:
    palette = QPalette()
    for role, hex_color in _DARK_PALETTE.items():
        color = QColor(hex_color)
        palette.setColor(role, color)
        # Применяем ко всем группам состояния
        palette.setColor(QPalette.ColorGroup.Disabled, role, color.darker(140))
    app.setPalette(palette)
    app.setStyleSheet("""
        /* ── Подсказки ── */
        QToolTip { color: #e0e0e0; background-color: #2d2d2d; border: 1px solid #555; }

        /* ── Поля ввода ── */
        QLineEdit {
            color: #e0e0e0;
            background-color: #2b2b2b;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 3px 6px;
            selection-background-color: #0d6efd;
            selection-color: #ffffff;
        }
        QLineEdit:focus { border-color: #0d6efd; }
        QLineEdit:read-only { color: #999; background-color: #252525; }
        QLineEdit:disabled { color: #666; background-color: #252525; }

        QPlainTextEdit {
            color: #e0e0e0;
            background-color: #2b2b2b;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 3px;
            selection-background-color: #0d6efd;
        }
        QPlainTextEdit:focus { border-color: #0d6efd; }

        QSpinBox {
            color: #e0e0e0;
            background-color: #2b2b2b;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 3px 6px;
        }
        QSpinBox:focus { border-color: #0d6efd; }
        QSpinBox:read-only { color: #999; background-color: #252525; }
        QSpinBox::up-button, QSpinBox::down-button { background: #3a3a3a; border: none; }

        /* ── Комбобоксы ── */
        QComboBox {
            color: #e0e0e0;
            background-color: #2b2b2b;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 3px 6px;
            min-height: 22px;
        }
        QComboBox:focus { border-color: #0d6efd; }
        QComboBox:disabled { color: #666; }
        QComboBox::drop-down { border: none; background: #3a3a3a; border-radius: 0 4px 4px 0; }
        QComboBox::down-arrow { image: none; border-left: 4px solid transparent;
            border-right: 4px solid transparent; border-top: 6px solid #aaa;
            width: 0; height: 0; }
        QComboBox QAbstractItemView {
            color: #e0e0e0;
            background-color: #2b2b2b;
            border: 1px solid #555;
            selection-background-color: #0d6efd;
            selection-color: #ffffff;
            outline: none;
        }

        /* ── Вкладки ── */
        QTabWidget::pane { background-color: transparent; border: none; }
        QTabBar::tab {
            color: #aaaaaa;
            background-color: transparent;
            min-width: 120px;
            margin: 2px;
            padding: 8px 14px;
            border-radius: 8px;
        }
        QTabBar::tab:selected { background-color: #3a3a3a; color: #ffffff; }
        QTabBar::tab:hover:!selected { background-color: #2d2d2d; color: #cccccc; }

        /* ── Кнопки ── */
        QPushButton {
            color: #e0e0e0;
            background-color: #3a3a3a;
            border: 1px solid #555;
            border-radius: 6px;
            padding: 5px 12px;
        }
        QPushButton:hover { background-color: #484848; }
        QPushButton:pressed { background-color: #2d2d2d; }
        QPushButton:disabled { color: #666; }

        /* ── Группы и метки ── */
        QGroupBox {
            border: 1px solid #555; border-radius: 6px;
            margin-top: 16px; padding-top: 10px; color: #e0e0e0;
        }
        QGroupBox::title {
            subcontrol-origin: margin; subcontrol-position: top left;
            left: 10px; padding: 0 4px; color: #aaa;
        }
        QLabel { color: #e0e0e0; }

        /* ── Таблицы ── */
        QTableWidget { color: #e0e0e0; background-color: #2b2b2b; gridline-color: #444;
            border: 1px solid #555; alternate-background-color: #252525; }
        QHeaderView::section { color: #e0e0e0; background-color: #3a3a3a;
            border: 1px solid #555; padding: 4px; }

        /* ── Скроллбары ── */
        QScrollBar:vertical { background: #2d2d2d; width: 10px; margin: 0; }
        QScrollBar::handle:vertical { background: #555; border-radius: 5px; min-height: 20px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal { background: #2d2d2d; height: 10px; margin: 0; }
        QScrollBar::handle:horizontal { background: #555; border-radius: 5px; min-width: 20px; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

        /* ── Диалоги ── */
        QDialog { background-color: #1e1e1e; }
        QMessageBox { background-color: #1e1e1e; }
        QMessageBox QLabel { color: #e0e0e0; }

        /* ── Статусная строка ── */
        QStatusBar { background-color: #1e1e1e; color: #aaaaaa; }
    """)
    logger.info("Применена тёмная тема")


def apply_light_theme(app: QApplication) -> None:
    app.setPalette(QApplication.style().standardPalette())
    app.setStyleSheet("")
    logger.info("Применена светлая тема")


def load_and_apply_theme(app: QApplication) -> None:
    """Читает настройку темы из app_state.json и применяет."""
    from config.settings import _load_state
    dark = _load_state().get("dark_theme", False)
    if dark:
        apply_dark_theme(app)
    else:
        apply_light_theme(app)


def toggle_theme(app: QApplication) -> bool:
    """Переключает тему, сохраняет в настройки. Возвращает True если тёмная."""
    from config.settings import _load_state, _save_state
    state = _load_state()
    dark = not state.get("dark_theme", False)
    state["dark_theme"] = dark
    _save_state(state)
    if dark:
        apply_dark_theme(app)
    else:
        apply_light_theme(app)
    return dark
