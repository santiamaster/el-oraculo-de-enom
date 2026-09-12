"""Consistent, non-destructive guidance for failed history reads."""

from PySide6.QtWidgets import QMessageBox, QWidget


def show_history_read_error(parent: QWidget, error: OSError) -> None:
    QMessageBox.critical(
        parent,
        "No se pudo leer el historial",
        f"{error}\n\nSe conserva la vista anterior. Revisá el acceso a "
        "datos/historial.db. Volvé a intentar abriendo el historial o "
        "actualizando sus filtros; si el problema continúa, cerrá la "
        "aplicación y conservá una copia de la base antes de pedir ayuda.",
    )
