# Informe de correcciones de la revisión final

## Estado

**COMPLETO EN LOCAL.** Los seis findings importantes de
`final-review-findings.md` quedaron corregidos en `feature/initial-app`, con
versión `0.1.0`, suite completa verde, compilación, diff-check, build limpio e
inspección del bundle. No se hizo push, CI, merge, tag, release ni publicación.

Base de esta ola: `ef5228c6d8c2b0a00f8795d9684454046393643a`.

## Findings, archivos y pruebas

### 1. Umbrales enteros arbitrarios en SQLite

Archivos:

- `src/oraculo_enom/domain/integer_text.py`
- `src/oraculo_enom/persistence/thresholds.py`
- `src/oraculo_enom/persistence/database.py`
- `src/oraculo_enom/persistence/history.py`
- `tests/persistence/test_history.py`
- `tests/ui/test_main_window.py`
- `tests/ui/test_combined_dialog.py`

Implementación:

- Los valores dentro de int64 se enlazan como `INTEGER`.
- Los valores fuera de int64 se enlazan como `TEXT` canónico
  `int:<decimal>`, evitando que la afinidad `INTEGER` los convierta en `REAL`.
- El `CHECK` de la columna rechaza marcadores no canónicos y marcadores que
  representan valores que sí caben en int64.
- `values_json` continúa conteniendo exclusivamente valores obtenidos de los
  dados.
- Los registros v1 que guardan el umbral como `INTEGER` siguen hidratando.
- La conversión decimal por bloques evita imponer indirectamente el límite de
  4.300 dígitos de Python; se verificó un umbral de 5.001 dígitos.

Pruebas principales:

- `test_arbitrary_thresholds_and_legacy_integer_records_reopen_exactly`
- `test_sqlite_accepts_canonical_marked_arbitrary_threshold`
- `test_sqlite_rejects_noncanonical_marked_threshold`
- `test_combined_builder_executes_saves_and_reads_arbitrary_threshold`
- `test_threshold_beyond_python_decimal_limit_round_trips_exactly`
- `test_component_threshold_round_trips_beyond_python_decimal_limit`

### 2. Restore/repeat exacto en el flujo simple

Archivos:

- `src/oraculo_enom/ui/integer_spin_box.py`
- `src/oraculo_enom/ui/combined_dialog.py`
- `src/oraculo_enom/ui/main_window.py`
- `tests/ui/test_combined_dialog.py`
- `tests/ui/test_main_window.py`

Implementación:

- El flujo simple y el combinado comparten `ArbitraryIntegerSpinBox`.
- Restore, repeat, edición, step y posterior ejecución conservan el entero sin
  clipping ni `OverflowError`.

Pruebas principales:

- `test_simple_restore_repeat_and_next_roll_preserve_exact_threshold`
- `test_component_threshold_round_trips_beyond_qspinbox_range`
- `test_arbitrary_threshold_editor_keeps_spinbox_ergonomics`
- `test_component_threshold_round_trips_beyond_python_decimal_limit`

### 3. Fallos de lectura no destruyen el estado visible

Archivos:

- `src/oraculo_enom/ui/history_errors.py`
- `src/oraculo_enom/ui/main_window.py`
- `src/oraculo_enom/ui/history_dialog.py`
- `tests/ui/test_main_window.py`
- `tests/ui/test_history_dialog.py`

Implementación:

- El historial reciente obtiene los registros antes de vaciar el layout.
- El diálogo obtiene y valida ambos resultados de búsqueda antes de sustituir
  filtros, filas, selección o detalle.
- Los fallos de apertura/refresco se contienen en UI, preservan la vista previa
  y muestran instrucciones de reintento y conservación de la base.

Pruebas principales:

- `test_recent_read_failure_preserves_visible_roll_and_history`
- `test_failed_history_refresh_preserves_rows_selection_detail_and_filters`
- `test_failed_full_history_open_is_contained_and_can_be_retried`

