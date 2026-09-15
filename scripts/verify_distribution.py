#!/usr/bin/env python3
"""Validate the contents of an El Oráculo de ENOM portable distribution."""

import argparse
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from zipfile import BadZipFile, ZipFile, ZipInfo, is_zipfile


_NOTICE_REFERENCE = re.compile(
    r"\(([^)\s]+)\)|`([^`\s]+)`|"
    r"(?<![\w./])((?:\./)?licenses[\\/][A-Za-z0-9_.+@%/\\-]*)"
)
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


def _license_references(notices: str) -> list[str]:
    references: set[str] = set()
    for match in _NOTICE_REFERENCE.finditer(notices):
        groups = match.groups()
        candidate = next(
            value for value in groups if value is not None
        ).replace("\\", "/")
        if groups[2] is not None:
            candidate = candidate.rstrip(".,;")
        if candidate.startswith("./"):
            candidate = candidate[2:]
        if candidate == "licenses/" or candidate.startswith("licenses/"):
            references.add(candidate)
    return sorted(references)


def _is_forbidden(path: PurePosixPath, *, is_directory: bool) -> bool:
    folded_parts = tuple(part.casefold() for part in path.parts)
    if "src" in folded_parts or "tests" in folded_parts:
        return True
    if not is_directory and path.name.casefold() == "historial.db":
        return True
    return not is_directory and path.suffix.casefold() == ".py"


def _validate_entries(
    files: set[str],
    directories: set[str],
    read_text: Callable[[str], str],
) -> list[str]:
    errors: list[str] = []

    for required_file in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        if required_file not in files:
            errors.append(
                f"Falta el archivo obligatorio en la raíz: {required_file}"
            )

    if "licenses" not in directories:
        errors.append("Falta el directorio obligatorio en la raíz: licenses/")
    elif not any(path.startswith("licenses/") for path in files):
        errors.append("El directorio licenses/ no contiene archivos de licencia")

    if "THIRD_PARTY_NOTICES.md" in files:
        try:
            notices = read_text("THIRD_PARTY_NOTICES.md")
        except UnicodeDecodeError:
            errors.append("No se pudo leer THIRD_PARTY_NOTICES.md como UTF-8")
            notices = ""
        except BadZipFile:
            errors.append(
                "No se pudo leer THIRD_PARTY_NOTICES.md por un error de integridad ZIP"
            )
            notices = ""
        for reference in _license_references(notices):
            reference_path = PurePosixPath(reference)
            if ".." in reference_path.parts or "." in reference_path.parts:
                errors.append(
                    f"La referencia de licencia no es segura: {reference}"
                )
                continue
            normalized = reference.rstrip("/")
            if normalized not in files and normalized not in directories:
                errors.append(f"La referencia de licencia no existe: {reference}")
            elif normalized not in files:
                errors.append(
                    f"La referencia de licencia no apunta a un archivo: {reference}"
                )

    entries = [(path, False) for path in files]
    entries.extend((path, True) for path in directories)
    for path, is_directory in sorted(entries):
        pure_path = PurePosixPath(path)
        if _is_forbidden(pure_path, is_directory=is_directory):
            display_path = path + ("/" if is_directory else "")
            errors.append(
                f"Contenido prohibido en la distribución: {display_path}"
            )

    return errors


def _validate_directory(source: Path) -> list[str]:
    files: set[str] = set()
    directories: set[str] = set()
    for path in source.rglob("*"):
        relative = path.relative_to(source).as_posix()
        if path.is_dir():
            directories.add(relative)
        elif path.is_file():
            files.add(relative)

    def read_text(relative: str) -> str:
        return source.joinpath(*PurePosixPath(relative).parts).read_text(
            encoding="utf-8"
        )

    return _validate_entries(files, directories, read_text)


def _unsafe_zip_path(name: str) -> bool:
    normalized = name.replace("\\", "/")
    parts = normalized.rstrip("/").split("/")
    return (
        not name
        or "\x00" in name
        or normalized.startswith("/")
        or _WINDOWS_DRIVE.match(normalized) is not None
        or ":" in normalized
        or any(part in {"", ".", ".."} for part in parts)
    )


def _is_zip_symlink(info: ZipInfo) -> bool:
    return info.create_system == 3 and stat.S_ISLNK(info.external_attr >> 16)


def _validate_zip(source: Path) -> list[str]:
    errors: list[str] = []
    files: set[str] = set()
    directories: set[str] = set()
    file_infos: dict[str, ZipInfo] = {}
    names_by_windows_path: dict[str, list[str]] = {}

    with ZipFile(source) as archive:
        damaged_member = archive.testzip()
        if damaged_member is not None:
            errors.append(f"CRC ZIP inválido: {damaged_member}")

        for info in archive.infolist():
            original_name = info.filename
            if _unsafe_zip_path(original_name):
                errors.append(f"Ruta ZIP no segura: {original_name}")
                continue
            if _is_zip_symlink(info):
                errors.append(
                    "Entrada ZIP no permitida (enlace simbólico): "
                    f"{original_name}"
                )
                continue

            normalized = original_name.replace("\\", "/").rstrip("/")
            collision_key = normalized.casefold()
            names_by_windows_path.setdefault(collision_key, []).append(original_name)

            is_directory = info.is_dir() or original_name.endswith(("/", "\\"))
            if is_directory:
                directories.add(normalized)
            else:
                files.add(normalized)
                file_infos.setdefault(normalized, info)

            parent = PurePosixPath(normalized).parent
            while parent != PurePosixPath("."):
                directories.add(parent.as_posix())
                parent = parent.parent

        for names in names_by_windows_path.values():
            if len(names) > 1:
                errors.append(
                    "Rutas ZIP duplicadas o ambiguas: " + ", ".join(sorted(names))
                )

        files_by_windows_path: dict[str, list[str]] = {}
        directories_by_windows_path: dict[str, list[str]] = {}
        for path in files:
            files_by_windows_path.setdefault(path.casefold(), []).append(path)
        for path in directories:
            directories_by_windows_path.setdefault(path.casefold(), []).append(path)
        for names in directories_by_windows_path.values():
            if len(names) > 1:
                errors.append(
                    "Rutas ZIP duplicadas o ambiguas: "
                    + ", ".join(f"{name}/" for name in sorted(names))
                )
        for collision_key in sorted(
            files_by_windows_path.keys() & directories_by_windows_path.keys()
        ):
            file_names = sorted(files_by_windows_path[collision_key])
            directory_names = [
                f"{name}/"
                for name in sorted(directories_by_windows_path[collision_key])
            ]
            errors.append(
                "Colisión ZIP entre archivo y directorio: "
                + ", ".join(file_names + directory_names)
            )

        def read_text(relative: str) -> str:
            return archive.read(file_infos[relative]).decode("utf-8")

        errors.extend(_validate_entries(files, directories, read_text))

    return errors


def validate_distribution(source: Path) -> list[str]:
    """Return every portable-distribution contract violation found in *source*."""
    if not source.exists():
        return [f"No existe la ruta de distribución: {source}"]
    if source.is_dir():
        return _validate_directory(source)
    if source.is_file() and is_zipfile(source):
        try:
            return _validate_zip(source)
        except BadZipFile as error:
            return [f"ZIP inválido: {error}"]
    return [f"La ruta no es un directorio ni un ZIP válido: {source}"]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verifica el contrato del portable de El Oráculo de ENOM."
    )
    parser.add_argument("distribution", type=Path, help="Directorio o ZIP portable")
    arguments = parser.parse_args(argv)

    errors = validate_distribution(arguments.distribution)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Distribución válida: {arguments.distribution}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
