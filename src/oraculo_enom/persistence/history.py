"""Repository for persistent roll history."""

from datetime import date, datetime, timedelta
import json
from pathlib import Path
import sqlite3

from oraculo_enom.domain.analysis import OPERATIONS
from oraculo_enom.domain.models import Comparator, RollRecord, RollRequest, RollResult
from oraculo_enom.services.paths import HISTORY_STORAGE_ERROR, database_path

from .database import connect


class HistoryRepository:
    """Store and retrieve immutable roll records in SQLite."""

    def __init__(self, database: Path | None = None) -> None:
        self._connection = connect(database if database is not None else database_path())

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._connection.close()

    def add(self, result: RollResult) -> RollRecord:
        """Persist a roll result and return it with its database identifier."""
        request = result.request
        cursor = self._write(
            """
            INSERT INTO rolls (
                created_at, count, sides, values_json, total, show_sum,
                comparator, threshold, match_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.created_at.isoformat(),
                request.count,
                request.sides,
                json.dumps(result.values),
                result.total,
                int(request.show_sum),
                request.comparator.value if request.comparator is not None else None,
                request.threshold,
                len(result.matches),
            ),
        )
        return RollRecord(id=cursor.lastrowid, result=result)

    def recent(self, limit: int = 5) -> list[RollRecord]:
        """Return the most recent saved rolls."""
        rows = self._connection.execute(
            "SELECT * FROM rolls ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._record_from_row(row) for row in rows]

    def search(
        self,
        sides: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[RollRecord]:
        """Return rolls matching the optional die and inclusive date filters."""
        clauses: list[str] = []
        parameters: list[object] = []
        if sides is not None:
            clauses.append("sides = ?")
            parameters.append(sides)
        if date_from is not None:
            clauses.append("created_at >= ?")
            parameters.append(date_from.isoformat())
        if date_to is not None:
            clauses.append("created_at < ?")
            parameters.append((date_to + timedelta(days=1)).isoformat())

        statement = "SELECT * FROM rolls"
        if clauses:
            statement += " WHERE " + " AND ".join(clauses)
        statement += " ORDER BY created_at DESC, id DESC"
        rows = self._connection.execute(statement, parameters).fetchall()
        return [self._record_from_row(row) for row in rows]

    def delete(self, record_id: int) -> None:
        """Delete one saved roll by its identifier."""
        self._write("DELETE FROM rolls WHERE id = ?", (record_id,))

    def clear(self) -> None:
        """Delete all saved rolls."""
        self._write("DELETE FROM rolls")

    def _write(
        self, statement: str, parameters: tuple[object, ...] = ()
    ) -> sqlite3.Cursor:
        try:
            cursor = self._connection.execute(statement, parameters)
            self._connection.commit()
        except sqlite3.Error as error:
            raise OSError(HISTORY_STORAGE_ERROR) from error
        return cursor

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> RollRecord:
        comparator = (
            Comparator(row["comparator"]) if row["comparator"] is not None else None
        )
        threshold = row["threshold"]
        values = tuple(json.loads(row["values_json"]))
        request = RollRequest(
            count=row["count"],
            sides=row["sides"],
            show_sum=bool(row["show_sum"]),
            comparator=comparator,
            threshold=threshold,
        )
        matches = ()
        if comparator is not None and threshold is not None:
            operation = OPERATIONS[comparator]
            matches = tuple(value for value in values if operation(value, threshold))
        result = RollResult(
            request=request,
            values=values,
            total=row["total"],
            matches=matches,
            created_at=datetime.fromisoformat(row["created_at"]),
        )
        return RollRecord(id=row["id"], result=result)
