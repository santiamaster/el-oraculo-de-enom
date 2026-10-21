from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import subprocess
import sys
import tomllib
from types import ModuleType
from zipfile import ZipFile, ZipInfo

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERIFIER_PATH = PROJECT_ROOT / "scripts" / "verify_distribution.py"


def test_release_build_uses_audited_dependency_versions() -> None:
    """Prevents CI from silently replacing the audited portable runtime."""
    project = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]
    workflow = (PROJECT_ROOT / ".github/workflows/build-windows.yml").read_text(
        encoding="utf-8"
    )

    assert project["dependencies"] == ["PySide6==6.11.2"]
    assert "pyinstaller==6.22.2" in project["optional-dependencies"]["dev"]
    assert (
        "pyinstaller-hooks-contrib==2026.7"
        in project["optional-dependencies"]["dev"]
    )
    assert 'python-version: "3.12.10"' in workflow


def _load_verifier() -> ModuleType:
    assert VERIFIER_PATH.is_file(), "falta el verificador de la distribución"
    spec = spec_from_file_location("verify_distribution", VERIFIER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_valid_distribution(root: Path) -> None:
    (root / "licenses").mkdir(parents=True)
    (root / "LICENSE").write_text("GPL-2.0-or-later\n", encoding="utf-8")
    (root / "THIRD_PARTY_NOTICES.md").write_text(
        "[Componente de prueba](licenses/component.txt)\n",
        encoding="utf-8",
    )
    (root / "licenses" / "component.txt").write_text(
        "Texto de licencia de prueba\n",
        encoding="utf-8",
    )
    (root / "El Oraculo de ENOM.exe").write_bytes(b"portable")


def _zip_directory(source: Path, destination: Path) -> None:
    with ZipFile(destination, "w") as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source).as_posix())


def test_valid_directory_has_no_contract_violations(tmp_path: Path) -> None:
    """Catches a complete portable directory being rejected."""
    _write_valid_distribution(tmp_path)
    verifier = _load_verifier()

    assert verifier.validate_distribution(tmp_path) == []


@pytest.mark.parametrize(
    ("relative_path", "expected_error"),
    [
        ("LICENSE", "Falta el archivo obligatorio en la raíz: LICENSE"),
        (
            "THIRD_PARTY_NOTICES.md",
            "Falta el archivo obligatorio en la raíz: THIRD_PARTY_NOTICES.md",
        ),
    ],
)
def test_missing_required_root_file_is_reported(
    tmp_path: Path, relative_path: str, expected_error: str
) -> None:
    """Catches a mandatory legal file being omitted from the portable root."""
    _write_valid_distribution(tmp_path)
    (tmp_path / relative_path).unlink()
    verifier = _load_verifier()

    assert expected_error in verifier.validate_distribution(tmp_path)


def test_missing_licenses_directory_is_reported(tmp_path: Path) -> None:
    """Catches all third-party license texts being omitted."""
    _write_valid_distribution(tmp_path)
    (tmp_path / "licenses" / "component.txt").unlink()
    (tmp_path / "licenses").rmdir()
    verifier = _load_verifier()

    assert (
        "Falta el directorio obligatorio en la raíz: licenses/"
        in verifier.validate_distribution(tmp_path)
    )


def test_empty_licenses_directory_is_reported(tmp_path: Path) -> None:
    """Catches a placeholder licenses directory with no distributable texts."""
    _write_valid_distribution(tmp_path)
    (tmp_path / "licenses" / "component.txt").unlink()
    verifier = _load_verifier()

    assert (
        "El directorio licenses/ no contiene archivos de licencia"
        in verifier.validate_distribution(tmp_path)
    )


@pytest.mark.parametrize(
    "reference",
    [
        "[Componente](licenses/missing.txt)",
        "Texto local: `./licenses/missing.txt`",
        "License: licenses/missing.txt",
        "License: ./licenses/missing.txt",
    ],
)
def test_notice_reference_to_missing_license_is_reported(
    tmp_path: Path, reference: str
) -> None:
    """Catches a notice pointing at a license text absent from the package."""
    _write_valid_distribution(tmp_path)
    (tmp_path / "THIRD_PARTY_NOTICES.md").write_text(reference, encoding="utf-8")
    verifier = _load_verifier()

    assert (
        "La referencia de licencia no existe: licenses/missing.txt"
        in verifier.validate_distribution(tmp_path)
    )


