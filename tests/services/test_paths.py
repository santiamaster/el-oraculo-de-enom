from pathlib import Path
import sys

import pytest

from oraculo_enom.services import paths


def test_application_dir_uses_executable_parent_for_frozen_application(
    monkeypatch,
) -> None:
    """Catches a packaged app writing its history back to the source location."""
    executable = Path("/portable/El Oraculo de ENOM.exe")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))

    assert paths.application_dir() == executable.parent


def test_application_dir_uses_repository_root_when_running_from_source(
    monkeypatch,
) -> None:
    """Catches source runs resolving data relative to the current directory."""
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert paths.application_dir() == Path(__file__).resolve().parents[2]


def test_database_path_creates_data_directory(monkeypatch, tmp_path: Path) -> None:
    """Catches a first run failing because its portable data directory is absent."""
    monkeypatch.setattr(paths, "application_dir", lambda: tmp_path)

    path = paths.database_path()

    assert path == tmp_path / "datos" / "historial.db"
    assert path.parent.is_dir()


def test_database_path_explains_when_data_directory_cannot_be_created(
    monkeypatch, tmp_path: Path
) -> None:
    """Catches a permission failure being exposed as an unhelpful system error."""
    monkeypatch.setattr(paths, "application_dir", lambda: tmp_path)

    def fail_to_create_directory(self, *args, **kwargs) -> None:
        raise PermissionError("read-only")

    monkeypatch.setattr(Path, "mkdir", fail_to_create_directory)

    with pytest.raises(
        OSError,
        match="No se puede guardar el historial en esta ubicación",
    ):
        paths.database_path()
