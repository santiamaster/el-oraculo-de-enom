# Third-party notices

This checkpoint covers the Python runtime and the native components explicitly
listed below. Qt, PySide6, Shiboken6, Qt PDF and Qt's remaining vendored/static
third-party dependencies are intentionally reserved for Tramo 14D. The Qt-side
OpenSSL and Microsoft runtimes plus Mesa/LLVM are already listed here because
their standalone binaries or versions were directly identifiable.

Versions were established from the bundled binaries and, for CPython's linked
extensions, from the dependency manifest of the exact CPython 3.12.10 tag.
The accepted artifact was produced from commit `58d28a631fdfb764bd4d97445d277d024cb19a77`.
This inventory was reviewed on 2026-09-15.

## CPython

- Bundled version: 3.12.10
- Copyright: Python Software Foundation and contributors; see the complete text
- License identifier: PSF-2.0
- Upstream: https://www.python.org/
- Local license: [licenses/CPython-3.12.10.txt](licenses/CPython-3.12.10.txt)
- Bundled evidence: `_internal/python312.dll`, `_internal/python3.dll` and
  `_internal/base_library.zip`

## libmpdec

- Bundled version: 2.5.1
- Copyright: 2008-2020 Stefan Krah
- License identifier: BSD-2-Clause
- Upstream: https://www.bytereef.org/mpdecimal/
- Local license: [licenses/libmpdec-2.5.1.txt](licenses/libmpdec-2.5.1.txt)
- Bundled evidence: statically linked in `_internal/_decimal.pyd`

## HACL*

- Bundled version: revision `bb3d0dc8d9d15a5cd51094d5b69e70aa09005ff0`
  vendored by CPython 3.12.10
- Copyright: 2016-2022 INRIA, CMU and Microsoft Corporation; 2022-2023
  HACL* Contributors
- License identifier: MIT
- Upstream: https://github.com/hacl-star/hacl-star/
- Local license:
  [licenses/HACL-star-bb3d0dc.txt](licenses/HACL-star-bb3d0dc.txt)
- Bundled evidence: HACL* hash implementation symbols and source identifiers
  in `_internal/python312.dll`

## bzip2 / libbzip2

- Bundled version: 1.0.8
- Copyright: 1996-2019 Julian R Seward
- License identifier: bzip2-1.0.6
- Upstream: https://sourceware.org/bzip2/
- Local license: [licenses/bzip2-1.0.8.txt](licenses/bzip2-1.0.8.txt)
- Bundled evidence: statically linked in `_internal/_bz2.pyd`

## XZ Utils / liblzma

- Bundled version: 5.2.5
- Copyright: XZ Utils contributors
- License identifier: LicenseRef-XZ-Utils-Public-Domain
- Upstream: https://tukaani.org/xz/
- Local license: [licenses/XZ-Utils-5.2.5.txt](licenses/XZ-Utils-5.2.5.txt)
- Bundled evidence: liblzma is statically linked in `_internal/_lzma.pyd`

The bundled part is liblzma. XZ Utils' own licensing statement places liblzma
in the public domain; command-line tools, scripts and build-system files with
other licenses are not present in this portable.

## zlib

- Bundled version: 1.3.1
- Copyright: 1995-2022 Jean-loup Gailly and Mark Adler
- License identifier: Zlib
- Upstream: https://zlib.net/
- Local license: [licenses/zlib-1.3.1.txt](licenses/zlib-1.3.1.txt)
- Bundled evidence: zlib 1.3.1 version and runtime strings in
  `_internal/python312.dll`; CPython uses it for ZIP import support

## OpenSSL

- Bundled versions: 3.0.16 (11 February 2025) and 3.5.5 (27 January 2026)
- Copyright: 1998-2025 and 1998-2026 The OpenSSL Authors
- License identifier: Apache-2.0
- Upstream: https://www.openssl.org/
- Local licenses:
  [licenses/OpenSSL-3.0.16.txt](licenses/OpenSSL-3.0.16.txt) and
  [licenses/OpenSSL-3.5.5.txt](licenses/OpenSSL-3.5.5.txt)
- Bundled evidence: 3.0.16 in `_internal/libcrypto-3.dll` for CPython;
  3.5.5 in `_internal/libcrypto-3-x64.dll` and
  `_internal/libssl-3-x64.dll`; `_internal/_hashlib.pyd` consumes OpenSSL

## SQLite

- Bundled version: 3.49.1
- Copyright: dedicated to the public domain by its authors
- License identifier: LicenseRef-SQLite-Public-Domain
- Upstream: https://sqlite.org/
- Local license: [licenses/SQLite-3.49.1.txt](licenses/SQLite-3.49.1.txt)
- Bundled evidence: `_internal/sqlite3.dll` and `_internal/_sqlite3.pyd`

## Unicode Character Database

- Bundled version: 15.0.0
- Copyright: 1991-2026 Unicode, Inc. (current Unicode License V3 notice)
- License identifier: Unicode-3.0
- Upstream: https://www.unicode.org/
- Local license:
  [licenses/Unicode-Data-15.0.0.txt](licenses/Unicode-Data-15.0.0.txt)
- Bundled evidence: generated Unicode 15.0.0 tables in
  `_internal/unicodedata.pyd`

## Microsoft Visual C++ and Universal C Runtime

- Bundled versions: Visual C++ Runtime 14.42.34438.0 and 14.44.35211.0;
  Universal C Runtime 10.0.26100.1742
- Copyright: Microsoft Corporation
- License identifier: LicenseRef-Microsoft-Visual-Cpp-Runtime
- Upstream license terms:
  https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/
- Local license information:
  [licenses/Microsoft-Visual-Cpp-Runtime.txt](licenses/Microsoft-Visual-Cpp-Runtime.txt)
- Bundled evidence: `VCRUNTIME140*.dll`, `MSVCP140*.dll`, `ucrtbase.dll` and
  the `api-ms-win-*` runtime forwarders

## Mesa software rasterizer

- Bundled version: 11.2.2
- Copyright: Brian Paul and Mesa contributors; see the complete text
- License identifier: MIT (component-specific licenses may also apply)
- Upstream: https://www.mesa3d.org/
- Local license: [licenses/Mesa-11.2.2.html](licenses/Mesa-11.2.2.html)
- Bundled evidence: Mesa and llvmpipe version strings in
  `_internal/PySide6/opengl32sw.dll`

## LLVM

- Bundled version: 3.6.2
- Copyright: 2003-2014 University of Illinois at Urbana-Champaign
- License identifier: NCSA
- Upstream: https://llvm.org/
- Local license: [licenses/LLVM-3.6.2.txt](licenses/LLVM-3.6.2.txt)
- Bundled evidence: LLVM and llvmpipe version strings in
  `_internal/PySide6/opengl32sw.dll`
