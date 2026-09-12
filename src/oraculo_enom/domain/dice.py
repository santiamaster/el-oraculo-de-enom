import secrets
from collections.abc import Callable

from .models import (
    MAX_COMPONENTS,
    MAX_SIDES,
    MAX_TITLE_LENGTH,
    MAX_TOTAL_DICE,
    MIN_SIDES,
    RollRequest,
)


def validate_request(request: RollRequest) -> None:
    """Validate component limits and relationships for one complete roll."""
    if not request.components:
        raise ValueError("La tirada debe contener al menos un tipo de dado")
    if len(request.components) > MAX_COMPONENTS:
        raise ValueError("La tirada admite hasta 10 tipos de dado")
    if len(request.title) > MAX_TITLE_LENGTH:
        raise ValueError("El título admite hasta 150 caracteres")

    for component in request.components:
        if not 1 <= component.count <= MAX_TOTAL_DICE:
            raise ValueError("La cantidad de dados debe estar entre 1 y 1.000")
        if not MIN_SIDES <= component.sides <= MAX_SIDES:
            raise ValueError("La cantidad de caras debe estar entre 2 y 1.000")
        if (component.comparator is None) != (component.threshold is None):
            raise ValueError("El filtro necesita un comparador y un umbral")

    if not 1 <= request.total_count <= MAX_TOTAL_DICE:
        raise ValueError("La cantidad total de dados debe estar entre 1 y 1.000")
    if len({component.sides for component in request.components}) != len(
        request.components
    ):
        raise ValueError("Cada tipo de dado debe aparecer una sola vez")


def roll_values(
    request: RollRequest,
    randbelow: Callable[[int], int] = secrets.randbelow,
) -> tuple[tuple[int, ...], ...]:
    """Generate one ordered tuple of one-based values per component."""
    validate_request(request)
    return tuple(
        tuple(randbelow(component.sides) + 1 for _ in range(component.count))
        for component in request.components
    )
