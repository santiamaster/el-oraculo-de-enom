from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
from threading import Barrier

import pytest

from oraculo_enom.persistence import database as database_module
from oraculo_enom.persistence.database import connect


SCHEMA_RESET_REQUIRED = (
    "El historial pertenece a una versión de prueba anterior. Cerrá la aplicación "
    "y mové o eliminá datos/historial.db antes de continuar."
)


def _insert_roll(
    connection: sqlite3.Connection,
    *,
    title: str = "Ataque combinado de Arhat",
    show_sum: int = 1,
    total: int | None = 47,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO rolls (created_at, title, show_sum, total)
        VALUES (?, ?, ?, ?)
        """,
        ("2026-09-07T12:00:00", title, show_sum, total),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def _insert_component(
    connection: sqlite3.Connection,
    roll_id: int,
    *,
    position: int = 0,
    count: int = 2,
    sides: int = 6,
    subtotal: int | None = 10,
    comparator: str | None = ">=",
    threshold: int | None = 5,
) -> None:
    connection.execute(
        """
        INSERT INTO roll_components (
            roll_id, position, count, sides, values_json, subtotal,
            comparator, threshold
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            roll_id,
            position,
            count,
            sides,
            "[4, 6]",
            subtotal,
            comparator,
            threshold,
        ),
    )


def test_connect_creates_the_versioned_schema_and_indexes(tmp_path: Path) -> None:
    """Catches a fresh database missing versioning, relations, or query indexes."""
    connection = connect(tmp_path / "historial.db")

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    indexes = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        )
    }

    assert tables == {"rolls", "roll_components"}
    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
    assert {
        "idx_rolls_created_at",
        "idx_rolls_title",
        "idx_roll_components_roll_id",
        "idx_roll_components_sides",
    } <= indexes
    connection.close()


def test_connect_rejects_an_experimental_schema_without_changing_it(
    tmp_path: Path,
) -> None:
    """Catches an incompatible pre-1.0 history being silently erased or migrated."""
    database = tmp_path / "historial.db"
    old_connection = sqlite3.connect(database)
    old_connection.execute(
        """
        CREATE TABLE rolls (
            id INTEGER PRIMARY KEY,
            count INTEGER NOT NULL,
            sides INTEGER NOT NULL,
            values_json TEXT NOT NULL
        )
        """
    )
    old_connection.execute(
        "INSERT INTO rolls (count, sides, values_json) VALUES (3, 20, '[4, 16, 19]')"
    )
    old_connection.commit()
    old_connection.close()

    with pytest.raises(OSError) as error:
        connect(database)

    assert str(error.value) == SCHEMA_RESET_REQUIRED
    assert database.is_file()
    preserved = sqlite3.connect(database)
    assert preserved.execute("PRAGMA user_version").fetchone()[0] == 0
    assert preserved.execute("SELECT * FROM rolls").fetchone() == (
        1,
        3,
        20,
        "[4, 16, 19]",
    )
    assert {
        row[0]
        for row in preserved.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    } == {"rolls"}
    preserved.close()


def test_connect_rejects_a_schema_newer_than_supported(tmp_path: Path) -> None:
    """Catches newer history data being opened with an older application schema."""
    database = tmp_path / "historial.db"
    newer = sqlite3.connect(database)
    newer.execute("PRAGMA user_version = 2")
    newer.commit()
    newer.close()

    with pytest.raises(OSError) as error:
        connect(database)

    assert str(error.value) == SCHEMA_RESET_REQUIRED
    unchanged = sqlite3.connect(database)
    assert unchanged.execute("PRAGMA user_version").fetchone()[0] == 2
    unchanged.close()


def test_connect_reopens_a_valid_version_one_schema(tmp_path: Path) -> None:
    """Catches valid persisted history being rejected on the next application run."""
    database = tmp_path / "historial.db"
    first = connect(database)
    roll_id = _insert_roll(first)
    _insert_component(first, roll_id)
    first.commit()
    first.close()

    reopened = connect(database)

    assert reopened.execute("SELECT COUNT(*) FROM rolls").fetchone()[0] == 1
    assert reopened.execute("SELECT COUNT(*) FROM roll_components").fetchone()[0] == 1
    reopened.close()


def test_connect_rejects_a_declared_v1_with_an_incomplete_schema(
    tmp_path: Path,
) -> None:
    """Catches user_version alone disguising a missing or incompatible v1 schema."""
    database = tmp_path / "historial.db"
    incomplete = sqlite3.connect(database)
    incomplete.execute(
        """
        CREATE TABLE rolls (
            id INTEGER PRIMARY KEY,
            count INTEGER NOT NULL,
            sides INTEGER NOT NULL,
            values_json TEXT NOT NULL
        )
        """
    )
    incomplete.execute("PRAGMA user_version = 1")
    incomplete.commit()
    incomplete.close()

    with pytest.raises(OSError) as error:
        connect(database)

    assert str(error.value) == SCHEMA_RESET_REQUIRED
    unchanged = sqlite3.connect(database)
    assert unchanged.execute("PRAGMA user_version").fetchone()[0] == 1
    assert unchanged.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall() == [("rolls",)]
    unchanged.close()


