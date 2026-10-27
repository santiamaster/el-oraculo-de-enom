import pytest
from PySide6.QtWidgets import QMessageBox

from oraculo_enom import app as app_module


def test_main_shows_repository_startup_error_and_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = "La carpeta actual no permite escribir el historial"
    shown_messages: list[str] = []

    def fail_to_open_repository():
        raise OSError(message)

    def capture_critical_message(parent, title: str, text: str):
        shown_messages.append(text)
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(app_module, "HistoryRepository", fail_to_open_repository)
    monkeypatch.setattr(QMessageBox, "critical", capture_critical_message)

    assert app_module.main() == 1
    assert shown_messages == [message]
