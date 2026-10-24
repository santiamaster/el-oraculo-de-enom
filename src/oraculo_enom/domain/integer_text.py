"""Exact decimal conversion without Python's configurable digit ceiling."""

_CHUNK_DIGITS = 9
_CHUNK_BASE = 10**_CHUNK_DIGITS


def format_integer(value: int) -> str:
    """Return the canonical decimal form of an arbitrarily large integer."""
    sign = "-" if value < 0 else ""
    remaining = abs(value)
    if remaining == 0:
        return "0"

    chunks: list[int] = []
    while remaining:
        remaining, chunk = divmod(remaining, _CHUNK_BASE)
        chunks.append(chunk)
    return sign + str(chunks[-1]) + "".join(
        f"{chunk:0{_CHUNK_DIGITS}d}" for chunk in reversed(chunks[:-1])
    )


def parse_integer(text: str) -> int:
    """Parse an ASCII decimal integer without a digit-count side effect."""
    sign = -1 if text.startswith("-") else 1
    digits = text[1:] if text[:1] in {"+", "-"} else text
    if not digits or not digits.isascii() or not digits.isdigit():
        raise ValueError("invalid decimal integer")

    first_chunk_size = len(digits) % _CHUNK_DIGITS or _CHUNK_DIGITS
    value = int(digits[:first_chunk_size])
    for index in range(first_chunk_size, len(digits), _CHUNK_DIGITS):
        chunk = digits[index : index + _CHUNK_DIGITS]
        value = value * _CHUNK_BASE + int(chunk)
    return sign * value
