from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from oraculo_enom.domain.models import Comparator, RollRequest
from oraculo_enom.persistence.history import HistoryRepository
from oraculo_enom.ui.main_window import MainWindow


@pytest.fixture
def repository(tmp_path: Path) -> Iterator[HistoryRepository]:
    history = HistoryRepository(tmp_path / "history.db")
    yield history
    history.close()


def test_roll_renders_deterministic_results_and_saves_history(
    qtbot, repository: HistoryRepository
) -> None:
    values = tuple(range(1, 21)) + (20, 20)
    received_requests: list[RollRequest] = []

    def deterministic_roller(request: RollRequest) -> tuple[int, ...]:
        received_requests.append(request)
        return values

    window = MainWindow(repository, roller=deterministic_roller)
    qtbot.addWidget(window)

    assert not window.comparator_combo.isEnabled()
    assert not window.threshold_spin.isEnabled()
    window.die_buttons[20].click()
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
    assert received_requests == [
        RollRequest(22, 20, True, Comparator.GREATER_THAN, 12)
    ]
    assert len(badges) == 22
    assert [badge.text() for badge in badges] == [str(value) for value in values]
    assert sum(badge.property("matched") is True for badge in badges) == 10
    assert window.sum_label.text() == "Suma: 250"
    assert window.match_summary_label.text() == (
        "10 de 22 resultados superaron 12"
    )
    assert len(repository.recent()) == 1
    history_entries = window.recent_history_widget.findChildren(
        QLabel, "historyEntry"
    )
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

    assert window.validation_label.text() == (
        "La cantidad de caras debe estar entre 2 y 1.000"
    )
    assert window.custom_sides_spin.value() == 1
    assert repository.recent() == []


def test_repeat_restores_last_request_and_generates_new_values(
    qtbot, repository: HistoryRepository
) -> None:
    generated_values = iter(((1, 2), (5, 6)))
    received_requests: list[RollRequest] = []

    def deterministic_roller(request: RollRequest) -> tuple[int, ...]:
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

    expected_request = RollRequest(2, 6, True)
    assert received_requests == [expected_request, expected_request]
    assert repository.recent(1)[0].result.values == (5, 6)
    badges = window.results_widget.findChildren(QLabel, "resultBadge")
    assert [badge.text() for badge in badges] == ["5", "6"]


def test_copy_places_the_formatted_last_roll_on_the_clipboard(
    qtbot, repository: HistoryRepository
) -> None:
    window = MainWindow(repository, roller=lambda request: (3, 4))
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
    window = MainWindow(repository, roller=lambda request: (1,) * request.count)
    qtbot.addWidget(window)
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
    window = MainWindow(repository, roller=lambda request: (4,))
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
