from ..domain.models import RollResult


def format_roll(result: RollResult) -> str:
    """Format a roll result as compact, copyable Spanish text."""
    lines = [
        f"{result.request.notation}: {', '.join(str(value) for value in result.values)}"
    ]
    if result.request.show_sum:
        lines.append(f"Suma: {result.total}")
    if result.request.comparator is not None:
        lines.append(
            f"Filtro {result.request.comparator.value} {result.request.threshold}: "
            f"{len(result.matches)} de {len(result.values)}"
        )
    return "\n".join(lines)
