# Third-party notices

This inventory covers the Python runtime, PySide6, Shiboken6, the Qt libraries
and plugins shipped in the accepted Windows portable, their identified vendored
or statically linked dependencies, and the PyInstaller bootloader and runtime
support embedded in the executable. Build-only Python packages that are not
present in the portable, such as pytest and pytest-qt, are excluded.

Versions were established from the bundled binaries and, for CPython's linked
extensions, from the dependency manifest of the exact CPython 3.12.10 tag.
The accepted functional artifact was produced from commit
`58d28a631fdfb764bd4d97445d277d024cb19a77`. The audited build versions were
then pinned at commit `b67c339f30bcd6a6940898dd5fcce6fb02db5705` and reproduced
successfully by Windows workflow run 39535094753.
Qt versions and components were established from the bundled binaries and
checked against Qt's official 6.11.2 licensing pages and the corresponding
`v6.11.2` source tags. The Qt PDF snapshot is tied to the Chromium submodule
commit recorded by that exact Qt tag. This inventory was reviewed on
2026-10-21.

## PyInstaller bootloader and runtime support

- Build tool version: 6.22.2
- Copyright: 2002-2023 McMillan Enterprises, Giovanni Bajo and the
  PyInstaller Development Team; see the complete terms
- License identifiers: GPL-2.0-or-later WITH Bootloader-exception for the
  bootloader and loader; Apache-2.0 for embedded run-time hooks and additional
  run-time modules
- Upstream: https://pyinstaller.org/ and
  https://github.com/pyinstaller/pyinstaller
- Local terms:
  [PyInstaller COPYING and Bootloader Exception](licenses/PyInstaller-6.22.2-COPYING.txt)
  and [Apache License 2.0](licenses/Qt-6.11.2-Apache-2.0.txt)
- Bundled evidence: the Windows `runw.exe` bootloader is embedded in
  `El Oraculo de ENOM.exe`; PyInstaller also embeds its loader, the
  `pyi_rth_inspect.py` and `pyi_rth_pyside6.py` run-time hooks, and
  `_pyi_rth_utils`

PyInstaller itself is used only as a build tool and is not distributed as an
installable Python package in the portable. Its Bootloader Exception grants
unlimited permission to link or embed the compiled bootloader and related files
in another program and distribute that combined executable without restrictions
arising solely from those files. The complete exception and the terms that still
apply to PyInstaller itself are preserved in the local COPYING file above.

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

## PySide6

- Bundled version: 6.11.2 (PySide6, PySide6 Essentials and PySide6 Addons)
- Copyright: The Qt Company Ltd. and the PySide contributors
- License identifier: LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
- Upstream: https://code.qt.io/cgit/pyside/pyside-setup.git/
- Local licenses:
  [LGPL-3.0-only](licenses/Qt-6.11.2-LGPL-3.0-only.txt),
  [GPL-2.0-only](licenses/Qt-6.11.2-GPL-2.0-only.txt) and
  [GPL-3.0-only](licenses/Qt-6.11.2-GPL-3.0-only.txt)
- Bundled evidence: `_internal/PySide6/pyside6.abi3.dll` and the PySide6
  `Qt*.pyd` bindings; version metadata and binaries match 6.11.2

## Shiboken6

- Bundled version: 6.11.2
- Copyright: The Qt Company Ltd. and the Shiboken contributors
- License identifier: LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
- Upstream: https://code.qt.io/cgit/pyside/pyside-setup.git/
- Local licenses:
  [LGPL-3.0-only](licenses/Qt-6.11.2-LGPL-3.0-only.txt),
  [GPL-2.0-only](licenses/Qt-6.11.2-GPL-2.0-only.txt) and
  [GPL-3.0-only](licenses/Qt-6.11.2-GPL-3.0-only.txt)
- Bundled evidence: `_internal/shiboken6/shiboken6.abi3.dll` and
  `_internal/shiboken6/Shiboken.pyd`; embedded version is 6.11.2

## Qt framework

- Bundled version: 6.11.2
- Copyright: The Qt Company Ltd., its subsidiaries and Qt contributors
- License identifier for Qt Core, GUI, Widgets, Network, OpenGL, PDF, QML,
  Quick, SVG and their plugins: LGPL-3.0-only OR GPL-2.0-only OR
  GPL-3.0-only
