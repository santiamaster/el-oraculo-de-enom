"""Main dice-roller window."""

from collections import Counter
from collections.abc import Callable

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from oraculo_enom.domain.analysis import analyze
from oraculo_enom.domain.dice import roll_values, validate_request
from oraculo_enom.domain.models import (
    Comparator,
    RollComponentRequest,
    RollRecord,
    RollRequest,
    RollResult,
)
from oraculo_enom.persistence.history import HistoryRepository
from oraculo_enom.services.clipboard import format_roll
from oraculo_enom.ui.combined_dialog import CombinedRollDialog
from oraculo_enom.ui.history_dialog import HistoryDialog
from oraculo_enom.ui.history_errors import show_history_read_error
from oraculo_enom.ui.integer_spin_box import ArbitraryIntegerSpinBox


Roller = Callable[[RollRequest], tuple[tuple[int, ...], ...]]
QUICK_DICE = (4, 6, 8, 10, 12, 16, 20, 50, 100)


class MainWindow(QMainWindow):
    """Configure, execute, display, and persist dice rolls."""

    def __init__(
        self,
        repository: HistoryRepository,
        roller: Roller = roll_values,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._roller = roller
        self._selected_sides = 20
        self._last_request: RollRequest | None = None
        self._last_result: RollResult | None = None
        self._last_record_id: int | None = None
        self._combined_dialog: CombinedRollDialog | None = None
        self._history_dialog: HistoryDialog | None = None

        self.setWindowTitle("El Oráculo de ENOM")
        self.setMinimumSize(960, 640)
        self.resize(1180, 760)
        self._build_ui()
        self._refresh_recent_history()

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("mainSplitter")
        splitter.addWidget(self._build_main_panel())
        splitter.addWidget(self._build_history_panel())
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([880, 300])
        self.setCentralWidget(splitter)

    def _build_main_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        title = QLabel("EL ORÁCULO DE ENOM")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        title_row = QHBoxLayout()
        title_label = QLabel("Título de la tirada")
        title_row.addWidget(title_label)
        self.roll_title_edit = QLineEdit()
        self.roll_title_edit.setObjectName("rollTitleEdit")
        self.roll_title_edit.setMaxLength(150)
        self.roll_title_edit.setPlaceholderText("Opcional")
        title_row.addWidget(self.roll_title_edit, 1)
        self.clear_roll_title_button = QPushButton("×")
        self.clear_roll_title_button.setObjectName("clearRollTitleButton")
        self.clear_roll_title_button.setAccessibleName("Limpiar título")
        self.clear_roll_title_button.setEnabled(False)
        self.clear_roll_title_button.clicked.connect(self.roll_title_edit.clear)
        self.roll_title_edit.textChanged.connect(
            lambda text: self.clear_roll_title_button.setEnabled(bool(text))
        )
        title_row.addWidget(self.clear_roll_title_button)
        layout.addLayout(title_row)

        dice_label = QLabel("ELIGE TU DADO")
        dice_label.setObjectName("sectionLabel")
        layout.addWidget(dice_label)

        dice_row = QHBoxLayout()
        self._die_group = QButtonGroup(self)
        self._die_group.setExclusive(True)
        self.die_buttons: dict[int, QPushButton] = {}
        for sides in QUICK_DICE:
            button = QPushButton(f"d{sides}")
            button.setObjectName(f"die{sides}Button")
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, value=sides: self._select_quick_die(value)
            )
            self._die_group.addButton(button)
            self.die_buttons[sides] = button
            dice_row.addWidget(button)
        self.die_buttons[20].setChecked(True)
        layout.addLayout(dice_row)

        custom_die_row = QHBoxLayout()
        custom_die_row.addWidget(QLabel("Caras personalizadas"))
        self.custom_sides_spin = QSpinBox()
        self.custom_sides_spin.setObjectName("customSidesSpin")
        self.custom_sides_spin.setRange(-9_999, 9_999)
        self.custom_sides_spin.setValue(20)
        self.custom_sides_spin.setProperty("selected", False)
        self.custom_sides_spin.valueChanged.connect(self._select_custom_sides)
        custom_die_row.addWidget(self.custom_sides_spin)
        custom_die_row.addStretch()
        layout.addLayout(custom_die_row)

        options = QGridLayout()
        options.setHorizontalSpacing(12)
        options.setVerticalSpacing(10)
        options.addWidget(QLabel("Cantidad"), 0, 0)
        self.quantity_combo = QComboBox()
        self.quantity_combo.setObjectName("quantityCombo")
        for count in range(1, 11):
            self.quantity_combo.addItem(str(count), count)
        self.quantity_combo.addItem("Personalizada", None)
        self.quantity_combo.currentIndexChanged.connect(
            self._set_custom_quantity_enabled
        )
        options.addWidget(self.quantity_combo, 0, 1)

        self.custom_quantity_spin = QSpinBox()
        self.custom_quantity_spin.setObjectName("customQuantitySpin")
        self.custom_quantity_spin.setRange(-9_999, 9_999)
        self.custom_quantity_spin.setValue(11)
        self.custom_quantity_spin.setEnabled(False)
        self.custom_quantity_spin.valueChanged.connect(self._update_roll_button)
        self.custom_quantity_label = QLabel("Cantidad personalizada")
        self.custom_quantity_label.setObjectName("customQuantityLabel")
        options.addWidget(self.custom_quantity_label, 0, 2)
        options.addWidget(self.custom_quantity_spin, 0, 3)

        self.show_sum_check = QCheckBox("Mostrar suma")
        self.show_sum_check.setObjectName("showSumCheck")
        self.show_sum_check.setChecked(True)
        options.addWidget(self.show_sum_check, 1, 3)

        self.filter_check = QCheckBox("Aplicar filtro")
        self.filter_check.setObjectName("filterCheck")
        self.filter_check.toggled.connect(self._set_filter_enabled)
        options.addWidget(self.filter_check, 1, 0)

        self.comparator_combo = QComboBox()
        self.comparator_combo.setObjectName("comparatorCombo")
        for comparator in Comparator:
            self.comparator_combo.addItem(comparator.value, comparator)
        self.comparator_combo.setEnabled(False)
        options.addWidget(self.comparator_combo, 1, 1)

        self.threshold_spin = ArbitraryIntegerSpinBox()
        self.threshold_spin.setObjectName("thresholdSpin")
        self.threshold_spin.setValue(1)
        self.threshold_spin.setEnabled(False)
        options.addWidget(self.threshold_spin, 1, 2)
        layout.addLayout(options)

        self.validation_label = QLabel()
        self.validation_label.setObjectName("validationLabel")
        self.validation_label.setWordWrap(True)
        self.validation_label.hide()
        layout.addWidget(self.validation_label)

        roll_row = QHBoxLayout()
        self.roll_button = QPushButton()
        self.roll_button.setObjectName("primaryButton")
        self.roll_button.clicked.connect(self._roll)
        self._update_roll_button()
        roll_row.addWidget(self.roll_button, 1)
        self.combined_roll_button = QPushButton("Configurar tirada combinada")
        self.combined_roll_button.setObjectName("combinedRollButton")
        self.combined_roll_button.clicked.connect(self._open_combined_roll)
        roll_row.addWidget(self.combined_roll_button)
        layout.addLayout(roll_row)

        results_label = QLabel("RESULTADOS")
        results_label.setObjectName("sectionLabel")
        layout.addWidget(results_label)

        self.results_scroll = QScrollArea()
        self.results_scroll.setObjectName("resultsScroll")
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setMinimumHeight(180)
        self.results_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.results_widget = QWidget()
        self.results_widget.setObjectName("resultsWidget")
        self.results_layout = QGridLayout(self.results_widget)
        self.results_layout.setSizeConstraint(
            QLayout.SizeConstraint.SetMinAndMaxSize
        )
        self.results_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.results_scroll.setWidget(self.results_widget)
        layout.addWidget(self.results_scroll, 1)

        summary_row = QHBoxLayout()
        sum_card = QFrame()
        sum_card.setObjectName("summaryCard")
        sum_layout = QVBoxLayout(sum_card)
        self.sum_label = QLabel()
        self.sum_label.setObjectName("sumLabel")
        self.sum_label.hide()
        sum_layout.addWidget(self.sum_label)
        summary_row.addWidget(sum_card)

        match_card = QFrame()
        match_card.setObjectName("summaryCard")
        match_layout = QVBoxLayout(match_card)
        self.match_summary_label = QLabel()
        self.match_summary_label.setObjectName("matchSummaryLabel")
        self.match_summary_label.setWordWrap(True)
        self.match_summary_label.hide()
        match_layout.addWidget(self.match_summary_label)
        summary_row.addWidget(match_card, 1)
        layout.addLayout(summary_row)

        action_row = QHBoxLayout()
        self.repeat_button = QPushButton("Repetir tirada")
        self.repeat_button.setObjectName("repeatButton")
        self.repeat_button.setEnabled(False)
        self.repeat_button.clicked.connect(self._repeat_last_roll)
        action_row.addWidget(self.repeat_button)
        self.copy_button = QPushButton("Copiar resultados")
        self.copy_button.setObjectName("copyButton")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self._copy_last_roll)
        action_row.addWidget(self.copy_button)
        action_row.addStretch()
        layout.addLayout(action_row)
        return panel

    def _build_history_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumWidth(250)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 20, 16, 20)

        heading = QLabel("HISTORIAL RECIENTE")
        heading.setObjectName("sectionLabel")
        layout.addWidget(heading)

        self.recent_history_widget = QWidget()
        self.recent_history_widget.setObjectName("recentHistoryWidget")
        self.recent_history_layout = QVBoxLayout(self.recent_history_widget)
        self.recent_history_layout.setContentsMargins(0, 8, 0, 8)
        self.recent_history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.recent_history_widget, 1)

        self.full_history_button = QPushButton("Ver historial completo")
        self.full_history_button.setObjectName("fullHistoryButton")
        self.full_history_button.clicked.connect(self._open_full_history)
        layout.addWidget(self.full_history_button)
        return panel

    def _select_quick_die(self, sides: int) -> None:
        self._selected_sides = sides
        self.die_buttons[sides].setChecked(True)
        self._set_custom_die_selected(False)
        self._update_roll_button()

    def _select_custom_sides(self, sides: int) -> None:
        self._die_group.setExclusive(False)
        for button in self.die_buttons.values():
            button.setChecked(False)
        self._die_group.setExclusive(True)
        self._selected_sides = sides
        self._set_custom_die_selected(True)
        self._update_roll_button()

    def _set_custom_die_selected(self, selected: bool) -> None:
        self.custom_sides_spin.setProperty("selected", selected)
        style = self.custom_sides_spin.style()
        style.unpolish(self.custom_sides_spin)
        style.polish(self.custom_sides_spin)
        self.custom_sides_spin.update()

    def _set_custom_quantity_enabled(self) -> None:
        is_custom = self.quantity_combo.currentData() is None
        self.custom_quantity_spin.setEnabled(is_custom)
        self._update_roll_button()

    def _set_filter_enabled(self, enabled: bool) -> None:
        self.comparator_combo.setEnabled(enabled)
        self.threshold_spin.setEnabled(enabled)

    def _selected_count(self) -> int:
        count = self.quantity_combo.currentData()
        if count is None:
            return self.custom_quantity_spin.value()
        return int(count)

    def _update_roll_button(self) -> None:
        self.roll_button.setText(
            f"TIRAR {self._selected_count()}D{self._selected_sides}"
        )

    def _current_simple_request(self) -> RollRequest:
        comparator = None
        threshold = None
        if self.filter_check.isChecked():
            comparator = Comparator(self.comparator_combo.currentText())
            threshold = self.threshold_spin.value()
        component = RollComponentRequest(
            count=self._selected_count(),
            sides=self._selected_sides,
            comparator=comparator,
            threshold=threshold,
        )
        return RollRequest(
            components=(component,),
            show_sum=self.show_sum_check.isChecked(),
            title=self.roll_title_edit.text(),
        )

    def _apply_request(self, request: RollRequest) -> None:
        component = request.components[0]
        if component.sides in self.die_buttons:
            self._selected_sides = component.sides
            self.die_buttons[component.sides].setChecked(True)
            self._set_custom_die_selected(False)
        else:
            with QSignalBlocker(self.custom_sides_spin):
                self.custom_sides_spin.setValue(component.sides)
            self._die_group.setExclusive(False)
            for button in self.die_buttons.values():
                button.setChecked(False)
            self._die_group.setExclusive(True)
            self._selected_sides = component.sides
            self._set_custom_die_selected(True)

        with QSignalBlocker(self.quantity_combo), QSignalBlocker(
            self.custom_quantity_spin
        ):
            if 1 <= component.count <= 10:
                self.quantity_combo.setCurrentIndex(component.count - 1)
            else:
                self.custom_quantity_spin.setValue(component.count)
                self.quantity_combo.setCurrentIndex(self.quantity_combo.count() - 1)

        self._set_custom_quantity_enabled()
        self.roll_title_edit.setText(request.title)
        self.show_sum_check.setChecked(request.show_sum)
        filter_enabled = component.comparator is not None
        self.filter_check.setChecked(filter_enabled)
        if component.comparator is not None:
            self.comparator_combo.setCurrentText(component.comparator.value)
        if component.threshold is not None:
            self.threshold_spin.setValue(component.threshold)
        self._update_roll_button()

    def _roll(self) -> None:
        self._execute_request(self._current_simple_request())

    def _execute_request(self, request: RollRequest) -> None:
        try:
            validate_request(request)
            values_by_component = self._roller(request)
            result = analyze(request, values_by_component)
            record = self._repository.add(result)
        except (ValueError, OSError) as error:
            self.validation_label.setText(str(error))
            self.validation_label.show()
            return

        self.validation_label.clear()
        self.validation_label.hide()
        self.roll_title_edit.setText(request.title)
        self._last_request = request
        self._last_result = result
        self._last_record_id = record.id
        self._render_result(result)
        self._refresh_recent_history()
        self.repeat_button.setText(
            "Repetir tirada combinada" if request.is_combined else "Repetir tirada"
        )
        self.repeat_button.setEnabled(True)
        self.copy_button.setEnabled(True)

    def _repeat_last_roll(self) -> None:
        if self._last_request is None:
            return
        self._repeat_request(self._last_request)

    def _repeat_request(self, request: RollRequest) -> None:
        if not request.is_combined:
            self._apply_request(request)
        self._execute_request(request)

    def _open_combined_roll(self) -> None:
        if self._combined_dialog is None:
            self._combined_dialog = CombinedRollDialog(self)
            self._combined_dialog.roll_requested.connect(self._execute_request)
        self._combined_dialog.set_title(self.roll_title_edit.text())
        self._combined_dialog.show()
        self._combined_dialog.raise_()
        self._combined_dialog.activateWindow()

    def _open_full_history(self) -> None:
        if self._history_dialog is None:
            self._history_dialog = HistoryDialog(self._repository, self)
            self._history_dialog.repeat_requested.connect(self._repeat_from_history)
            self._history_dialog.record_updated.connect(
                self._history_record_updated
            )
            self._history_dialog.history_changed.connect(
                self._refresh_recent_history
            )
            self._history_dialog.finished.connect(self._refresh_recent_history)
        else:
            self._history_dialog.refresh()
        self._history_dialog.show()
        self._history_dialog.raise_()
        self._history_dialog.activateWindow()

    def _repeat_from_history(self, request: RollRequest) -> None:
        if self._history_dialog is not None:
            self._history_dialog.close()
        self._repeat_request(request)

    def _history_record_updated(self, record: RollRecord) -> None:
        if record.id != self._last_record_id:
            return
        self._last_request = record.result.request
        self._last_result = record.result

    def _copy_last_roll(self) -> None:
        if self._last_result is None:
            return
        QApplication.clipboard().setText(format_roll(self._last_result))

    def _render_result(self, result: RollResult) -> None:
        self._clear_layout(self.results_layout)
        row = 0
        for component in result.components:
            count = len(component.values)
            roll_word = "tirada" if count == 1 else "tiradas"
            group_label = QLabel(
                f"d{component.request.sides} — {count} {roll_word}"
            )
            group_label.setObjectName("resultGroupLabel")
            self.results_layout.addWidget(group_label, row, 0, 1, 12)
            row += 1

            remaining_matches = Counter(component.matches)
            for index, value in enumerate(component.values):
                badge = QLabel(str(value))
                badge.setObjectName("resultBadge")
                matched = remaining_matches[value] > 0
                badge.setProperty("matched", matched)
                if matched:
                    remaining_matches[value] -= 1
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.results_layout.addWidget(
                    badge, row + index // 12, index % 12
                )
            row += max(1, (count + 11) // 12)

            if result.request.is_combined and result.request.show_sum:
                subtotal_label = QLabel(f"Subtotal: {component.subtotal}")
                subtotal_label.setObjectName("componentSubtotalLabel")
                self.results_layout.addWidget(subtotal_label, row, 0, 1, 12)
                row += 1
            if (
                result.request.is_combined
                and component.request.comparator is not None
            ):
                filter_label = QLabel(
                    f"Filtro {component.request.comparator.value} "
                    f"{component.request.threshold}: {len(component.matches)} "
                    f"de {len(component.values)}"
                )
                filter_label.setObjectName("componentMatchSummaryLabel")
                self.results_layout.addWidget(filter_label, row, 0, 1, 12)
                row += 1

        total_prefix = "Suma total" if result.request.is_combined else "Suma"
        self.sum_label.setText(f"{total_prefix}: {result.total}")
        self.sum_label.setVisible(result.request.show_sum)
        if (
            result.request.is_combined
            or result.components[0].request.comparator is None
        ):
            self.match_summary_label.clear()
            self.match_summary_label.hide()
        else:
            self.match_summary_label.setText(self._match_summary(result))
            self.match_summary_label.show()

    @staticmethod
    def _match_summary(result: RollResult) -> str:
        verbs = {
            Comparator.GREATER_THAN: "superaron",
            Comparator.GREATER_OR_EQUAL: "alcanzaron o superaron",
            Comparator.LESS_THAN: "quedaron por debajo de",
            Comparator.LESS_OR_EQUAL: "alcanzaron o quedaron por debajo de",
            Comparator.EQUAL: "igualaron",
        }
        component = result.components[0]
        comparator = component.request.comparator
        assert comparator is not None
        return (
            f"{len(component.matches)} de {len(component.values)} resultados "
            f"{verbs[comparator]} {component.request.threshold}"
        )

    def _refresh_recent_history(self) -> None:
        try:
            records = self._repository.recent(5)
        except OSError as error:
            show_history_read_error(self, error)
            return
        self._clear_layout(self.recent_history_layout)
        if not records:
            empty_label = QLabel("Todavía no hay tiradas.")
            empty_label.setObjectName("emptyHistoryLabel")
            empty_label.setWordWrap(True)
            self.recent_history_layout.addWidget(empty_label)
            return
        for record in records:
            result = record.result
            title = f"{result.request.title}\n" if result.request.title else ""
            sum_text = f" · Suma {result.total}" if result.total is not None else ""
            entry = QLabel(
                f"{result.created_at:%d/%m/%Y %H:%M}\n"
                f"{title}{result.request.notation.upper()}{sum_text}"
            )
            entry.setObjectName("historyEntry")
            entry.setWordWrap(True)
            self.recent_history_layout.addWidget(entry)

    @staticmethod
    def _clear_layout(layout: QGridLayout | QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
