# El Oráculo de ENOM — Tramo 15D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar las advertencias de runtimes obsoletos del workflow de Windows y demostrar la estabilidad remota del pipeline que genera los metadatos de publicación.

**Architecture:** Conservar sin cambios la construcción, el SBOM, el checksum y el verificador introducidos en 15C. Actualizar únicamente las acciones oficiales que todavía usan Node.js 20, cubrir sus versiones mediante una prueba de contrato y validar el resultado en un nuevo run del Pull Request antes de cerrar 15D.

**Tech Stack:** GitHub Actions, Node.js 24, Python 3.12.10, pytest.

**Spec:** `docs/superpowers/specs/2026-09-08-oraculo-enom-1.0-release-design.md`

## Global Constraints

- Mantener Python `3.12.10` y las versiones auditadas de las dependencias de la aplicación.
- Mantener los tres activos y su validación antes de `upload-artifact`.
- No inspeccionar todavía el contenido descargado del artefacto; corresponde al 15E.
- No modificar README ni la versión `0.1.0`; corresponden a tramos posteriores.
- No fusionar el Pull Request ni crear una etiqueta o GitHub Release.

## Review Focus

- El workflow no debe conservar referencias a acciones basadas en Node.js 20.
- El cambio de versiones no debe alterar nombres, rutas ni orden de los tres activos.
- La ejecución remota debe usar el SHA exacto de la rama y finalizar sin advertencias de Node.js 20.
- La carga debe continuar fallando si falta cualquiera de los tres archivos.
- La inspección interna del ZIP, SBOM y checksum se reserva para el 15E.

---

### Task 1: Actualizar las acciones oficiales

**Files:**
- Modify: `.github/workflows/build-windows.yml`
- Modify: `tests/release/test_distribution.py`
- Modify: `docs/release/1.0.0-status.md`

**Interfaces:**
- Consumes: pipeline de tres activos implementado en 15C.
- Produces: workflow equivalente sobre acciones oficiales Node.js 24.

- [ ] Agregar una prueba que exija `actions/checkout@v7`, `actions/setup-python@v7` y `actions/upload-artifact@v7`, y rechace las versiones anteriores.
- [ ] Ejecutar la prueba y confirmar RED contra el workflow del 15C.
- [ ] Actualizar las tres referencias sin modificar el resto del pipeline.
- [ ] Ejecutar las pruebas de distribución y confirmar GREEN.
- [ ] Registrar el hallazgo del run 23 y dejar 15D en validación remota.
- [ ] Ejecutar la suite completa, `compileall`, `pip check` y `git diff --check`; revisar y crear el checkpoint para push.

### Task 2: Validar el run remoto y cerrar 15D

**Files:**
- Modify: `docs/release/1.0.0-status.md`

**Interfaces:**
- Consumes: nuevo run del Pull Request sobre el commit de Task 1.
- Produces: evidencia de CI estabilizado y 15D completo; 15E permanece pendiente.

- [ ] Confirmar SHA, estado y conclusión del nuevo run.
- [ ] Revisar pasos y registro para comprobar la ausencia de la advertencia de Node.js 20.
- [ ] Confirmar que el artefacto contiene tres archivos publicados, sin inspeccionar todavía su contenido.
- [ ] Registrar run, SHA y resultado; marcar 15D completo y conservar 15E pendiente.
- [ ] Ejecutar las comprobaciones documentales y crear el checkpoint final del subtramo.
