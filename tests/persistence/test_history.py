from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path
import sqlite3

import pytest

from oraculo_enom.domain.analysis import analyze
from oraculo_enom.domain.models import (
    Comparator,
    RollComponentRequest,
    RollRequest,
    RollResult,
)
from oraculo_enom.persistence.history import HistoryRepository


HISTORY_STORAGE_ERROR = (
    "No se puede guardar el historial en esta ubicación. Mové la aplicación a una "
    "carpeta con permisos de escritura."
)


@pytest.fixture
def repository(tmp_path: Path) -> Iterator[HistoryRepository]:
    history = HistoryRepository(tmp_path / "historial.db")
    yield history
    history.close()


def make_combined_result(
    *,
    created_at: datetime = datetime(2026, 9, 5, 12, 0),
    title: str = "Ataque combinado de Arhat",
) -> RollResult:
    request = RollRequest(
        (
            RollComponentRequest(2, 6, Comparator.GREATER_OR_EQUAL, 5),
            RollComponentRequest(3, 20, Comparator.GREATER_THAN, 12),
        ),
        show_sum=True,
        title=title,
    )
    return analyze(
        request,
        ((4, 6), (3, 15, 19)),
        created_at=created_at,
    )


def make_simple_result(
    *,
    created_at: datetime = datetime(2026, 9, 6, 18, 45),
    title: str = "Ataque de Máximo",
    sides: int = 20,
    values: tuple[int, ...] = (7, 18, 20),
    show_sum: bool = False,
    comparator: Comparator | None = Comparator.GREATER_THAN,
    threshold: int | None = 12,
) -> RollResult:
    request = RollRequest(
        (
            RollComponentRequest(
                len(values),
                sides,
                comparator,
                threshold,
            ),
        ),
        show_sum=show_sum,
        title=title,
    )
    return analyze(request, (values,), created_at=created_at)


def test_add_round_trips_a_combined_roll_and_ordered_components(
    tmp_path: Path,
) -> None:
    """Catches lossy or reordered serialization across an application restart."""
    database = tmp_path / "historial.db"
    result = make_combined_result()
    first = HistoryRepository(database)
    try:
        added = first.add(result)
        stored_header = first._connection.execute("SELECT * FROM rolls").fetchone()
        stored_components = first._connection.execute(
            "SELECT * FROM roll_components ORDER BY position"
        ).fetchall()
    finally:
        first.close()

    assert added.id > 0
    assert added.result == result
    assert stored_header["title"] == "Ataque combinado de Arhat"
    assert stored_header["show_sum"] == 1
    assert stored_header["total"] == 47
    assert [row["position"] for row in stored_components] == [0, 1]
    assert [row["sides"] for row in stored_components] == [6, 20]

    reopened = HistoryRepository(database)
    try:
        [round_tripped] = reopened.recent()
    finally:
        reopened.close()

    assert round_tripped.id == added.id
    assert round_tripped.result == result
    assert round_tripped.result.components[0].matches == (6,)
    assert round_tripped.result.components[1].matches == (15, 19)


def test_add_round_trips_nullable_sums_for_a_simple_roll(
    repository: HistoryRepository,
) -> None:
    """Catches a hidden sum being calculated or persisted when disabled."""
    result = make_simple_result()

    added = repository.add(result)
    [stored] = repository.recent()
    header = repository._connection.execute(
        "SELECT total FROM rolls WHERE id = ?", (added.id,)
    ).fetchone()
    component = repository._connection.execute(
        "SELECT subtotal FROM roll_components WHERE roll_id = ?", (added.id,)
    ).fetchone()

    assert header["total"] is None
    assert component["subtotal"] is None
    assert stored.result == result


def test_add_rolls_back_header_and_first_component_when_second_insert_fails(
    repository: HistoryRepository,
) -> None:
    """Catches a combined roll being left partially stored after an insert error."""
    repository._connection.execute(
        """
        CREATE TRIGGER fail_second_component
        BEFORE INSERT ON roll_components
        WHEN NEW.position = 1
        BEGIN
            SELECT RAISE(ABORT, 'forced second component failure');
        END
        """
    )
    repository._connection.commit()

    with pytest.raises(OSError) as error:
        repository.add(make_combined_result())

    assert str(error.value) == HISTORY_STORAGE_ERROR
    roll_count = repository._connection.execute(
        "SELECT COUNT(*) FROM rolls"
    ).fetchone()[0]
    assert roll_count == 0
    assert repository._connection.execute(
        "SELECT COUNT(*) FROM roll_components"
    ).fetchone()[0] == 0


