import secrets
from collections.abc import Callable

from .models import RollRequest


def validate_request(request: RollRequest) -> None:
    """Validate dice count, sides, and the optional filter pair."""
    if not 1 <= request.count <= 1000:
        raise ValueError(
            "La cantidad de dados debe estar entre 1 y 1.000 "
            "(dados debe estar entre 1 y 1.000)"
        )
    if not 2 <= request.sides <= 1000:
        raise ValueError(
            "La cantidad de caras debe estar entre 2 y 1.000 "
            "(caras debe estar entre 2 y 1.000)"
        )
    if (request.comparator is None) != (request.threshold is None):
        raise ValueError("El filtro necesita un comparador y un umbral")


def roll_values(
    request: RollRequest,
    randbelow: Callable[[int], int] = secrets.randbelow,
) -> tuple[int, ...]:
    """Generate one-based die values using an injectable random source."""
    validate_request(request)
    return tuple(randbelow(request.sides) + 1 for _ in range(request.count))
