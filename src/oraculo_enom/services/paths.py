"""Portable filesystem locations used by the application."""

from pathlib import Path
import sys


HISTORY_STORAGE_ERROR = (
    "No se puede guardar el historial en esta ubicación. Mové la aplicación a una "
    "carpeta con permisos de escritura."
)


def application_dir() -> Path:
    """Return the directory containing the packaged app or source repository."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[3]


def database_path() -> Path:
    """Return the portable database location, creating its data directory."""
    data_directory = application_dir() / "datos"
    try:
        data_directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise OSError(HISTORY_STORAGE_ERROR) from error
    return data_directory / "historial.db"