def test_add_rolls_back_every_insert_when_commit_fails(
    repository: HistoryRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catches a failed commit leaving an allegedly unsaved roll pending."""
    connection = repository._connection
    commit_error = sqlite3.OperationalError("disk I/O error")

    class FailingCommitConnection:
        def execute(
            self, statement: str, parameters: tuple[object, ...] = ()
        ) -> sqlite3.Cursor:
            return connection.execute(statement, parameters)

        def commit(self) -> None:
            raise commit_error

        def rollback(self) -> None:
            connection.rollback()

        def close(self) -> None:
            connection.close()

    monkeypatch.setattr(repository, "_connection", FailingCommitConnection())

    with pytest.raises(OSError) as error:
        repository.add(make_combined_result())

    assert str(error.value) == HISTORY_STORAGE_ERROR
    assert error.value.__cause__ is commit_error
    assert connection.execute("SELECT COUNT(*) FROM rolls").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM roll_components").fetchone()[0] == 0


def test_recent_returns_newest_records_first_with_a_limit(
    repository: HistoryRepository,
) -> None:
    """Catches recent history ignoring timestamp order or its requested limit."""
    oldest = repository.add(
        make_simple_result(created_at=datetime(2026, 9, 4, 8, 0), title="Antigua")
    )
    middle = repository.add(make_combined_result())
    newest = repository.add(make_simple_result())

    records = repository.recent(limit=2)

    assert [record.id for record in records] == [newest.id, middle.id]
    assert oldest.id not in [record.id for record in records]


def test_recent_materializes_components_before_a_concurrent_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catches headers and components coming from different database snapshots."""
    database = tmp_path / "historial.db"
    reader = HistoryRepository(database)
    writer = HistoryRepository(database)
    added = reader.add(make_combined_result())
    connection = reader._connection
    deletion_happened = False

    class DeleteAfterFetchCursor:
        def __init__(self, cursor: sqlite3.Cursor) -> None:
            self._cursor = cursor

        def fetchall(self) -> list[sqlite3.Row]:
            nonlocal deletion_happened
            rows = self._cursor.fetchall()
            writer.delete(added.id)
            deletion_happened = True
            return rows

    class InterleavingConnection:
        def __init__(self) -> None:
            self.intercepted = False

        def execute(
            self, statement: str, parameters: tuple[object, ...] = ()
        ) -> sqlite3.Cursor | DeleteAfterFetchCursor:
            cursor = connection.execute(statement, parameters)
            if not self.intercepted and "FROM rolls" in statement:
                self.intercepted = True
                return DeleteAfterFetchCursor(cursor)
            return cursor

        def close(self) -> None:
            connection.close()

    monkeypatch.setattr(reader, "_connection", InterleavingConnection())

    try:
        records = reader.recent()
    finally:
        reader.close()
        writer.close()

    assert deletion_happened
    assert records == [added]


def test_search_title_is_a_case_insensitive_substring(
    repository: HistoryRepository,
) -> None:
    """Catches title search requiring exact case or an exact full title."""
    selected = repository.add(make_combined_result())
    repository.add(make_simple_result())

    records = repository.search(title="aRhAt")

    assert [record.id for record in records] == [selected.id]


def test_search_sides_matches_any_component_without_duplicate_headers(
    repository: HistoryRepository,
) -> None:
    """Catches combined rolls being omitted or repeated by a die-side search."""
    combined = repository.add(make_combined_result())
    simple = repository.add(make_simple_result())
    repository.add(
        make_simple_result(
            created_at=datetime(2026, 9, 4, 8, 0),
            title="Curación",
            sides=12,
            values=(9,),
            comparator=None,
            threshold=None,
        )
    )

    records = repository.search(sides=20)

    assert [record.id for record in records] == [simple.id, combined.id]
    assert [record.id for record in records].count(combined.id) == 1


def test_search_date_range_keeps_both_calendar_endpoints(
    repository: HistoryRepository,
) -> None:
    """Catches inclusive date filtering losing either edge of the selected day."""
    repository.add(
        make_simple_result(created_at=datetime(2026, 9, 4, 23, 59), title="Antes")
    )
    selected = repository.add(make_combined_result())
    repository.add(
        make_simple_result(created_at=datetime(2026, 9, 6, 0, 0), title="Después")
    )

    records = repository.search(
        date_from=date(2026, 9, 5),
        date_to=date(2026, 9, 5),
    )

    assert [record.id for record in records] == [selected.id]


def test_update_title_trims_it_and_changes_nothing_else(
    repository: HistoryRepository,
) -> None:
    """Catches title editing replacing or mutating the stored roll configuration."""
    original = make_combined_result()
    added = repository.add(original)

    updated = repository.update_title(added.id, "  Ataque corregido  ")
    [stored] = repository.recent()

    assert updated.result.request.title == "Ataque corregido"
    assert updated.result.request.components == original.request.components
    assert updated.result.request.show_sum is True
    assert updated.result.components == original.components
    assert updated.result.total == original.total
    assert updated.result.created_at == original.created_at
    assert stored == updated


def test_update_title_accepts_an_empty_title(
    repository: HistoryRepository,
) -> None:
    """Catches title removal being rejected even though titles are optional."""
    added = repository.add(make_simple_result())

    updated = repository.update_title(added.id, "   ")

    assert updated.result.request.title == ""


def test_update_title_rejects_151_characters_without_changing_storage(
    repository: HistoryRepository,
) -> None:
    """Catches an overlong title reaching SQLite or overwriting the valid title."""
    added = repository.add(make_combined_result())

    with pytest.raises(ValueError) as error:
        repository.update_title(added.id, "x" * 151)

    assert str(error.value) == "El título admite hasta 150 caracteres"
    assert repository.recent()[0].result.request.title == "Ataque combinado de Arhat"


def test_update_title_rejects_a_nonexistent_record(
    repository: HistoryRepository,
) -> None:
    """Catches a title edit reporting success when no history row was updated."""
    with pytest.raises(LookupError):
        repository.update_title(999, "Ataque")


def test_failed_title_update_rolls_back_and_preserves_the_record(
    repository: HistoryRepository,
) -> None:
    """Catches a storage error exposing a title that was never committed."""
    added = repository.add(make_combined_result())
    repository._connection.execute(
        """
        CREATE TRIGGER prevent_title_update
        BEFORE UPDATE OF title ON rolls
        BEGIN
            SELECT RAISE(ABORT, 'forced title failure');
        END
        """
    )
    repository._connection.commit()

    with pytest.raises(OSError) as error:
        repository.update_title(added.id, "Título perdido")

    assert str(error.value) == HISTORY_STORAGE_ERROR
    assert repository.recent()[0].result.request.title == "Ataque combinado de Arhat"


def test_delete_cascades_to_every_component(
    repository: HistoryRepository,
) -> None:
    """Catches deleting a header while leaving orphaned component rows."""
    removed = repository.add(make_combined_result())
    kept = repository.add(make_simple_result())

    repository.delete(removed.id)

    assert [record.id for record in repository.recent()] == [kept.id]
    assert repository._connection.execute(
        "SELECT COUNT(*) FROM roll_components WHERE roll_id = ?", (removed.id,)
    ).fetchone()[0] == 0


def test_failed_delete_rolls_back_and_preserves_the_complete_roll(
    repository: HistoryRepository,
) -> None:
    """Catches a failed deletion removing only part of a saved combination."""
    added = repository.add(make_combined_result())
    repository._connection.execute(
        """
        CREATE TRIGGER prevent_roll_delete
        BEFORE DELETE ON rolls
        BEGIN
            SELECT RAISE(ABORT, 'forced delete failure');
        END
        """
    )
    repository._connection.commit()

    with pytest.raises(OSError) as error:
        repository.delete(added.id)

    assert str(error.value) == HISTORY_STORAGE_ERROR
    assert repository.recent() == [added]
    assert repository._connection.execute(
        "SELECT COUNT(*) FROM roll_components WHERE roll_id = ?", (added.id,)
    ).fetchone()[0] == 2


def test_clear_removes_all_headers_and_components(
    repository: HistoryRepository,
) -> None:
    """Catches clear history leaving rows in either persistence table."""
    repository.add(make_combined_result())
    repository.add(make_simple_result())

    repository.clear()

    assert repository.recent() == []
    roll_count = repository._connection.execute(
        "SELECT COUNT(*) FROM rolls"
    ).fetchone()[0]
    assert roll_count == 0
    assert repository._connection.execute(
        "SELECT COUNT(*) FROM roll_components"
    ).fetchone()[0] == 0


def test_repository_translates_database_open_failure(tmp_path: Path) -> None:
    """Catches an unwritable history location leaking SQLite details to the UI."""
    database_directory = tmp_path / "historial.db"
    database_directory.mkdir()

    with pytest.raises(OSError) as error:
        HistoryRepository(database_directory)

    assert str(error.value) == HISTORY_STORAGE_ERROR
    assert isinstance(error.value.__cause__, sqlite3.Error)


def test_recent_translates_sqlite_read_failure(
    repository: HistoryRepository,
) -> None:
    """Catches a failed history read leaking raw SQLite details to the UI."""
    repository._connection.close()

    with pytest.raises(OSError) as error:
        repository.recent()

    assert str(error.value) == HISTORY_STORAGE_ERROR
    assert isinstance(error.value.__cause__, sqlite3.Error)
