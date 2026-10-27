# El Oráculo de ENOM — Tramo 15C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer que el workflow de Windows genere automáticamente el SBOM CycloneDX y el SHA-256 del ZIP, valide el conjunto y publique los tres activos juntos.

**Architecture:** `cyclonedx-bom` se incorpora únicamente al extra de desarrollo. Actions crea un entorno temporal separado, instala la aplicación y sus dependencias de ejecución, retira `pip` para que no aparezca como componente distribuido, genera un SBOM reproducible CycloneDX 1.6 y aplica el contrato del 15B antes de subir el artefacto. La estabilización e inspección del run remoto corresponden a 15D y 15E.

**Tech Stack:** Python 3.12.10, cyclonedx-bom 7.x, PowerShell, GitHub Actions, pytest.

**Spec:** `docs/superpowers/specs/2026-09-08-oraculo-enom-1.0-release-design.md`

## Global Constraints

- Agregar exactamente `cyclonedx-bom>=7.3,<8` al extra `dev`.
- Mantener el entorno SBOM separado del entorno que ejecuta pruebas y PyInstaller.
- Generar CycloneDX JSON 1.6 reproducible y validarlo durante la generación.
- El SHA-256 debe ser hexadecimal minúsculo, seguido por dos espacios y `El-Oraculo-de-ENOM-Windows.zip`.
- Subir ZIP, SBOM y checksum dentro del mismo artefacto `El-Oraculo-de-ENOM-Windows`.
- No modificar todavía README ni la versión `0.1.0`; no inspeccionar ni corregir el run remoto en este subtramo.

## Review Focus

- El SBOM no debe inventariar pytest, PyInstaller, cyclonedx-bom ni pip como componentes de ejecución.
- La generación debe usar el `pyproject.toml` para declarar correctamente la aplicación raíz.
- El workflow debe validar los tres archivos después de crearlos y antes de subirlos.
- El hash debe referenciar exactamente el basename del ZIP y ser compatible con el contrato del 15B.
- `upload-artifact` debe fallar si falta cualquiera de los tres activos.

---

### Task 1: Dependencia y workflow de metadatos

**Files:**
- Modify: `tests/release/test_distribution.py`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/build-windows.yml`

**Interfaces:**
- Consumes: `validate_release_assets` y las opciones `--sbom`/`--sha256` del 15B.
- Produces: tres archivos con nombres exactos dentro del artefacto de Actions.

- [ ] Escribir pruebas que exijan la dependencia acotada, el entorno runtime aislado, generación/validación CycloneDX 1.6, checksum canónico, verificación integrada y carga de los tres archivos.
- [ ] Ejecutar las pruebas nuevas y confirmar RED contra el workflow actual.
- [ ] Agregar la dependencia y los pasos mínimos de PowerShell/Actions.
- [ ] Ejecutar las pruebas de distribución y confirmar GREEN.

### Task 2: Generación real, registro y checkpoint

**Files:**
- Modify: `docs/release/1.0.0-status.md`

**Interfaces:**
- Consumes: comandos exactos introducidos en Task 1.
- Produces: evidencia local de SBOM compatible y registro de 15C completo con 15D–15E pendientes.

- [ ] Instalar `.[dev]` desde PyPI en el worktree y comprobar `pip check`.
- [ ] Reproducir localmente el entorno runtime, generar un SBOM real y validarlo con el contrato del 15B junto a un ZIP/checksum de prueba.
- [ ] Confirmar que el SBOM runtime no contiene herramientas de desarrollo o construcción.
- [ ] Actualizar el registro de estado sin afirmar todavía que Actions fue estabilizado.
- [ ] Ejecutar suite completa, `compileall`, `pip check` y `git diff --check`; revisar y crear un único commit.
