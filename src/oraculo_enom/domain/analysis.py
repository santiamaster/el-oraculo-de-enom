import operator
from collections.abc import Callable
from datetime import datetime

from .models import Comparator, RollRequest, RollResult


OPERATIONS: dict[Comparator, Callable[[int, int], bool]] = {
    Comparator.GREATER_THAN: operator.gt,
    Comparator.GREATER_OR_EQUAL: operator.ge,
    Comparator.LESS_THAN: operator.lt,
    Comparator.LESS_OR_EQUAL: operator.le,
    Comparator.EQUAL: operator.eq,
}


def analyze(
    request: RollRequest,
    values: tuple[int, ...],
    created_at: datetime | None = None,
) -> RollResult:
    """Build an immutable roll result and apply the optional value filter."""
    if len(values) != request.count:
        raise ValueError(f"expected {request.count} values, got {len(values)}")

    total = sum(values)
    matches: tuple[int, ...] = ()
    if request.comparator is not None:
        if request.threshold is None:
            raise ValueError("a comparator requires a threshold")
        operation = OPERATIONS[request.comparator]
        matches = tuple(
            value for value in values if operation(value, request.threshold)
        )

    return RollResult(
        request=request,
        values=values,
        total=total,
        matches=matches,
        created_at=created_at if created_at is not None else datetime.now(),
    )
