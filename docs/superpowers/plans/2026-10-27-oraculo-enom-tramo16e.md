# El Oráculo de ENOM — Tramo 16E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Congelar el candidato `1.0.0`, completar la revisión final del pull request y dejar una única puerta pendiente: la integración y publicación del Tramo 17.

**Architecture:** El subtramo no modifica código, dependencias, empaquetado ni comportamiento. Contrasta el HEAD remoto aceptado con GitHub Actions, revisa el pull request completo, actualiza sus metadatos obsoletos y registra un checkpoint documental final; tras su push, el workflow del nuevo HEAD debe quedar verde antes del merge.

**Tech Stack:** Git, GitHub Pull Requests, GitHub Actions, Python 3.12 y documentación Markdown.

**Spec:** `docs/superpowers/specs/2026-09-08-oraculo-enom-1.0-release-design.md`

## Global Constraints

- Ejecutar únicamente el Tramo 16E y detenerse antes de mergear, etiquetar o publicar.
- Partir del commit aceptado `2937549af561b8452862434524099e4e3f1f71c1` y exigir que sea el HEAD remoto y del PR #1.
- Confirmar que el workflow del HEAD aceptado terminó en `success` y que todos sus pasos aprobaron.
- No modificar dependencias, workflow, especificación de PyInstaller ni materiales
  de distribución. `src/` y pruebas solo pueden cambiar para corregir un defecto
  reproducido y clasificado como bloqueante durante la revisión final.
- Exigir que el PR permanezca abierto, no sea borrador, sea fusionable y no tenga revisiones ni hilos pendientes.
- El commit documental de cierre debe recibir un workflow verde antes de autorizar el Tramo 17.
- No hacer push desde este entorno; entregar un bundle para actualización fast-forward.

## Review Focus

- No confundir el run exitoso del commit aceptado con el workflow que generará el checkpoint documental del 16E.
- Rechazar cualquier diferencia local o remota no registrada después de la aceptación Windows.
- Mantener el Tramo 17 pendiente: este subtramo no autoriza merge, tag ni GitHub Release.
- Evitar que el título o cuerpo del PR sigan describiendo `v0.1.0`, 51 pruebas o CI pendiente.
- Confirmar que la rama pueda integrarse por fast-forward local y que GitHub la declare fusionable.

---

### Task 1: Congelar y revisar el candidato previo al merge

**Files:**
- Create: `docs/superpowers/plans/2026-10-27-oraculo-enom-tramo16e.md`
- Modify: `docs/release/1.0.0-status.md`

**Interfaces:**
- Consumes: aceptación Windows del 16D, HEAD remoto `2937549`, run `40590908951` y estado del PR #1.
- Produces: checkpoint documental final que el Tramo 17 verificará, integrará y publicará.

- [x] **Step 1: Confirmar rama, PR y workflow del candidato aceptado**

Verificar que remoto y PR apunten a `2937549`, que el PR esté abierto, no sea borrador y sea fusionable, y que el run `40590908951` haya terminado en `success` con todos sus pasos aprobados.

- [x] **Step 2: Revisar comentarios y actualizar los metadatos del PR**

Confirmar que no existan revisiones ni hilos pendientes. Actualizar el título a `Publicar El Oráculo de ENOM 1.0.0` y reemplazar la descripción experimental por el resumen, verificación y materiales reales de `1.0.0`.

- [x] **Step 3: Ejecutar la puerta local final**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest -q && python -m pip check && python -m compileall -q src tests scripts && git diff --check && git diff --check origin/main...HEAD -- . ':(exclude)licenses/**'`

Expected: 312 pruebas aprobadas, dependencias íntegras, compilación sin errores,
diff propio sin defectos y diff histórico sin defectos fuera de los textos de
licencia de terceros conservados literalmente.

- [x] **Step 4: Revisar el rango completo del pull request**

Inspeccionar `origin/main...HEAD`, confirmar que la versión y los materiales de publicación sean coherentes y solicitar una revisión independiente. Resolver cualquier hallazgo Critical o Important antes del cierre.

La revisión independiente no encontró defectos Critical. Encontró un defecto
Important en la conversión a texto de umbrales con más de 4.300 dígitos y un
defecto Minor diferido en el límite `date.max` del filtro **Hasta**.

- [x] **Step 5: Corregir el hallazgo bloqueante con RED→GREEN**

Agregar regresiones para copia, renderizado simple y combinado, detalle de
historial y repetición con umbrales de 5.001 dígitos. Confirmar RED por
`ValueError`, reutilizar `format_integer()` en todos los puntos de presentación y
confirmar GREEN más la suite completa.

- [ ] **Step 6: Registrar el checkpoint de revalidación**

Actualizar `docs/release/1.0.0-status.md` con el estado del PR, el run verde del
candidato anterior, el hallazgo corregido y la necesidad de generar un nuevo
artefacto. Mantener 16E en revalidación y el Tramo 17 pendiente.

- [ ] **Step 7: Crear el checkpoint y entregar el bundle**

Commits previstos:

- `fix: render arbitrary filter thresholds`
- `release: record 1.0.0 revalidation checkpoint`

Entregar el bundle para actualización fast-forward. No declarar congelación
definitiva hasta validar el workflow, artefacto y humo Windows del nuevo HEAD.

- [ ] **Step 8: Detenerse para el push**

No fusionar el PR, crear `v1.0.0` ni publicar la GitHub Release.

---

### Task 2: Revalidar el candidato corregido después del push

**Files:**
- Modify: `docs/release/1.0.0-status.md`
- Modify: `docs/acceptance/1.0.0-windows.md`

**Interfaces:**
- Consumes: workflow y artefacto nativo del checkpoint corregido del Task 1.
- Produces: candidato congelado y autorizado para iniciar el Tramo 17.

- [ ] **Step 1: Verificar CI y artefacto del nuevo HEAD**

Exigir workflow `success`, todos los pasos verdes, contrato ZIP/SBOM/SHA válido y
ausencia de contenidos prohibidos.

- [ ] **Step 2: Ejecutar aceptación focalizada en Windows**

Comprobar inicio, tirada con filtro, copia, historial, repetición y persistencia
usando exclusivamente el nuevo ZIP.

- [ ] **Step 3: Registrar la congelación definitiva**

Registrar nuevo HEAD, run, hashes y aceptación. Marcar 16E y el Tramo 16 como
completos; mantener el Tramo 17 pendiente.

- [ ] **Step 4: Confirmar CI verde del registro final**

Después del último checkpoint documental, exigir que su propio workflow quede
verde y que el PR siga abierto, fusionable y sin hilos pendientes.

- [ ] **Step 5: Detenerse**

No fusionar el PR, crear `v1.0.0` ni publicar la GitHub Release. Esperar autorización explícita para el Tramo 17.
