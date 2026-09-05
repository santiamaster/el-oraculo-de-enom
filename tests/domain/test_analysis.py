from datetime import datetime

import pytest

from oraculo_enom.domain.analysis import analyze
from oraculo_enom.domain.models import Comparator, RollRequest


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
def test_analyze_applies_comparator_in_original_value_order(
    comparator: Comparator, expected: tuple[int, ...]
) -> None:
    request = RollRequest(3, 20, True, comparator, 10)

    result = analyze(request, (2, 10, 15), datetime(2026, 9, 5, 12, 0))

    assert result.total == 27
    assert result.matches == expected
    assert result.values == (2, 10, 15)
    assert result.created_at == datetime(2026, 9, 5, 12, 0)


def test_analyze_rejects_a_value_count_different_from_request() -> None:
    with pytest.raises(ValueError, match="expected 3 values"):
        analyze(RollRequest(3, 20, True), (2, 10))


def test_analyze_without_filter_has_no_matches() -> None:
    result = analyze(RollRequest(2, 6, False), (2, 5))

    assert result.matches == ()

