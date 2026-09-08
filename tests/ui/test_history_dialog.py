from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
)

from oraculo_enom.domain.analysis import analyze
from oraculo_enom.domain.models import (
    Comparator,
    RollComponentRequest,
    RollRecord,
    RollRequest,
)
from oraculo_enom.persistence.history import HistoryRepository
from oraculo_enom.services.paths import HISTORY_STORAGE_ERROR
from oraculo_enom.ui.history_dialog import HistoryDialog
from oraculo_enom.ui.main_window import MainWindow
from oraculo_enom.ui.theme import STYLESHEET


@pytest.fixture
def repository(tmp_path: Path) -> Iterator[HistoryRepository]:
    history = HistoryRepository(tmp_path / "history.db")
    yield history
    history.close()


@pytest.mark.parametrize("failed_query", [1, 2])
def test_failed_history_refresh_preserves_rows_selection_detail_and_filters(
    qtbot, repository, monkeypatch, failed_query
):
    """Catches a read exception escaping or partial UI swaps before all reads succeed."""
    seed_three(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)
    dialog.records_table.selectRow(1)
    selected = dialog.selected_record_id
    detail = dialog.detail_view.toPlainText()
    items = [dialog.records_table.item(row, 1) for row in range(3)]
    filter_items = [dialog.sides_filter.itemText(i) for i in range(dialog.sides_filter.count())]
    before = tuple(repository._connection.iterdump())
    original_search = repository.search
    calls = 0
    messages = []

    def fail_at_read_boundary(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == failed_query:
            raise OSError("Lectura interrumpida")
        # A successful first read may discover a changed catalog, but must not
        # publish that change before the second (filtered) read succeeds.
        return []

    monkeypatch.setattr(repository, "search", fail_at_read_boundary)
    monkeypatch.setattr(QMessageBox, "critical", lambda parent, title, text: messages.append(text))
    dialog.refresh()

    assert dialog.selected_record_id == selected
    assert dialog.detail_view.toPlainText() == detail
    assert [dialog.records_table.item(row, 1) for row in range(3)] == items
    assert [dialog.sides_filter.itemText(i) for i in range(dialog.sides_filter.count())] == filter_items
    assert dialog.copy_button.isEnabled() and dialog.repeat_button.isEnabled()
    assert len(messages) == 1
    assert "Lectura interrumpida" in messages[0] and "Volvé a intentar" in messages[0]
    assert tuple(repository._connection.iterdump()) == before
    monkeypatch.setattr(repository, "search", original_search)
    dialog.refresh()
    assert dialog.records_table.rowCount() == 3


def test_failed_full_history_open_is_contained_and_can_be_retried(qtbot, repository, monkeypatch):
    seed_three(repository)
    window = MainWindow(repository)
    qtbot.addWidget(window)
    original_search = repository.search
    before = tuple(repository._connection.iterdump())
    messages = []

    def fail_to_read(*args, **kwargs):
        raise OSError("Lectura interrumpida")

    monkeypatch.setattr(repository, "search", fail_to_read)
    monkeypatch.setattr(QMessageBox, "critical", lambda parent, title, text: messages.append(text))
    window._open_full_history()
    dialog = window.findChild(HistoryDialog)
    assert dialog.isVisible()
    assert dialog.records_table.rowCount() == 0
    assert "Volvé a intentar" in messages[0]
    assert tuple(repository._connection.iterdump()) == before
    monkeypatch.setattr(repository, "search", original_search)
    window._open_full_history()
    assert dialog.records_table.rowCount() == 3


def add_roll(
    repository: HistoryRepository,
    *,
    sides: int | None = None,
    values: tuple[int, ...] = (),
    created_at: datetime,
    show_sum: bool = True,
    comparator: Comparator | None = None,
    threshold: int | None = None,
    title: str = "",
    components: tuple[
        tuple[RollComponentRequest, tuple[int, ...]], ...
    ] | None = None,
) -> RollRecord:
    if components is None:
        assert sides is not None
        components = (
            (
                RollComponentRequest(
                    len(values), sides, comparator, threshold
                ),
                values,
            ),
        )
    request = RollRequest(
        tuple(component for component, _ in components),
        show_sum=show_sum,
        title=title,
    )
    result = analyze(
        request,
        tuple(component_values for _, component_values in components),
        created_at=created_at,
    )
    return repository.add(result)


def add_combined_roll(
    repository: HistoryRepository,
    *,
    title: str = "Ataque combinado de Arhat",
) -> RollRecord:
    return add_roll(
        repository,
        title=title,
        created_at=datetime(2026, 9, 7, 10, 15),
        components=(
            (
                RollComponentRequest(2, 6, Comparator.GREATER_OR_EQUAL, 5),
                (4, 6),
            ),
            (RollComponentRequest(1, 8), (7,)),
            (
                RollComponentRequest(3, 20, Comparator.GREATER_THAN, 12),
                (3, 15, 19),
            ),
        ),
    )


def seed_three(
    repository: HistoryRepository,
) -> tuple[RollRecord, RollRecord, RollRecord]:
    oldest = add_roll(
        repository,
        sides=6,
        values=(1, 2),
        created_at=datetime(2026, 9, 4, 8, 30),
    )
    middle = add_roll(
        repository,
        sides=20,
        values=(4, 16, 19),
        created_at=datetime(2026, 9, 5, 12, 0),
        comparator=Comparator.GREATER_OR_EQUAL,
        threshold=16,
    )
    newest = add_roll(
        repository,
        sides=20,
        values=(7,),
        created_at=datetime(2026, 9, 6, 18, 45),
        show_sum=False,
    )
    return oldest, middle, newest


def test_records_are_newest_first_and_selection_shows_read_only_details(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches reversed history order or details belonging to a different row."""
    _, middle, _ = seed_three(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)

    assert dialog.records_table.rowCount() == 3
    assert [
        dialog.records_table.item(row, 1).text() for row in range(3)
    ] == ["1D20", "3D20", "2D6"]

    dialog.records_table.selectRow(1)

    assert dialog.detail_view.isReadOnly()
    assert dialog.detail_view.toPlainText() == (
        "Fecha: 05/09/2026 12:00\n"
        "3d20: 4, 16, 19\n"
        "Suma: 39\n"
        "Filtro >= 16: 2 de 3"
    )
    assert dialog.selected_record_id == middle.id


def test_combined_history_shows_title_notation_and_all_component_details(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches history flattening a combined record to its first component."""
    combined = add_combined_roll(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)

    assert dialog.records_table.item(0, 1).text() == (
        "Ataque combinado de Arhat\n2D6 + 1D8 + 3D20"
    )
    assert dialog.records_table.item(0, 2).text() == (
        "d6: 4, 6 | d8: 7 | d20: 3, 15, 19"
    )

    dialog.records_table.selectRow(0)
    clipboard = QApplication.clipboard()
    clipboard.clear()
    qtbot.mouseClick(dialog.copy_button, Qt.MouseButton.LeftButton)

    expected_detail = (
        "Fecha: 07/09/2026 10:15\n"
        "Ataque combinado de Arhat\n"
        "2d6: 4, 6\nSubtotal d6: 10\nFiltro d6 >= 5: 1 de 2\n"
        "1d8: 7\nSubtotal d8: 7\n"
        "3d20: 3, 15, 19\nSubtotal d20: 37\n"
        "Filtro d20 > 12: 2 de 3\nSuma total: 54"
    )
    assert dialog.selected_record_id == combined.id
    assert dialog.detail_view.toPlainText() == expected_detail
    assert clipboard.text() == expected_detail.split("\n", 1)[1]


def test_titled_history_row_is_tall_enough_for_title_and_notation(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches the fixed table row height clipping canonical notation."""
    add_combined_roll(repository)
    app = QApplication.instance()
    assert app is not None
    previous_stylesheet = app.styleSheet()
    app.setStyleSheet(STYLESHEET)
    try:
        dialog = HistoryDialog(repository)
        qtbot.addWidget(dialog)
        dialog.show()
        app.processEvents()

        table = dialog.records_table
        assert table.item(0, 1).text().endswith("2D6 + 1D8 + 3D20")
        assert table.rowHeight(0) >= table.sizeHintForRow(0)
        assert table.visualRect(table.model().index(0, 1)).height() >= (
            2 * table.fontMetrics().lineSpacing()
        )
    finally:
        app.setStyleSheet(previous_stylesheet)


def test_title_search_is_case_insensitive_and_sides_match_any_component(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches UI filters omitting title input or checking only the first group."""
    combined = add_combined_roll(repository, title="Ataque combinado de ARHAT")
    add_roll(
        repository,
        sides=8,
        values=(2,),
        title="Exploración",
        created_at=datetime(2026, 9, 6, 10, 15),
    )
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)

    dialog.title_search.setText("arhat")

    assert dialog.records_table.rowCount() == 1
    assert (
        dialog.records_table.item(0, 0).data(Qt.ItemDataRole.UserRole)
        == combined.id
    )
    dialog.sides_filter.setCurrentIndex(dialog.sides_filter.findData(20))
    assert dialog.records_table.rowCount() == 1
    assert (
        dialog.records_table.item(0, 0).data(Qt.ItemDataRole.UserRole)
        == combined.id
    )


def test_optional_side_and_inclusive_date_filters_limit_visible_rows(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches filters ignoring die sides or either inclusive date endpoint."""
    _, middle, newest = seed_three(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)

    dialog.sides_filter.setCurrentIndex(dialog.sides_filter.findData(20))

    assert dialog.records_table.rowCount() == 2
    assert [
        dialog.records_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        for row in range(2)
    ] == [newest.id, middle.id]

    dialog.start_date_check.setChecked(True)
    dialog.start_date_edit.setDate(QDate(2026, 9, 5))
    dialog.end_date_check.setChecked(True)
    dialog.end_date_edit.setDate(QDate(2026, 9, 5))

    assert dialog.records_table.rowCount() == 1
    assert dialog.records_table.item(0, 1).text() == "3D20"
    assert (
        dialog.records_table.item(0, 0).data(Qt.ItemDataRole.UserRole)
        == middle.id
    )


def test_refresh_discovers_die_sides_added_after_the_dialog_was_created(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches a reopened dialog offering stale side-filter choices."""
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)
    assert dialog.sides_filter.findData(12) == -1

    add_roll(
        repository,
        sides=12,
        values=(9,),
        created_at=datetime(2026, 9, 6, 19, 0),
    )
    dialog.refresh()

    assert dialog.sides_filter.findData(12) >= 0
    assert dialog.records_table.rowCount() == 1


def test_copy_uses_the_selected_roll_not_the_newest_roll(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches copy silently formatting the first row instead of the selection."""
    seed_three(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)
    clipboard = QApplication.clipboard()
    clipboard.clear()

    dialog.records_table.selectRow(2)
    qtbot.mouseClick(dialog.copy_button, Qt.MouseButton.LeftButton)

    assert clipboard.text() == "2d6: 1, 2\nSuma: 3"


def test_repeat_emits_the_selected_records_configuration(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches repeat emitting values or another row's request configuration."""
    seed_three(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)
    received: list[RollRequest] = []
    dialog.repeat_requested.connect(received.append)

    dialog.records_table.selectRow(1)
    qtbot.mouseClick(dialog.repeat_button, Qt.MouseButton.LeftButton)

    assert received == [
        RollRequest(
            (RollComponentRequest(3, 20, Comparator.GREATER_OR_EQUAL, 16),),
            show_sum=True,
        )
    ]


def test_repeat_emits_every_combined_component_in_order(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches history repeat rebuilding only the first combined component."""
    combined = add_combined_roll(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)
    received: list[RollRequest] = []
    dialog.repeat_requested.connect(received.append)

    dialog.records_table.selectRow(0)
    qtbot.mouseClick(dialog.repeat_button, Qt.MouseButton.LeftButton)

    assert received == [combined.result.request]


def test_title_edit_updates_repository_detail_and_recent_history_immediately(
    qtbot,
    repository: HistoryRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches successful edits leaving either history view stale."""
    record = add_combined_roll(repository, title="Título original")
    window = MainWindow(repository)
    qtbot.addWidget(window)
    window.show()
    qtbot.mouseClick(window.full_history_button, Qt.MouseButton.LeftButton)
    dialog = window.findChild(HistoryDialog)
    assert dialog is not None
    dialog.records_table.selectRow(0)

    def accept_corrected(input_dialog: QInputDialog) -> int:
        input_dialog.setTextValue("Título corregido")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QInputDialog, "exec", accept_corrected)
    qtbot.mouseClick(dialog.edit_title_button, Qt.MouseButton.LeftButton)

    assert repository.recent(1)[0].result.request.title == "Título corregido"
    assert dialog.selected_record_id == record.id
    assert dialog.records_table.item(0, 1).text().startswith(
        "Título corregido\n"
    )
    assert "Título corregido" in dialog.detail_view.toPlainText()
    [recent_entry] = window.recent_history_widget.findChildren(
        QLabel, "historyEntry"
    )
    assert "Título corregido\n2D6 + 1D8 + 3D20" in recent_entry.text()


def test_title_edit_cancellation_preserves_record_and_selection(
    qtbot,
    repository: HistoryRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches cancellation being treated as an empty-title edit."""
    record = add_combined_roll(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)
    dialog.records_table.selectRow(0)
    original_row = dialog.records_table.item(0, 1).text()
    original_detail = dialog.detail_view.toPlainText()
    changes: list[str] = []
    dialog.history_changed.connect(lambda: changes.append("changed"))
    monkeypatch.setattr(
        QInputDialog, "exec", lambda input_dialog: QDialog.DialogCode.Rejected
    )

    qtbot.mouseClick(dialog.edit_title_button, Qt.MouseButton.LeftButton)

    assert repository.recent(1)[0].result.request.title == record.result.request.title
    assert dialog.selected_record_id == record.id
    assert dialog.records_table.item(0, 1).text() == original_row
    assert dialog.detail_view.toPlainText() == original_detail
    assert changes == []


def test_title_edit_accepts_empty_text_and_keeps_the_updated_row_selected(
    qtbot,
    repository: HistoryRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches empty optional titles being rejected or shown as stale."""
    record = add_combined_roll(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)
    dialog.records_table.selectRow(0)

    def accept_empty(input_dialog: QInputDialog) -> int:
        input_dialog.setTextValue("")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QInputDialog, "exec", accept_empty)
    qtbot.mouseClick(dialog.edit_title_button, Qt.MouseButton.LeftButton)

    assert repository.recent(1)[0].result.request.title == ""
    assert dialog.selected_record_id == record.id
    assert dialog.records_table.item(0, 1).text() == "2D6 + 1D8 + 3D20"
    assert "Ataque combinado" not in dialog.detail_view.toPlainText()


def test_title_edit_input_is_bounded_to_one_hundred_fifty_characters(
    qtbot,
    repository: HistoryRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches the edit dialog accepting a title the repository must reject."""
    add_combined_roll(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)
    dialog.records_table.selectRow(0)
    limits: list[int] = []

    def accept_overlong(input_dialog: QInputDialog) -> int:
        editor = input_dialog.findChild(QLineEdit)
        assert editor is not None
        limits.append(editor.maxLength())
        input_dialog.setTextValue("x" * 151)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QInputDialog, "exec", accept_overlong)
    qtbot.mouseClick(dialog.edit_title_button, Qt.MouseButton.LeftButton)

    assert limits == [150]
    assert repository.recent(1)[0].result.request.title == "x" * 150


def test_title_edit_storage_failure_preserves_row_detail_and_selection(
    qtbot,
    repository: HistoryRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches a failed title write refreshing away the visible selection."""
    record = add_combined_roll(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)
    dialog.records_table.selectRow(0)
    original_row = dialog.records_table.item(0, 1).text()
    original_detail = dialog.detail_view.toPlainText()
    messages: list[tuple[str, str]] = []
    changes: list[str] = []
    dialog.history_changed.connect(lambda: changes.append("changed"))

    def accept_changed(input_dialog: QInputDialog) -> int:
        input_dialog.setTextValue("No persistido")
        return QDialog.DialogCode.Accepted

    def fail_to_update(record_id: int, title: str) -> RollRecord:
        raise OSError(HISTORY_STORAGE_ERROR)

    monkeypatch.setattr(QInputDialog, "exec", accept_changed)
    monkeypatch.setattr(repository, "update_title", fail_to_update)
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda parent, title, message: messages.append((title, message)),
    )

    qtbot.mouseClick(dialog.edit_title_button, Qt.MouseButton.LeftButton)

    assert messages == [
        ("No se pudo actualizar el historial", HISTORY_STORAGE_ERROR)
    ]
    assert dialog.selected_record_id == record.id
    assert dialog.records_table.item(0, 1).text() == original_row
    assert dialog.detail_view.toPlainText() == original_detail
    assert changes == []


def test_delete_removes_only_the_selected_record_and_refreshes_rows(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches single deletion targeting the wrong record or leaving a stale row."""
    oldest, middle, newest = seed_three(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)

    dialog.records_table.selectRow(1)
    qtbot.mouseClick(dialog.delete_button, Qt.MouseButton.LeftButton)

    assert [record.id for record in repository.recent()] == [newest.id, oldest.id]
    assert dialog.records_table.rowCount() == 2
    assert middle.id not in [
        dialog.records_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        for row in range(dialog.records_table.rowCount())
    ]


def test_delete_failure_reports_error_without_changing_rows_or_selection(
    qtbot,
    repository: HistoryRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches a delete error escaping after the dialog discards its selection."""
    _, middle, _ = seed_three(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)
    dialog.records_table.selectRow(1)
    original_ids = [
        dialog.records_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        for row in range(dialog.records_table.rowCount())
    ]
    original_detail = dialog.detail_view.toPlainText()
    messages: list[tuple[str, str]] = []
    changes: list[str] = []
    dialog.history_changed.connect(lambda: changes.append("changed"))

    def fail_to_delete(record_id: int) -> None:
        raise OSError(HISTORY_STORAGE_ERROR)

    monkeypatch.setattr(repository, "delete", fail_to_delete)
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda parent, title, message: messages.append((title, message)),
    )

    qtbot.mouseClick(dialog.delete_button, Qt.MouseButton.LeftButton)

    assert messages == [
        ("No se pudo actualizar el historial", HISTORY_STORAGE_ERROR)
    ]
    assert [record.id for record in repository.recent()] == original_ids
    assert [
        dialog.records_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        for row in range(dialog.records_table.rowCount())
    ] == original_ids
    assert dialog.selected_record_id == middle.id
    assert dialog.detail_view.toPlainText() == original_detail
    assert changes == []


def test_clear_all_requires_acceptance_before_removing_records(
    qtbot, repository: HistoryRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catches destructive clearing proceeding after the user rejects confirmation."""
    seed_three(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)
    answers = iter(
        (QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
    )
    monkeypatch.setattr(QMessageBox, "question", lambda *args: next(answers))

    qtbot.mouseClick(dialog.clear_all_button, Qt.MouseButton.LeftButton)

    assert len(repository.recent()) == 3
    assert dialog.records_table.rowCount() == 3

    qtbot.mouseClick(dialog.clear_all_button, Qt.MouseButton.LeftButton)

    assert repository.recent() == []
    assert dialog.records_table.rowCount() == 0


def test_clear_failure_reports_error_without_changing_rows_or_selection(
    qtbot,
    repository: HistoryRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches a clear error escaping after the dialog discards its selection."""
    oldest, _, _ = seed_three(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)
    dialog.records_table.selectRow(2)
    original_ids = [
        dialog.records_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        for row in range(dialog.records_table.rowCount())
    ]
    original_detail = dialog.detail_view.toPlainText()
    messages: list[tuple[str, str]] = []
    changes: list[str] = []
    dialog.history_changed.connect(lambda: changes.append("changed"))

    def fail_to_clear() -> None:
        raise OSError(HISTORY_STORAGE_ERROR)

    monkeypatch.setattr(repository, "clear", fail_to_clear)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda parent, title, message: messages.append((title, message)),
    )

    qtbot.mouseClick(dialog.clear_all_button, Qt.MouseButton.LeftButton)

    assert messages == [
        ("No se pudo actualizar el historial", HISTORY_STORAGE_ERROR)
    ]
    assert [record.id for record in repository.recent()] == original_ids
    assert [
        dialog.records_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        for row in range(dialog.records_table.rowCount())
    ] == original_ids
    assert dialog.selected_record_id == oldest.id
    assert dialog.detail_view.toPlainText() == original_detail
    assert changes == []


def test_clear_all_remains_available_when_filters_hide_every_record(
    qtbot, repository: HistoryRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catches an empty filtered view preventing the user from clearing history."""
    seed_three(repository)
    dialog = HistoryDialog(repository)
    qtbot.addWidget(dialog)
    dialog.start_date_check.setChecked(True)
    dialog.start_date_edit.setDate(QDate(2030, 1, 1))
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )

    assert dialog.records_table.rowCount() == 0
    assert dialog.clear_all_button.isEnabled()

    qtbot.mouseClick(dialog.clear_all_button, Qt.MouseButton.LeftButton)

    assert repository.recent() == []


def test_main_window_history_repeat_closes_dialog_and_rolls_fresh_values(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches history repeat reusing stored values instead of invoking the roller."""
    stored = add_roll(
        repository,
        sides=6,
        values=(1, 1),
        created_at=datetime(2026, 9, 5, 9, 0),
        show_sum=False,
    )
    received_requests: list[RollRequest] = []

    def fresh_roller(request: RollRequest) -> tuple[tuple[int, ...], ...]:
        received_requests.append(request)
        return ((5, 6),)

    window = MainWindow(repository, roller=fresh_roller)
    qtbot.addWidget(window)
    window.show()

    qtbot.mouseClick(window.full_history_button, Qt.MouseButton.LeftButton)
    dialog = window.findChild(HistoryDialog)
    assert dialog is not None
    assert dialog.isVisible()

    dialog.records_table.selectRow(0)
    qtbot.mouseClick(dialog.repeat_button, Qt.MouseButton.LeftButton)

    expected = RollRequest((RollComponentRequest(2, 6),), show_sum=False)
    assert received_requests == [expected]
    assert not dialog.isVisible()
    assert repository.recent(1)[0].id != stored.id
    assert repository.recent(1)[0].result.components[0].values == (5, 6)
    assert window.die_buttons[6].isChecked()
    assert window.quantity_combo.currentData() == 2
    assert not window.show_sum_check.isChecked()


def test_main_window_recent_history_refreshes_immediately_after_dialog_delete(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches the main recent-history panel staying stale after one deletion."""
    seed_three(repository)
    window = MainWindow(repository)
    qtbot.addWidget(window)
    window.show()
    qtbot.mouseClick(window.full_history_button, Qt.MouseButton.LeftButton)
    dialog = window.findChild(HistoryDialog)
    assert dialog is not None

    dialog.records_table.selectRow(0)
    qtbot.mouseClick(dialog.delete_button, Qt.MouseButton.LeftButton)

    entries = window.recent_history_widget.findChildren(QLabel, "historyEntry")
    assert dialog.isVisible()
    assert len(entries) == 2
    assert all("1D20 · Suma 7" not in entry.text() for entry in entries)


def test_main_window_recent_history_refreshes_immediately_after_dialog_clear(
    qtbot,
    repository: HistoryRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches the main recent-history panel staying stale after clear-all."""
    seed_three(repository)
    window = MainWindow(repository)
    qtbot.addWidget(window)
    window.show()
    qtbot.mouseClick(window.full_history_button, Qt.MouseButton.LeftButton)
    dialog = window.findChild(HistoryDialog)
    assert dialog is not None
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )

    qtbot.mouseClick(dialog.clear_all_button, Qt.MouseButton.LeftButton)

    entries = window.recent_history_widget.findChildren(QLabel, "historyEntry")
    empty = window.recent_history_widget.findChildren(QLabel, "emptyHistoryLabel")
    assert dialog.isVisible()
    assert entries == []
    assert len(empty) == 1
