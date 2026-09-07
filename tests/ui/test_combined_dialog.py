from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from oraculo_enom.domain.models import Comparator, RollComponentRequest, RollRequest
from oraculo_enom.ui.combined_dialog import CombinedRollDialog


def row_control(dialog: CombinedRollDialog, sides: int, suffix: str):
    control = dialog.findChild(object, f"component{sides}{suffix}")
    assert control is not None
    return control


def select_quick_sides(dialog: CombinedRollDialog, sides: int) -> None:
    index = dialog.quick_sides_combo.findData(sides)
    assert index >= 0
    dialog.quick_sides_combo.setCurrentIndex(index)


def test_dialog_exposes_dense_builder_controls_and_starts_empty(qtbot) -> None:
    dialog = CombinedRollDialog()
    qtbot.addWidget(dialog)

    expected_names = {
        dialog: "combinedRollDialog",
        dialog.title_edit: "combinedTitleEdit",
        dialog.clear_title_button: "clearCombinedTitleButton",
        dialog.show_sum_check: "combinedShowSumCheck",
        dialog.component_table: "combinedComponentTable",
        dialog.quick_sides_combo: "quickSidesCombo",
        dialog.custom_sides_spin: "combinedCustomSidesSpin",
        dialog.quantity_spin: "combinedQuantitySpin",
        dialog.add_button: "addComponentButton",
        dialog.preview_label: "combinedPreviewLabel",
        dialog.total_count_label: "combinedTotalCountLabel",
        dialog.clear_button: "clearConfigurationButton",
        dialog.cancel_button: "cancelCombinedRollButton",
        dialog.roll_button: "rollCombinedButton",
        dialog.validation_label: "combinedValidationLabel",
    }
    assert {widget.objectName() for widget in expected_names} == set(
        expected_names.values()
    )
    assert dialog.windowTitle() == "Tirada combinada"
    assert dialog.component_table.horizontalHeaderItem(0).text() == "Dado"
    assert dialog.component_table.horizontalHeaderItem(5).text() == "Acciones"
    assert dialog.title_edit.maxLength() == 150
    assert dialog.show_sum_check.isChecked()
    assert dialog.component_table.rowCount() == 0
    assert dialog.current_request().components == ()
    assert not dialog.roll_button.isEnabled()


def test_quick_and_custom_dice_merge_duplicates_in_stable_order(qtbot) -> None:
    dialog = CombinedRollDialog()
    qtbot.addWidget(dialog)

    select_quick_sides(dialog, 6)
    dialog.quantity_spin.setValue(2)
    qtbot.mouseClick(dialog.add_button, Qt.MouseButton.LeftButton)
    select_quick_sides(dialog, 20)
    dialog.quantity_spin.setValue(1)
    qtbot.mouseClick(dialog.add_button, Qt.MouseButton.LeftButton)

    dialog.quick_sides_combo.setCurrentIndex(dialog.quick_sides_combo.count() - 1)
    assert dialog.custom_sides_spin.isEnabled()
    dialog.custom_sides_spin.setValue(7)
    dialog.quantity_spin.setValue(4)
    qtbot.mouseClick(dialog.add_button, Qt.MouseButton.LeftButton)

    select_quick_sides(dialog, 6)
    dialog.quantity_spin.setValue(3)
    qtbot.mouseClick(dialog.add_button, Qt.MouseButton.LeftButton)

    request = dialog.current_request()
    assert [(item.count, item.sides) for item in request.components] == [
        (5, 6),
        (1, 20),
        (4, 7),
    ]
    assert dialog.component_table.rowCount() == 3


def test_remove_component_preserves_remaining_order(qtbot) -> None:
    dialog = CombinedRollDialog()
    qtbot.addWidget(dialog)
    for sides in (6, 8, 20):
        dialog.add_component(RollComponentRequest(1, sides))

    qtbot.mouseClick(
        row_control(dialog, 8, "RemoveButton"), Qt.MouseButton.LeftButton
    )

    assert [item.sides for item in dialog.current_request().components] == [6, 20]


