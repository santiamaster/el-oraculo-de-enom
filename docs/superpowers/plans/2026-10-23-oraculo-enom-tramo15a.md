# El Oráculo de ENOM — Tramo 15A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preparar el changelog y las notas públicas de la futura versión 1.0.0 sin cambiar todavía la versión declarada del proyecto.

**Architecture:** Este subtramo solo agrega documentación editorial basada en funciones ya implementadas y aceptadas. La generación y validación de SBOM y SHA-256 permanecen reservadas para los subtramos 15B–15E.

**Tech Stack:** Markdown, Keep a Changelog, Git y pytest como puerta de regresión.

**Spec:** `docs/superpowers/specs/2026-09-08-oraculo-enom-1.0-release-design.md`

## Global Constraints

- No agregar funciones ni modificar comportamiento de la aplicación.
- Mantener `0.1.0` en `pyproject.toml` y `README.md` hasta el Tramo 16.
- Documentar únicamente funciones y correcciones comprobadas en los Tramos 10–14.
- Indicar que la aplicación no posee firma Authenticode.
- Mantener como obligatoria la eliminación o archivo de la base experimental anterior.
- No modificar el workflow ni introducir CycloneDX en este subtramo.

## Review Focus

- Las notas no deben presentar 1.0.0 como publicada antes del merge, tag y GitHub Release.
- El changelog no debe prometer funciones ajenas al candidato aceptado.
- La instrucción de retirar `datos/historial.db` debe ser visible y explícita.
- La verificación por SHA-256 no debe describirse como sustituto de una firma digital.
- Los nombres previstos del ZIP, SBOM y checksum deben coincidir con el plan de publicación.

---

### Task 1: Changelog del candidato

**Files:**
- Create: `CHANGELOG.md`

- [ ] Crear una sección `Unreleased` con `Added`, `Changed` y `Fixed`.
- [ ] Contrastar cada entrada con README, aceptación Windows y código versionado.
- [ ] Reservar la fecha y encabezado final `1.0.0` para el Tramo 16.

### Task 2: Notas públicas de 1.0.0

**Files:**
- Create: `docs/release/1.0.0-notes.md`

- [ ] Describir funciones, uso del portable y compatibilidad comprobada.
- [ ] Documentar el restablecimiento de la base experimental.
- [ ] Documentar los tres activos previstos y la comprobación SHA-256.
- [ ] Declarar la ausencia de firma Authenticode y la licencia GPL-2.0-or-later.

### Task 3: Registro y verificación

**Files:**
- Modify: `docs/release/1.0.0-status.md`

- [ ] Registrar la subdivisión 15A–15E y marcar únicamente 15A como completo.
- [ ] Validar enlaces Markdown locales, `git diff --check` y la suite completa.
- [ ] Revisar el diff, crear un único commit y generar un bundle verificable.
