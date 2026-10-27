"""In-memory builder dialog for combined dice rolls."""

from dataclasses import dataclass

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from oraculo_enom.domain.dice import validate_request
from oraculo_enom.ui.integer_spin_box import ArbitraryIntegerSpinBox
from oraculo_enom.domain.models import (
    MAX_SIDES,
    MAX_TITLE_LENGTH,
    MAX_TOTAL_DICE,
    MIN_SIDES,
    Comparator,
    RollComponentRequest,
    RollRequest,
)


QUICK_DICE = (4, 6, 8, 10, 12, 16, 20, 50, 100)


@dataclass(slots=True)
class _ComponentRow:
    sides: int
    count_spin: QSpinBox
    filter_check: QCheckBox
    comparator_combo: QComboBox
    threshold_spin: ArbitraryIntegerSpinBox
    remove_button: QPushButton

    def to_request(self) -> RollComponentRequest:
        comparator = None
        threshold = None
        if self.filter_check.isChecked():
            comparator = Comparator(self.comparator_combo.currentText())
            threshold = self.threshold_spin.value()
        return RollComponentRequest(
            count=self.count_spin.value(),
            sides=self.sides,
            comparator=comparator,
            threshold=threshold,
        )


class CombinedRollDialog(QDialog):
    """Build one validated aggregate request without persisting draft state."""

    roll_requested = Signal(RollRequest)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[_ComponentRow] = []

        self.setObjectName("combinedRollDialog")
        self.setWindowTitle("Tirada combinada")
        self.setModal(True)
        self.setMinimumSize(860, 560)
        self.resize(980, 650)
        self._build_ui()
        self._refresh_state()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        heading = QLabel("TIRADA COMBINADA")
        heading.setObjectName("titleLabel")
        root.addWidget(heading)

        general_section, general_layout = self._section("CONFIGURACIÓN GENERAL")
        general_grid = QGridLayout()
        general_grid.setHorizontalSpacing(12)
        general_grid.addWidget(QLabel("Título de la tirada"), 0, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setObjectName("combinedTitleEdit")
        self.title_edit.setMaxLength(MAX_TITLE_LENGTH)
        self.title_edit.setPlaceholderText("Opcional")
        general_grid.addWidget(self.title_edit, 0, 1)
        self.clear_title_button = QPushButton("×")
        self.clear_title_button.setObjectName("clearCombinedTitleButton")
        self.clear_title_button.setAccessibleName("Limpiar título")
        self.clear_title_button.setAutoDefault(False)
        self.clear_title_button.setDefault(False)
        self.clear_title_button.setEnabled(False)
        self.clear_title_button.clicked.connect(self.title_edit.clear)
        general_grid.addWidget(self.clear_title_button, 0, 2)
        self.show_sum_check = QCheckBox("Mostrar suma")
        self.show_sum_check.setObjectName("combinedShowSumCheck")
        self.show_sum_check.setChecked(True)
        general_grid.addWidget(self.show_sum_check, 0, 3)
        general_grid.setColumnStretch(1, 1)
        general_layout.addLayout(general_grid)
        root.addWidget(general_section)

        component_section, component_layout = self._section(
            "COMPONENTES DE LA TIRADA"
        )
        self.component_table = QTableWidget(0, 6)
        self.component_table.setObjectName("combinedComponentTable")
        self.component_table.setHorizontalHeaderLabels(
            ["Dado", "Cantidad", "Filtro", "Comparador", "Umbral", "Acciones"]
        )
        self.component_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.component_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.component_table.verticalHeader().hide()
        self.component_table.setMinimumHeight(120)
        header = self.component_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        component_layout.addWidget(self.component_table)

        editor = QHBoxLayout()
        editor.setSpacing(10)
        editor.addWidget(QLabel("Dado"))
        self.quick_sides_combo = QComboBox()
        self.quick_sides_combo.setObjectName("quickSidesCombo")
        for sides in QUICK_DICE:
            self.quick_sides_combo.addItem(f"d{sides}", sides)
        self.quick_sides_combo.addItem("Personalizado", None)
        self.quick_sides_combo.setCurrentIndex(self.quick_sides_combo.findData(6))
        self.quick_sides_combo.currentIndexChanged.connect(
            self._set_custom_sides_enabled
        )
        editor.addWidget(self.quick_sides_combo)
        self.custom_sides_spin = QSpinBox()
        self.custom_sides_spin.setObjectName("combinedCustomSidesSpin")
        self.custom_sides_spin.setRange(MIN_SIDES, MAX_SIDES)
        self.custom_sides_spin.setValue(100)
        self.custom_sides_spin.setEnabled(False)
        editor.addWidget(self.custom_sides_spin)
        editor.addWidget(QLabel("Cantidad"))
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setObjectName("combinedQuantitySpin")
        self.quantity_spin.setRange(1, MAX_TOTAL_DICE)
        self.quantity_spin.setValue(1)
        editor.addWidget(self.quantity_spin)
        self.add_button = QPushButton("+ Agregar dado")
        self.add_button.setObjectName("addComponentButton")
        self.add_button.setAutoDefault(False)
        self.add_button.setDefault(False)
        self.add_button.clicked.connect(self._add_from_editor)
        editor.addWidget(self.add_button)
        editor.addStretch()
        component_layout.addLayout(editor)

        limits = QLabel("Máximo: 10 tipos diferentes y 1.000 dados en total")
        limits.setObjectName("limitsLabel")
        component_layout.addWidget(limits)
        root.addWidget(component_section, 1)

        summary_section, summary_layout = self._section("RESUMEN")
        summary_card = QFrame()
        summary_card.setObjectName("combinedSummaryCard")
        summary_card_layout = QVBoxLayout(summary_card)
        self.preview_label = QLabel()
        self.preview_label.setObjectName("combinedPreviewLabel")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setWordWrap(True)
        summary_card_layout.addWidget(self.preview_label)
        self.total_count_label = QLabel()
        self.total_count_label.setObjectName("combinedTotalCountLabel")
        self.total_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_card_layout.addWidget(self.total_count_label)
        summary_layout.addWidget(summary_card)
        root.addWidget(summary_section)

        self.validation_label = QLabel()
        self.validation_label.setObjectName("combinedValidationLabel")
        self.validation_label.setWordWrap(True)
        self.validation_label.hide()
        root.addWidget(self.validation_label)

        actions = QHBoxLayout()
        self.clear_button = QPushButton("Limpiar configuración")
        self.clear_button.setObjectName("clearConfigurationButton")
        self.clear_button.setAutoDefault(False)
        self.clear_button.setDefault(False)
        self.clear_button.clicked.connect(self.clear_configuration)
        actions.addWidget(self.clear_button)
        actions.addStretch()
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setObjectName("cancelCombinedRollButton")
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.setDefault(False)
        self.cancel_button.clicked.connect(self.reject)
        actions.addWidget(self.cancel_button)
        self.roll_button = QPushButton("TIRAR COMBINACIÓN")
        self.roll_button.setObjectName("rollCombinedButton")
        self.roll_button.setProperty("primary", True)
        self.roll_button.setDefault(True)
        self.roll_button.clicked.connect(self._submit)
        actions.addWidget(self.roll_button)
        root.addLayout(actions)

        self.title_edit.textChanged.connect(self._title_changed)

    @staticmethod
    def _section(title: str) -> tuple[QFrame, QVBoxLayout]:
        section = QFrame()
        section.setObjectName("dialogSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(10)
        heading = QLabel(title)
        heading.setObjectName("dialogSectionLabel")
        layout.addWidget(heading)
        return section, layout

    def set_title(self, title: str) -> None:
        """Replace the draft title, subject to the shared field limit."""
        self.title_edit.setText(title)

    def add_component(self, component: RollComponentRequest) -> None:
        """Add or merge one component if the resulting request remains valid."""
        try:
            validate_request(RollRequest((component,), show_sum=True))
            candidate = list(self.current_request().components)
            duplicate_index = next(
                (
                    index
                    for index, existing in enumerate(candidate)
                    if existing.sides == component.sides
                ),
                None,
            )
            if duplicate_index is None:
                candidate.append(component)
            else:
                existing = candidate[duplicate_index]
                candidate[duplicate_index] = RollComponentRequest(
                    existing.count + component.count,
                    existing.sides,
                    existing.comparator,
                    existing.threshold,
                )
            validate_request(
                RollRequest(
                    tuple(candidate),
                    show_sum=self.show_sum_check.isChecked(),
                    title=self.title_edit.text(),
                )
            )
        except ValueError as error:
            self._show_error(str(error))
            return

        self._clear_error()
        if duplicate_index is not None:
            row = self._rows[duplicate_index]
            with QSignalBlocker(row.count_spin):
                row.count_spin.setValue(candidate[duplicate_index].count)
        else:
            self._append_row(component)
        self._refresh_state()

    def current_request(self) -> RollRequest:
        """Return a fresh immutable snapshot of the current draft widgets."""
        return RollRequest(
            components=tuple(row.to_request() for row in self._rows),
            show_sum=self.show_sum_check.isChecked(),
            title=self.title_edit.text(),
        )

    def clear_configuration(self) -> None:
        """Reset component options while retaining the draft title."""
        self.component_table.setRowCount(0)
        self._rows.clear()
        self.show_sum_check.setChecked(True)
        self._clear_error()
        self._refresh_state()

    def _append_row(self, component: RollComponentRequest) -> None:
        table_row = self.component_table.rowCount()
        self.component_table.insertRow(table_row)
        sides = component.sides

        die_label = QLabel(f"d{sides}")
        die_label.setObjectName(f"component{sides}DieLabel")
        die_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.component_table.setCellWidget(table_row, 0, die_label)

        count_spin = QSpinBox()
        count_spin.setObjectName(f"component{sides}CountSpin")
        count_spin.setRange(1, MAX_TOTAL_DICE)
        count_spin.setValue(component.count)
        count_spin.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.component_table.setCellWidget(table_row, 1, count_spin)

        filter_check = QCheckBox()
        filter_check.setObjectName(f"component{sides}FilterCheck")
        filter_check.setAccessibleName(f"Aplicar filtro a d{sides}")
        filter_check.setChecked(component.comparator is not None)
        filter_holder = QWidget()
        filter_layout = QHBoxLayout(filter_holder)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        filter_layout.addWidget(filter_check)
        self.component_table.setCellWidget(table_row, 2, filter_holder)

        comparator_combo = QComboBox()
        comparator_combo.setObjectName(f"component{sides}ComparatorCombo")
        for comparator in Comparator:
            comparator_combo.addItem(comparator.value, comparator)
        if component.comparator is not None:
            comparator_combo.setCurrentText(component.comparator.value)
        comparator_combo.setEnabled(component.comparator is not None)
        self.component_table.setCellWidget(table_row, 3, comparator_combo)

        threshold_spin = ArbitraryIntegerSpinBox()
        threshold_spin.setObjectName(f"component{sides}ThresholdSpin")
        threshold_spin.setValue(
            component.threshold if component.threshold is not None else 1
        )
        threshold_spin.setEnabled(component.threshold is not None)
        self.component_table.setCellWidget(table_row, 4, threshold_spin)

        remove_button = QPushButton("Eliminar")
        remove_button.setObjectName(f"component{sides}RemoveButton")
        remove_button.setAutoDefault(False)
        remove_button.setDefault(False)
        self.component_table.setCellWidget(table_row, 5, remove_button)

        row = _ComponentRow(
            sides=sides,
            count_spin=count_spin,
            filter_check=filter_check,
            comparator_combo=comparator_combo,
            threshold_spin=threshold_spin,
            remove_button=remove_button,
        )
        self._rows.append(row)
        count_spin.valueChanged.connect(self._refresh_state)
        filter_check.toggled.connect(
            lambda enabled, owned_row=row: self._set_row_filter_enabled(
                owned_row, enabled
            )
        )
        remove_button.clicked.connect(
            lambda checked=False, owned_row=row: self._remove_row(owned_row)
        )
        self.component_table.resizeRowToContents(table_row)

    def _remove_row(self, row: _ComponentRow) -> None:
        try:
            index = self._rows.index(row)
        except ValueError:
            return
        self._rows.pop(index)
        self.component_table.removeRow(index)
        self._clear_error()
        self._refresh_state()

    def _set_row_filter_enabled(self, row: _ComponentRow, enabled: bool) -> None:
        row.comparator_combo.setEnabled(enabled)
        row.threshold_spin.setEnabled(enabled)
        self._refresh_state()

    def _set_custom_sides_enabled(self) -> None:
        self.custom_sides_spin.setEnabled(
            self.quick_sides_combo.currentData() is None
        )

    def _add_from_editor(self) -> None:
        sides = self.quick_sides_combo.currentData()
        if sides is None:
            sides = self.custom_sides_spin.value()
        self.add_component(
            RollComponentRequest(count=self.quantity_spin.value(), sides=int(sides))
        )

    def _title_changed(self, title: str) -> None:
        self.clear_title_button.setEnabled(bool(title))
        self._refresh_state()

    def _refresh_state(self) -> None:
        request = self.current_request()
        self.preview_label.setText(request.notation or "Añade dados para empezar")
        component_count = len(request.components)
        type_word = "tipo diferente" if component_count == 1 else "tipos diferentes"
        self.total_count_label.setText(
            f"{request.total_count} dados · {component_count} {type_word}"
        )
        try:
            validate_request(request)
        except ValueError as error:
            self.roll_button.setEnabled(False)
            if request.components:
                self._show_error(str(error))
        else:
            self.roll_button.setEnabled(True)
            self._clear_error()

    def _submit(self) -> None:
        request = self.current_request()
        try:
            validate_request(request)
        except ValueError as error:
            self._show_error(str(error))
            self.roll_button.setEnabled(False)
            return
        self._clear_error()
        self.roll_requested.emit(request)
        self.accept()

    def _show_error(self, message: str) -> None:
        self.validation_label.setText(message)
        self.validation_label.show()

    def _clear_error(self) -> None:
        self.validation_label.clear()
        self.validation_label.hide()