def test_unsafe_notice_reference_is_reported(tmp_path: Path) -> None:
    """Catches a notice escaping licenses/ through parent traversal."""
    _write_valid_distribution(tmp_path)
    (tmp_path / "THIRD_PARTY_NOTICES.md").write_text(
        "[Texto](licenses/../LICENSE)", encoding="utf-8"
    )
    verifier = _load_verifier()

    assert (
        "La referencia de licencia no es segura: licenses/../LICENSE"
        in verifier.validate_distribution(tmp_path)
    )


def test_notice_reference_must_point_to_a_file(tmp_path: Path) -> None:
    """Catches the licenses directory itself being used as a license text."""
    _write_valid_distribution(tmp_path)
    (tmp_path / "THIRD_PARTY_NOTICES.md").write_text(
        "Texto local: `licenses/`", encoding="utf-8"
    )
    verifier = _load_verifier()

    assert (
        "La referencia de licencia no apunta a un archivo: licenses/"
        in verifier.validate_distribution(tmp_path)
    )


def test_direct_notice_reference_ignores_sentence_punctuation(
    tmp_path: Path,
) -> None:
    """Catches a final period being mistaken for part of a license filename."""
    _write_valid_distribution(tmp_path)
    (tmp_path / "THIRD_PARTY_NOTICES.md").write_text(
        "License: licenses/component.txt.", encoding="utf-8"
    )
    verifier = _load_verifier()

    assert verifier.validate_distribution(tmp_path) == []


@pytest.mark.parametrize(
    ("relative_path", "is_directory", "reported_path"),
    [
        ("historial.db", False, "historial.db"),
        ("datos/HISTORIAL.DB", False, "datos/HISTORIAL.DB"),
        ("helper.py", False, "helper.py"),
        ("_internal/module.PY", False, "_internal/module.PY"),
        ("src", True, "src/"),
        ("payload/SRC", True, "payload/SRC/"),
        ("tests", True, "tests/"),
        ("payload/Tests", True, "payload/Tests/"),
    ],
)
def test_forbidden_content_is_reported_even_when_directory_is_empty(
    tmp_path: Path,
    relative_path: str,
    is_directory: bool,
    reported_path: str,
) -> None:
    """Catches development data, source, or test content shipping to users."""
    _write_valid_distribution(tmp_path)
    forbidden_path = tmp_path / relative_path
    if is_directory:
        forbidden_path.mkdir(parents=True)
    else:
        forbidden_path.parent.mkdir(parents=True, exist_ok=True)
        forbidden_path.write_text("forbidden", encoding="utf-8")
    verifier = _load_verifier()

    assert (
        f"Contenido prohibido en la distribución: {reported_path}"
        in verifier.validate_distribution(tmp_path)
    )


def test_similar_names_are_not_treated_as_forbidden(tmp_path: Path) -> None:
    """Catches the verifier rejecting harmless names by substring alone."""
    _write_valid_distribution(tmp_path)
    (tmp_path / "contest").mkdir()
    (tmp_path / "src-data").mkdir()
    (tmp_path / "_internal" / "module.pyc").parent.mkdir()
    (tmp_path / "_internal" / "module.pyc").write_bytes(b"compiled")
    verifier = _load_verifier()

    assert verifier.validate_distribution(tmp_path) == []


def test_valid_zip_without_explicit_directory_entries_is_accepted(
    tmp_path: Path,
) -> None:
    """Catches ordinary ZIP creation omitting directory entries being rejected."""
    distribution = tmp_path / "distribution"
    _write_valid_distribution(distribution)
    archive = tmp_path / "portable.zip"
    _zip_directory(distribution, archive)
    verifier = _load_verifier()

    assert verifier.validate_distribution(archive) == []


def test_zip_missing_required_file_is_reported(tmp_path: Path) -> None:
    """Catches ZIP validation bypassing the mandatory root files."""
    archive = tmp_path / "portable.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("THIRD_PARTY_NOTICES.md", "")
        output.writestr("licenses/component.txt", "license")
    verifier = _load_verifier()

    assert (
        "Falta el archivo obligatorio en la raíz: LICENSE"
        in verifier.validate_distribution(archive)
    )


def test_zip_notice_reference_to_missing_license_is_reported(tmp_path: Path) -> None:
    """Catches absent license references being ignored only for ZIP input."""
    archive = tmp_path / "portable.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("LICENSE", "GPL")
        output.writestr(
            "THIRD_PARTY_NOTICES.md", "[Missing](./licenses/missing.txt)"
        )
        output.writestr("licenses/component.txt", "license")
    verifier = _load_verifier()

    assert (
        "La referencia de licencia no existe: licenses/missing.txt"
        in verifier.validate_distribution(archive)
    )


