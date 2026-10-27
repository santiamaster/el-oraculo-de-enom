"""Lossless filter thresholds in the version-one INTEGER-affinity column.

Ordinary thresholds keep their original SQLite INTEGER representation. Larger
ones use canonical ``int:<decimal>`` TEXT: an unmarked decimal would be coerced
to an imprecise REAL by SQLite's INTEGER affinity.
"""

import re

from oraculo_enom.domain.integer_text import format_integer, parse_integer


MIN_SQLITE_INTEGER = -(2**63)
MAX_SQLITE_INTEGER = 2**63 - 1


def encode_threshold(value: int | None) -> int | str | None:
    if value is None or MIN_SQLITE_INTEGER <= value <= MAX_SQLITE_INTEGER:
        return value
    return f"int:{format_integer(value)}"


def decode_threshold(value: object) -> int | None:
    if value is None or type(value) is int:
        return value
    if isinstance(value, str) and re.fullmatch(r"int:-?[1-9][0-9]*", value):
        integer = parse_integer(value[4:])
        if not MIN_SQLITE_INTEGER <= integer <= MAX_SQLITE_INTEGER:
            return integer
    raise ValueError("El umbral almacenado no es un entero canónico")
