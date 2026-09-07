from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


MAX_TITLE_LENGTH = 150
MAX_COMPONENTS = 10
MAX_TOTAL_DICE = 1_000
MIN_SIDES = 2
MAX_SIDES = 1_000


class Comparator(StrEnum):
    GREATER_THAN = ">"
    GREATER_OR_EQUAL = ">="
    LESS_THAN = "<"
    LESS_OR_EQUAL = "<="
    EQUAL = "="


@dataclass(frozen=True, slots=True)
class RollComponentRequest:
    count: int
    sides: int
    comparator: Comparator | None = None
    threshold: int | None = None

    @property
    def notation(self) -> str:
        return f"{self.count}d{self.sides}"


@dataclass(frozen=True, slots=True)
class RollRequest:
    components: tuple[RollComponentRequest, ...]
    show_sum: bool
    title: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", self.title.strip())

    @property
    def notation(self) -> str:
        return " + ".join(component.notation for component in self.components)

    @property
    def total_count(self) -> int:
        return sum(component.count for component in self.components)

    @property
    def is_combined(self) -> bool:
        return len(self.components) > 1


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