### 4. Hidratación estricta y error controlado

Archivos:

- `src/oraculo_enom/persistence/history.py`
- `tests/persistence/test_history.py`

Implementación:

- Se validan JSON estricto, array raíz, enteros exactos (sin booleanos), conteo
  y rango de valores.
- Se validan posiciones, componentes, tipos, comparadores, umbrales, título,
  fecha ISO canónica, `show_sum`, subtotales y total.
- `analyze()` reconstruye el resultado canónico; subtotales, total y matches no
  se confían a los datos almacenados.
- Filas corruptas se traducen a un `OSError` accionable sobre datos
  inconsistentes y copia de `datos/historial.db`.
- Las lecturas no escriben; si `update_title()` descubre corrupción después del
  `UPDATE`, la transacción revierte.

Pruebas principales:

- `test_corrupt_values_are_controlled_and_never_mutate_storage` (32 casos)
- `test_corrupt_aggregate_is_controlled_and_never_mutates_storage` (16 casos)
- `test_retitle_of_corrupt_record_rolls_back_instead_of_committing`

### 5. Título principal autoritativo al reabrir el builder

Archivos:

- `src/oraculo_enom/ui/main_window.py`
- `tests/ui/test_main_window.py`

Implementación:

- Cada apertura llama `set_title()` con el título principal vigente.
- El mismo objeto de diálogo y sus componentes/show-sum se conservan; cancelar
  no ejecuta ni persiste.

Prueba:

- `test_reopening_combined_builder_syncs_main_title_and_preserves_components`

### 6. Retitulado de la tirada activa actualiza copy/repeat

Archivos:

- `src/oraculo_enom/ui/history_dialog.py`
- `src/oraculo_enom/ui/main_window.py`
- `tests/ui/test_main_window.py`

Implementación:

- La ventana conserva el ID devuelto por `HistoryRepository.add()`.
- El diálogo emite el `RollRecord` actualizado después de un retitulado
  exitoso.
- La ventana sustituye `_last_request` y `_last_result` únicamente cuando el ID
  editado coincide con la tirada activa.

Pruebas:

- `test_retitle_of_active_last_roll_updates_main_copy_and_repeat`
- `test_retitle_of_older_roll_does_not_replace_active_main_copy_state`

## Evidencia RED/GREEN

### Evidencia heredada no recuperable

- Findings 1–3 ya tenían implementación y tests parciales al reanudar. No se
  inventa evidencia RED: sus ejecuciones RED originales no estaban disponibles
  en esta sesión. Se inspeccionó el diff y se observó su GREEN conjunto.
- El controller informó como punto de partida para finding 4: `83 passed, 48
  failed`; esa cifra se reprodujo exactamente al iniciar esta reanudación.

### Evidencia observada en esta reanudación

- Finding 4 RED: `83 passed, 48 failed`; los 48 fallos correspondían a las
  parametrizaciones de corrupción/hidratación y al rollback del retitulado.
- Finding 4 GREEN inicial: `tests/persistence/test_history.py` → `83 passed`.
- Fecha estricta adicional RED: `15 passed, 1 failed` porque
  `datetime.fromisoformat()` aceptaba una fecha sin hora.
- Fecha estricta adicional GREEN: `16 passed`.
- Finding 5 RED: `1 failed`, el builder devolvía `Título inicial` en vez de
  `Título vigente`.
- Finding 5 GREEN: `1 passed`.
- Finding 6 RED: `1 failed`, copy conservaba `Título original` después del
  retitulado.
- Finding 6 GREEN: `2 passed`, incluyendo la protección frente a retitular un
  registro anterior.
- Borde de entero de 5.001 dígitos RED: `2 failed`; persistencia y editor
  chocaban con el límite de conversión decimal de Python.
- Borde de entero de 5.001 dígitos GREEN: `2 passed` y representación cruda
  `int:1` seguida de 5.000 ceros.
