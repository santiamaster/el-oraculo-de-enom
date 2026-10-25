# El Oráculo de ENOM — Tramo 15E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inspeccionar los tres activos generados por el último run estable de Windows, registrar evidencia reproducible y cerrar el Tramo 15.

**Architecture:** Descargar el artefacto exacto del run 25 fuera del repositorio, verificar primero el contenedor de Actions y luego validar de forma independiente el ZIP, el SBOM CycloneDX y el checksum. Registrar hashes, tamaños, versiones e inventario sin cambiar todavía la versión `0.1.0` ni modificar el pipeline.

**Tech Stack:** GitHub Actions, ZIP, SHA-256, CycloneDX JSON 1.6, Python 3.12.10.

**Spec:** `docs/superpowers/specs/2026-09-08-oraculo-enom-1.0-release-design.md`

## Global Constraints

- Inspeccionar el artefacto del run 25 asociado exactamente al SHA `475040349663bce52286fb752aaea37ef54fd3a7`.
- El contenedor de Actions debe contener únicamente ZIP, SBOM y checksum con los nombres previstos.
- El SHA-256 registrado debe coincidir con los bytes reales del ZIP portable.
- El SBOM debe ser CycloneDX JSON 1.6 y declarar la aplicación raíz y las dependencias runtime auditadas.
- El portable no debe contener base de desarrollo, fuentes, pruebas ni rutas inseguras.
- Mantener la versión `0.1.0`; el cambio coherente a `1.0.0` pertenece al Tramo 16.
- No fusionar el Pull Request ni publicar etiqueta o GitHub Release.

## Review Focus

- Diferenciar el digest del contenedor de Actions del SHA-256 del ZIP portable.
- Confirmar que el SBOM no inventaría herramientas de desarrollo o construcción.
- Comprobar la integridad CRC y la seguridad de rutas del ZIP, además del contrato automatizado.
- Registrar el SHA exacto del commit y el ID exacto del run y del artefacto.
- Cerrar el Tramo 15 sin adelantar cambios del Tramo 16.

---

### Task 1: Inspección del artefacto remoto

**Files:**
- Inspect: artefacto `12587715550` de la ejecución `40163670517`

**Interfaces:**
- Consumes: pipeline estabilizado en 15D y contrato de validación de 15B.
- Produces: evidencia independiente del conjunto de publicación generado por CI.

- [ ] Descargar el artefacto y comprobar su digest externo contra GitHub Actions.
- [ ] Confirmar que el contenedor contiene exactamente los tres activos previstos.
- [ ] Recalcular el SHA-256 del ZIP y compararlo con el archivo `.sha256`.
- [ ] Ejecutar el verificador integrado contra ZIP, SBOM y checksum.
- [ ] Parsear el SBOM y revisar formato, versión, raíz, dependencias y componentes prohibidos.
- [ ] Revisar estructura, CRC, rutas, licencias y exclusiones del ZIP portable.

### Task 2: Registro y cierre del Tramo 15

**Files:**
- Modify: `docs/release/1.0.0-status.md`

**Interfaces:**
- Consumes: evidencia de Task 1.
- Produces: Tramo 15 completo y Tramo 16 todavía pendiente.

- [ ] Registrar run, SHA, ID y digest del artefacto de Actions.
- [ ] Registrar tamaños y SHA-256 del ZIP y del SBOM.
- [ ] Registrar versión e inventario CycloneDX y resultado de la inspección del portable.
- [ ] Marcar 15E y el Tramo 15 como completos sin cambiar la versión.
- [ ] Ejecutar suite completa, `compileall`, `pip check` y `git diff --check`.
- [ ] Revisar y crear un único checkpoint para push.
