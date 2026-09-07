"""Repository for persistent simple and combined roll history."""

from collections.abc import Callable
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import sqlite3
from typing import TypeVar

from oraculo_enom.domain.analysis import OPERATIONS
from oraculo_enom.domain.models import (
    Comparator,
    MAX_TITLE_LENGTH,
    RollComponentRequest,
    RollComponentResult,
    RollRecord,
    RollRequest,
    RollResult,
)
from oraculo_enom.services.paths import HISTORY_STORAGE_ERROR, database_path

from .database import connect


T = TypeVar("T")

_JOINED_COLUMNS = """
    rolls.id AS roll_id,
    rolls.created_at,
    rolls.title,
    rolls.show_sum,
    rolls.total,
    roll_components.id AS component_id,
    roll_components.position,
    roll_components.count,
    roll_components.sides,
    roll_components.values_json,
    roll_components.subtotal,
    roll_components.comparator
    AS comparator,
    roll_components.threshold
"""


class HistoryRepository:
    """Store and retrieve immutable roll records in SQLite."""

    def __init__(self, database: Path | None = None) -> None:
        history_database = database if database is not None else database_path()
        self._connection = connect(history_database)

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._connection.close()

    def add(self, result: RollResult) -> RollRecord:
        """Persist a complete roll in one transaction and return its record."""

        def insert_roll() -> RollRecord:
            request = result.request
            cursor = self._connection.execute(
                """
                INSERT INTO rolls (created_at, title, show_sum, total)
                VALUES (?, ?, ?, ?)
                """,
                (
                    result.created_at.isoformat(),
                    request.title,
                    int(request.show_sum),
                    result.total,
                ),
            )
            if cursor.lastrowid is None:
                raise sqlite3.DatabaseError("SQLite did not return a roll identifier")
            record_id = int(cursor.lastrowid)

            for position, component_result in enumerate(result.components):
                component = component_result.request
                self._connection.execute(
                    """
                    INSERT INTO roll_components (
                        roll_id, position, count, sides, values_json, subtotal,
                        comparator, threshold
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record_id,
                        position,
                        component.count,
                        component.sides,
                        json.dumps(component_result.values),
                        component_result.subtotal,
                        component.comparator.value
                        if component.comparator is not None
                        else None,
                        component.threshold,
                    ),
                )

            return RollRecord(id=record_id, result=result)

        return self._write_transaction(insert_roll)

    def recent(self, limit: int = 5) -> list[RollRecord]:
        """Return the most recent saved rolls."""

        def load_recent() -> list[RollRecord]:
            rows = self._connection.execute(
                f"""
                WITH recent_rolls AS (
                    SELECT * FROM rolls
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                )
                SELECT
                    recent_rolls.id AS roll_id,
                    recent_rolls.created_at,
                    recent_rolls.title,
                    recent_rolls.show_sum,
                    recent_rolls.total,
                    roll_components.id AS component_id,
                    roll_components.position,
                    roll_components.count,
                    roll_components.sides,
                    roll_components.values_json,
                    roll_components.subtotal,
                    roll_components.comparator,
                    roll_components.threshold
                FROM recent_rolls
                LEFT JOIN roll_components
                    ON roll_components.roll_id = recent_rolls.id
                ORDER BY
                    recent_rolls.created_at DESC,
                    recent_rolls.id DESC,
                    roll_components.position
                """,
                (limit,),
            ).fetchall()
            return self._records_from_rows(rows)

        return self._read(load_recent)

    def search(
        self,
        sides: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        title: str | None = None,
    ) -> list[RollRecord]:
        """Return rolls matching optional title, die, and inclusive dates."""

        def load_matches() -> list[RollRecord]:
            clauses: list[str] = []
            parameters: list[object] = []
            if sides is not None:
                clauses.append(
                    """
                    EXISTS (
                        SELECT 1 FROM roll_components
                        AS matching_components
                        WHERE matching_components.roll_id = rolls.id
                          AND matching_components.sides = ?
                    )
                    """
                )
                parameters.append(sides)
            if date_from is not None:
                clauses.append("created_at >= ?")
                parameters.append(date_from.isoformat())
            if date_to is not None:
                clauses.append("created_at < ?")
                parameters.append((date_to + timedelta(days=1)).isoformat())

            statement = f"""
                SELECT {_JOINED_COLUMNS}
                FROM rolls
                LEFT JOIN roll_components
                    ON roll_components.roll_id = rolls.id
            """
            if clauses:
                statement += " WHERE " + " AND ".join(clauses)
            statement += (
                " ORDER BY rolls.created_at DESC, rolls.id DESC, "
                "roll_components.position"
            )
            rows = self._connection.execute(statement, parameters).fetchall()
            if title is not None:
                normalized_title = title.casefold()
                rows = [
                    row
                    for row in rows
                    if normalized_title in str(row["title"]).casefold()
                ]
            return self._records_from_rows(rows)

        return self._read(load_matches)

    def update_title(self, record_id: int, title: str) -> RollRecord:
        """Replace only one record's normalized optional title."""
        normalized_title = title.strip()
        if len(normalized_title) > MAX_TITLE_LENGTH:
            raise ValueError(f"El título admite hasta {MAX_TITLE_LENGTH} caracteres")

        def update() -> RollRecord:
            cursor = self._connection.execute(
                "UPDATE rolls SET title = ? WHERE id = ?",
                (normalized_title, record_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"No existe una tirada con id {record_id}")
            record = self._record_by_id(record_id)
            if record is None:
                raise LookupError(f"No existe una tirada con id {record_id}")
            return record

        return self._write_transaction(update)

    def delete(self, record_id: int) -> None:
        """Delete one saved roll and its components atomically."""

        def delete_roll() -> None:
            self._connection.execute("DELETE FROM rolls WHERE id = ?", (record_id,))

        self._write_transaction(delete_roll)

    def clear(self) -> None:
        """Delete every saved roll and component atomically."""

        def clear_rolls() -> None:
            self._connection.execute("DELETE FROM rolls")

        self._write_transaction(clear_rolls)

    def _write_transaction(self, operation: Callable[[], T]) -> T:
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            result = operation()
            self._connection.commit()
            return result
        except sqlite3.Error as error:
            self._rollback_quietly()
            raise OSError(HISTORY_STORAGE_ERROR) from error
        except Exception:
            self._rollback_quietly()
            raise

    def _read(self, operation: Callable[[], T]) -> T:
        try:
            return operation()
        except sqlite3.Error as error:
            raise OSError(HISTORY_STORAGE_ERROR) from error

    def _rollback_quietly(self) -> None:
        try:
            self._connection.rollback()
        except sqlite3.Error:
            pass

    def _records_from_rows(self, rows: list[sqlite3.Row]) -> list[RollRecord]:
        grouped_rows: dict[int, list[sqlite3.Row]] = {}
        for row in rows:
            grouped_rows.setdefault(row["roll_id"], []).append(row)
        return [
            self._record_from_rows(record_rows)
            for record_rows in grouped_rows.values()
        ]

    def _record_by_id(self, record_id: int) -> RollRecord | None:
        rows = self._connection.execute(
            f"""
            SELECT {_JOINED_COLUMNS}
            FROM rolls
            LEFT JOIN roll_components
                ON roll_components.roll_id = rolls.id
            WHERE rolls.id = ?
            ORDER BY roll_components.position
            """,
            (record_id,),
        ).fetchall()
        return self._record_from_rows(rows) if rows else None

    @staticmethod
    def _record_from_rows(rows: list[sqlite3.Row]) -> RollRecord:
        header = rows[0]
        component_requests: list[RollComponentRequest] = []
        component_results: list[RollComponentResult] = []
        for component_row in rows:
            if component_row["component_id"] is None:
                raise sqlite3.DatabaseError(
                    f"Roll {header['roll_id']} has no stored components"
                )
            comparator = (
                Comparator(component_row["comparator"])
                if component_row["comparator"] is not None
                else None
            )
            component_request = RollComponentRequest(
                count=component_row["count"],
                sides=component_row["sides"],
                comparator=comparator,
                threshold=component_row["threshold"],
            )
            values = tuple(json.loads(component_row["values_json"]))
            matches: tuple[int, ...] = ()
            if comparator is not None and component_request.threshold is not None:
                operation = OPERATIONS[comparator]
                matches = tuple(
                    value
                    for value in values
                    if operation(value, component_request.threshold)
                )
            component_requests.append(component_request)
            component_results.append(
                RollComponentResult(
                    request=component_request,
                    values=values,
                    subtotal=component_row["subtotal"],
                    matches=matches,
                )
            )

        request = RollRequest(
            components=tuple(component_requests),
            show_sum=bool(header["show_sum"]),
            title=header["title"],
        )
        result = RollResult(
            request=request,
            components=tuple(component_results),
            total=header["total"],
            created_at=datetime.fromisoformat(header["created_at"]),
        )
        return RollRecord(id=header["roll_id"], result=result)