- License identifier for Qt Virtual Keyboard: GPL-3.0-only (the portable uses
  the open-source distribution, not a commercial Qt license)
- Upstream: https://code.qt.io/cgit/qt/
- Local licenses:
  [LGPL-3.0-only](licenses/Qt-6.11.2-LGPL-3.0-only.txt),
  [GPL-2.0-only](licenses/Qt-6.11.2-GPL-2.0-only.txt) and
  [GPL-3.0-only](licenses/Qt-6.11.2-GPL-3.0-only.txt)
- Bundled evidence: the 6.11.2 `Qt6*.dll` libraries under
  `_internal/PySide6/`, together with the platform, image-format, TLS, SVG,
  PDF and virtual-keyboard plugins shipped beside them

El Oráculo de ENOM is licensed as `GPL-2.0-or-later`; redistribution of the
bundled GPLv3-only Qt Virtual Keyboard module therefore uses the GPLv3 option.

## Third-party code in Qt Core 6.11.2

These components are present in the shipped `Qt6Core.dll`. Components that Qt
documents as macOS- or Unix-only were excluded from this Windows inventory.

| Component and bundled version | Copyright | License identifier | Upstream | Local license |
| --- | --- | --- | --- | --- |
| Apache Tika MIME definitions, `c2972478` | 2026 The Apache Software Foundation | Apache-2.0 | https://tika.apache.org/ | [text](licenses/Qt-6.11.2-Apache-2.0.txt) |
| BLAKE2 reference implementation, `ed1974e` | 2012 Samuel Neves | CC0-1.0 OR Apache-2.0 | https://github.com/BLAKE2/BLAKE2/ | [CC0 text](licenses/Qt-6.11.2-CC0-1.0.txt) |
| zlib, 1.3.2 | 1995-2026 Jean-loup Gailly and Mark Adler | Zlib | https://zlib.net/ | [text](licenses/Qt-zlib-1.3.2.txt) |
| Easing equations | 2001 Robert Penner | BSD-3-Clause | https://robertpenner.com/easing/ | [text](licenses/Qt-6.11.2-BSD-3-Clause.txt) |
| double-conversion, 3.4.0 | 2006-2012 the V8 project authors | BSD-3-Clause | https://github.com/google/double-conversion/ | [text](licenses/Qt-double-conversion-3.4.0.txt) |
| MD4 and MD5 implementations | Alexander Peslyak; Colin Plumb and contributors | CC0-1.0 / public-domain dedication | https://openwall.info/wiki/people/solar/software/public-domain-source-code/md4 | [text](licenses/Qt-6.11.2-CC0-1.0.txt) |
| PCRE2 and SLJIT, 10.47 | University of Cambridge, Philip Hazel and Zoltan Herczeg | LicenseRef-BSD-3-Clause-with-PCRE2-Binary-Like-Packages-Exception AND BSD-2-Clause | https://github.com/PCRE2Project/pcre2/ | [text](licenses/Qt-PCRE2-10.47.txt) |
| SHA-1 implementation | Dominik Reichl and The Qt Company Ltd. | LicenseRef-SHA1-Public-Domain | https://www.qt.io/ | [text](licenses/Qt-6.11.2-SHA1-Public-Domain.txt) |
| SHA-3 / Keccak, 3.2 | Guido Bertoni, Joan Daemen, Michaël Peeters and Gilles Van Assche | CC0-1.0 | https://keccak.team/ | [text](licenses/Qt-6.11.2-CC0-1.0.txt) |
| SHA-3 `brg_endian`, 1.0.0 | 1998-2013 Brian Gladman | BSD-2-Clause | https://www.gladman.me.uk/ | [text](licenses/Qt-6.11.2-BSD-2-Clause.txt) |
| SHA-384 and SHA-512 | 2011 IETF Trust and identified authors | BSD-3-Clause | https://www.rfc-editor.org/rfc/rfc6234 | [text](licenses/Qt-6.11.2-BSD-3-Clause.txt) |
| SipHash | Jean-Philippe Aumasson, Daniel J. Bernstein and Intel Corporation | CC0-1.0 | https://github.com/veorq/SipHash/ | [text](licenses/Qt-6.11.2-CC0-1.0.txt) |
| TinyCBOR, 7.0 | 2015-2025 Intel Corporation | MIT | https://github.com/intel/tinycbor/ | [text](licenses/Qt-TinyCBOR-7.0.txt) |
| Unicode Character Database, revision 36 (Unicode 16.0.0 tables) | 1991-2025 Unicode, Inc. | Unicode-3.0 | https://www.unicode.org/ucd/ | [text](licenses/Qt-6.11.2-Unicode-3.0.txt) |
| Unicode CLDR, v48.2 | 2004-2025 Unicode, Inc. | Unicode-3.0 | https://cldr.unicode.org/ | [text](licenses/Qt-6.11.2-Unicode-3.0.txt) |
| `tl::expected`, `41d3e1f` | Sy Brand (rights waived) | CC0-1.0 | https://github.com/TartanLlama/expected/ | [text](licenses/Qt-6.11.2-CC0-1.0.txt) |

