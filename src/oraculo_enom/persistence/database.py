"""SQLite connection and versioned schema setup."""

from functools import lru_cache
from pathlib import Path
import sqlite3

from oraculo_enom.services.paths import HISTORY_STORAGE_ERROR, SCHEMA_RESET_REQUIRED


SCHEMA_VERSION = 1

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE rolls (
        id INTEGER PRIMARY KEY,
        created_at TEXT NOT NULL,
        title TEXT NOT NULL DEFAULT '' CHECK (length(title) <= 150),
        show_sum INTEGER NOT NULL CHECK (show_sum IN (0, 1)),
        total INTEGER CHECK (total IS NULL OR typeof(total) = 'integer'),
        CHECK (
            (show_sum = 0 AND total IS NULL)
            OR (show_sum = 1 AND total IS NOT NULL)
        )
    )
    """,
    """
    CREATE TABLE roll_components (
        id INTEGER PRIMARY KEY,
        roll_id INTEGER NOT NULL,
        position INTEGER NOT NULL CHECK (
            typeof(position) = 'integer' AND position BETWEEN 0 AND 9
        ),
        count INTEGER NOT NULL CHECK (
            typeof(count) = 'integer' AND count BETWEEN 1 AND 1000
        ),
        sides INTEGER NOT NULL CHECK (
            typeof(sides) = 'integer' AND sides BETWEEN 2 AND 1000
        ),
        values_json TEXT NOT NULL,
        subtotal INTEGER CHECK (
            subtotal IS NULL OR typeof(subtotal) = 'integer'
        ),
        comparator TEXT CHECK (
            comparator IS NULL OR comparator IN ('>', '>=', '<', '<=', '=')
        ),
        threshold INTEGER CHECK (
            threshold IS NULL OR typeof(threshold) = 'integer'
            OR (
                typeof(threshold) = 'text'
                AND instr(threshold, char(0)) = 0
                AND (
                    (
                        substr(threshold, 1, 4) = 'int:'
                        AND substr(threshold, 5, 1) GLOB '[1-9]'
                        AND substr(threshold, 5) NOT GLOB '*[^0-9]*'
                        AND (
                            length(substr(threshold, 5)) > 19
                            OR (length(substr(threshold, 5)) = 19
                                AND substr(threshold, 5) > '9223372036854775807')
                        )
                    )
                    OR (
                        substr(threshold, 1, 5) = 'int:-'
                        AND substr(threshold, 6, 1) GLOB '[1-9]'
                        AND substr(threshold, 6) NOT GLOB '*[^0-9]*'
                        AND (
                            length(substr(threshold, 6)) > 19
                            OR (length(substr(threshold, 6)) = 19
                                AND substr(threshold, 6) > '9223372036854775808')
                        )
                    )
                )
            )
        ),
        FOREIGN KEY (roll_id) REFERENCES rolls (id) ON DELETE CASCADE,
        UNIQUE (roll_id, position),
        UNIQUE (roll_id, sides),
        CHECK (
            (comparator IS NULL AND threshold IS NULL)
            OR (comparator IS NOT NULL AND threshold IS NOT NULL)
        )
    )
    """,
    "CREATE INDEX idx_rolls_created_at ON rolls (created_at)",
    "CREATE INDEX idx_rolls_title ON rolls (title)",
    "CREATE INDEX idx_roll_components_roll_id ON roll_components (roll_id)",
    "CREATE INDEX idx_roll_components_sides ON roll_components (sides)",
    """
    CREATE TRIGGER validate_component_subtotal_insert
    BEFORE INSERT ON roll_components
    WHEN (
        ((SELECT show_sum FROM rolls WHERE id = NEW.roll_id) = 0
            AND NEW.subtotal IS NOT NULL)
        OR ((SELECT show_sum FROM rolls WHERE id = NEW.roll_id) = 1
            AND NEW.subtotal IS NULL)
    )
    BEGIN
        SELECT RAISE(ABORT, 'component subtotal must match roll show_sum');
    END
    """,
    """
    CREATE TRIGGER validate_component_subtotal_update
    BEFORE UPDATE OF roll_id, subtotal ON roll_components
    WHEN (
        ((SELECT show_sum FROM rolls WHERE id = NEW.roll_id) = 0
            AND NEW.subtotal IS NOT NULL)
        OR ((SELECT show_sum FROM rolls WHERE id = NEW.roll_id) = 1
            AND NEW.subtotal IS NULL)
    )
    BEGIN
        SELECT RAISE(ABORT, 'component subtotal must match roll show_sum');
    END
    """,
    """
    CREATE TRIGGER validate_roll_sum_update
    BEFORE UPDATE OF show_sum, total ON rolls
    WHEN EXISTS (
        SELECT 1
        FROM roll_components
        WHERE roll_id = NEW.id
          AND (
              (NEW.show_sum = 0 AND subtotal IS NOT NULL)
              OR (NEW.show_sum = 1 AND subtotal IS NULL)
          )
    )
    BEGIN
        SELECT RAISE(ABORT, 'roll show_sum must match component subtotals');
    END
    """,
)


def connect(database: Path) -> sqlite3.Connection:
    """Open a database connection with the history schema ready for use."""
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")

        version = connection.execute("PRAGMA user_version").fetchone()[0]
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                """
            )
        }
        if version == 0:
            if tables:
                _reject_incompatible_schema(connection)
            _create_schema(connection)
        elif version != SCHEMA_VERSION or not _schema_is_current(connection):
            _reject_incompatible_schema(connection)

        connection.commit()
        return connection
    except sqlite3.Error as error:
        _rollback_quietly(connection)
        _close_quietly(connection)
        raise OSError(HISTORY_STORAGE_ERROR) from error


def _create_schema(connection: sqlite3.Connection) -> None:
    """Create schema version 1 as one atomic SQLite transaction."""
    for statement in _SCHEMA_STATEMENTS:
        connection.execute(statement)
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _schema_is_current(connection: sqlite3.Connection) -> bool:
    """Return whether required objects exactly match canonical version-one DDL."""
    actual_definitions = {
        (row[0], row[1]): _normalize_sql(row[2])
        for row in connection.execute(
            """
            SELECT type, name, sql
            FROM sqlite_master
            WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
            """
        )
    }
    return actual_definitions == _expected_schema_definitions()


@lru_cache(maxsize=1)
def _expected_schema_definitions() -> dict[tuple[str, str], str]:
    """Build SQLite's canonical representation of the supported schema."""
    reference = sqlite3.connect(":memory:")
    try:
        for statement in _SCHEMA_STATEMENTS:
            reference.execute(statement)
        return {
            (row[0], row[1]): _normalize_sql(row[2])
            for row in reference.execute(
                """
                SELECT type, name, sql
                FROM sqlite_master
                WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
                """
            )
        }
    finally:
        reference.close()


def _normalize_sql(statement: str) -> str:
    return " ".join(statement.split())


def _reject_incompatible_schema(connection: sqlite3.Connection) -> None:
    """Close an unsupported database without mutating it."""
    _close_quietly(connection)
    raise OSError(SCHEMA_RESET_REQUIRED)


def _close_quietly(connection: sqlite3.Connection | None) -> None:
    if connection is None:
        return
    try:
        connection.close()
    except sqlite3.Error:
        pass


def _rollback_quietly(connection: sqlite3.Connection | None) -> None:
    if connection is None:
        return
    try:
        connection.rollback()
    except sqlite3.Error:
        pass
