"""Repository for persistent simple and combined roll history."""

from collections.abc import Callable
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import sqlite3
from typing import TypeVar

from oraculo_enom.domain.analysis import analyze
from oraculo_enom.domain.dice import validate_request
from oraculo_enom.domain.models import (
    Comparator,
    MAX_TITLE_LENGTH,
    RollComponentRequest,
    RollRecord,
    RollRequest,
    RollResult,
)
from oraculo_enom.services.paths import HISTORY_STORAGE_ERROR, database_path

from .database import connect
from .thresholds import decode_threshold, encode_threshold


T = TypeVar("T")

HISTORY_CORRUPTION_ERROR = (
    "El historial contiene datos inconsistentes. Cerrá la aplicación y conservá "
    "una copia de datos/historial.db antes de pedir ayuda."
)


class _CorruptHistoryError(ValueError):
    """Stored rows cannot be reconstructed as a valid immutable result."""


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


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
                        encode_threshold(component.threshold),
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
        except _CorruptHistoryError as error:
            self._rollback_quietly()
            raise OSError(HISTORY_CORRUPTION_ERROR) from error
        except Exception:
            self._rollback_quietly()
            raise

    def _read(self, operation: Callable[[], T]) -> T:
        try:
            return operation()
        except sqlite3.Error as error:
            raise OSError(HISTORY_STORAGE_ERROR) from error
        except _CorruptHistoryError as error:
            raise OSError(HISTORY_CORRUPTION_ERROR) from error

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
        try:
            return HistoryRepository._hydrate_record(rows)
        except _CorruptHistoryError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise _CorruptHistoryError("invalid stored roll") from error

    @staticmethod
    def _hydrate_record(rows: list[sqlite3.Row]) -> RollRecord:
        header = rows[0]
        record_id = header["roll_id"]
        if type(record_id) is not int:
            raise _CorruptHistoryError("invalid roll identifier")

        created_at_value = header["created_at"]
        if type(created_at_value) is not str:
            raise _CorruptHistoryError("invalid creation date")
        created_at = datetime.fromisoformat(created_at_value)
        if created_at.isoformat() != created_at_value:
            raise _CorruptHistoryError("creation date is not canonical")

        title = header["title"]
        show_sum_value = header["show_sum"]
        total = header["total"]
        if type(title) is not str:
            raise _CorruptHistoryError("invalid title")
        if type(show_sum_value) is not int or show_sum_value not in (0, 1):
            raise _CorruptHistoryError("invalid show_sum flag")
        if total is not None and type(total) is not int:
            raise _CorruptHistoryError("invalid total")

        component_requests: list[RollComponentRequest] = []
        stored_values: list[tuple[int, ...]] = []
        stored_subtotals: list[int | None] = []
        for expected_position, component_row in enumerate(rows):
            if component_row["component_id"] is None:
                raise _CorruptHistoryError("roll has no stored components")
            if component_row["roll_id"] != record_id:
                raise _CorruptHistoryError("mixed roll identifiers")
            if component_row["position"] != expected_position:
                raise _CorruptHistoryError("invalid component positions")

            count = component_row["count"]
            sides = component_row["sides"]
            subtotal = component_row["subtotal"]
            if type(count) is not int or type(sides) is not int:
                raise _CorruptHistoryError("invalid component request")
            if subtotal is not None and type(subtotal) is not int:
                raise _CorruptHistoryError("invalid subtotal")

            comparator = (
                Comparator(component_row["comparator"])
                if component_row["comparator"] is not None
                else None
            )
            component_request = RollComponentRequest(
                count=count,
                sides=sides,
                comparator=comparator,
                threshold=decode_threshold(component_row["threshold"]),
            )

            values_json = component_row["values_json"]
            if type(values_json) is not str:
                raise _CorruptHistoryError("invalid values payload")
            decoded_values = json.loads(
                values_json,
                parse_constant=_reject_json_constant,
            )
            if not isinstance(decoded_values, list) or any(
                type(value) is not int for value in decoded_values
            ):
                raise _CorruptHistoryError("values must be an integer array")

            component_requests.append(component_request)
            stored_values.append(tuple(decoded_values))
            stored_subtotals.append(subtotal)

        request = RollRequest(
            components=tuple(component_requests),
            show_sum=bool(show_sum_value),
            title=title,
        )
        if request.title != title:
            raise _CorruptHistoryError("stored title is not normalized")
        validate_request(request)
        result = analyze(request, tuple(stored_values), created_at=created_at)
        if [component.subtotal for component in result.components] != stored_subtotals:
            raise _CorruptHistoryError("stored subtotals are inconsistent")
        if result.total != total:
            raise _CorruptHistoryError("stored total is inconsistent")
        return RollRecord(id=record_id, result=result)
