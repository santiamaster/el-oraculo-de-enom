from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from oraculo_enom.domain.models import Comparator, RollComponentRequest, RollRequest
from oraculo_enom.persistence.history import HistoryRepository
from oraculo_enom.ui.main_window import MainWindow


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