- Focal final de findings: `182 passed` antes de los tres casos de borde
  adicionales; todos esos casos también quedaron incluidos en la suite final.

## Comandos y resultados finales

```text
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
229 passed in 4.22s

.venv/bin/python -m compileall -q src tests
código 0

git diff --check ef5228c6d8c2b0a00f8795d9684454046393643a
código 0

.venv/bin/python -m PyInstaller El-Oraculo-de-ENOM.spec --clean --noconfirm
código 0; PyInstaller 6.22.2; Build complete
```

Inspección de `dist/El Oraculo de ENOM/`:

- `El Oraculo de ENOM` existe, tiene permiso ejecutable y es ELF x86-64.
- Tamaño del bundle local: 191 MiB.
- Cero `historial.db`.
- Cero directorios `tests` o `src`.
- Cero archivos `.py`.
- `build/` y `dist/` permanecen fuera del commit.

Versión verificada:

- `pyproject.toml`: `0.1.0`.
- `README.md`: `0.1.0`.

## Decisiones y compatibilidad

- Se conserva `SCHEMA_VERSION = 1`; no se añadió migración.
- La representación marcada solo se usa fuera de int64. Esto mantiene la forma
  histórica `INTEGER` para registros v1 válidos y evita afinidad `REAL` para
  enteros arbitrarios.
- No se reutiliza `values_json` para metadatos.
- La hidratación es validación de solo lectura; ninguna recuperación altera o
  elimina filas corruptas.
- El mensaje de corrupción pide conservar una copia, de modo que un usuario
  pueda pedir ayuda sin perder evidencia.
- La sincronización de título del builder cambia la expectativa anterior: al
  abrir, el título principal es autoritativo; el borrador de componentes sigue
  siendo temporal y persistente durante la sesión.
- El retitulado se propaga por identidad de registro, no por posición temporal
  ni por igualdad estructural.

## Archivos

Implementación y tests incluidos en el commit:

- `src/oraculo_enom/domain/integer_text.py`
- `src/oraculo_enom/persistence/database.py`
- `src/oraculo_enom/persistence/history.py`
- `src/oraculo_enom/persistence/thresholds.py`
- `src/oraculo_enom/ui/combined_dialog.py`
- `src/oraculo_enom/ui/history_dialog.py`
- `src/oraculo_enom/ui/history_errors.py`
- `src/oraculo_enom/ui/integer_spin_box.py`
- `src/oraculo_enom/ui/main_window.py`
- `tests/persistence/test_history.py`
- `tests/ui/test_combined_dialog.py`
- `tests/ui/test_history_dialog.py`
- `tests/ui/test_main_window.py`

## Commits

- `f9f15ac38905e3efc3b51aaaed34ace9e28f36d1` — `fix: address final review findings`
- El presente informe se agrega en un commit documental separado posterior al
  commit de implementación.

## Self-review

- Se releyeron los seis findings contra spec, plan y diff final.
- Cada ruta nueva tiene cobertura observable; no se prueban mocks como resultado.
- Las escrituras siguen usando una única transacción y rollback.
- Los reemplazos visuales ocurren solo después de lecturas completas.
- El estado de última tirada se actualiza solo después de persistencia exitosa.
- El marcador decimal y su parser tienen pruebas contra valores int64, formas
  inválidas, signos, extremos y un valor superior al límite decimal de Python.
- No se detectaron findings abiertos dentro del alcance local.

## Concerns

- El build local es Linux, no el portable Windows entregable.
- PyInstaller emitió avisos por bibliotecas XCB opcionales ausentes en el
  contenedor (`libxkbcommon-x11`, `libxcb-*`). El build offscreen y la suite Qt
  terminaron correctamente, pero esto no sustituye la aceptación en Windows.
- Por instrucción expresa quedan sin ejecutar push, CI Windows, descarga e
  inspección de su ZIP y aceptación manual.