def test_connect_rejects_v1_objects_that_only_copy_the_expected_names(
    tmp_path: Path,
) -> None:
    """Catches named but unconstrained tables, indexes, and triggers posing as v1."""
    database = tmp_path / "historial.db"
    impostor = sqlite3.connect(database)
    impostor.executescript(
        """
        CREATE TABLE rolls (
            id, created_at, title, show_sum, total
        );
        CREATE TABLE roll_components (
            id, roll_id, position, count, sides, values_json, subtotal,
            comparator, threshold
        );
        CREATE INDEX idx_rolls_created_at ON rolls (id);
        CREATE INDEX idx_rolls_title ON rolls (id);
        CREATE INDEX idx_roll_components_roll_id ON roll_components (id);
        CREATE INDEX idx_roll_components_sides ON roll_components (id);
        CREATE TRIGGER validate_component_subtotal_insert
            AFTER INSERT ON roll_components BEGIN SELECT 1; END;
        CREATE TRIGGER validate_component_subtotal_update
            AFTER UPDATE ON roll_components BEGIN SELECT 1; END;
        CREATE TRIGGER validate_roll_sum_update
            AFTER UPDATE ON rolls BEGIN SELECT 1; END;
        PRAGMA user_version = 1;
        """
    )
    impostor.close()

    with pytest.raises(OSError) as error:
        connect(database)

    assert str(error.value) == SCHEMA_RESET_REQUIRED


def test_connect_rejects_an_extra_trigger_in_the_dedicated_history_schema(
    tmp_path: Path,
) -> None:
    """Catches an unrecognized trigger silently changing stored history."""
    database = tmp_path / "historial.db"
    original = connect(database)
    original.close()
    altered = sqlite3.connect(database)
    altered.execute(
        """
        CREATE TRIGGER discard_new_roll
        AFTER INSERT ON rolls
        BEGIN
            DELETE FROM rolls WHERE id = NEW.id;
        END
        """
    )
    altered.commit()
    altered.close()

    with pytest.raises(OSError) as error:
        connect(database)

    assert str(error.value) == SCHEMA_RESET_REQUIRED


def test_simultaneous_first_connections_share_one_atomic_schema_creation(
    tmp_path: Path,
) -> None:
    """Catches two first launches racing between schema inspection and creation."""
    database = tmp_path / "historial.db"
    start = Barrier(2)

    def open_database() -> int:
        start.wait()
        connection = connect(database)
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        connection.close()
        return version

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(open_database) for _ in range(2)]

    assert [future.result() for future in futures] == [1, 1]


