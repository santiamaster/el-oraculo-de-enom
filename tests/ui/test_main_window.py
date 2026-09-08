from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QInputDialog,
    QLabel,
    QMessageBox,
)

from oraculo_enom.domain.models import Comparator, RollComponentRequest, RollRequest
from oraculo_enom.persistence.history import HistoryRepository
from oraculo_enom.ui.combined_dialog import CombinedRollDialog
from oraculo_enom.ui.history_dialog import HistoryDialog
from oraculo_enom.ui.main_window import MainWindow
from oraculo_enom.ui.theme import STYLESHEET


@pytest.fixture
def repository(tmp_path: Path) -> Iterator[HistoryRepository]:
    history = HistoryRepository(tmp_path / "history.db")
    yield history
    history.close()


def simple_request(
    count: int,
    sides: int,
    show_sum: bool = True,
    comparator: Comparator | None = None,
    threshold: int | None = None,
    title: str = "",
) -> RollRequest:
    return RollRequest(
        (RollComponentRequest(count, sides, comparator, threshold),),
        show_sum=show_sum,
        title=title,
    )


@pytest.mark.parametrize("threshold", [1_000_001, -1_000_001, 10**10, -(10**10)])
def test_simple_restore_repeat_and_next_roll_preserve_exact_threshold(
    qtbot, repository: HistoryRepository, threshold: int
) -> None:
    """Catches Qt clipping or overflowing a valid saved one-component filter."""
    request = simple_request(1, 6, True, Comparator.GREATER_THAN, threshold)
    window = MainWindow(repository, roller=lambda request: ((4,),))
    qtbot.addWidget(window)
    window._execute_request(request)

    window._repeat_last_roll()
    assert window.threshold_spin.value() == threshold
    window._roll()

    records = repository.recent()
    assert len(records) == 3
    assert all(record.result.request == request for record in records)


def combined_request(*, show_sum: bool = True) -> RollRequest:
    return RollRequest(
        (
            RollComponentRequest(2, 6, Comparator.GREATER_OR_EQUAL, 5),
            RollComponentRequest(1, 8),
            RollComponentRequest(3, 20, Comparator.GREATER_THAN, 12),
        ),
        show_sum=show_sum,
        title="Ataque combinado de Arhat",
    )


def test_recent_read_failure_preserves_visible_roll_and_history(qtbot, repository, monkeypatch):
    """Catches deleting recent entries before the repository read succeeds."""
    window = MainWindow(repository, roller=lambda request: ((4,),))
    qtbot.addWidget(window)
    window._roll()
    entries = window.recent_history_widget.findChildren(QLabel, "historyEntry")
    badges = window.results_widget.findChildren(QLabel, "resultBadge")
    before = tuple(repository._connection.iterdump())
    messages = []

    def fail_to_read(*args, **kwargs):
        raise OSError("Lectura interrumpida")

    monkeypatch.setattr(repository, "recent", fail_to_read)
    monkeypatch.setattr(QMessageBox, "critical", lambda parent, title, text: messages.append(text))
    window._refresh_recent_history()

    assert window.recent_history_widget.findChildren(QLabel, "historyEntry") == entries
    assert window.results_widget.findChildren(QLabel, "resultBadge") == badges
    assert window.copy_button.isEnabled() and window.repeat_button.isEnabled()
    assert len(messages) == 1
    assert "Lectura interrumpida" in messages[0] and "Volvé a intentar" in messages[0]
    assert tuple(repository._connection.iterdump()) == before


@pytest.mark.parametrize("threshold", [10**50, -(10**50)])
def test_combined_builder_executes_saves_and_reads_arbitrary_threshold(
    qtbot, repository: HistoryRepository, threshold: int
) -> None:
    """Catches binding an arbitrary builder threshold to SQLite's int64 slot."""
    window = MainWindow(repository, roller=lambda request: ((4,), (7,)))
    qtbot.addWidget(window)
    window._open_combined_roll()
    dialog = window.findChild(CombinedRollDialog)
    dialog.add_component(RollComponentRequest(1, 6, Comparator.GREATER_THAN, threshold))
    dialog.add_component(RollComponentRequest(1, 8))

    dialog._submit()

    [stored] = repository.recent()
    assert stored.result.request.components[0].threshold == threshold
    assert stored.result.components[0].values == (4,)
    assert stored.result.components[1].values == (7,)
    assert stored.result.total == 11
    assert not dialog.isVisible()


