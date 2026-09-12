# -*- mode: python ; coding: utf-8 -*-

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
