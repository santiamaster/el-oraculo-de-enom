"""ENOM color palette and application-wide Qt stylesheet."""

BACKGROUND = "#171311"
PANEL = "#231d19"
FIELD = "#151210"
GOLD = "#f2cf7b"
GOLD_DARK = "#8b6229"
BORDER = "#665237"
TEXT = "#efe2c3"
MUTED = "#a99b83"


STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 10pt;
}}
QFrame#panel, QFrame#summaryCard {{
    background-color: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
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
QLabel#validationLabel {{
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
QPushButton, QSpinBox, QComboBox {{
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
QPushButton#primaryButton {{
    min-height: 40px;
}}
QPushButton:focus, QSpinBox:focus, QComboBox:focus, QCheckBox:focus {{
    border: 2px solid {GOLD};
    outline: none;
}}
QPushButton:disabled, QSpinBox:disabled, QComboBox:disabled,
QCheckBox:disabled {{
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
QSplitter::handle {{
    background-color: {BORDER};
    width: 2px;
}}
"""
