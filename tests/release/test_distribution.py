import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
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


def test_pyinstaller_bootloader_terms_are_documented() -> None:
    """Keeps the embedded bootloader traceable to its redistribution terms."""
    notices = (PROJECT_ROOT / "THIRD_PARTY_NOTICES.md").read_text(
        encoding="utf-8"
    )

    assert "## PyInstaller bootloader and runtime support" in notices
    assert "6.22.2" in notices
    assert "Bootloader Exception" in notices
    assert "licenses/PyInstaller-6.22.2-COPYING.txt" in notices
    assert (PROJECT_ROOT / "licenses/PyInstaller-6.22.2-COPYING.txt").is_file()


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


def _write_valid_release_assets(root: Path) -> tuple[Path, Path, Path]:
    distribution = root / "distribution"
    _write_valid_distribution(distribution)
    portable = root / "El-Oraculo-de-ENOM-Windows.zip"
    _zip_directory(distribution, portable)

    checksum = root / "El-Oraculo-de-ENOM-Windows.zip.sha256"
    digest = hashlib.sha256(portable.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {portable.name}\n", encoding="utf-8")

    sbom = root / "El-Oraculo-de-ENOM-Windows.sbom.cdx.json"
    sbom.write_text(
        json.dumps(
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.6",
                "version": 1,
                "metadata": {
                    "component": {
                        "type": "application",
                        "name": "el-oraculo-de-enom",
                        "version": "0.1.0",
                    }
                },
                "components": [
                    {
                        "type": "library",
                        "name": "PySide6",
                        "version": "6.11.2",
                        "purl": "pkg:pypi/pyside6@6.11.2",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return portable, sbom, checksum


def test_valid_release_assets_have_no_contract_violations(
    tmp_path: Path,
) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    verifier = _load_verifier()

    assert verifier.validate_release_assets(portable, sbom, checksum) == []


@pytest.mark.parametrize(
    ("asset", "expected_error"),
    [
        ("sbom", "No existe el archivo SBOM CycloneDX:"),
        ("checksum", "No existe el archivo SHA-256:"),
    ],
)
def test_missing_release_metadata_file_is_reported(
    tmp_path: Path, asset: str, expected_error: str
) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    selected = sbom if asset == "sbom" else checksum
    selected.unlink()
    verifier = _load_verifier()

    errors = verifier.validate_release_assets(portable, sbom, checksum)

    assert any(error.startswith(expected_error) for error in errors)


def test_malformed_checksum_file_is_reported(tmp_path: Path) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    checksum.write_text("not-a-checksum\n", encoding="utf-8")
    verifier = _load_verifier()

    assert (
        "Formato SHA-256 inválido: se espera hexadecimal minúsculo, dos espacios "
        "y el nombre del ZIP"
        in verifier.validate_release_assets(portable, sbom, checksum)
    )


def test_checksum_for_another_filename_is_reported(tmp_path: Path) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    digest = hashlib.sha256(portable.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  another.zip\n", encoding="utf-8")
    verifier = _load_verifier()

    assert (
        "El archivo SHA-256 referencia another.zip, no " + portable.name
        in verifier.validate_release_assets(portable, sbom, checksum)
    )


def test_checksum_mismatch_is_reported(tmp_path: Path) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    checksum.write_text(f"{'0' * 64}  {portable.name}\n", encoding="utf-8")
    verifier = _load_verifier()

    assert (
        f"El SHA-256 no coincide con {portable.name}"
        in verifier.validate_release_assets(portable, sbom, checksum)
    )


def test_release_assets_require_a_zip_file(tmp_path: Path) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    distribution = portable.with_name("distribution")
    checksum.write_text(
        f"{'0' * 64}  {distribution.name}\n", encoding="utf-8"
    )
    verifier = _load_verifier()

    assert (
        f"El activo portable debe ser un archivo ZIP válido: {distribution}"
        in verifier.validate_release_assets(distribution, sbom, checksum)
    )


def test_cli_rejects_directory_in_release_mode(tmp_path: Path) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    distribution = portable.with_name("distribution")
    checksum.write_text(
        f"{'0' * 64}  {distribution.name}\n", encoding="utf-8"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(VERIFIER_PATH),
            str(distribution),
            "--sbom",
            str(sbom),
            "--sha256",
            str(checksum),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "El activo portable debe ser un archivo ZIP válido" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("asset", ["sbom", "checksum"])
def test_non_utf8_release_metadata_is_reported(
    tmp_path: Path, asset: str
) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    selected = sbom if asset == "sbom" else checksum
    selected.write_bytes(b"\xff\xfe")
    verifier = _load_verifier()

    errors = verifier.validate_release_assets(portable, sbom, checksum)

    label = "SBOM CycloneDX" if asset == "sbom" else "SHA-256"
    assert f"No se pudo leer el archivo {label} como UTF-8" in errors


@pytest.mark.parametrize("asset", ["sbom", "checksum"])
def test_release_metadata_oserror_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, asset: str
) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    verifier = _load_verifier()
    selected = sbom if asset == "sbom" else checksum
    original_read_text = Path.read_text

    def denied_read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path == selected:
            raise PermissionError("denied for test")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", denied_read_text)

    errors = verifier.validate_release_assets(portable, sbom, checksum)

    label = "SBOM CycloneDX" if asset == "sbom" else "SHA-256"
    assert any(
        error.startswith(f"No se pudo leer el archivo {label}:")
        for error in errors
    )


def test_zip_hash_oserror_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    verifier = _load_verifier()
    original_open = Path.open

    def denied_open(path: Path, *args: object, **kwargs: object):
        if path == portable and args and args[0] == "rb":
            raise PermissionError("denied for test")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied_open)

    errors = verifier.validate_release_assets(portable, sbom, checksum)

    assert any(
        error.startswith(f"No se pudo calcular el SHA-256 de {portable.name}:")
        for error in errors
    )


def test_invalid_sbom_json_is_reported(tmp_path: Path) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    sbom.write_text("{not-json", encoding="utf-8")
    verifier = _load_verifier()

    assert (
        "El SBOM no contiene JSON válido"
        in verifier.validate_release_assets(portable, sbom, checksum)
    )


def test_non_cyclonedx_1_6_sbom_is_reported(tmp_path: Path) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    document = json.loads(sbom.read_text(encoding="utf-8"))
    document["bomFormat"] = "SPDX"
    document["specVersion"] = "2.3"
    sbom.write_text(json.dumps(document), encoding="utf-8")
    verifier = _load_verifier()

    assert (
        "El SBOM debe declarar bomFormat CycloneDX y specVersion 1.6"
        in verifier.validate_release_assets(portable, sbom, checksum)
    )


def test_boolean_sbom_serial_is_reported(tmp_path: Path) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    document = json.loads(sbom.read_text(encoding="utf-8"))
    document["version"] = True
    sbom.write_text(json.dumps(document), encoding="utf-8")
    verifier = _load_verifier()

    assert (
        "El SBOM debe declarar una versión serial positiva"
        in verifier.validate_release_assets(portable, sbom, checksum)
    )


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        (
            "root",
            "El SBOM no declara la aplicación raíz el-oraculo-de-enom==0.1.0",
        ),
        ("pyside6", "El SBOM no declara el componente PySide6==6.11.2"),
    ],
)
def test_required_sbom_component_is_reported(
    tmp_path: Path, mutation: str, expected_error: str
) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    document = json.loads(sbom.read_text(encoding="utf-8"))
    if mutation == "root":
        document["metadata"]["component"]["version"] = "9.9.9"
    else:
        document["components"] = []
    sbom.write_text(json.dumps(document), encoding="utf-8")
    verifier = _load_verifier()

    assert expected_error in verifier.validate_release_assets(
        portable, sbom, checksum
    )


@pytest.mark.parametrize("option", ["--sbom", "--sha256"])
def test_cli_requires_sbom_and_sha256_options_together(
    tmp_path: Path, option: str
) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)
    selected = sbom if option == "--sbom" else checksum

    result = subprocess.run(
        [sys.executable, str(VERIFIER_PATH), str(portable), option, str(selected)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "--sbom y --sha256 deben usarse juntos" in result.stderr


def test_cli_returns_zero_for_valid_release_assets(tmp_path: Path) -> None:
    portable, sbom, checksum = _write_valid_release_assets(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(VERIFIER_PATH),
            str(portable),
            "--sbom",
            str(sbom),
            "--sha256",
            str(checksum),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == f"Activos de publicación válidos: {portable}\n"
    assert result.stderr == ""


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