def test_custom_quantity_is_explicit_enabled_only_when_selected_and_restored(
    qtbot, repository: HistoryRepository
) -> None:
    window = MainWindow(repository)
    qtbot.addWidget(window)

    assert window.custom_quantity_label.text() == "Cantidad personalizada"
    assert not window.custom_quantity_spin.isEnabled()

    custom_index = window.quantity_combo.count() - 1
    window.quantity_combo.setCurrentIndex(custom_index)
    assert window.custom_quantity_spin.isEnabled()

    window.custom_quantity_spin.setValue(22)
    window.quantity_combo.setCurrentIndex(1)
    assert not window.custom_quantity_spin.isEnabled()
    assert window.custom_quantity_spin.value() == 22

    window._apply_request(simple_request(35, 6))
    assert window.quantity_combo.currentIndex() == custom_index
    assert window.custom_quantity_spin.isEnabled()
    assert window.custom_quantity_spin.value() == 35


def test_title_controls_clear_state_and_successful_roll_preserves_title(
    qtbot, repository: HistoryRepository
) -> None:
    window = MainWindow(repository, roller=lambda request: ((8,),))
    qtbot.addWidget(window)

    assert window.roll_title_edit.maxLength() == 150
    assert window.roll_title_edit.text() == ""
    assert not window.clear_roll_title_button.isEnabled()
    assert window.clear_roll_title_button.text() == "×"
    assert window.clear_roll_title_button.accessibleName() == "Limpiar título"

    window.roll_title_edit.setText("Ataque de Máximo")
    assert window.clear_roll_title_button.isEnabled()
    qtbot.mouseClick(window.clear_roll_title_button, Qt.MouseButton.LeftButton)
    assert window.roll_title_edit.text() == ""
    assert not window.clear_roll_title_button.isEnabled()

    window.roll_title_edit.setText("Ataque de Máximo")
    qtbot.mouseClick(window.roll_button, Qt.MouseButton.LeftButton)
    assert window.roll_title_edit.text() == "Ataque de Máximo"


