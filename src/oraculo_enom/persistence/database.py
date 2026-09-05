"""SQLite connection and schema setup."""

from pathlib import Path
import sqlite3

from oraculo_enom.services.paths import HISTORY_STORAGE_ERROR


def connect(database: Path) -> sqlite3.Connection:
    """Open a database connection with the history schema ready for use."""
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS rolls (
                id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL,
                count INTEGER NOT NULL,
                sides INTEGER NOT NULL,
                values_json TEXT NOT NULL,
                total INTEGER NOT NULL,
                show_sum INTEGER NOT NULL,
                comparator TEXT,
                threshold INTEGER,
                match_count INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_rolls_created_at ON rolls (created_at)"
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_rolls_sides ON rolls (sides)")
        connection.commit()
        return connection
    except sqlite3.Error as error:
        if connection is not None:
            try:
                connection.close()
            except sqlite3.Error:
                pass
        raise OSError(HISTORY_STORAGE_ERROR) from error