## Third-party code in Qt GUI and Windows plugins 6.11.2

These entries cover `Qt6Gui.dll`, `Qt6Widgets.dll`, `Qt6OpenGL.dll`, the
Windows platform plugins and the shipped image-format plugins. Android,
WebAssembly, XCB and ARM-only components are not distributed in this portable.

| Component and bundled version | Copyright | License identifier | Upstream | Local license |
| --- | --- | --- | --- | --- |
| Adobe Glyph List, 1.7 | 2002-2015 Adobe Systems | BSD-3-Clause | https://github.com/adobe-type-tools/agl-aglfn/ | [text](licenses/Qt-6.11.2-BSD-3-Clause.txt) |
| FreeType anti-aliasing rasterizer and FreeType, 2.14.3 | The FreeType Project authors and contributors named in the text | FTL OR GPL-2.0-only | https://freetype.org/ | [text](licenses/Qt-FreeType-2.14.3.txt) |
| FreeType BDF support | Computing Research Labs and Francesco Zappa Nardelli | MIT | https://freetype.org/ | [text](licenses/Qt-6.11.2-MIT.txt) |
| FreeType PCF support | David Turner, Robert Wilhelm, Werner Lemberg, Francesco Zappa Nardelli and The Open Group | MIT AND MIT-open-group | https://freetype.org/ | [MIT](licenses/Qt-6.11.2-MIT.txt), [Open Group](licenses/Qt-6.11.2-MIT-open-group.txt) |
| FreeType zlib code | 1995-2024 Jean-loup Gailly and Mark Adler | Zlib | https://zlib.net/ | [text](licenses/Qt-6.11.2-Zlib.txt) |
| D3D12 Memory Allocator, `f128d39` | 2019-2022 Advanced Micro Devices, Inc. | MIT | https://github.com/GPUOpen-LibrariesAndSDKs/D3D12MemoryAllocator/ | [text](licenses/Qt-6.11.2-MIT.txt) |
| D3D12 mipmap generator, `0aa79ba` | 2015 Microsoft | MIT | https://github.com/microsoft/DirectX-Graphics-Samples/ | [text](licenses/Qt-6.11.2-MIT.txt) |
| Emoji Segmenter, 0.4.0 | 2019 Google LLC | Apache-2.0 | https://github.com/google/emoji-segmenter/ | [text](licenses/Qt-6.11.2-Apache-2.0.txt) |
| HarfBuzz-NG, 14.3.0 | HarfBuzz authors and contributors named in the text | MIT | https://github.com/harfbuzz/harfbuzz/ | [text](licenses/Qt-HarfBuzz-14.3.0.txt) |
| libjpeg-turbo, 3.2.0 | Independent JPEG Group, D. R. Commander and contributors | IJG AND BSD-3-Clause | https://libjpeg-turbo.org/ | [BSD and notices](licenses/Qt-libjpeg-turbo-3.2.0.txt), [IJG](licenses/Qt-IJG-libjpeg-turbo-3.2.0.txt) |
| libpng, 1.6.58 | PNG Reference Library authors and contributors named in the text | Libpng AND libpng-2.0 | http://www.libpng.org/pub/png/libpng.html | [text](licenses/Qt-libpng-1.6.58.txt) |
| MD4C, 0.5.3 | 2016-2024 Martin Mitáš | MIT | https://github.com/mity/md4c/ | [text](licenses/Qt-6.11.2-MIT.txt) |
| OpenGL and OpenGL ES 2 headers, revisions 27684 and 27673 | 2013-2014 The Khronos Group Inc. | MIT | https://registry.khronos.org/OpenGL/ | [text](licenses/Qt-6.11.2-MIT.txt) |
| Smooth scaling algorithm | Daniel M. Duley, Carsten Haitzler, Willem Monsuwe and contributors | BSD-2-Clause AND Imlib2 | https://www.enlightenment.org/ | [BSD](licenses/Qt-6.11.2-BSD-2-Clause.txt), [Imlib2](licenses/Qt-6.11.2-Imlib2.txt) |
| Vulkan API Registry, 1.4.308 | 2015-2025 The Khronos Group Inc. | Apache-2.0 OR MIT | https://github.com/KhronosGroup/Vulkan-Headers/ | [Apache](licenses/Qt-6.11.2-Apache-2.0.txt), [MIT](licenses/Qt-6.11.2-MIT.txt) |
| Vulkan Memory Allocator, 3.2.1 | 2017-2025 Advanced Micro Devices, Inc. | MIT | https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator/ | [text](licenses/Qt-6.11.2-MIT.txt) |
| WebGradients presets | 2017 itmeo | MIT | https://webgradients.com/ | [text](licenses/Qt-6.11.2-MIT.txt) |
| Wintab API | 1991-1998 LCS/Telegraphics | LicenseRef-Lcs-Telegraphics | https://www.wacom.com/ | [text](licenses/Qt-6.11.2-LCS-Telegraphics.txt) |
| X server region helper | X Consortium and Digital Equipment Corporation | X11 AND HPND | https://www.x.org/ | [X11](licenses/Qt-6.11.2-X11.txt), [HPND](licenses/Qt-6.11.2-HPND.txt) |
| sRGB ICC color profile | 2015 International Color Consortium | LicenseRef-ICC-License | https://www.color.org/ | [text](licenses/Qt-6.11.2-ICC.txt) |
| libtiff, 4.7.2 | 1988-1997 Sam Leffler; 1991-1997 Silicon Graphics, Inc. | libtiff | https://libtiff.gitlab.io/libtiff/ | [text](licenses/Qt-libtiff-4.7.2.txt) |
| libwebp, 1.6.0 | 2010 Google Inc. | BSD-3-Clause | https://chromium.googlesource.com/webm/libwebp/ | [text](licenses/Qt-libwebp-1.6.0.txt) |

