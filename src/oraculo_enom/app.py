"""Application composition and executable entry point."""

import sys

from PySide6.QtWidgets import QApplication

from oraculo_enom.persistence.history import HistoryRepository
from oraculo_enom.ui.main_window import MainWindow
from oraculo_enom.ui.theme import STYLESHEET


def main() -> int:
    """Create and run the desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("El Oráculo de ENOM")
    app.setApplicationDisplayName("El Oráculo de ENOM")
    app.setOrganizationName("ENOM")
    app.setStyleSheet(STYLESHEET)

    repository = HistoryRepository()
    window = MainWindow(repository)
    window.show()
    try:
        return app.exec()
    finally:
        repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
