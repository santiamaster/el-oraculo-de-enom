from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from oraculo_enom.domain.analysis import analyze
from oraculo_enom.domain.models import Comparator, RollComponentRequest, RollRequest


FIXED_TIME = datetime(2026, 9, 7, 12, 0)


def combined_request(*, show_sum: bool = True) -> RollRequest:
    return RollRequest(
        (
            RollComponentRequest(2, 6, Comparator.GREATER_OR_EQUAL, 5),
            RollComponentRequest(3, 20, Comparator.GREATER_THAN, 12),
        ),
        show_sum=show_sum,
        title="Ataque combinado de Arhat",
    )


def test_analyze_builds_ordered_component_results() -> None:
    request = combined_request()

    result = analyze(request, ((4, 6), (3, 15, 19)), created_at=FIXED_TIME)

    assert result.request is request
    assert (
        tuple(component.request for component in result.components)
        == request.components
    )
    assert tuple(component.values for component in result.components) == (
        (4, 6),
        (3, 15, 19),
    )
    assert tuple(component.subtotal for component in result.components) == (10, 37)
    assert tuple(component.matches for component in result.components) == (
        (6,),
        (15, 19),
    )
    assert result.total == 47
    assert result.created_at == FIXED_TIME


def test_analyze_omits_subtotals_and_total_when_sum_is_hidden() -> None:
    result = analyze(
        combined_request(show_sum=False),
        ((4, 6), (3, 15, 19)),
        created_at=FIXED_TIME,
    )

    assert tuple(component.subtotal for component in result.components) == (
        None,
        None,
    )
    assert result.total is None
    assert tuple(component.matches for component in result.components) == (
        (6,),
        (15, 19),
    )


@pytest.mark.parametrize(
    "comparator,expected",
    [
        (Comparator.GREATER_THAN, (15,)),
        (Comparator.GREATER_OR_EQUAL, (10, 15)),
        (Comparator.LESS_THAN, (2,)),
        (Comparator.LESS_OR_EQUAL, (2, 10)),
        (Comparator.EQUAL, (10,)),
    ],
)
def test_analyze_applies_each_comparator_in_original_value_order(
    comparator: Comparator,
    expected: tuple[int, ...],
) -> None:
    request = RollRequest(
        (RollComponentRequest(3, 20, comparator, 10),),
        show_sum=True,
    )

    result = analyze(request, ((2, 10, 15),), created_at=FIXED_TIME)

    assert result.components[0].matches == expected


def test_analyze_without_filter_has_no_matches() -> None:
    request = RollRequest((RollComponentRequest(2, 6),), show_sum=False)

    result = analyze(request, ((2, 5),), created_at=FIXED_TIME)

    assert result.components[0].matches == ()


@pytest.mark.parametrize(
    "values,message",
    [
        (((4, 6),), "expected 2 value groups, got 1"),
        (((4,), (3, 15, 19)), "expected 2 values for 2d6, got 1"),
        (((0, 6), (3, 15, 19)), "values for d6 must be between 1 and 6"),
        (((4, 7), (3, 15, 19)), "values for d6 must be between 1 and 6"),
    ],
)
def test_analyze_rejects_values_that_do_not_match_the_request(
    values: tuple[tuple[int, ...], ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        analyze(combined_request(), values, created_at=FIXED_TIME)


def test_analyzed_results_are_immutable() -> None:
    result = analyze(
        RollRequest((RollComponentRequest(1, 20),), show_sum=True),
        ((15,),),
        created_at=FIXED_TIME,
    )

    with pytest.raises(FrozenInstanceError):
        result.total = 16
    with pytest.raises(FrozenInstanceError):
        result.components[0].subtotal = 16
