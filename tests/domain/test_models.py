from dataclasses import FrozenInstanceError

import pytest

from oraculo_enom.domain.models import Comparator, RollComponentRequest, RollRequest


def test_roll_request_describes_ordered_components() -> None:
    component = RollComponentRequest(2, 6, Comparator.GREATER_OR_EQUAL, 5)
    request = RollRequest(
        (component, RollComponentRequest(1, 20)),
        True,
        "Ataque",
    )

    assert component.notation == "2d6"
    assert request.notation == "2d6 + 1d20"
    assert request.total_count == 3
    assert request.is_combined is True
    assert request.title == "Ataque"


def test_one_component_is_not_combined() -> None:
    request = RollRequest((RollComponentRequest(1, 20),), False)

    assert request.is_combined is False


def test_title_normalization_removes_only_exterior_whitespace() -> None:
    request = RollRequest(
        (RollComponentRequest(1, 20),),
        False,
        "  Ataque  combinado de Arhat  ",
    )

    assert request.title == "Ataque  combinado de Arhat"


def test_component_and_request_are_immutable() -> None:
    component = RollComponentRequest(2, 6)
    request = RollRequest((component,), True)

    with pytest.raises(FrozenInstanceError):
        component.count = 3
    with pytest.raises(FrozenInstanceError):
        request.show_sum = False
