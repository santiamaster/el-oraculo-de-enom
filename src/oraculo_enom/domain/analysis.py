import operator
from collections.abc import Callable
from datetime import datetime

from .dice import validate_request
from .models import (
    Comparator,
    RollComponentRequest,
    RollComponentResult,
    RollRequest,
    RollResult,
)


OPERATIONS: dict[Comparator, Callable[[int, int], bool]] = {
    Comparator.GREATER_THAN: operator.gt,
    Comparator.GREATER_OR_EQUAL: operator.ge,
    Comparator.LESS_THAN: operator.lt,
    Comparator.LESS_OR_EQUAL: operator.le,
    Comparator.EQUAL: operator.eq,
}


def analyze(
    request: RollRequest,
    values_by_component: tuple[tuple[int, ...], ...],
    created_at: datetime | None = None,
) -> RollResult:
    """Validate and analyze ordered values for every request component."""
    validate_request(request)
    if len(values_by_component) != len(request.components):
        raise ValueError(
            f"expected {len(request.components)} value groups, "
            f"got {len(values_by_component)}"
        )

    component_results: list[RollComponentResult] = []
    running_total = 0
    for component, values in zip(request.components, values_by_component):
        _validate_values(component, values)
        subtotal = sum(values) if request.show_sum else None
        if subtotal is not None:
            running_total += subtotal

        matches: tuple[int, ...] = ()
        if component.comparator is not None:
            threshold = component.threshold
            if threshold is None:
                raise ValueError("El filtro necesita un comparador y un umbral")
            operation = OPERATIONS[component.comparator]
            matches = tuple(
                value for value in values if operation(value, threshold)
            )

        component_results.append(
            RollComponentResult(
                request=component,
                values=values,
                subtotal=subtotal,
                matches=matches,
            )
        )

    return RollResult(
        request=request,
        components=tuple(component_results),
        total=running_total if request.show_sum else None,
        created_at=created_at if created_at is not None else datetime.now(),
    )


def _validate_values(
    component: RollComponentRequest,
    values: tuple[int, ...],
) -> None:
    if len(values) != component.count:
        raise ValueError(
            f"expected {component.count} values for {component.notation}, "
            f"got {len(values)}"
        )
    if any(value < 1 or value > component.sides for value in values):
        raise ValueError(
            f"values for d{component.sides} must be between 1 and {component.sides}"
        )
