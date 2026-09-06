import pytest

from oraculo_enom.domain.dice import roll_values, validate_request
from oraculo_enom.domain.models import Comparator, RollRequest


@pytest.mark.parametrize("req", [RollRequest(1, 2, False), RollRequest(1000, 1000, True)])
def test_valid_boundaries(req: RollRequest) -> None:
    validate_request(req)


@pytest.mark.parametrize(
    "req,message",
    [
        (RollRequest(0, 20, False), "dados debe estar entre 1 y 1.000"),
        (RollRequest(1001, 20, False), "dados debe estar entre 1 y 1.000"),
        (RollRequest(1, 1, False), "caras debe estar entre 2 y 1.000"),
        (RollRequest(1, 1001, False), "caras debe estar entre 2 y 1.000"),
    ],
)
def test_invalid_boundaries(req: RollRequest, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_request(req)


def test_roll_maps_zero_based_random_values_to_dice_values() -> None:
    generated = iter([0, 19, 9])
    assert roll_values(RollRequest(3, 20, False), lambda _: next(generated)) == (1, 20, 10)


def test_roll_executes_the_minimum_1d2_boundary() -> None:
    """Catches generation skipping the inclusive upper face at the minimum size."""
    values = roll_values(RollRequest(1, 2, False), lambda sides: sides - 1)

    assert values == (2,)


def test_roll_executes_1000d1000_with_every_value_in_bounds() -> None:
    """Catches maximum-size generation truncating values or exceeding d1000."""
    generated = iter(range(1_000))

    def deterministic_randbelow(sides: int) -> int:
        assert sides == 1_000
        return next(generated)

    values = roll_values(
        RollRequest(1_000, 1_000, True), deterministic_randbelow
    )

    assert len(values) == 1_000
    assert all(1 <= value <= 1_000 for value in values)
    assert values == tuple(range(1, 1_001))


@pytest.mark.parametrize(
    "req",
    [
        RollRequest(1, 20, False, comparator=Comparator.GREATER_THAN, threshold=None),
        RollRequest(1, 20, False, comparator=None, threshold=10),
    ],
)
def test_filter_requires_comparator_and_threshold(req: RollRequest) -> None:
    with pytest.raises(ValueError, match="El filtro necesita un comparador y un umbral"):
        validate_request(req)
