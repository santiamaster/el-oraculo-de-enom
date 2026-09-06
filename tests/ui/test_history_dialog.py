from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from oraculo_enom.domain.models import Comparator, RollRecord, RollRequest, RollResult
from oraculo_enom.persistence.history import HistoryRepository
from oraculo_enom.ui.history_dialog import HistoryDialog
from oraculo_enom.ui.main_window import MainWindow


@pytest.fixture
def repository(tmp_path: Path) -> Iterator[HistoryRepository]:
    history = HistoryRepository(tmp_path / "history.db")
    yield history
    history.close()


def add_roll(
    repository: HistoryRepository,
    *,
    sides: int,
    values: tuple[int, ...],
    created_at: datetime,
    show_sum: bool = True,
    comparator: Comparator | None = None,
    threshold: int | None = None,
) -> RollRecord:
    request = RollRequest(
        count=len(values),
        sides=sides,
        show_sum=show_sum,
        comparator=comparator,
        threshold=threshold,
    )
    matches = ()
    if comparator is Comparator.GREATER_OR_EQUAL and threshold is not None:
        matches = tuple(value for value in values if value >= threshold)
    result = RollResult(
        request=request,
        values=values,
        total=sum(values),
        matches=matches,
        created_at=created_at,
    )
    return repository.add(result)


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
        RollRequest(3, 20, True, Comparator.GREATER_OR_EQUAL, 16)
    ]


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

    def fresh_roller(request: RollRequest) -> tuple[int, ...]:
        received_requests.append(request)
        return (5, 6)

    window = MainWindow(repository, roller=fresh_roller)
    qtbot.addWidget(window)
    window.show()

    qtbot.mouseClick(window.full_history_button, Qt.MouseButton.LeftButton)
    dialog = window.findChild(HistoryDialog)
    assert dialog is not None
    assert dialog.isVisible()

    dialog.records_table.selectRow(0)
    qtbot.mouseClick(dialog.repeat_button, Qt.MouseButton.LeftButton)

    expected = RollRequest(2, 6, False)
    assert received_requests == [expected]
    assert not dialog.isVisible()
    assert repository.recent(1)[0].id != stored.id
    assert repository.recent(1)[0].result.values == (5, 6)
    assert window.die_buttons[6].isChecked()
    assert window.quantity_combo.currentData() == 2
    assert not window.show_sum_check.isChecked()
