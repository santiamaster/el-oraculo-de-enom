from datetime import datetime

from oraculo_enom.domain.analysis import analyze
from oraculo_enom.domain.models import Comparator, RollRequest
from oraculo_enom.services.clipboard import format_roll


def test_format_roll_includes_values_sum_and_filter() -> None:
    request = RollRequest(3, 20, True, Comparator.GREATER_THAN, 12)
    result = analyze(request, (7, 18, 20), datetime(2026, 9, 5, 12, 0))

    assert format_roll(result) == "3d20: 7, 18, 20\nSuma: 45\nFiltro > 12: 2 de 3"


def test_format_roll_omits_sum_when_hidden() -> None:
    request = RollRequest(3, 20, False, Comparator.GREATER_THAN, 12)
    result = analyze(request, (7, 18, 20), datetime(2026, 9, 5, 12, 0))

    assert format_roll(result) == "3d20: 7, 18, 20\nFiltro > 12: 2 de 3"


def test_format_roll_omits_filter_when_inactive() -> None:
    request = RollRequest(2, 6, True)
    result = analyze(request, (2, 5), datetime(2026, 9, 5, 12, 0))

    assert format_roll(result) == "2d6: 2, 5\nSuma: 7"
