from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Comparator(StrEnum):
    GREATER_THAN = ">"
    GREATER_OR_EQUAL = ">="
    LESS_THAN = "<"
    LESS_OR_EQUAL = "<="
    EQUAL = "="


@dataclass(frozen=True, slots=True)
class RollRequest:
    count: int
    sides: int
    show_sum: bool
    comparator: Comparator | None = None
    threshold: int | None = None

    @property
    def notation(self) -> str:
        return f"{self.count}d{self.sides}"


@dataclass(frozen=True, slots=True)
class RollResult:
    request: RollRequest
    values: tuple[int, ...]
    total: int
    matches: tuple[int, ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RollRecord:
    id: int
    result: RollResult
