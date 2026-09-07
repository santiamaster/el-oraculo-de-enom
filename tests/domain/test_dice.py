import pytest

from oraculo_enom.domain.dice import roll_values, validate_request
from oraculo_enom.domain.models import Comparator, RollComponentRequest, RollRequest


@pytest.mark.parametrize(
    "req",
    [
        RollRequest((RollComponentRequest(1, 2),), False),
        RollRequest((RollComponentRequest(1000, 1000),), True),
        RollRequest(
            tuple(RollComponentRequest(100, sides) for sides in range(2, 12)),
            False,
        ),
    ],
)
def test_valid_boundaries(req: RollRequest) -> None:
    validate_request(req)


@pytest.mark.parametrize(
    "req,message",
    [
        (
            RollRequest((RollComponentRequest(0, 20),), False),
            "dados debe estar entre 1 y 1.000",
        ),
        (
            RollRequest((RollComponentRequest(1001, 20),), False),
            "dados debe estar entre 1 y 1.000",
        ),
        (
            RollRequest((RollComponentRequest(1, 1),), False),
            "caras debe estar entre 2 y 1.000",
        ),
        (
            RollRequest((RollComponentRequest(1, 1001),), False),
            "caras debe estar entre 2 y 1.000",
        ),
        (RollRequest((), False), "La tirada debe contener al menos un tipo de dado"),
        (
            RollRequest(
                tuple(RollComponentRequest(1, sides) for sides in range(2, 13)),
                False,
            ),
            "La tirada admite hasta 10 tipos de dado",
        ),
        (
            RollRequest(
                (RollComponentRequest(500, 6), RollComponentRequest(501, 20)),
                False,
            ),
            "La cantidad total de dados debe estar entre 1 y 1.000",
        ),
        (
            RollRequest(
                (RollComponentRequest(1, 20), RollComponentRequest(2, 20)),
                False,
            ),
            "Cada tipo de dado debe aparecer una sola vez",
        ),
        (
            RollRequest((RollComponentRequest(1, 20),), False, "A" * 151),
            "El título admite hasta 150 caracteres",
        ),
    ],
)
def test_invalid_boundaries(req: RollRequest, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_request(req)


def test_roll_maps_zero_based_random_values_to_dice_values() -> None:
    generated = iter([0, 5, 19])
    request = RollRequest(
        (RollComponentRequest(2, 6), RollComponentRequest(1, 20)),
        False,
    )

    assert roll_values(request, lambda _: next(generated)) == ((1, 6), (20,))


def test_roll_executes_the_minimum_1d2_boundary() -> None:
    """Catches generation skipping the inclusive upper face at the minimum size."""
    values = roll_values(
        RollRequest((RollComponentRequest(1, 2),), False),
        lambda sides: sides - 1,
    )

    assert values == ((2,),)


def test_roll_executes_1000d1000_with_every_value_in_bounds() -> None:
    """Catches maximum-size generation truncating values or exceeding d1000."""
    generated = iter(range(1_000))

    def deterministic_randbelow(sides: int) -> int:
        assert sides == 1_000
        return next(generated)

    values = roll_values(
        RollRequest((RollComponentRequest(1_000, 1_000),), True),
        deterministic_randbelow,
    )

    assert len(values) == 1
    assert len(values[0]) == 1_000
    assert all(1 <= value <= 1_000 for value in values[0])
    assert values[0] == tuple(range(1, 1_001))


@pytest.mark.parametrize(
    "req",
    [
        RollRequest(
            (RollComponentRequest(1, 20, comparator=Comparator.GREATER_THAN),),
            False,
        ),
        RollRequest((RollComponentRequest(1, 20, threshold=10),), False),
    ],
)
def test_filter_requires_comparator_and_threshold(req: RollRequest) -> None:
    with pytest.raises(ValueError, match="El filtro necesita un comparador y un umbral"):
        validate_request(req)
