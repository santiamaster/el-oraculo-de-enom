# El Oráculo de ENOM — Tramo 16A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Declarar coherentemente el candidato `1.0.0` en los metadatos, documentación pública, changelog, registro de estado y contrato SBOM, sin modificar comportamiento de la aplicación.

**Architecture:** Una prueba de coherencia lee los cinco puntos de verdad versionados y exige `1.0.0`. El cambio actualiza únicamente metadatos y documentación; el verificador continúa obteniendo dinámicamente la versión desde `pyproject.toml`, mientras sus fixtures pasan a representar el candidato final.

**Tech Stack:** Python 3.12.10, PEP 621/TOML, pytest, Markdown, CycloneDX JSON 1.6.

**Spec:** `docs/superpowers/specs/2026-09-08-oraculo-enom-1.0-release-design.md`

## Global Constraints

- La versión objetivo es exactamente `1.0.0`.
- La fecha del encabezado de changelog es `2026-10-25`, fecha argentina del candidato.
- No introducir funciones, cambios de interfaz, esquema de datos ni dependencias.
- Mantener Python `3.12.10`, PySide6 `6.11.2` y las herramientas de construcción auditadas.
- Mantener el Tramo 15 completo y registrar únicamente 16A como completo; 16B–16E permanecen pendientes.
- No construir todavía el portable local definitivo; corresponde al 16B.
- No hacer push, merge, tag ni GitHub Release desde este worktree.

## Review Focus

- No debe quedar ninguna declaración pública de versión actual `0.1.0`.
- El changelog debe conservar todo el contenido existente bajo un único encabezado fechado `1.0.0`.
- Las notas deben describir un candidato, no afirmar que la GitHub Release ya fue publicada.
- El fixture SBOM y el mensaje esperado del verificador deben coincidir con la versión dinámica del proyecto.
- El registro de estado no debe marcar como completos 16B–16E ni adelantar el Tramo 17.

---

### Task 1: Contrato y metadatos del candidato 1.0.0

**Files:**
- Create: `docs/superpowers/plans/2026-10-25-oraculo-enom-tramo16a.md`
- Modify: `tests/release/test_distribution.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/release/1.0.0-notes.md`
- Modify: `docs/release/1.0.0-status.md`

**Interfaces:**
- Consumes: verificador dinámico de versión y cierre del Tramo 15.
- Produces: candidato versionado coherentemente como `1.0.0`, consumido por el build local del 16B y el SBOM remoto del 16C.

- [x] Agregar `test_release_candidate_version_is_consistent` para exigir versión PEP 621, README, encabezado fechado del changelog, título/notas, estado y SBOM raíz `1.0.0`.
- [x] Ejecutar la prueba contra `0.1.0` y confirmar RED por la versión PEP 621.
- [x] Cambiar `pyproject.toml` a `1.0.0` y actualizar README, changelog, notas y estado sin tocar funciones.
- [x] Actualizar el fixture SBOM y el mensaje esperado que todavía declaran `0.1.0`.
- [x] Ejecutar la prueba nueva y las pruebas de distribución; confirmar GREEN.
- [x] Ejecutar suite completa, `compileall`, `pip check` y `git diff --check`.
- [x] Revisar el diff completo y crear un único checkpoint para bundle y push.