def test_forbidden_empty_directory_in_zip_is_reported(tmp_path: Path) -> None:
    """Catches an empty development directory hidden in a ZIP."""
    distribution = tmp_path / "distribution"
    _write_valid_distribution(distribution)
    archive = tmp_path / "portable.zip"
    _zip_directory(distribution, archive)
    with ZipFile(archive, "a") as output:
        output.writestr("src/", b"")
    verifier = _load_verifier()

    assert (
        "Contenido prohibido en la distribución: src/"
        in verifier.validate_distribution(archive)
    )


def test_empty_licenses_directory_in_zip_is_reported(tmp_path: Path) -> None:
    """Catches an explicit but empty ZIP licenses directory passing compliance."""
    archive = tmp_path / "portable.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("LICENSE", "GPL")
        output.writestr("THIRD_PARTY_NOTICES.md", "")
        output.writestr("licenses/", b"")
    verifier = _load_verifier()

    assert verifier.validate_distribution(archive) == [
        "El directorio licenses/ no contiene archivos de licencia"
    ]


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../escape.txt",
        "folder/../../escape.txt",
        "/absolute.txt",
        "C:/absolute.txt",
        "C:\\absolute.txt",
        "//server/share.txt",
        "\\\\server\\share.txt",
        "safe.txt:alternate-stream",
    ],
)
def test_unsafe_zip_member_is_reported(
    tmp_path: Path, unsafe_path: str
) -> None:
    """Catches extraction-dangerous or Windows-absolute ZIP member names."""
    distribution = tmp_path / "distribution"
    _write_valid_distribution(distribution)
    archive = tmp_path / "portable.zip"
    _zip_directory(distribution, archive)
    with ZipFile(archive, "a") as output:
        output.writestr(unsafe_path, b"unsafe")
    with ZipFile(archive) as stored_archive:
        stored_unsafe_path = stored_archive.infolist()[-1].filename
    verifier = _load_verifier()

    assert (
        f"Ruta ZIP no segura: {stored_unsafe_path}"
        in verifier.validate_distribution(archive)
    )


def test_case_insensitive_duplicate_zip_members_are_reported(tmp_path: Path) -> None:
    """Catches two ZIP members resolving to the same Windows path."""
    distribution = tmp_path / "distribution"
    _write_valid_distribution(distribution)
    archive = tmp_path / "portable.zip"
    _zip_directory(distribution, archive)
    with ZipFile(archive, "a") as output:
        output.writestr("licenses/COMPONENT.txt", "duplicate")
    verifier = _load_verifier()

    assert (
        "Rutas ZIP duplicadas o ambiguas: licenses/COMPONENT.txt, "
        "licenses/component.txt"
        in verifier.validate_distribution(archive)
    )


@pytest.mark.parametrize("file_name", ["Licenses", "licenses"])
def test_zip_file_cannot_collide_with_implicit_directory(
    tmp_path: Path, file_name: str
) -> None:
    """Catches a file blocking the directory hierarchy when extracted on Windows."""
    archive = tmp_path / "portable.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("LICENSE", "GPL")
        output.writestr(
            "THIRD_PARTY_NOTICES.md", "[Component](licenses/component.txt)"
        )
        output.writestr("licenses/component.txt", "license")
        output.writestr(file_name, "blocking file")
    verifier = _load_verifier()

    assert (
        f"Colisión ZIP entre archivo y directorio: {file_name}, licenses/"
        in verifier.validate_distribution(archive)
    )


def test_case_insensitive_implicit_zip_directories_are_reported(
    tmp_path: Path,
) -> None:
    """Catches parent directories that cannot coexist after Windows extraction."""
    distribution = tmp_path / "distribution"
    _write_valid_distribution(distribution)
    archive = tmp_path / "portable.zip"
    _zip_directory(distribution, archive)
    with ZipFile(archive, "a") as output:
        output.writestr("Payload/a.txt", "a")
        output.writestr("payload/b.txt", "b")
    verifier = _load_verifier()

    assert (
        "Rutas ZIP duplicadas o ambiguas: Payload/, payload/"
        in verifier.validate_distribution(archive)
    )