## Third-party code in other shipped Qt modules 6.11.2

| Qt module / component and bundled version | Copyright | License identifier | Upstream | Local license |
| --- | --- | --- | --- | --- |
| Qt Network / Public Suffix List, `2026-05-14_08-35-31_UTC` | Public Suffix List maintainers | MPL-2.0 | https://publicsuffix.org/ | [text](licenses/Qt-Public-Suffix-List.txt) |
| Qt Network / libpsl, `664f3dc` | 2014-2016 The Chromium Authors | BSD-3-Clause | https://github.com/rockdaboot/libpsl/ | [text](licenses/Qt-libpsl.txt) |
| Qt QML / JavaScriptCore Macro Assembler | Apple Inc. and contributors named in the text | BSD-2-Clause | https://webkit.org/ | [text](licenses/Qt-JavaScriptCore-MASM.txt) |
| Qt Quick / Yoga, 2.0.1 | Facebook, Inc. and Meta Platforms, Inc. | MIT | https://github.com/facebook/yoga/ | [text](licenses/Qt-Yoga-2.0.1.txt) |
| Qt SVG / XSVG | 2002 USC/Information Sciences Institute | HPND-sell-variant | https://www.qt.io/ | [text](licenses/Qt-XSVG.txt) |
| Qt Virtual Keyboard / OpenWnn | 2008-2012 OMRON SOFTWARE Co., Ltd. | Apache-2.0 | https://android.googlesource.com/platform/packages/inputmethods/OpenWnn/ | [text](licenses/Qt-OpenWnn.txt) |
| Qt Virtual Keyboard / PinyinIME | 2009 The Android Open Source Project | Apache-2.0 | https://android.googlesource.com/platform/packages/inputmethods/PinyinIME/ | [text](licenses/Qt-PinyinIME.txt) |
| Qt Virtual Keyboard / Traditional Chinese IME | Google Inc., TaBE Project, Academia Sinica, Chih-Hao Tsai and contributors named in the text | Apache-2.0 AND BSD-3-Clause | https://code.qt.io/cgit/qt/qtvirtualkeyboard.git/ | [text](licenses/Qt-TCIME.txt) |

