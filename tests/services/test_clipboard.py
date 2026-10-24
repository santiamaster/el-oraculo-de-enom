from datetime import datetime

from oraculo_enom.domain.analysis import analyze
from oraculo_enom.domain.models import Comparator, RollComponentRequest, RollRequest
from oraculo_enom.services.clipboard import format_roll


FIXED_TIME = datetime(2026, 9, 7, 12, 0)


def test_format_combined_roll_includes_title_sums_and_component_filters() -> None:
    request = RollRequest(
        (
            RollComponentRequest(2, 6, Comparator.GREATER_OR_EQUAL, 5),
            RollComponentRequest(3, 20, Comparator.GREATER_THAN, 12),
        ),
        show_sum=True,
        title="Ataque combinado de Arhat",
    )
    result = analyze(request, ((4, 6), (3, 15, 19)), created_at=FIXED_TIME)

    assert format_roll(result) == (
        "Ataque combinado de Arhat\n"
        "2d6: 4, 6\n"
        "Subtotal d6: 10\n"
        "Filtro d6 >= 5: 1 de 2\n"
        "3d20: 3, 15, 19\n"
        "Subtotal d20: 37\n"
        "Filtro d20 > 12: 2 de 3\n"
        "Suma total: 47"
    )


def test_format_simple_titled_roll_places_title_before_values() -> None:
    request = RollRequest(
        (RollComponentRequest(3, 20, Comparator.GREATER_THAN, 12),),
        show_sum=False,
        title="Ataque de Máximo",
    )
    result = analyze(request, ((7, 18, 20),), created_at=FIXED_TIME)

    assert format_roll(result) == (
        "Ataque de Máximo\n"
        "3d20: 7, 18, 20\n"
        "Filtro > 12: 2 de 3"
    )


def test_format_untitled_roll_starts_with_notation() -> None:
    request = RollRequest((RollComponentRequest(2, 6),), show_sum=False)
    result = analyze(request, ((2, 5),), created_at=FIXED_TIME)

    assert format_roll(result) == "2d6: 2, 5"


def test_format_combined_filters_without_hidden_sums() -> None:
    request = RollRequest(
        (
            RollComponentRequest(2, 6, Comparator.GREATER_OR_EQUAL, 5),
            RollComponentRequest(1, 8),
            RollComponentRequest(3, 20, Comparator.GREATER_THAN, 12),
        ),
        show_sum=False,
    )
    result = analyze(request, ((4, 6), (8,), (3, 15, 19)), created_at=FIXED_TIME)

    assert format_roll(result) == (
        "2d6: 4, 6\n"
        "Filtro d6 >= 5: 1 de 2\n"
        "1d8: 8\n"
        "3d20: 3, 15, 19\n"
        "Filtro d20 > 12: 2 de 3"
    )


def test_format_simple_sum_uses_compact_sum_label() -> None:
    request = RollRequest((RollComponentRequest(2, 6),), show_sum=True)
    result = analyze(request, ((2, 5),), created_at=FIXED_TIME)

    assert format_roll(result) == "2d6: 2, 5\nSuma: 7"