def test_zip_symbolic_link_is_reported(tmp_path: Path) -> None:
    """Catches a symbolic link entering the portable through ZIP metadata."""
    distribution = tmp_path / "distribution"
    _write_valid_distribution(distribution)
    archive = tmp_path / "portable.zip"
    _zip_directory(distribution, archive)
    link = ZipInfo("licenses/link.txt")
    link.create_system = 3
    link.external_attr = 0o120777 << 16
    with ZipFile(archive, "a") as output:
        output.writestr(link, "component.txt")
    verifier = _load_verifier()

    assert (
        "Entrada ZIP no permitida (enlace simbólico): licenses/link.txt"
        in verifier.validate_distribution(archive)
    )


def test_missing_input_path_is_reported(tmp_path: Path) -> None:
    """Catches a typo in the requested distribution path being treated as valid."""
    missing = tmp_path / "missing"
    verifier = _load_verifier()

    assert verifier.validate_distribution(missing) == [
        f"No existe la ruta de distribución: {missing}"
    ]


def test_regular_non_zip_file_is_reported(tmp_path: Path) -> None:
    """Catches an unsupported file being treated as an empty valid package."""
    unsupported = tmp_path / "portable.bin"
    unsupported.write_bytes(b"not a zip")
    verifier = _load_verifier()

    assert verifier.validate_distribution(unsupported) == [
        f"La ruta no es un directorio ni un ZIP válido: {unsupported}"
    ]


def test_cli_returns_zero_for_valid_distribution(tmp_path: Path) -> None:
    """Catches the command-line verifier failing a valid CI package."""
    _write_valid_distribution(tmp_path)

    result = subprocess.run(
        [sys.executable, str(VERIFIER_PATH), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == f"Distribución válida: {tmp_path}\n"
    assert result.stderr == ""


def test_cli_returns_nonzero_and_reports_every_violation(tmp_path: Path) -> None:
    """Catches CI receiving only the first error or a successful exit status."""
    result = subprocess.run(
        [sys.executable, str(VERIFIER_PATH), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.splitlines() == [
        "ERROR: Falta el archivo obligatorio en la raíz: LICENSE",
        "ERROR: Falta el archivo obligatorio en la raíz: THIRD_PARTY_NOTICES.md",
        "ERROR: Falta el directorio obligatorio en la raíz: licenses/",
    ]


@pytest.mark.parametrize("as_zip", [False, True])
def test_non_utf8_notices_are_reported_without_crashing(
    tmp_path: Path, as_zip: bool
) -> None:
    """Catches malformed notice bytes terminating the verifier with a traceback."""
    distribution = tmp_path / "distribution"
    _write_valid_distribution(distribution)
    (distribution / "THIRD_PARTY_NOTICES.md").write_bytes(b"\xff\xfe")
    source = distribution
    if as_zip:
        source = tmp_path / "portable.zip"
        _zip_directory(distribution, source)
    verifier = _load_verifier()

    assert verifier.validate_distribution(source) == [
        "No se pudo leer THIRD_PARTY_NOTICES.md como UTF-8"
    ]


def test_corrupt_zip_member_is_reported(tmp_path: Path) -> None:
    """Catches damaged payload bytes outside the legal files going unnoticed."""
    distribution = tmp_path / "distribution"
    _write_valid_distribution(distribution)
    archive = tmp_path / "portable.zip"
    _zip_directory(distribution, archive)
    damaged = bytearray(archive.read_bytes())
    payload_offset = damaged.index(b"portable")
    damaged[payload_offset] ^= 0xFF
    archive.write_bytes(damaged)
    verifier = _load_verifier()

    assert (
        "CRC ZIP inválido: El Oraculo de ENOM.exe"
        in verifier.validate_distribution(archive)
    )


def test_corrupt_notices_preserve_crc_and_other_contract_errors(
    tmp_path: Path,
) -> None:
    """Catches a damaged notice discarding CRC and independent contract errors."""
    distribution = tmp_path / "distribution"
    _write_valid_distribution(distribution)
    (distribution / "LICENSE").unlink()
    notice_bytes = b"unique-notice-payload"
    (distribution / "THIRD_PARTY_NOTICES.md").write_bytes(notice_bytes)
    archive = tmp_path / "portable.zip"
    _zip_directory(distribution, archive)
    damaged = bytearray(archive.read_bytes())
    payload_offset = damaged.index(notice_bytes)
    damaged[payload_offset] ^= 0xFF
    archive.write_bytes(damaged)
    verifier = _load_verifier()

    errors = verifier.validate_distribution(archive)

    assert "CRC ZIP inválido: THIRD_PARTY_NOTICES.md" in errors
    assert "Falta el archivo obligatorio en la raíz: LICENSE" in errors
