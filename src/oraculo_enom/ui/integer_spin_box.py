"""Shared exact integer editor for simple and combined roll filters."""

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QAbstractSpinBox

from oraculo_enom.domain.integer_text import format_integer, parse_integer


class ArbitraryIntegerSpinBox(QAbstractSpinBox):
    """Spin-box editor that preserves integers outside Qt's fixed int range."""

    def __init__(self) -> None:
        super().__init__()
        self._value = 0
        validator = QRegularExpressionValidator(
            QRegularExpression(r"[+-]?[0-9]+"), self
        )
        self.lineEdit().setValidator(validator)
        self.lineEdit().textChanged.connect(self._remember_valid_value)
        self.editingFinished.connect(self._restore_valid_text)
        self.setValue(0)

    def value(self) -> int:
        parsed = self._parse(self.lineEdit().text())
        return self._value if parsed is None else parsed

    def setValue(self, value: int) -> None:
        self._value = value
        self.lineEdit().setText(format_integer(value))

    def stepBy(self, steps: int) -> None:
        self.setValue(self.value() + steps)

    def stepEnabled(self) -> QAbstractSpinBox.StepEnabled:
        return (
            QAbstractSpinBox.StepEnabledFlag.StepUpEnabled
            | QAbstractSpinBox.StepEnabledFlag.StepDownEnabled
        )

    @staticmethod
    def _parse(text: str) -> int | None:
        if not text or text in {"+", "-"}:
            return None
        return parse_integer(text)

    def _remember_valid_value(self, text: str) -> None:
        parsed = self._parse(text)
        if parsed is not None:
            self._value = parsed

    def _restore_valid_text(self) -> None:
        if self._parse(self.lineEdit().text()) is None:
            self.lineEdit().setText(format_integer(self._value))
