"""Application composition and executable entry point."""

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from oraculo_enom.persistence.history import HistoryRepository
from oraculo_enom.ui.main_window import MainWindow
from oraculo_enom.ui.theme import STYLESHEET, SpinBoxProxyStyle


def main() -> int:
    """Create and run the desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("El Oráculo de ENOM")
    app.setApplicationDisplayName("El Oráculo de ENOM")
    app.setOrganizationName("ENOM")
    app.setStyle(SpinBoxProxyStyle())
    app.setStyleSheet(STYLESHEET)

    try:
        repository = HistoryRepository()
    except OSError as error:
        QMessageBox.critical(None, "Error de almacenamiento", str(error))
        return 1

    window = MainWindow(repository)
    window.show()
    try:
        return app.exec()
    finally:
        repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
