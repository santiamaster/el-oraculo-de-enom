# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from shutil import copy2, copytree

# PyInstaller's bundled PySide6 hooks collect the Qt libraries and plugins used
# by the PySide6 modules imported from the application entry point.

analysis = Analysis(
    ["src/oraculo_enom/app.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6.QtTest",
        "_pytest",
        "pytest",
        "pytestqt",
        "tests",
    ],
    noarchive=False,
    optimize=0,
)

python_archive = PYZ(analysis.pure)

executable = EXE(
    python_archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="El Oraculo de ENOM",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

distribution = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="El Oraculo de ENOM",
)

# PyInstaller 6 places all ``datas`` below ``_internal``.  These legal files
# must remain visible at the portable root without flattening the runtime
# layout audited in THIRD_PARTY_NOTICES.md.
distribution_root = Path(distribution.name)
copy2("LICENSE", distribution_root / "LICENSE")
copy2(
    "THIRD_PARTY_NOTICES.md",
    distribution_root / "THIRD_PARTY_NOTICES.md",
)
copytree("licenses", distribution_root / "licenses", dirs_exist_ok=True)
