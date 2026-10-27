# El Oráculo de ENOM — Tramo 16D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Asociar una aceptación manual focalizada en Windows al artefacto remoto `1.0.0` generado para el commit exacto `06e514f3f607e2a30fd8c6d13fc0a75e26fc1d3c`.

**Architecture:** Se reutiliza la aceptación funcional completa del Tramo 13 porque desde entonces no cambió el código de la aplicación. El 16D comprueba únicamente los riesgos introducidos por el empaquetado, las licencias, los metadatos de distribución y el cambio de versión: integridad del ZIP, extracción limpia, arranque, escritura local, tirada mínima, historial persistente y presencia de avisos legales.

**Tech Stack:** Windows 10 x64, PowerShell, GitHub Actions, ZIP portable, SQLite y SHA-256.

**Spec:** `docs/superpowers/specs/2026-09-08-oraculo-enom-1.0-release-design.md`

## Global Constraints

- Ejecutar únicamente el Tramo 16D y detenerse al completar o bloquear su aceptación.
- Probar el artefacto de la ejecución `40429058864`, asociado exactamente al commit `06e514f3f607e2a30fd8c6d13fc0a75e26fc1d3c`.
- Exigir que el ZIP portable interior tenga SHA-256 `d01efb4745640c95fc596b99f05741b1a84b4a57b9f4812303f5f5a952be5eb1`.
- Usar una carpeta de extracción nueva, local y con permisos de escritura; no reutilizar `datos/historial.db` de compilaciones anteriores.
- No repetir la aceptación exhaustiva del Tramo 13: no hubo cambios en `src/` desde el candidato aceptado.
- Un fallo funcional o de empaquetado bloquea el tramo y debe conservar sus pasos de reproducción.
- No hacer push, merge, tag ni GitHub Release durante la prueba manual.

## Review Focus

- Evitar probar el artefacto del run 28 o cualquier ZIP anterior al commit `06e514f`.
- No confundir el SHA-256 del contenedor de Actions con el SHA-256 del ZIP portable interior.
- Una base experimental preexistente puede falsear la prueba de creación y persistencia; la carpeta debe empezar limpia.
- El ejecutable y `_internal` deben permanecer juntos; mover solo el `.exe` no constituye una prueba válida.
- La aceptación debe registrar resultados observados por el tester, no inferirlos del workflow verde.

---

### Task 1: Revalidar manualmente el candidato final en Windows

**Files:**
- Create: `docs/superpowers/plans/2026-10-26-oraculo-enom-tramo16d.md`
- Modify after manual PASS: `docs/acceptance/1.0.0-windows.md`
- Modify after manual PASS: `docs/release/1.0.0-status.md`

**Interfaces:**
- Consumes: artefacto `12701138100` del run `40429058864` y aceptación funcional completa del Tramo 13.
- Produces: evidencia manual vinculada al commit y al hash exactos que el Tramo 16E congelará.

- [x] **Step 1: Resolver y auditar el artefacto exacto**

Confirmar run, commit, job y artefacto; descargar el contenedor, comprobar su digest de Actions, CRC e inventario de tres activos, y ejecutar el verificador integrado sobre ZIP, SBOM y checksum.

- [x] **Step 2: Verificar el checksum en Windows**

Ejecutar los comandos publicados en `docs/release/1.0.0-notes.md` y exigir `True`. Confirmar además que `$Actual` sea `d01efb4745640c95fc596b99f05741b1a84b4a57b9f4812303f5f5a952be5eb1`.

- [x] **Step 3: Probar extracción y arranque limpios**

Extraer el ZIP portable interior en una carpeta nueva y escribible, confirmar que inicialmente no existe `datos/historial.db`, ejecutar `El Oraculo de ENOM.exe` y comprobar que la aplicación abre sin error ni bloqueo. Confirmar luego la creación de `datos/historial.db` junto al portable.

- [x] **Step 4: Ejecutar el humo funcional focalizado**

Realizar una tirada simple y una combinada con título y suma; comprobarlas en el historial, cerrar la aplicación, abrirla nuevamente y confirmar que ambas persisten. Verificar también que `LICENSE`, `THIRD_PARTY_NOTICES.md` y `licenses/` estén presentes junto al ejecutable.

- [x] **Step 5: Registrar la aceptación observada**

Agregar al registro de aceptación la fecha, tester, entorno, resolución/escala, run, commit, hashes y resultado de cada control. Marcar 16D como completo en el estado de release únicamente si todos los controles son PASS.

- [x] **Step 6: Verificar y crear el checkpoint documental**

Run: `python -m pytest -q && python -m compileall -q src tests scripts && git diff --check`

Expected: 312 pruebas aprobadas, compilación sin errores y diff sin defectos.

Commit previsto: `docs: record final Windows acceptance`

- [ ] **Step 7: Detenerse**

Entregar el bundle del checkpoint para que el usuario actualice `feature/initial-app`. No comenzar el Tramo 16E.
