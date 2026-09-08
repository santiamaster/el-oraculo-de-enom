"""Searchable full-history dialog for saved dice rolls."""

from datetime import date

from PySide6.QtCore import QDate, QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from oraculo_enom.domain.models import MAX_TITLE_LENGTH, RollRecord, RollRequest
from oraculo_enom.persistence.history import HistoryRepository
from oraculo_enom.services.clipboard import format_roll
from oraculo_enom.ui.history_errors import show_history_read_error


class HistoryDialog(QDialog):
    """Browse, filter, copy, repeat, and delete saved rolls."""

    repeat_requested = Signal(RollRequest)
    record_updated = Signal(RollRecord)
    history_changed = Signal()

    def __init__(self, repository: HistoryRepository, parent=None) -> None:
        super().__init__(parent)
        self._repository = repository
        self._records_by_id: dict[int, RollRecord] = {}

        self.setWindowTitle("Historial completo")
        self.setMinimumSize(780, 520)
        self.resize(900, 620)
        self._build_ui()
        self.refresh()

    @property
    def selected_record_id(self) -> int | None:
        """Return the selected database identifier, if any."""
        row = self.records_table.currentRow()
        if row < 0:
            return None
        item = self.records_table.item(row, 0)
        if item is None:
            return None
        record_id = item.data(Qt.ItemDataRole.UserRole)
        return int(record_id) if record_id is not None else None

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        heading = QLabel("HISTORIAL COMPLETO")
        heading.setObjectName("titleLabel")
        layout.addWidget(heading)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Título"))
        self.title_search = QLineEdit()
        self.title_search.setObjectName("historyTitleSearch")
        self.title_search.setPlaceholderText("Buscar por título")
        self.title_search.textChanged.connect(self.refresh)
        filters.addWidget(self.title_search)
        filters.addWidget(QLabel("Dado"))
        self.sides_filter = QComboBox()
        self.sides_filter.setObjectName("historySidesFilter")
        self.sides_filter.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.sides_filter)

        self.start_date_check = QCheckBox("Desde")
        self.start_date_check.toggled.connect(self._set_start_date_enabled)
        filters.addWidget(self.start_date_check)
        self.start_date_edit = QDateEdit(QDate.currentDate())
        self.start_date_edit.setObjectName("historyStartDate")
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.start_date_edit.setEnabled(False)
        self.start_date_edit.dateChanged.connect(self._date_filter_changed)
        filters.addWidget(self.start_date_edit)

        self.end_date_check = QCheckBox("Hasta")
        self.end_date_check.toggled.connect(self._set_end_date_enabled)
        filters.addWidget(self.end_date_check)
        self.end_date_edit = QDateEdit(QDate.currentDate())
        self.end_date_edit.setObjectName("historyEndDate")
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("dd/MM/yyyy")
        self.end_date_edit.setEnabled(False)
        self.end_date_edit.dateChanged.connect(self._date_filter_changed)
        filters.addWidget(self.end_date_edit)
        filters.addStretch()
        layout.addLayout(filters)

        self.records_table = QTableWidget(0, 4)
        self.records_table.setObjectName("historyTable")
        self.records_table.setHorizontalHeaderLabels(
            ["Fecha", "Tirada", "Resultados", "Suma"]
        )
        self.records_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.records_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.records_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.records_table.verticalHeader().hide()
        header = self.records_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.records_table.itemSelectionChanged.connect(self._show_selection)
        layout.addWidget(self.records_table, 2)

        detail_label = QLabel("DETALLE")
        detail_label.setObjectName("sectionLabel")
        layout.addWidget(detail_label)
        self.detail_view = QPlainTextEdit()
        self.detail_view.setObjectName("historyDetail")
        self.detail_view.setReadOnly(True)
        self.detail_view.setMaximumHeight(130)
        layout.addWidget(self.detail_view)

        action_row = QHBoxLayout()
        self.edit_title_button = QPushButton("Editar título")
        self.edit_title_button.setObjectName("editHistoryTitleButton")
        self.edit_title_button.clicked.connect(self._edit_selected_title)
        action_row.addWidget(self.edit_title_button)
        self.copy_button = QPushButton("Copiar")
        self.copy_button.clicked.connect(self._copy_selected)
        action_row.addWidget(self.copy_button)
        self.repeat_button = QPushButton("Repetir")
        self.repeat_button.clicked.connect(self._repeat_selected)
        action_row.addWidget(self.repeat_button)
        self.delete_button = QPushButton("Eliminar")
        self.delete_button.clicked.connect(self._delete_selected)
        action_row.addWidget(self.delete_button)
        self.clear_all_button = QPushButton("Borrar todo")
        self.clear_all_button.setObjectName("destructiveButton")
        self.clear_all_button.clicked.connect(self._clear_all)
        action_row.addWidget(self.clear_all_button)
        action_row.addStretch()
        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.rejected.connect(self.reject)
        action_row.addWidget(close_buttons)
        layout.addLayout(action_row)

        self._set_selection_actions_enabled(False)

    def _populate_sides_filter(self, sides: list[int]) -> None:
        selected_sides = self.sides_filter.currentData()
        with QSignalBlocker(self.sides_filter):
            self.sides_filter.clear()
            self.sides_filter.addItem("Todos", None)
            for side_count in sides:
                self.sides_filter.addItem(f"d{side_count}", side_count)
            selected_index = self.sides_filter.findData(selected_sides)
            self.sides_filter.setCurrentIndex(max(0, selected_index))

    def refresh(self) -> None:
        """Reload records using the currently enabled filters."""
        try:
            all_records = self._repository.search()
            available_sides = sorted(
                {
                    component.sides
                    for record in all_records
                    for component in record.result.request.components
                }
            )
            sides = self.sides_filter.currentData()
            records = self._repository.search(
                sides=sides if sides in available_sides else None,
                date_from=self._selected_date(
                    self.start_date_check, self.start_date_edit
                ),
                date_to=self._selected_date(
                    self.end_date_check, self.end_date_edit
                ),
                title=self.title_search.text() or None,
            )
        except OSError as error:
            show_history_read_error(self, error)
            return

        self._populate_sides_filter(available_sides)
        self._records_by_id = {record.id: record for record in records}

        with QSignalBlocker(self.records_table):
            self.records_table.clearContents()
            self.records_table.setRowCount(len(records))
            for row, record in enumerate(records):
                result = record.result
                date_item = QTableWidgetItem(
                    result.created_at.strftime("%d/%m/%Y %H:%M")
                )
                date_item.setData(Qt.ItemDataRole.UserRole, record.id)
                self.records_table.setItem(row, 0, date_item)
                self.records_table.setItem(
                    row, 1, QTableWidgetItem(self._roll_label(result.request))
                )
                self.records_table.setItem(
                    row,
                    2,
                    QTableWidgetItem(
                        " | ".join(
                            f"d{component.request.sides}: "
                            + ", ".join(str(value) for value in component.values)
                            for component in result.components
                        )
                    ),
                )
                self.records_table.setItem(
                    row,
                    3,
                    QTableWidgetItem(
                        str(result.total) if result.total is not None else ""
                    ),
                )
            self.records_table.resizeRowsToContents()
            self.records_table.clearSelection()
            self.records_table.setCurrentItem(None)

        self.detail_view.clear()
        self._set_selection_actions_enabled(False)
        self.clear_all_button.setEnabled(self.sides_filter.count() > 1)

    @staticmethod
    def _roll_label(request: RollRequest) -> str:
        title = f"{request.title}\n" if request.title else ""
        return f"{title}{request.notation.upper()}"

    @staticmethod
    def _selected_date(check: QCheckBox, editor: QDateEdit) -> date | None:
        if not check.isChecked():
            return None
        selected = editor.date()
        return date(selected.year(), selected.month(), selected.day())

    def _set_start_date_enabled(self, enabled: bool) -> None:
        self.start_date_edit.setEnabled(enabled)
        self.refresh()

    def _set_end_date_enabled(self, enabled: bool) -> None:
        self.end_date_edit.setEnabled(enabled)
        self.refresh()

    def _date_filter_changed(self) -> None:
        if (
            self.sender() is self.start_date_edit
            and not self.start_date_check.isChecked()
        ):
            return
        if (
            self.sender() is self.end_date_edit
            and not self.end_date_check.isChecked()
        ):
            return
        self.refresh()

    def _selected_record(self) -> RollRecord | None:
        record_id = self.selected_record_id
        if record_id is None:
            return None
        return self._records_by_id.get(record_id)

    def _show_selection(self) -> None:
        record = self._selected_record()
        self._set_selection_actions_enabled(record is not None)
        if record is None:
            self.detail_view.clear()
            return
        result = record.result
        self.detail_view.setPlainText(
            f"Fecha: {result.created_at:%d/%m/%Y %H:%M}\n{format_roll(result)}"
        )

    def _set_selection_actions_enabled(self, enabled: bool) -> None:
        self.edit_title_button.setEnabled(enabled)
        self.copy_button.setEnabled(enabled)
        self.repeat_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)

    def _copy_selected(self) -> None:
        record = self._selected_record()
        if record is not None:
            QApplication.clipboard().setText(format_roll(record.result))

    def _repeat_selected(self) -> None:
        record = self._selected_record()
        if record is not None:
            self.repeat_requested.emit(record.result.request)

    def _edit_selected_title(self) -> None:
        record = self._selected_record()
        if record is None:
            return

        input_dialog = QInputDialog(self)
        input_dialog.setWindowTitle("Editar título")
        input_dialog.setLabelText("Título de la tirada")
        input_dialog.setTextValue(record.result.request.title)
        editor = input_dialog.findChild(QLineEdit)
        if editor is not None:
            editor.setMaxLength(MAX_TITLE_LENGTH)
        if input_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            updated = self._repository.update_title(
                record.id, input_dialog.textValue()
            )
        except OSError as error:
            QMessageBox.critical(
                self, "No se pudo actualizar el historial", str(error)
            )
            return

        self.refresh()
        self._select_record(updated.id)
        self.record_updated.emit(updated)
        self.history_changed.emit()

    def _select_record(self, record_id: int) -> None:
        for row in range(self.records_table.rowCount()):
            item = self.records_table.item(row, 0)
            if (
                item is not None
                and item.data(Qt.ItemDataRole.UserRole) == record_id
            ):
                self.records_table.selectRow(row)
                return

    def _delete_selected(self) -> None:
        record_id = self.selected_record_id
        if record_id is None:
            return
        try:
            self._repository.delete(record_id)
        except OSError as error:
            QMessageBox.critical(
                self, "No se pudo actualizar el historial", str(error)
            )
            return
        self.refresh()
        self.history_changed.emit()

    def _clear_all(self) -> None:
        answer = QMessageBox.question(
            self,
            "Borrar historial",
            "¿Querés borrar todas las tiradas guardadas?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._repository.clear()
        except OSError as error:
            QMessageBox.critical(
                self, "No se pudo actualizar el historial", str(error)
            )
            return
        self.refresh()
        self.history_changed.emit()
