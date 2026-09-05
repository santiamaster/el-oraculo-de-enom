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
from oraculo_enom.domain.models import Comparator, RollRequest, RollResult
from oraculo_enom.persistence.history import HistoryRepository
from oraculo_enom.services.clipboard import format_roll


Roller = Callable[[RollRequest], tuple[int, ...]]
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
        self.quantity_combo.currentIndexChanged.connect(self._update_roll_button)
        options.addWidget(self.quantity_combo, 0, 1)

        self.custom_quantity_spin = QSpinBox()
        self.custom_quantity_spin.setObjectName("customQuantitySpin")
        self.custom_quantity_spin.setRange(-9_999, 9_999)
        self.custom_quantity_spin.setValue(11)
        self.custom_quantity_spin.valueChanged.connect(self._select_custom_quantity)
        options.addWidget(self.custom_quantity_spin, 0, 2)

        self.show_sum_check = QCheckBox("Mostrar suma")
        self.show_sum_check.setObjectName("showSumCheck")
        self.show_sum_check.setChecked(True)
        options.addWidget(self.show_sum_check, 0, 3)

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

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setObjectName("thresholdSpin")
        self.threshold_spin.setRange(-1_000_000, 1_000_000)
        self.threshold_spin.setValue(1)
        self.threshold_spin.setEnabled(False)
        options.addWidget(self.threshold_spin, 1, 2)
        layout.addLayout(options)

        self.validation_label = QLabel()
        self.validation_label.setObjectName("validationLabel")
        self.validation_label.setWordWrap(True)
        self.validation_label.hide()
        layout.addWidget(self.validation_label)

        self.roll_button = QPushButton()
        self.roll_button.setObjectName("primaryButton")
        self.roll_button.clicked.connect(self._roll)
        self._update_roll_button()
        layout.addWidget(self.roll_button)

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
        layout.addWidget(self.full_history_button)
        return panel

    def _select_quick_die(self, sides: int) -> None:
        self._selected_sides = sides
        self.die_buttons[sides].setChecked(True)
        self._update_roll_button()

    def _select_custom_sides(self, sides: int) -> None:
        self._die_group.setExclusive(False)
        for button in self.die_buttons.values():
            button.setChecked(False)
        self._die_group.setExclusive(True)
        self._selected_sides = sides
        self._update_roll_button()

    def _select_custom_quantity(self) -> None:
        with QSignalBlocker(self.quantity_combo):
            self.quantity_combo.setCurrentIndex(self.quantity_combo.count() - 1)
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

    def _request_from_controls(self) -> RollRequest:
        comparator = None
        threshold = None
        if self.filter_check.isChecked():
            comparator = Comparator(self.comparator_combo.currentText())
            threshold = self.threshold_spin.value()
        return RollRequest(
            count=self._selected_count(),
            sides=self._selected_sides,
            show_sum=self.show_sum_check.isChecked(),
            comparator=comparator,
            threshold=threshold,
        )

    def _apply_request(self, request: RollRequest) -> None:
        if request.sides in self.die_buttons:
            self._selected_sides = request.sides
            self.die_buttons[request.sides].setChecked(True)
        else:
            with QSignalBlocker(self.custom_sides_spin):
                self.custom_sides_spin.setValue(request.sides)
            self._die_group.setExclusive(False)
            for button in self.die_buttons.values():
                button.setChecked(False)
            self._die_group.setExclusive(True)
            self._selected_sides = request.sides

        with QSignalBlocker(self.quantity_combo), QSignalBlocker(
            self.custom_quantity_spin
        ):
            if 1 <= request.count <= 10:
                self.quantity_combo.setCurrentIndex(request.count - 1)
            else:
                self.custom_quantity_spin.setValue(request.count)
                self.quantity_combo.setCurrentIndex(self.quantity_combo.count() - 1)

        self.show_sum_check.setChecked(request.show_sum)
        filter_enabled = request.comparator is not None
        self.filter_check.setChecked(filter_enabled)
        if request.comparator is not None:
            self.comparator_combo.setCurrentText(request.comparator.value)
        if request.threshold is not None:
            self.threshold_spin.setValue(request.threshold)
        self._update_roll_button()

    def _roll(self) -> None:
        try:
            request = self._request_from_controls()
            validate_request(request)
            values = self._roller(request)
            result = analyze(request, values)
            self._repository.add(result)
        except (ValueError, OSError) as error:
            self.validation_label.setText(str(error))
            self.validation_label.show()
            return

        self.validation_label.clear()
        self.validation_label.hide()
        self._last_request = request
        self._last_result = result
        self._render_result(result)
        self._refresh_recent_history()
        self.repeat_button.setEnabled(True)
        self.copy_button.setEnabled(True)

    def _repeat_last_roll(self) -> None:
        if self._last_request is None:
            return
        self._apply_request(self._last_request)
        self._roll()

    def _copy_last_roll(self) -> None:
        if self._last_result is None:
            return
        QApplication.clipboard().setText(format_roll(self._last_result))

    def _render_result(self, result: RollResult) -> None:
        self._clear_layout(self.results_layout)
        remaining_matches = Counter(result.matches)
        for index, value in enumerate(result.values):
            badge = QLabel(str(value))
            badge.setObjectName("resultBadge")
            matched = remaining_matches[value] > 0
            badge.setProperty("matched", matched)
            if matched:
                remaining_matches[value] -= 1
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_layout.addWidget(badge, index // 12, index % 12)

        self.sum_label.setText(f"Suma: {result.total}")
        self.sum_label.setVisible(result.request.show_sum)
        if result.request.comparator is None:
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
        comparator = result.request.comparator
        assert comparator is not None
        return (
            f"{len(result.matches)} de {len(result.values)} resultados "
            f"{verbs[comparator]} {result.request.threshold}"
        )

    def _refresh_recent_history(self) -> None:
        self._clear_layout(self.recent_history_layout)
        records = self._repository.recent(5)
        if not records:
            empty_label = QLabel("Todavía no hay tiradas.")
            empty_label.setObjectName("emptyHistoryLabel")
            empty_label.setWordWrap(True)
            self.recent_history_layout.addWidget(empty_label)
            return
        for record in records:
            result = record.result
            entry = QLabel(
                f"{result.created_at:%d/%m/%Y %H:%M}\n"
                f"{result.request.notation.upper()} · Suma {result.total}"
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