def test_schema_creation_rolls_back_every_object_and_version_on_ddl_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catches partial schema objects surviving a failed first-run transaction."""
    database = tmp_path / "historial.db"
    monkeypatch.setattr(
        database_module,
        "_SCHEMA_STATEMENTS",
        ("CREATE TABLE partial_schema (id INTEGER PRIMARY KEY)", "INVALID SQL"),
    )

    with pytest.raises(OSError) as error:
        connect(database)

    assert str(error.value) == (
        "No se puede guardar el historial en esta ubicación. Mové la aplicación a "
        "una carpeta con permisos de escritura."
    )
    unchanged = sqlite3.connect(database)
    assert unchanged.execute("PRAGMA user_version").fetchone()[0] == 0
    assert unchanged.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall() == []
    unchanged.close()


@pytest.mark.parametrize(
    ("title", "show_sum", "total"),
    (
        ("x" * 151, 1, 10),
        ("Ataque", 2, 10),
        ("Ataque", 0, 10),
        ("Ataque", 1, None),
    ),
)
def test_roll_constraints_reject_invalid_headers(
    tmp_path: Path, title: str, show_sum: int, total: int | None
) -> None:
    """Catches invalid titles, booleans, or total visibility reaching storage."""
    connection = connect(tmp_path / "historial.db")

    with pytest.raises(sqlite3.IntegrityError):
        _insert_roll(
            connection,
            title=title,
            show_sum=show_sum,
            total=total,
        )

    connection.close()


def test_roll_total_requires_an_integer_when_present(tmp_path: Path) -> None:
    """Catches SQLite storing nonnumeric text in an aggregate total."""
    connection = connect(tmp_path / "historial.db")

    with pytest.raises(sqlite3.IntegrityError):
        _insert_roll(connection, total="bogus")  # type: ignore[arg-type]

    connection.close()


@pytest.mark.parametrize(
    ("comparator", "threshold"),
    ((">=", None), (None, 5), ("!=", 5)),
)
def test_component_constraints_reject_incomplete_or_unknown_filters(
    tmp_path: Path, comparator: str | None, threshold: int | None
) -> None:
    """Catches a component storing a partial or unsupported filter."""
    connection = connect(tmp_path / "historial.db")
    roll_id = _insert_roll(connection)

    with pytest.raises(sqlite3.IntegrityError):
        _insert_component(
            connection,
            roll_id,
            comparator=comparator,
            threshold=threshold,
        )

    connection.close()


@pytest.mark.parametrize(
    ("position", "count", "sides"),
    ((-1, 2, 6), (10, 2, 6), (0, 0, 6), (0, 1_001, 6), (0, 2, 1), (0, 2, 1_001)),
)
def test_component_constraints_reject_values_outside_domain_limits(
    tmp_path: Path, position: int, count: int, sides: int
) -> None:
    """Catches component positions, quantities, or sides outside shared limits."""
    connection = connect(tmp_path / "historial.db")
    roll_id = _insert_roll(connection)

    with pytest.raises(sqlite3.IntegrityError):
        _insert_component(
            connection,
            roll_id,
            position=position,
            count=count,
            sides=sides,
        )

    connection.close()


@pytest.mark.parametrize(
    ("position", "count", "sides"),
    ((0.5, 2, 6), (0, 1.5, 6), (0, 2, 6.5)),
)
def test_component_constraints_require_integer_domain_values(
    tmp_path: Path, position: float | int, count: float | int, sides: float | int
) -> None:
    """Catches SQLite numeric affinity accepting fractional domain values."""
    connection = connect(tmp_path / "historial.db")
    roll_id = _insert_roll(connection)

    with pytest.raises(sqlite3.IntegrityError):
        _insert_component(
            connection,
            roll_id,
            position=position,  # type: ignore[arg-type]
            count=count,  # type: ignore[arg-type]
            sides=sides,  # type: ignore[arg-type]
        )

    connection.close()


@pytest.mark.parametrize(
    ("subtotal", "threshold"), (("bogus", 5), (10, 5.5))
)
def test_component_subtotal_and_threshold_require_integers_when_present(
    tmp_path: Path, subtotal: str | int, threshold: float | int
) -> None:
    """Catches noninteger sums or thresholds being stored in a component."""
    connection = connect(tmp_path / "historial.db")
    roll_id = _insert_roll(connection)

    with pytest.raises(sqlite3.IntegrityError):
        _insert_component(
            connection,
            roll_id,
            subtotal=subtotal,  # type: ignore[arg-type]
            threshold=threshold,  # type: ignore[arg-type]
        )

    connection.close()


@pytest.mark.parametrize("duplicate_field", ("position", "sides"))
def test_components_require_unique_positions_and_sides_per_roll(
    tmp_path: Path, duplicate_field: str
) -> None:
    """Catches ambiguous ordering or repeated die types in one stored roll."""
    connection = connect(tmp_path / "historial.db")
    roll_id = _insert_roll(connection)
    _insert_component(connection, roll_id)

    second = {"position": 1, "sides": 20}
    second[duplicate_field] = 0 if duplicate_field == "position" else 6
    with pytest.raises(sqlite3.IntegrityError):
        _insert_component(connection, roll_id, **second)

    connection.close()


@pytest.mark.parametrize(
    ("show_sum", "total", "subtotal"),
    ((0, None, 10), (1, 10, None)),
)
def test_component_subtotal_must_follow_the_parent_sum_setting(
    tmp_path: Path,
    show_sum: int,
    total: int | None,
    subtotal: int | None,
) -> None:
    """Catches totals and component subtotals disagreeing about sum visibility."""
    connection = connect(tmp_path / "historial.db")
    roll_id = _insert_roll(connection, show_sum=show_sum, total=total)

    with pytest.raises(sqlite3.IntegrityError):
        _insert_component(connection, roll_id, subtotal=subtotal)

    connection.close()


def test_deleting_a_roll_cascades_to_its_components(tmp_path: Path) -> None:
    """Catches deletion leaving orphaned component rows."""
    connection = connect(tmp_path / "historial.db")
    roll_id = _insert_roll(connection)
    _insert_component(connection, roll_id)
    connection.commit()

    connection.execute("DELETE FROM rolls WHERE id = ?", (roll_id,))

    assert connection.execute("SELECT COUNT(*) FROM roll_components").fetchone()[0] == 0
    connection.close()
