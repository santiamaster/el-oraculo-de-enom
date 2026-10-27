# El Oráculo de ENOM — Tramo 16C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Descargar y auditar el artefacto nativo de Windows generado por GitHub Actions para el SHA exacto del candidato `1.0.0` del Tramo 16B.

**Architecture:** El subtramo resuelve el run de pull request por SHA, descarga su contenedor fuera del repositorio y verifica en conjunto el ZIP portable, el SBOM CycloneDX y el checksum. Solo la evidencia textual se versiona; la ejecución funcional manual del portable queda reservada para el 16D.

**Tech Stack:** GitHub Actions, Python 3.12.10, ZIP, CycloneDX JSON 1.6, SHA-256 y `scripts/verify_distribution.py`.

**Spec:** `docs/superpowers/specs/2026-09-08-oraculo-enom-1.0-release-design.md`

## Global Constraints

- Ejecutar únicamente el Tramo 16C y detenerse al completarlo.
- Exigir que remoto, pull request, run y artefacto correspondan al SHA `9a3b9400e0b6533be73244923de7aa246cc75f0d`.
- Aceptar únicamente un run de pull request concluido en `success`.
- Descargar y extraer el artefacto fuera del repositorio; no versionar ZIP, SBOM, checksum, ejecutable ni temporales.
- Exigir exactamente `El-Oraculo-de-ENOM-Windows.zip`, `El-Oraculo-de-ENOM-Windows.sbom.cdx.json` y `El-Oraculo-de-ENOM-Windows.zip.sha256`.
- Validar integridad, rutas seguras, ausencia de contenidos prohibidos, versión raíz `1.0.0` y PySide6 `6.11.2`.
- No ejecutar ni afirmar aceptación manual en Windows; corresponde al 16D.
- No hacer push, merge, tag ni GitHub Release.

## Review Focus

- No aceptar un run exitoso perteneciente a otro SHA o evento.
- No confundir el digest del contenedor de Actions con el SHA-256 del ZIP portable.
- Rechazar activos faltantes, adicionales, duplicados o renombrados.
- El SBOM debe inventariar el runtime y excluir herramientas de desarrollo.
- El registro debe marcar solo 16C como completo y mantener 16D–16E pendientes.

---

### Task 1: Inspeccionar y registrar el artefacto remoto 1.0.0

**Files:**
- Create: `docs/superpowers/plans/2026-10-26-oraculo-enom-tramo16c.md`
- Modify: `docs/release/1.0.0-status.md`

**Interfaces:**
- Consumes: SHA remoto y candidato local del 16B; contrato integrado de `validate_release_assets`.
- Produces: hash e inventario exactos del artefacto Windows que el 16D deberá probar manualmente.

- [x] Confirmar rama remota, PR y run exitoso asociados al SHA exacto del 16B; revisar que todos los pasos del job estén aprobados.
- [x] Resolver el artefacto `El-Oraculo-de-ENOM-Windows`, registrar identificador, tamaño y digest de Actions, y descargarlo fuera del repositorio.
- [x] Comprobar la integridad y el inventario del contenedor de Actions; exigir exactamente los tres activos previstos.
- [x] Ejecutar el verificador integrado sobre ZIP, SBOM y checksum, y recomputar los hashes de los tres archivos.
- [x] Inspeccionar el ZIP portable y el SBOM: ejecutable PE32+ x86-64, rutas seguras, licencias, cero contenidos prohibidos, raíz `1.0.0`, runtime esperado y cero herramientas de desarrollo.
- [x] Registrar run, artefacto, tamaños, hashes y resultados en `docs/release/1.0.0-status.md`; marcar solo 16C como completo.
- [x] Ejecutar suite completa, bytecode, `pip check`, verificador, `git diff --check`; revisar y crear un único checkpoint.