## Qt PDF and PDFium snapshot

`Qt6Pdf.dll` contains the PDFium snapshot from Qt WebEngine 6.11.2. The Qt tag
pins Chromium/PDFium submodule commit
`5170777d28bee1ce92cc693a0dbf2ad01492e5cf`; components without their own
release number below therefore use that immutable snapshot as the bundled
version. FreeType and libpng reuse the corresponding texts already listed
above; Chromium's libjpeg-turbo and zlib copies have their own exact versions
and license files below.

| Component and bundled version | Copyright | License identifier | Upstream | Local license |
| --- | --- | --- | --- | --- |
| Abseil, revision `56945519` | Abseil authors and contributors | Apache-2.0 | https://github.com/abseil/abseil-cpp/ | [text](licenses/Qt-PDF-Abseil.txt) |
| Anti-Grain Geometry, 2.3 | 2002-2005 Maxim Shemanarev | LicenseRef-Anti-Grain-Geometry-2.3 | https://sourceforge.net/projects/agg/ | [text](licenses/Qt-PDF-Anti-Grain-Geometry-2.3.txt) |
| FreeType, snapshot `5170777d` | The FreeType Project authors | FTL | https://freetype.org/ | [text](licenses/Qt-FreeType-2.14.3.txt) |
| PDFium, snapshot `5170777d` | 2014 The PDFium Authors and included contributors | BSD-3-Clause and included notices | https://pdfium.googlesource.com/pdfium/ | [text](licenses/Qt-PDFium-5170777d.txt) |
| Chromium support code, snapshot `5170777d` | 2015 The Chromium Authors | BSD-3-Clause | https://www.chromium.org/ | [text](licenses/Qt-Chromium.txt) |
| fast_float, 7.0.0 (`cb1d42aa`) | 2021 the fast_float authors | MIT | https://github.com/fastfloat/fast_float/ | [text](licenses/Qt-PDF-fast_float.txt) |
| ICU, 74.2 | Unicode, Inc., IBM Corporation and included contributors | Unicode-3.0 / included third-party notices | https://github.com/unicode-org/icu/ | [text](licenses/Qt-PDF-ICU.txt) |
| Little CMS, 2.15 (`d0752309`) | 2023 Marti Maria Saguer | MIT | https://github.com/mm2/Little-CMS/ | [text](licenses/Qt-PDF-Little-CMS-2.15.txt) |
| libjpeg-turbo, 3.1.0 | Independent JPEG Group, D. R. Commander and contributors | IJG AND BSD-3-Clause AND Zlib | https://libjpeg-turbo.org/ | [BSD, Zlib and notices](licenses/Qt-PDF-libjpeg-turbo-3.1.0.txt), [IJG](licenses/Qt-PDF-IJG-libjpeg-turbo-3.1.0.txt) |
| libpng, 1.6.58 | PNG Reference Library authors | Libpng-2.0 AND Libpng | http://www.libpng.org/pub/png/libpng.html | [text](licenses/Qt-libpng-1.6.58.txt) |
| OpenJPEG, 2.5.3 (`210a8a56`) | UCL, Benoit Macq, Antonin Descampe and contributors named in the text | BSD-2-Clause | https://github.com/uclouvain/openjpeg/ | [text](licenses/Qt-PDF-OpenJPEG-2.5.3.txt) |
| zlib, 1.3.1 (`51b7f2ab`) | Jean-loup Gailly and Mark Adler | Zlib | https://zlib.net/ | [text](licenses/Qt-PDF-zlib-1.3.1.txt) |
