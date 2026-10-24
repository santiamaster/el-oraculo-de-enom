from collections.abc import Iterator
from datetime import date, datetime
import json
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


def test_arbitrary_thresholds_and_legacy_integer_records_reopen_exactly(tmp_path):
    """Catches precision loss, incompatible v1 arrays, or schema version drift."""
    database = tmp_path / "thresholds.db"
    thresholds = [None, 0, -(2**63), 2**63 - 1, -(2**63) - 1, 2**63, 10**50, -(10**50)]
    history = HistoryRepository(database)
    expected = {}
    try:
        for threshold in thresholds:
            result = make_simple_result(
                threshold=threshold,
                comparator=Comparator.GREATER_THAN if threshold is not None else None,
            )
            expected[history.add(result).id] = threshold
        rows = history._connection.execute(
            "SELECT threshold, values_json FROM roll_components ORDER BY roll_id"
        ).fetchall()
        assert [row["threshold"] for row in rows[:4]] == thresholds[:4]
        assert all(json.loads(row["values_json"]) == [7, 18, 20] for row in rows)
        assert history._connection.execute("PRAGMA user_version").fetchone()[0] == 1
    finally:
        history.close()
    reopened = HistoryRepository(database)
    try:
        for record in reopened.recent(20):
            assert record.result.request.components[0].threshold == expected.pop(record.id)
        assert not expected
    finally:
        reopened.close()


def test_threshold_beyond_python_decimal_limit_round_trips_exactly(repository):
    """Catches Python's digit guard imposing an undeclared domain limit."""
    threshold = 10**5000
    record = repository.add(
        make_simple_result(
            threshold=threshold,
            comparator=Comparator.GREATER_THAN,
        )
    )
    stored = repository._connection.execute(
        "SELECT threshold FROM roll_components WHERE roll_id = ?", (record.id,)
    ).fetchone()

    assert stored["threshold"] == "int:1" + "0" * 5000
    assert repository.recent(1)[0].id == record.id
    assert (
        repository.recent(1)[0].result.request.components[0].threshold
        == threshold
    )


@pytest.mark.parametrize("threshold", [
    "int:9223372036854775808", "int:-9223372036854775809", "int:" + "9" * 50,
])
def test_sqlite_accepts_canonical_marked_arbitrary_threshold(repository, threshold):
    record = repository.add(make_simple_result())
    repository._connection.execute(
        "UPDATE roll_components SET threshold = ? WHERE roll_id = ?", (threshold, record.id)
    )
    repository._connection.commit()
    assert repository.recent()[0].result.request.components[0].threshold == int(threshold[4:])


@pytest.mark.parametrize("threshold", [
    "int:1", "int:0", "int:-0", "int:+9223372036854775808",
    "int:09223372036854775808", "int:-09223372036854775809", "int:",
    "int:9223372036854775808.0", "int:9223372036854775808x", "int:1e50",
    "int:9223372036854775808\n", "int:9223372036854775808\x00",
])
def test_sqlite_rejects_noncanonical_marked_threshold(repository, threshold):
    repository.add(make_simple_result())
    with pytest.raises(sqlite3.IntegrityError):
        repository._connection.execute("UPDATE roll_components SET threshold = ?", (threshold,))
    repository._connection.rollback()
    assert repository.recent()[0].result.request.components[0].threshold == 12


@pytest.mark.parametrize("query", ["recent", "search"])
@pytest.mark.parametrize("payload", [
    "[99]", "[99, 6]", "[0, 6]", "[4]", "[4, 6, 1]", "[true, 6]",
    "[4.0, 6]", '["4", 6]', "[null, 6]", '[[4], 6]',
    '{"4": 6}', '"46"', "null", "4", "[4,", "[NaN, 6]",
])
def test_corrupt_values_are_controlled_and_never_mutate_storage(repository, payload, query):
    """Catches malformed JSON, noninteger values, or count/range mismatch hydration."""
    record = repository.add(make_combined_result())
    repository._connection.execute(
        "UPDATE roll_components SET values_json = ? WHERE roll_id = ? AND position = 0",
        (payload, record.id),
    )
    repository._connection.commit()
    before = tuple(repository._connection.iterdump())

    with pytest.raises(OSError, match="datos inconsistentes.*copia"):
        getattr(repository, query)()

    assert tuple(repository._connection.iterdump()) == before


@pytest.mark.parametrize("statement", [
    "UPDATE roll_components SET subtotal = 999 WHERE position = 0",
    "UPDATE rolls SET total = 999",
    "UPDATE roll_components SET position = 4 WHERE position = 1",
    "DELETE FROM roll_components",
    "UPDATE rolls SET created_at = 'ayer'",
    "UPDATE rolls SET created_at = '2026-09-05'",
    "UPDATE roll_components SET threshold = 'int:01' WHERE position = 0",
    "UPDATE roll_components SET threshold = 'int:12' WHERE position = 0",
    "UPDATE roll_components SET threshold = 1.5 WHERE position = 0",
    "UPDATE roll_components SET comparator = '!=' WHERE position = 0",
    "UPDATE roll_components SET comparator = NULL WHERE position = 0",
    "UPDATE rolls SET show_sum = 7",
    "UPDATE rolls SET show_sum = 0, total = NULL",
    "UPDATE roll_components SET subtotal = NULL WHERE position = 0",
    "UPDATE roll_components SET count = 1.5 WHERE position = 0",
    "UPDATE roll_components SET count = 999, values_json = '[' || rtrim(replace(hex(zeroblob(999)), '00', '1,'), ',') || ']' WHERE position = 0",
])
def test_corrupt_aggregate_is_controlled_and_never_mutates_storage(repository, statement):
    """Catches missing groups, invalid requests, malformed thresholds and inconsistent sums."""
    repository.add(make_combined_result())
    connection = repository._connection
    connection.execute("PRAGMA ignore_check_constraints = ON")
    connection.execute("DROP TRIGGER validate_component_subtotal_update")
    connection.execute("DROP TRIGGER validate_roll_sum_update")
    connection.execute(statement)
    connection.commit()
    before = tuple(connection.iterdump())

    with pytest.raises(OSError, match="datos inconsistentes.*copia"):
        repository.recent()

    assert tuple(connection.iterdump()) == before


def test_retitle_of_corrupt_record_rolls_back_instead_of_committing(repository):
    record = repository.add(make_combined_result())
    repository._connection.execute("UPDATE roll_components SET values_json = '[99]'")
    repository._connection.commit()
    before = tuple(repository._connection.iterdump())
    with pytest.raises(OSError, match="datos inconsistentes.*copia"):
        repository.update_title(record.id, "No guardar")
    assert tuple(repository._connection.iterdump()) == before


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