def test_rejects_eleventh_distinct_side_count_with_actionable_message(qtbot) -> None:
    dialog = CombinedRollDialog()
    qtbot.addWidget(dialog)
    for sides in range(2, 12):
        dialog.add_component(RollComponentRequest(1, sides))

    dialog.add_component(RollComponentRequest(1, 12))

    assert dialog.component_table.rowCount() == 10
    assert [item.sides for item in dialog.current_request().components] == list(
        range(2, 12)
    )
    assert dialog.validation_label.text() == "La tirada admite hasta 10 tipos de dado"
    assert dialog.validation_label.isVisibleTo(dialog)


def test_rejects_addition_that_would_exceed_one_thousand_dice(qtbot) -> None:
    dialog = CombinedRollDialog()
    qtbot.addWidget(dialog)
    dialog.add_component(RollComponentRequest(999, 6))

    dialog.add_component(RollComponentRequest(2, 8))

    assert dialog.current_request().components == (RollComponentRequest(999, 6),)
    assert (
        dialog.validation_label.text()
        == "La cantidad total de dados debe estar entre 1 y 1.000"
    )


def test_editing_counts_shows_and_clears_total_limit_message(qtbot) -> None:
    dialog = CombinedRollDialog()
    qtbot.addWidget(dialog)
    dialog.add_component(RollComponentRequest(500, 6))
    dialog.add_component(RollComponentRequest(500, 8))
    d6_count = row_control(dialog, 6, "CountSpin")

    d6_count.setValue(501)

    assert not dialog.roll_button.isEnabled()
    assert (
        dialog.validation_label.text()
        == "La cantidad total de dados debe estar entre 1 y 1.000"
    )
    assert dialog.validation_label.isVisibleTo(dialog)

    d6_count.setValue(500)

    assert dialog.roll_button.isEnabled()
    assert dialog.validation_label.text() == ""
    assert dialog.validation_label.isHidden()


def test_each_row_owns_an_independent_optional_filter(qtbot) -> None:
    dialog = CombinedRollDialog()
    qtbot.addWidget(dialog)
    dialog.add_component(RollComponentRequest(2, 6))
    dialog.add_component(RollComponentRequest(3, 20))

    d6_filter = row_control(dialog, 6, "FilterCheck")
    d6_comparator = row_control(dialog, 6, "ComparatorCombo")
    d6_threshold = row_control(dialog, 6, "ThresholdSpin")
    d20_comparator = row_control(dialog, 20, "ComparatorCombo")
    d20_threshold = row_control(dialog, 20, "ThresholdSpin")

    assert not d6_comparator.isEnabled()
    assert not d6_threshold.isEnabled()
    assert not d20_comparator.isEnabled()
    assert not d20_threshold.isEnabled()

    d6_filter.setChecked(True)
    d6_comparator.setCurrentText(Comparator.GREATER_OR_EQUAL.value)
    d6_threshold.setValue(5)

    assert d6_comparator.isEnabled()
    assert d6_threshold.isEnabled()
    assert not d20_comparator.isEnabled()
    assert not d20_threshold.isEnabled()
    assert dialog.current_request().components == (
        RollComponentRequest(2, 6, Comparator.GREATER_OR_EQUAL, 5),
        RollComponentRequest(3, 20, None, None),
    )


def test_initial_component_filters_are_mapped_to_their_own_rows(qtbot) -> None:
    dialog = CombinedRollDialog()
    qtbot.addWidget(dialog)

    dialog.add_component(RollComponentRequest(1, 8, Comparator.EQUAL, 7))
    dialog.add_component(RollComponentRequest(3, 20, Comparator.GREATER_THAN, 12))

    assert row_control(dialog, 8, "FilterCheck").isChecked()
    assert row_control(dialog, 8, "ComparatorCombo").currentText() == "="
    assert row_control(dialog, 8, "ThresholdSpin").value() == 7
    assert dialog.current_request().components == (
        RollComponentRequest(1, 8, Comparator.EQUAL, 7),
        RollComponentRequest(3, 20, Comparator.GREATER_THAN, 12),
    )


