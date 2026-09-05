from datetime import datetime

from oraculo_enom.domain.models import Comparator, RollRequest, RollResult


def test_roll_request_keeps_filter_configuration() -> None:
    request = RollRequest(22, 20, True, Comparator.GREATER_THAN, 12)
    assert request.notation == "22d20"
    assert request.threshold == 12


def test_roll_result_is_immutable() -> None:
    result = RollResult(
        request=RollRequest(2, 6, True),
        values=(2, 5),
        total=7,
        matches=(),
        created_at=datetime(2026, 9, 5, 12, 0),
    )
    assert result.values == (2, 5)