def test_simple_roll_uses_aggregate_request_nullable_sum_title_and_repeat_label(
    qtbot, repository: HistoryRepository
) -> None:
    received_requests: list[RollRequest] = []

    def deterministic_roller(request: RollRequest) -> tuple[tuple[int, ...], ...]:
        received_requests.append(request)
        return ((3, 4),)

    window = MainWindow(repository, roller=deterministic_roller)
    qtbot.addWidget(window)
    window.die_buttons[6].click()
    window.quantity_combo.setCurrentIndex(1)
    window.show_sum_check.setChecked(False)
    window.roll_title_edit.setText("Daño furtivo")
    window.repeat_button.setText("Repetir tirada combinada")
    clipboard = QApplication.clipboard()
    clipboard.clear()

    qtbot.mouseClick(window.roll_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(window.copy_button, Qt.MouseButton.LeftButton)

    expected = simple_request(2, 6, False, title="Daño furtivo")
    assert received_requests == [expected]
    [stored] = repository.recent()
    assert stored.result.request == expected
    assert stored.result.total is None
    assert stored.result.components[0].subtotal is None
    assert clipboard.text() == "Daño furtivo\n2d6: 3, 4"
    assert window.repeat_button.text() == "Repetir tirada"


def test_required_controls_have_stable_object_names(
    qtbot, repository: HistoryRepository
) -> None:
    window = MainWindow(repository)
    qtbot.addWidget(window)

    assert window.custom_quantity_label.objectName() == "customQuantityLabel"
    assert window.roll_title_edit.objectName() == "rollTitleEdit"
    assert window.clear_roll_title_button.objectName() == "clearRollTitleButton"
    assert window.combined_roll_button.objectName() == "combinedRollButton"
    assert window.combined_roll_button.text() == "Configurar tirada combinada"


def test_combined_builder_executes_once_and_renders_every_ordered_group(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches combined submission bypassing the one atomic execution path."""
    received_requests: list[RollRequest] = []

    def deterministic_roller(request: RollRequest) -> tuple[tuple[int, ...], ...]:
        received_requests.append(request)
        return ((4, 6), (7,), (3, 15, 19))

    window = MainWindow(repository, roller=deterministic_roller)
    qtbot.addWidget(window)
    window.show()

    qtbot.mouseClick(window.combined_roll_button, Qt.MouseButton.LeftButton)
    dialog = window.findChild(CombinedRollDialog)
    assert dialog is not None
    dialog.set_title("Ataque combinado de Arhat")
    for component in combined_request().components:
        dialog.add_component(component)

    qtbot.mouseClick(dialog.roll_button, Qt.MouseButton.LeftButton)

    assert not dialog.isVisible()
    assert received_requests == [combined_request()]
    [stored] = repository.recent()
    assert stored.result.request == combined_request()
    assert [component.values for component in stored.result.components] == [
        (4, 6),
        (7,),
        (3, 15, 19),
    ]
    group_labels = window.results_widget.findChildren(QLabel, "resultGroupLabel")
    assert [label.text() for label in group_labels] == [
        "d6 — 2 tiradas",
        "d8 — 1 tirada",
        "d20 — 3 tiradas",
    ]
    badges = window.results_widget.findChildren(QLabel, "resultBadge")
    assert [badge.text() for badge in badges] == ["4", "6", "7", "3", "15", "19"]
    assert [badge.property("matched") for badge in badges] == [
        False,
        True,
        False,
        False,
        True,
        True,
    ]
    subtotals = window.results_widget.findChildren(QLabel, "componentSubtotalLabel")
    assert [label.text() for label in subtotals] == [
        "Subtotal: 10",
        "Subtotal: 7",
        "Subtotal: 37",
    ]
    component_filters = window.results_widget.findChildren(
        QLabel, "componentMatchSummaryLabel"
    )
    assert [label.text() for label in component_filters] == [
        "Filtro >= 5: 1 de 2",
        "Filtro > 12: 2 de 3",
    ]
    assert window.sum_label.text() == "Suma total: 54"
    assert window.roll_title_edit.text() == "Ataque combinado de Arhat"


def test_combined_result_badges_keep_readable_height_and_scroll_when_needed(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches the resizable scroll area vertically compressing result badges."""
    app = QApplication.instance()
    assert app is not None
    previous_stylesheet = app.styleSheet()
    app.setStyleSheet(STYLESHEET)
    try:
        window = MainWindow(
            repository,
            roller=lambda request: ((4, 6), (7,), (3, 15, 19)),
        )
        qtbot.addWidget(window)
        window.resize(1180, 760)
        window.show()

        window._execute_request(combined_request())
        app.processEvents()

        badges = window.results_widget.findChildren(QLabel, "resultBadge")
        assert len(badges) == 6
        assert all(
            badge.height() >= badge.sizeHint().height() for badge in badges
        )
        assert window.results_scroll.verticalScrollBar().maximum() > 0
    finally:
        app.setStyleSheet(previous_stylesheet)


def test_combined_builder_without_sum_persists_and_renders_no_totals(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches the combined execution path ignoring disabled sum output."""
    window = MainWindow(
        repository,
        roller=lambda request: ((4, 6), (7,), (3, 15, 19)),
    )
    qtbot.addWidget(window)
    window.show()
    qtbot.mouseClick(window.combined_roll_button, Qt.MouseButton.LeftButton)
    dialog = window.findChild(CombinedRollDialog)
    assert dialog is not None
    dialog.set_title(combined_request(show_sum=False).title)
    dialog.show_sum_check.setChecked(False)
    for component in combined_request(show_sum=False).components:
        dialog.add_component(component)

    qtbot.mouseClick(dialog.roll_button, Qt.MouseButton.LeftButton)

    [stored] = repository.recent()
    assert stored.result.request == combined_request(show_sum=False)
    assert stored.result.total is None
    assert all(
        component.subtotal is None for component in stored.result.components
    )
    assert window.results_widget.findChildren(
        QLabel, "componentSubtotalLabel"
    ) == []
    assert not window.sum_label.isVisible()


def test_combined_repeat_is_immediate_then_simple_roll_replaces_repeat_context(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches repeat reopening the builder or retaining stale combined state."""
    generated = iter(
        (
            ((1, 2), (3,), (4, 5, 6)),
            ((5, 6), (7,), (18, 19, 20)),
            ((2,),),
            ((4,),),
        )
    )
    received_requests: list[RollRequest] = []

    def deterministic_roller(request: RollRequest) -> tuple[tuple[int, ...], ...]:
        received_requests.append(request)
        return next(generated)

    window = MainWindow(repository, roller=deterministic_roller)
    qtbot.addWidget(window)
    window.show()
    qtbot.mouseClick(window.combined_roll_button, Qt.MouseButton.LeftButton)
    dialog = window.findChild(CombinedRollDialog)
    assert dialog is not None
    dialog.set_title(combined_request().title)
    for component in combined_request().components:
        dialog.add_component(component)
    qtbot.mouseClick(dialog.roll_button, Qt.MouseButton.LeftButton)

    assert window.repeat_button.text() == "Repetir tirada combinada"
    qtbot.mouseClick(window.repeat_button, Qt.MouseButton.LeftButton)

    assert received_requests == [combined_request(), combined_request()]
    assert not dialog.isVisible()
    assert repository.recent(1)[0].result.components[2].values == (18, 19, 20)

    window.die_buttons[6].click()
    window.quantity_combo.setCurrentIndex(0)
    window.roll_title_edit.setText("Ataque simple")
    qtbot.mouseClick(window.roll_button, Qt.MouseButton.LeftButton)

    simple = simple_request(1, 6, title="Ataque simple")
    assert received_requests[-1] == simple
    assert window.repeat_button.text() == "Repetir tirada"
    qtbot.mouseClick(window.repeat_button, Qt.MouseButton.LeftButton)
    assert received_requests[-2:] == [simple, simple]


def test_combined_dialog_draft_survives_reopen_and_clear_keeps_last_repeat(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches recreating the builder or coupling its draft to repeat state."""
    window = MainWindow(
        repository,
        roller=lambda request: tuple(
            (1,) * component.count for component in request.components
        ),
    )
    qtbot.addWidget(window)
    window.show()
    window.roll_title_edit.setText(combined_request().title)
    qtbot.mouseClick(window.combined_roll_button, Qt.MouseButton.LeftButton)
    dialog = window.findChild(CombinedRollDialog)
    assert dialog is not None
    for component in combined_request().components:
        dialog.add_component(component)
    dialog.reject()

    qtbot.mouseClick(window.combined_roll_button, Qt.MouseButton.LeftButton)
    assert window.findChild(CombinedRollDialog) is dialog
    assert dialog.current_request() == combined_request()
    qtbot.mouseClick(dialog.roll_button, Qt.MouseButton.LeftButton)
    assert window.repeat_button.isEnabled()

    qtbot.mouseClick(window.combined_roll_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(dialog.clear_button, Qt.MouseButton.LeftButton)
    assert dialog.current_request().components == ()
    dialog.reject()

    qtbot.mouseClick(window.repeat_button, Qt.MouseButton.LeftButton)
    assert len(repository.recent()) == 2
    assert repository.recent(1)[0].result.request == combined_request()


def test_reopening_combined_builder_syncs_main_title_and_preserves_components(
    qtbot, repository: HistoryRepository
) -> None:
    """Catches a reopened builder submitting its stale title or losing its draft."""
    window = MainWindow(
        repository,
        roller=lambda request: tuple(
            (1,) * component.count for component in request.components
        ),
    )
    qtbot.addWidget(window)
    window.roll_title_edit.setText("Título inicial")
    window._open_combined_roll()
    dialog = window.findChild(CombinedRollDialog)
    assert dialog is not None
    dialog.add_component(RollComponentRequest(2, 6))
    dialog.add_component(RollComponentRequest(1, 8))
    dialog.reject()

    window.roll_title_edit.setText("Título vigente")
    window._open_combined_roll()

    assert dialog.current_request() == RollRequest(
        (RollComponentRequest(2, 6), RollComponentRequest(1, 8)),
        show_sum=True,
        title="Título vigente",
    )
    qtbot.mouseClick(dialog.roll_button, Qt.MouseButton.LeftButton)
    assert repository.recent(1)[0].result.request.title == "Título vigente"


def test_retitle_of_active_last_roll_updates_main_copy_and_repeat(
    qtbot, repository: HistoryRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catches main copy/repeat retaining the title saved before a history edit."""
    window = MainWindow(repository, roller=lambda request: ((3, 4),))
    qtbot.addWidget(window)
    window.die_buttons[6].click()
    window.quantity_combo.setCurrentIndex(1)
    window.roll_title_edit.setText("Título original")
    qtbot.mouseClick(window.roll_button, Qt.MouseButton.LeftButton)
    window._open_full_history()
    dialog = window.findChild(HistoryDialog)
    assert dialog is not None
    dialog.records_table.selectRow(0)

    def accept_edited(input_dialog: QInputDialog) -> int:
        input_dialog.setTextValue("Título corregido")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QInputDialog, "exec", accept_edited)
    qtbot.mouseClick(dialog.edit_title_button, Qt.MouseButton.LeftButton)

    clipboard = QApplication.clipboard()
    clipboard.clear()
    qtbot.mouseClick(window.copy_button, Qt.MouseButton.LeftButton)
    assert clipboard.text().startswith("Título corregido\n2d6: 3, 4")

    qtbot.mouseClick(window.repeat_button, Qt.MouseButton.LeftButton)
    assert repository.recent(1)[0].result.request.title == "Título corregido"


def test_retitle_of_older_roll_does_not_replace_active_main_copy_state(
    qtbot, repository: HistoryRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catches an unrelated history edit replacing the active last-roll identity."""
    window = MainWindow(repository, roller=lambda request: ((3, 4),))
    qtbot.addWidget(window)
    window.die_buttons[6].click()
    window.quantity_combo.setCurrentIndex(1)
    window.roll_title_edit.setText("Tirada anterior")
    qtbot.mouseClick(window.roll_button, Qt.MouseButton.LeftButton)
    window.roll_title_edit.setText("Tirada activa")
    qtbot.mouseClick(window.roll_button, Qt.MouseButton.LeftButton)
    window._open_full_history()
    dialog = window.findChild(HistoryDialog)
    assert dialog is not None
    dialog.records_table.selectRow(1)

    def accept_edited(input_dialog: QInputDialog) -> int:
        input_dialog.setTextValue("Anterior corregida")
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(QInputDialog, "exec", accept_edited)
    qtbot.mouseClick(dialog.edit_title_button, Qt.MouseButton.LeftButton)

    clipboard = QApplication.clipboard()
    clipboard.clear()
    qtbot.mouseClick(window.copy_button, Qt.MouseButton.LeftButton)
    assert clipboard.text().startswith("Tirada activa\n2d6: 3, 4")


def test_roll_renders_deterministic_results_and_saves_history(
    qtbot, repository: HistoryRepository
) -> None:
    values = tuple(range(1, 21)) + (20, 20)
    received_requests: list[RollRequest] = []

    def deterministic_roller(request: RollRequest) -> tuple[tuple[int, ...], ...]:
        received_requests.append(request)
        return (values,)

    window = MainWindow(repository, roller=deterministic_roller)
    qtbot.addWidget(window)

    assert not window.comparator_combo.isEnabled()
    assert not window.threshold_spin.isEnabled()
    window.die_buttons[20].click()
    window.quantity_combo.setCurrentIndex(window.quantity_combo.count() - 1)
    window.custom_quantity_spin.setValue(22)
    window.show_sum_check.setChecked(True)
    window.filter_check.setChecked(True)
    window.comparator_combo.setCurrentText(Comparator.GREATER_THAN.value)
    window.threshold_spin.setValue(12)

    assert window.roll_button.text() == "TIRAR 22D20"
    assert window.comparator_combo.isEnabled()
    assert window.threshold_spin.isEnabled()

    qtbot.mouseClick(window.roll_button, Qt.MouseButton.LeftButton)

    badges = window.results_widget.findChildren(QLabel, "resultBadge")
    expected = simple_request(22, 20, True, Comparator.GREATER_THAN, 12)
    assert received_requests == [expected]
    assert len(badges) == 22
    assert [badge.text() for badge in badges] == [str(value) for value in values]
    assert sum(badge.property("matched") is True for badge in badges) == 10
    assert window.sum_label.text() == "Suma: 250"
    assert window.match_summary_label.text() == "10 de 22 resultados superaron 12"
    assert len(repository.recent()) == 1
    history_entries = window.recent_history_widget.findChildren(QLabel, "historyEntry")
    assert len(history_entries) == 1
    assert "22D20 · Suma 250" in history_entries[0].text()
    assert window.repeat_button.isEnabled()
    assert window.copy_button.isEnabled()


def test_invalid_custom_sides_shows_error_without_changing_input(
    qtbot, repository: HistoryRepository
) -> None:
    window = MainWindow(repository)
    qtbot.addWidget(window)

    window.custom_sides_spin.setValue(1)
    qtbot.mouseClick(window.roll_button, Qt.MouseButton.LeftButton)

    assert window.validation_label.text() == "La cantidad de caras debe estar entre 2 y 1.000"
    assert window.custom_sides_spin.value() == 1
    assert repository.recent() == []


def test_repeat_restores_last_request_and_generates_new_values(
    qtbot, repository: HistoryRepository
) -> None:
    generated_values = iter((((1, 2),), ((5, 6),)))
    received_requests: list[RollRequest] = []

    def deterministic_roller(request: RollRequest) -> tuple[tuple[int, ...], ...]:
        received_requests.append(request)
        return next(generated_values)

    window = MainWindow(repository, roller=deterministic_roller)
    qtbot.addWidget(window)
    window.die_buttons[6].click()
    window.quantity_combo.setCurrentIndex(1)

    qtbot.mouseClick(window.roll_button, Qt.MouseButton.LeftButton)
    window.die_buttons[20].click()
    window.quantity_combo.setCurrentIndex(2)
    qtbot.mouseClick(window.repeat_button, Qt.MouseButton.LeftButton)

    expected_request = simple_request(2, 6)
    assert received_requests == [expected_request, expected_request]
    stored = repository.recent(1)[0].result.components[0]
    assert stored.values == (5, 6)
    badges = window.results_widget.findChildren(QLabel, "resultBadge")
    assert [badge.text() for badge in badges] == ["5", "6"]


def test_copy_places_the_formatted_last_roll_on_the_clipboard(
    qtbot, repository: HistoryRepository
) -> None:
    window = MainWindow(repository, roller=lambda request: ((3, 4),))
    qtbot.addWidget(window)
    window.die_buttons[6].click()
    window.quantity_combo.setCurrentIndex(1)
    clipboard = QApplication.clipboard()
    clipboard.clear()

    qtbot.mouseClick(window.roll_button, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(window.copy_button, Qt.MouseButton.LeftButton)

    assert clipboard.text() == "2d6: 3, 4\nSuma: 7"


def test_thousand_results_stay_inside_the_scroll_area(
    qtbot, repository: HistoryRepository
) -> None:
    window = MainWindow(repository, roller=lambda request: ((1,) * request.total_count,))
    qtbot.addWidget(window)
    window.quantity_combo.setCurrentIndex(window.quantity_combo.count() - 1)
    window.custom_quantity_spin.setValue(1_000)
    window.show()
    initial_size = window.size()

    qtbot.mouseClick(window.roll_button, Qt.MouseButton.LeftButton)

    badges = window.results_widget.findChildren(QLabel, "resultBadge")
    assert len(badges) == 1_000
    assert window.results_scroll.widget() is window.results_widget
    assert window.size() == initial_size


def test_storage_error_is_shown_without_rendering_an_unsaved_roll(
    qtbot, repository: HistoryRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = MainWindow(repository, roller=lambda request: ((4,),))
    qtbot.addWidget(window)

    def fail_to_save(result) -> None:
        raise OSError("No fue posible guardar la tirada")

    monkeypatch.setattr(repository, "add", fail_to_save)
    qtbot.mouseClick(window.roll_button, Qt.MouseButton.LeftButton)

    assert window.validation_label.text() == "No fue posible guardar la tirada"
    assert window.die_buttons[20].isChecked()
    assert window.results_widget.findChildren(QLabel, "resultBadge") == []
    assert not window.repeat_button.isEnabled()
    assert not window.copy_button.isEnabled()


def test_custom_die_keeps_selected_state_after_focus_leaves(
    qtbot, repository: HistoryRepository
) -> None:
    window = MainWindow(repository)
    qtbot.addWidget(window)
    window.show()

    window.custom_sides_spin.setValue(350)
    window.custom_sides_spin.setFocus()
    window.roll_button.setFocus()
    QApplication.processEvents()

    assert not window.custom_sides_spin.hasFocus()
    assert window.custom_sides_spin.property("selected") is True
    assert not any(button.isChecked() for button in window.die_buttons.values())

    window.die_buttons[20].click()
    assert window.custom_sides_spin.property("selected") is False
