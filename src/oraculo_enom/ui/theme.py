"""ENOM color palette and application-wide Qt styling."""

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QProxyStyle, QStyle, QStyleOptionComplex, QWidget

BACKGROUND = "#171311"
PANEL = "#231d19"
FIELD = "#151210"
GOLD = "#f2cf7b"
GOLD_DARK = "#8b6229"
BORDER = "#665237"
TEXT = "#efe2c3"
MUTED = "#a99b83"


class SpinBoxProxyStyle(QProxyStyle):
    """Keep native spin arrows while providing full-size stacked targets."""

    _BUTTON_WIDTH = 24

    def subControlRect(
        self,
        control: QStyle.ComplexControl,
        option: QStyleOptionComplex,
        sub_control: QStyle.SubControl,
        widget: QWidget | None = None,
    ) -> QRect:
        rect = super().subControlRect(control, option, sub_control, widget)
        if control != QStyle.ComplexControl.CC_SpinBox:
            return rect

        frame = option.rect
        button_left = frame.right() - self._BUTTON_WIDTH + 1
        upper_height = frame.height() // 2
        if sub_control == QStyle.SubControl.SC_SpinBoxUp:
            return QRect(
                button_left,
                frame.top(),
                self._BUTTON_WIDTH,
                upper_height,
            )
        if sub_control == QStyle.SubControl.SC_SpinBoxDown:
            return QRect(
                button_left,
                frame.top() + upper_height,
                self._BUTTON_WIDTH,
                frame.height() - upper_height,
            )
        if sub_control == QStyle.SubControl.SC_SpinBoxEditField:
            return QRect(
                rect.left(),
                rect.top(),
                max(0, button_left - rect.left()),
                rect.height(),
            )
        return rect


STYLESHEET = f"""
QMainWindow, QDialog, QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 10pt;
}}
QFrame#panel, QFrame#summaryCard, QFrame#dialogSection {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QFrame#combinedSummaryCard {{
    background-color: {FIELD};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QLabel#titleLabel {{
    color: {GOLD};
    font-size: 21pt;
    font-weight: 700;
}}
QLabel#sectionLabel {{
    color: {GOLD};
    font-size: 12pt;
    font-weight: 700;
}}
QLabel#dialogSectionLabel {{
    color: {GOLD};
    font-size: 12pt;
    font-weight: 700;
}}
QLabel#combinedPreviewLabel {{
    color: {GOLD};
    font-size: 22pt;
    font-weight: 700;
}}
QLabel#combinedTotalCountLabel, QLabel#limitsLabel {{
    color: {MUTED};
}}
QLabel#validationLabel {{
    background-color: #3a1d18;
    border: 1px solid #b65d4d;
    border-radius: 5px;
    color: #ffd7ce;
    padding: 7px;
}}
QLabel#combinedValidationLabel {{
    background-color: #3a1d18;
    border: 1px solid #b65d4d;
    border-radius: 5px;
    color: #ffd7ce;
    padding: 7px;
}}
QLabel#resultBadge {{
    background-color: {FIELD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT};
    font-size: 11pt;
    font-weight: 600;
    min-width: 34px;
    padding: 7px;
}}
QLabel#resultBadge[matched="true"] {{
    background-color: {GOLD_DARK};
    border: 2px solid {GOLD};
    color: {TEXT};
}}
QPushButton, QSpinBox, QAbstractSpinBox, QComboBox, QDateEdit, QLineEdit {{
    background-color: {FIELD};
    border: 1px solid {BORDER};
    border-radius: 5px;
    color: {TEXT};
    min-height: 28px;
    padding: 4px 8px;
}}
QPushButton:hover {{
    border-color: {GOLD};
}}
QPushButton:checked, QPushButton#primaryButton {{
    background-color: {GOLD_DARK};
    border: 1px solid {GOLD};
    color: {TEXT};
    font-weight: 700;
}}
QPushButton#rollCombinedButton {{
    background-color: {GOLD_DARK};
    border: 1px solid {GOLD};
    color: {TEXT};
    font-weight: 700;
    min-height: 36px;
}}
QSpinBox#customSidesSpin[selected="true"] {{
    background-color: {GOLD_DARK};
    border: 2px solid {GOLD};
    color: {TEXT};
    font-weight: 700;
}}
QPushButton#primaryButton {{
    min-height: 40px;
}}
QLineEdit#rollTitleEdit {{
    min-height: 30px;
}}
QPushButton#clearRollTitleButton {{
    min-height: 24px;
    padding: 2px 9px;
}}
QPushButton:focus, QSpinBox:focus, QAbstractSpinBox:focus, QComboBox:focus, QDateEdit:focus,
QLineEdit:focus, QCheckBox:focus {{
    border: 2px solid {GOLD};
    outline: none;
}}
QPushButton:disabled, QSpinBox:disabled, QAbstractSpinBox:disabled, QComboBox:disabled, QDateEdit:disabled,
QLineEdit:disabled, QCheckBox:disabled {{
    background-color: {PANEL};
    border-color: {BORDER};
    color: {MUTED};
}}
QCheckBox {{
    color: {TEXT};
    spacing: 7px;
}}
QCheckBox::indicator {{
    background-color: {FIELD};
    border: 1px solid {BORDER};
    height: 16px;
    width: 16px;
}}
QCheckBox::indicator:checked {{
    background-color: {GOLD_DARK};
    border: 2px solid {GOLD};
}}
QScrollArea {{
    background-color: {FIELD};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QScrollArea > QWidget > QWidget {{
    background-color: {FIELD};
}}
QTableWidget, QPlainTextEdit {{
    background-color: {FIELD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT};
    gridline-color: {BORDER};
    selection-background-color: {GOLD_DARK};
    selection-color: {TEXT};
}}
QHeaderView::section {{
    background-color: {PANEL};
    border: 0;
    border-bottom: 1px solid {BORDER};
    color: {GOLD};
    font-weight: 700;
    padding: 7px;
}}
QPushButton#destructiveButton {{
    border-color: #b65d4d;
}}
QSplitter::handle {{
    background-color: {BORDER};
    width: 2px;
}}
"""
