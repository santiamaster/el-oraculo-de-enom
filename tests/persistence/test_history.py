from datetime import date, datetime
from pathlib import Path

from oraculo_enom.domain.models import Comparator, RollRequest, RollResult
from oraculo_enom.persistence.history import HistoryRepository


def make_result(
    *,
    sides: int = 20,
    values: tuple[int, ...] = (4, 16, 19),
    created_at: datetime = datetime(2026, 9, 5, 12, 0),
    comparator: Comparator | None = None,
    threshold: int | None = None,
) -> RollResult:
    request = RollRequest(
        count=len(values),
        sides=sides,
        show_sum=True,
        comparator=comparator,
        threshold=threshold,
    )
    matches = (
        tuple(value for value in values if value >= threshold)
        if comparator is Comparator.GREATER_OR_EQUAL and threshold is not None
        else ()
    )
    return RollResult(
        request=request,
        values=values,
        total=sum(values),
        matches=matches,
        created_at=created_at,
    )


def test_add_survives_reopen_with_filtered_roll_details(tmp_path: Path) -> None:
    """Catches lossy serialization of a filtered roll across an app restart."""
    database = tmp_path / "historial.db"
    result = make_result(
        comparator=Comparator.GREATER_OR_EQUAL,
        threshold=16,
    )
    repository = HistoryRepository(database)
    added = repository.add(result)
    repository.close()

    reopened = HistoryRepository(database)
    [stored] = reopened.recent()

    assert stored.id == added.id
    assert stored.result.request.notation == "3d20"
    assert stored.result.values == (4, 16, 19)
    assert stored.result.total == 39
    assert stored.result.matches == (16, 19)
    assert stored.result.request.comparator is Comparator.GREATER_OR_EQUAL
    assert stored.result.request.threshold == 16
    assert stored.result.created_at == datetime(2026, 9, 5, 12, 0)
    reopened.close()


def test_recent_returns_newest_records_first(tmp_path: Path) -> None:
    """Catches the recent-history panel showing old rolls before new ones."""
    repository = HistoryRepository(tmp_path / "historial.db")
    first = repository.add(make_result(created_at=datetime(2026, 9, 5, 8, 0)))
    second = repository.add(make_result(created_at=datetime(2026, 9, 5, 9, 0)))
    third = repository.add(make_result(created_at=datetime(2026, 9, 5, 10, 0)))

    records = repository.recent(limit=2)

    assert [record.id for record in records] == [third.id, second.id]
    assert first.id not in [record.id for record in records]
    repository.close()


def test_search_filters_by_sides_and_inclusive_date_range(tmp_path: Path) -> None:
    """Catches history filters omitting a selected die type or either date endpoint."""
    repository = HistoryRepository(tmp_path / "historial.db")
    early = repository.add(
        make_result(sides=6, created_at=datetime(2026, 9, 4, 23, 59))
    )
    selected = repository.add(
        make_result(sides=20, created_at=datetime(2026, 9, 5, 12, 0))
    )
    late = repository.add(
        make_result(sides=20, created_at=datetime(2026, 9, 6, 0, 0))
    )

    records = repository.search(
        sides=20,
        date_from=date(2026, 9, 5),
        date_to=date(2026, 9, 5),
    )

    assert [record.id for record in records] == [selected.id]
    assert early.id not in [record.id for record in records]
    assert late.id not in [record.id for record in records]
    repository.close()


def test_delete_removes_only_the_selected_record(tmp_path: Path) -> None:
    """Catches deleting the wrong row or leaving a deleted row in history."""
    repository = HistoryRepository(tmp_path / "historial.db")
    kept = repository.add(make_result(created_at=datetime(2026, 9, 5, 8, 0)))
    removed = repository.add(make_result(created_at=datetime(2026, 9, 5, 9, 0)))

    repository.delete(removed.id)

    assert [record.id for record in repository.recent()] == [kept.id]
    repository.close()


def test_clear_removes_every_record(tmp_path: Path) -> None:
    """Catches a clear-history action that leaves rows behind."""
    repository = HistoryRepository(tmp_path / "historial.db")
    repository.add(make_result())
    repository.add(make_result(created_at=datetime(2026, 9, 5, 13, 0)))

    repository.clear()

    assert repository.recent() == []
    repository.close()
