# El Oráculo de ENOM — Tramo 15B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Definir y hacer ejecutable el contrato que comprobará que el ZIP, su SHA-256 y el SBOM CycloneDX forman un conjunto de publicación coherente.

**Architecture:** Se amplía `scripts/verify_distribution.py` sin romper su interfaz actual de un solo argumento. Una nueva función pura valida los tres activos; la CLI activa ese modo únicamente cuando recibe juntos `--sbom` y `--sha256`. La generación de esos activos, la dependencia CycloneDX y el workflow quedan fuera de este subtramo.

**Tech Stack:** Python 3.12 (`hashlib`, `json`, `tomllib`, `argparse`), pytest.

**Spec:** `docs/superpowers/specs/2026-09-08-oraculo-enom-1.0-release-design.md`

## Global Constraints

- Mantener compatible `python scripts/verify_distribution.py <directorio-o-zip>`.
- No modificar `pyproject.toml`, `.github/workflows/build-windows.yml` ni `README.md`; corresponden al 15C/15D.
- Mantener la versión declarada en `0.1.0` hasta el Tramo 16.
- Validar el formato real reproducible de CycloneDX 1.6 producido por `cyclonedx-bom` 7.x.
- El archivo SHA-256 debe usar hexadecimal minúsculo, dos espacios y el basename exacto del ZIP.

## Review Focus

- Archivos faltantes o no UTF-8 deben producir errores controlados, no tracebacks.
- Un checksum bien formado pero asociado a otro nombre debe rechazarse.
- Un checksum con digest incorrecto debe rechazarse aunque el nombre sea correcto.
- Un JSON válido que no sea CycloneDX 1.6 debe rechazarse.
- Un SBOM sin la aplicación raíz exacta o sin `PySide6==6.11.2` debe rechazarse.

---

### Task 1: Contrato de activos de publicación

**Files:**
- Modify: `tests/release/test_distribution.py`
- Modify: `scripts/verify_distribution.py`

**Interfaces:**
- Consumes: el contrato actual `validate_distribution(source: Path) -> list[str]`.
- Produces: `validate_release_assets(portable_zip: Path, sbom: Path, checksum: Path) -> list[str]` y las opciones CLI `--sbom PATH --sha256 PATH`.

- [ ] Escribir fixtures y pruebas para un conjunto válido, checksum faltante/malformado/nombre incorrecto/digest incorrecto, SBOM faltante/JSON inválido/formato incorrecto/aplicación raíz ausente/PySide6 ausente y uso incompleto de opciones CLI.
- [ ] Ejecutar las pruebas nuevas y confirmar RED porque `validate_release_assets` y las opciones todavía no existen.
- [ ] Implementar la validación mínima con `hashlib` y `json`, leyendo las versiones esperadas desde `pyproject.toml`.
- [ ] Extender la CLI conservando el modo anterior de un argumento y exigiendo que `--sbom` y `--sha256` aparezcan juntos.
- [ ] Ejecutar `tests/release/test_distribution.py` y confirmar GREEN.

### Task 2: Registro, regresión y checkpoint

**Files:**
- Modify: `docs/release/1.0.0-status.md`

**Interfaces:**
- Consumes: el contrato ejecutable y sus pruebas de Task 1.
- Produces: registro de 15B completo y 15C–15E pendientes.

- [ ] Documentar qué valida el contrato y marcar únicamente 15B como completo.
- [ ] Ejecutar la suite completa, `compileall`, `pip check` y `git diff --check`.
- [ ] Revisar el diff y crear un único commit del Tramo 15B.