def test_preview_summary_and_clear_preserve_title_and_external_last_request(
    qtbot,
) -> None:
    last_completed_request = RollRequest(
        (RollComponentRequest(4, 10),), show_sum=False, title="Tirada anterior"
    )
    dialog = CombinedRollDialog()
    qtbot.addWidget(dialog)
    dialog.set_title("Ataque combinado de Arhat")
    dialog.add_component(RollComponentRequest(2, 6, Comparator.EQUAL, 4))
    dialog.add_component(RollComponentRequest(1, 8))
    dialog.add_component(RollComponentRequest(3, 20))
    dialog.show_sum_check.setChecked(False)

    assert dialog.preview_label.text() == "2d6 + 1d8 + 3d20"
    assert dialog.total_count_label.text() == "6 dados · 3 tipos diferentes"

    qtbot.mouseClick(dialog.clear_button, Qt.MouseButton.LeftButton)

    assert dialog.current_request().components == ()
    assert dialog.title_edit.text() == "Ataque combinado de Arhat"
    assert dialog.show_sum_check.isChecked()
    assert dialog.component_table.rowCount() == 0
    assert last_completed_request == RollRequest(
        (RollComponentRequest(4, 10),), show_sum=False, title="Tirada anterior"
    )


def test_valid_submission_emits_one_immutable_request_and_accepts(qtbot) -> None:
    dialog = CombinedRollDialog()
    qtbot.addWidget(dialog)
    received: list[RollRequest] = []
    dialog.roll_requested.connect(received.append)
    dialog.set_title("  Ataque combinado  ")
    dialog.show_sum_check.setChecked(False)
    dialog.add_component(RollComponentRequest(2, 6))
    dialog.add_component(RollComponentRequest(1, 20, Comparator.GREATER_THAN, 12))

    qtbot.mouseClick(dialog.roll_button, Qt.MouseButton.LeftButton)

    assert received == [
        RollRequest(
            (
                RollComponentRequest(2, 6),
                RollComponentRequest(1, 20, Comparator.GREATER_THAN, 12),
            ),
            show_sum=False,
            title="Ataque combinado",
        )
    ]
    assert isinstance(received[0].components, tuple)
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_enter_in_title_submits_without_triggering_destructive_actions(qtbot) -> None:
    dialog = CombinedRollDialog()
    qtbot.addWidget(dialog)
    received: list[RollRequest] = []
    dialog.roll_requested.connect(received.append)
    dialog.add_component(RollComponentRequest(1, 6))
    dialog.set_title("Ataque con Enter")
    dialog.show()
    dialog.title_edit.setFocus()

    qtbot.keyClick(dialog.title_edit, Qt.Key.Key_Return)

    assert dialog.title_edit.text() == "Ataque con Enter"
    assert received == [
        RollRequest(
            (RollComponentRequest(1, 6),),
            show_sum=True,
            title="Ataque con Enter",
        )
    ]
    assert dialog.result() == QDialog.DialogCode.Accepted
    destructive_buttons = (
        dialog.clear_title_button,
        dialog.clear_button,
        row_control(dialog, 6, "RemoveButton"),
    )
    assert all(not button.autoDefault() for button in destructive_buttons)
    assert all(not button.isDefault() for button in destructive_buttons)


def test_invalid_submission_emits_nothing_and_shows_actionable_message(qtbot) -> None:
    dialog = CombinedRollDialog()
    qtbot.addWidget(dialog)
    received: list[RollRequest] = []
    dialog.roll_requested.connect(received.append)
    dialog.roll_button.setEnabled(True)

    qtbot.mouseClick(dialog.roll_button, Qt.MouseButton.LeftButton)

    assert received == []
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert (
        dialog.validation_label.text()
        == "La tirada debe contener al menos un tipo de dado"
    )
    assert dialog.validation_label.isVisibleTo(dialog)


def test_cancel_rejects_without_emitting(qtbot) -> None:
    dialog = CombinedRollDialog()
    qtbot.addWidget(dialog)
    received: list[RollRequest] = []
    dialog.roll_requested.connect(received.append)
    dialog.add_component(RollComponentRequest(1, 6))

    qtbot.mouseClick(dialog.cancel_button, Qt.MouseButton.LeftButton)

    assert received == []
    assert dialog.result() == QDialog.DialogCode.Rejected
