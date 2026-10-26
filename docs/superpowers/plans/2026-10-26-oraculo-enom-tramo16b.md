# El Oráculo de ENOM — Tramo 16B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir y auditar localmente el candidato estructural `1.0.0` sin modificar el comportamiento de la aplicación ni anticipar el artefacto nativo de Windows.

**Architecture:** El subtramo reproduce la puerta local definida para el Tramo 16: entorno limpio con el toolchain fijado, suite completa, compilación de bytecode, construcción PyInstaller y verificación de la carpeta portable. La evidencia se registra en el estado de publicación; el ZIP, SBOM y checksum nativos de Windows siguen perteneciendo al 16C.

**Tech Stack:** Python 3.12.10, PySide6 6.11.2, pytest, pytest-qt, PyInstaller 6.22.2 y verificador de distribución del proyecto.

**Spec:** `docs/superpowers/specs/2026-09-08-oraculo-enom-1.0-release-design.md`

## Global Constraints

- Ejecutar únicamente el Tramo 16B y detenerse al completarlo.
- Partir del commit remoto aceptado del 16A: `2f0e1e2b87b8c0d7d41bc128f9b4db88294baa9c`.
- Mantener la versión `1.0.0` y las dependencias auditadas sin cambios.
- No incorporar funciones, cambios de interfaz, esquema de datos ni dependencias.
- No versionar `.venv/`, `build/`, `dist/`, binarios, ZIP ni otros artefactos locales.
- No afirmar validación nativa de Windows desde la construcción Linux.
- No iniciar el 16C, hacer push, merge, tag ni GitHub Release.

## Review Focus

- El entorno debe usar Python `3.12.10`, no otra revisión de Python 3.12.
- La suite debe ejecutarse con Qt en modo `offscreen` y terminar sin fallos.
- La construcción debe partir sin `build/` ni `dist/` residuales.
- La carpeta portable debe contener el ejecutable, avisos y licencias, y excluir base de datos, fuentes y pruebas.
- El registro debe marcar solo 16B como completo y mantener 16C–16E pendientes.

---

### Task 1: Construir, inspeccionar y registrar el candidato local

**Files:**
- Create: `docs/superpowers/plans/2026-10-26-oraculo-enom-tramo16b.md`
- Modify: `docs/release/1.0.0-status.md`

**Interfaces:**
- Consumes: candidato versionado `1.0.0` del commit `2f0e1e2` y contrato de `scripts/verify_distribution.py`.
- Produces: evidencia local reproducible que el 16C complementará con el artefacto nativo de Windows.

- [x] Crear `.venv` con Python `3.12.10` e instalar el proyecto desde PyPI con `python -m pip install -e '.[dev]'`.
- [x] Confirmar versiones de Python, PySide6, Shiboken6, PyInstaller y hooks, y ejecutar `python -m pip check`.
- [x] Ejecutar `QT_QPA_PLATFORM=offscreen python -m pytest -q`, `python -m compileall -q src tests scripts` y `git diff --check`.
- [x] Eliminar únicamente `build/` y `dist/` locales y ejecutar `python -m PyInstaller El-Oraculo-de-ENOM.spec --clean --noconfirm`.
- [x] Ejecutar `python scripts/verify_distribution.py 'dist/El Oraculo de ENOM'` e inspeccionar ejecutable, avisos, licencias y contenidos prohibidos.
- [x] Registrar comandos, versiones, conteos y limitación Linux en `docs/release/1.0.0-status.md`; marcar solo 16B como completo.
- [x] Repetir suite, bytecode, `pip check`, verificador y `git diff --check`; revisar el diff y crear un único checkpoint.
