from ..domain.models import RollResult


def format_roll(result: RollResult) -> str:
    """Format a roll result as compact, copyable Spanish text."""
    lines: list[str] = []
    if result.request.title:
        lines.append(result.request.title)

    for component in result.components:
        request = component.request
        values = ", ".join(str(value) for value in component.values)
        lines.append(f"{request.notation}: {values}")

        if result.request.show_sum:
            if result.request.is_combined:
                lines.append(f"Subtotal d{request.sides}: {component.subtotal}")
            else:
                lines.append(f"Suma: {result.total}")

        if request.comparator is not None:
            die_label = f" d{request.sides}" if result.request.is_combined else ""
            lines.append(
                f"Filtro{die_label} {request.comparator.value} {request.threshold}: "
                f"{len(component.matches)} de {len(component.values)}"
            )

    if result.request.is_combined and result.request.show_sum:
        lines.append(f"Suma total: {result.total}")

    return "\n".join(lines)
