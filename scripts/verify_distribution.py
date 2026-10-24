#!/usr/bin/env python3
"""Validate the contents of an El Oráculo de ENOM portable distribution."""

import argparse
from collections.abc import Callable, Sequence
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tomllib
from zipfile import BadZipFile, ZipFile, ZipInfo, is_zipfile


_NOTICE_REFERENCE = re.compile(
    r"\(([^)\s]+)\)|`([^`\s]+)`|"
    r"(?<![\w./])((?:\./)?licenses[\\/][A-Za-z0-9_.+@%/\\-]*)"
)
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _project_versions() -> tuple[str, str]:
    project = tomllib.loads(
        (_PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    pyside6_prefix = "PySide6=="
    pyside6_dependency = next(
        dependency
        for dependency in project["dependencies"]
        if dependency.startswith(pyside6_prefix)
    )
    return project["version"], pyside6_dependency.removeprefix(pyside6_prefix)


_APPLICATION_VERSION, _PYSIDE6_VERSION = _project_versions()


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


def _validate_checksum(portable_zip: Path, checksum: Path) -> list[str]:
    if not checksum.is_file():
        return [f"No existe el archivo SHA-256: {checksum}"]

    try:
        checksum_text = checksum.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ["No se pudo leer el archivo SHA-256 como UTF-8"]
    except OSError as error:
        return [f"No se pudo leer el archivo SHA-256: {error}"]

    match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)\r?\n?", checksum_text)
    if match is None:
        return [
            "Formato SHA-256 inválido: se espera hexadecimal minúsculo, "
            "dos espacios y el nombre del ZIP"
        ]

    expected_digest, referenced_name = match.groups()
    errors: list[str] = []
    if referenced_name != portable_zip.name:
        errors.append(
            f"El archivo SHA-256 referencia {referenced_name}, no "
            f"{portable_zip.name}"
        )
    if portable_zip.is_file():
        try:
            with portable_zip.open("rb") as portable_stream:
                actual_digest = hashlib.file_digest(
                    portable_stream, "sha256"
                ).hexdigest()
        except OSError as error:
            errors.append(
                f"No se pudo calcular el SHA-256 de {portable_zip.name}: {error}"
            )
            return errors
        if actual_digest != expected_digest:
            errors.append(f"El SHA-256 no coincide con {portable_zip.name}")
    return errors


def _validate_sbom(sbom: Path) -> list[str]:
    if not sbom.is_file():
        return [f"No existe el archivo SBOM CycloneDX: {sbom}"]

    try:
        sbom_text = sbom.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ["No se pudo leer el archivo SBOM CycloneDX como UTF-8"]
    except OSError as error:
        return [f"No se pudo leer el archivo SBOM CycloneDX: {error}"]
    try:
        document = json.loads(sbom_text)
    except json.JSONDecodeError:
        return ["El SBOM no contiene JSON válido"]

    if not isinstance(document, dict):
        return ["El SBOM CycloneDX debe ser un objeto JSON"]

    errors: list[str] = []
    if (
        document.get("bomFormat") != "CycloneDX"
        or document.get("specVersion") != "1.6"
    ):
        errors.append(
            "El SBOM debe declarar bomFormat CycloneDX y specVersion 1.6"
        )
    serial_version = document.get("version")
    if type(serial_version) is not int or serial_version < 1:
        errors.append("El SBOM debe declarar una versión serial positiva")

    metadata = document.get("metadata")
    root_component = metadata.get("component") if isinstance(metadata, dict) else None
    expected_root = {
        "type": "application",
        "name": "el-oraculo-de-enom",
        "version": _APPLICATION_VERSION,
    }
    if not isinstance(root_component, dict) or any(
        root_component.get(key) != value for key, value in expected_root.items()
    ):
        errors.append(
            "El SBOM no declara la aplicación raíz "
            f"el-oraculo-de-enom=={_APPLICATION_VERSION}"
        )

    components = document.get("components")
    has_pyside6 = isinstance(components, list) and any(
        isinstance(component, dict)
        and component.get("type") == "library"
        and component.get("name") == "PySide6"
        and component.get("version") == _PYSIDE6_VERSION
        for component in components
    )
    if not has_pyside6:
        errors.append(
            f"El SBOM no declara el componente PySide6=={_PYSIDE6_VERSION}"
        )
    return errors


def validate_release_assets(
    portable_zip: Path, sbom: Path, checksum: Path
) -> list[str]:
    """Return violations across the ZIP, CycloneDX SBOM and SHA-256 assets."""
    errors = validate_distribution(portable_zip)
    if not portable_zip.is_file() or not is_zipfile(portable_zip):
        errors.append(
            f"El activo portable debe ser un archivo ZIP válido: {portable_zip}"
        )
    errors.extend(_validate_sbom(sbom))
    errors.extend(_validate_checksum(portable_zip, checksum))
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verifica el contrato del portable de El Oráculo de ENOM."
    )
    parser.add_argument("distribution", type=Path, help="Directorio o ZIP portable")
    parser.add_argument("--sbom", type=Path, help="SBOM CycloneDX JSON")
    parser.add_argument("--sha256", type=Path, help="Checksum SHA-256 del ZIP")
    arguments = parser.parse_args(argv)

    if (arguments.sbom is None) != (arguments.sha256 is None):
        parser.error("--sbom y --sha256 deben usarse juntos")

    release_mode = arguments.sbom is not None
    if release_mode:
        errors = validate_release_assets(
            arguments.distribution, arguments.sbom, arguments.sha256
        )
    else:
        errors = validate_distribution(arguments.distribution)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if release_mode:
        print(f"Activos de publicación válidos: {arguments.distribution}")
    else:
        print(f"Distribución válida: {arguments.distribution}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
