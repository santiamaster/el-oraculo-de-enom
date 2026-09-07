# El Oráculo de ENOM — General Dice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unificar tiradas simples y combinadas, agregar títulos editables y filtros por tipo de dado, y establecer el esquema SQLite definitivo previo a `1.0.0` sin recargar la interfaz principal.

**Architecture:** Toda tirada será un `RollRequest` inmutable compuesto por uno a diez `RollComponentRequest`; una tirada simple tendrá un solo componente. El motor, el análisis, el portapapeles y SQLite consumirán el mismo modelo. La ventana principal conservará el flujo rápido y delegará la edición avanzada a `CombinedRollDialog`.

**Tech Stack:** Python 3.12+, PySide6 6.8–6.x, SQLite, pytest, pytest-qt, PyInstaller y GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-07-oraculo-enom-general-dice-design.md`

## Global Constraints

- El título es opcional, se recorta en los extremos y admite como máximo 150 caracteres.
- Cada componente admite de 1 a 1.000 dados y de 2 a 1.000 caras.
- Cada solicitud admite de 1 a 10 cantidades de caras diferentes y como máximo 1.000 dados totales.
- Los dados rápidos son `d4`, `d6`, `d8`, `d10`, `d12`, `d16`, `d20`, `d50` y `d100`.
- Cada componente admite como máximo un filtro formado por comparador y umbral conjuntamente.
- Si `show_sum` es falso, `subtotal` y `total` son `None` y se persisten como `NULL`.
- El historial experimental no se migra; una base pre-`1.0.0` incompatible se rechaza con instrucciones para retirarla manualmente.
- Ninguna operación puede borrar silenciosamente una base existente.
- Todas las escrituras de una tirada y sus componentes son atómicas.
- La versión del paquete permanece en `0.1.0` durante esta implementación.

---

## File Map

### Domain

- `src/oraculo_enom/domain/models.py`: solicitudes y resultados inmutables, propiedades canónicas y límites compartidos.
- `src/oraculo_enom/domain/dice.py`: validación y generación de valores para todos los componentes.
- `src/oraculo_enom/domain/analysis.py`: coincidencias, subtotales opcionales y total global opcional.

### Persistence and services

- `src/oraculo_enom/persistence/database.py`: esquema versionado, claves foráneas y detección del esquema experimental.
- `src/oraculo_enom/persistence/history.py`: escritura/lectura atómica, búsqueda y edición de títulos.
- `src/oraculo_enom/services/clipboard.py`: representación textual simple y combinada.
- `src/oraculo_enom/services/paths.py`: mensaje accionable para bases incompatibles.

### UI

- `src/oraculo_enom/ui/main_window.py`: flujo simple, título, repetición contextual e integración del diálogo.
- `src/oraculo_enom/ui/combined_dialog.py`: constructor avanzado y estado temporal de una combinación.
- `src/oraculo_enom/ui/history_dialog.py`: notación combinada, búsqueda por título y edición.
- `src/oraculo_enom/ui/theme.py`: estilos de los controles nuevos.

### Tests

- `tests/domain/test_models.py`, `test_dice.py`, `test_analysis.py`
- `tests/persistence/test_database.py`, `test_history.py`
- `tests/services/test_clipboard.py`, `test_paths.py`
- `tests/ui/test_main_window.py`, `test_combined_dialog.py`, `test_history_dialog.py`, `test_app.py`

---

### Task 1: Unified immutable roll model

**Files:**
- Modify: `src/oraculo_enom/domain/models.py`
- Modify: `src/oraculo_enom/domain/dice.py`
- Modify: `tests/domain/test_models.py`
- Modify: `tests/domain/test_dice.py`

**Interfaces:**
- Produces: `RollComponentRequest`, `RollRequest`, `roll_values()` and shared constants.
- Consumed by: Tasks 2–7.

- [ ] **Step 1: Replace scalar-model tests with component-model tests**

Add tests that construct:

```python
component = RollComponentRequest(2, 6, Comparator.GREATER_OR_EQUAL, 5)
request = RollRequest((component, RollComponentRequest(1, 20)), True, "Ataque")

assert component.notation == "2d6"
assert request.notation == "2d6 + 1d20"
assert request.total_count == 3
assert request.is_combined
assert request.title == "Ataque"
```

Also assert frozen instances reject assignment, one component reports `is_combined is False`, and title normalization removes only exterior whitespace.

- [ ] **Step 2: Add failing boundary and validation tests**

Cover exact valid boundaries `1d2`, `1000d1000`, ten different sides totaling 1.000 dice, and these exact invalid cases:

```python
((), "La tirada debe contener al menos un tipo de dado")
(11 distinct components, "La tirada admite hasta 10 tipos de dado")
(total count 1001, "La cantidad total de dados debe estar entre 1 y 1.000")
(duplicate sides, "Cada tipo de dado debe aparecer una sola vez")
(title length 151, "El título admite hasta 150 caracteres")
(comparator without threshold, "El filtro necesita un comparador y un umbral")
```

- [ ] **Step 3: Run the focused tests and confirm RED**

Run:

```bash
python -m pytest tests/domain/test_models.py tests/domain/test_dice.py -v
```

Expected: failures because `RollComponentRequest` and the aggregate request do not exist.

- [ ] **Step 4: Implement the immutable types and validation**

Use these public shapes:

```python
MAX_TITLE_LENGTH = 150
MAX_COMPONENTS = 10
MAX_TOTAL_DICE = 1_000
MIN_SIDES = 2
MAX_SIDES = 1_000

@dataclass(frozen=True, slots=True)
class RollComponentRequest:
    count: int
    sides: int
    comparator: Comparator | None = None
    threshold: int | None = None

    @property
    def notation(self) -> str: ...

@dataclass(frozen=True, slots=True)
class RollRequest:
    components: tuple[RollComponentRequest, ...]
    show_sum: bool
    title: str = ""

    @property
    def notation(self) -> str: ...
    @property
    def total_count(self) -> int: ...
    @property
    def is_combined(self) -> bool: ...
```

Normalize `title` in `RollRequest.__post_init__` with `object.__setattr__`. Keep range and relationship checks in `validate_request(request)` so invalid requests can be constructed and rejected at the engine boundary.

- [ ] **Step 5: Adapt generation to all components**

Expose:

```python
def roll_values(
    request: RollRequest,
    randbelow: Callable[[int], int] = secrets.randbelow,
) -> tuple[tuple[int, ...], ...]:
```

Validate once, then return one tuple per component in request order.

- [ ] **Step 6: Run the focused domain tests**

```bash
python -m pytest tests/domain/test_models.py tests/domain/test_dice.py -q
```

Expected: all model and generation tests pass. Tasks 2–7 adapt the dependent layers before the next complete-suite gate.

- [ ] **Step 7: Commit the domain model**

```bash
git add src/oraculo_enom/domain/models.py src/oraculo_enom/domain/dice.py tests/domain/test_models.py tests/domain/test_dice.py
git commit -m "feat: model multi-die roll requests"
```

---

### Task 2: Component analysis and copy formatting

**Files:**
- Modify: `src/oraculo_enom/domain/models.py`
- Modify: `src/oraculo_enom/domain/analysis.py`
- Modify: `src/oraculo_enom/services/clipboard.py`
- Modify: `tests/domain/test_analysis.py`
- Modify: `tests/services/test_clipboard.py`

**Interfaces:**
- Consumes: `RollRequest` and `RollComponentRequest` from Task 1.
- Produces: `RollComponentResult`, `RollResult`, `analyze()` and `format_roll()`.
- Consumed by: persistence and UI tasks.

- [ ] **Step 1: Write failing analysis tests**

Use deterministic values:

```python
request = RollRequest(
    (
        RollComponentRequest(2, 6, Comparator.GREATER_OR_EQUAL, 5),
        RollComponentRequest(3, 20, Comparator.GREATER_THAN, 12),
    ),
    show_sum=True,
    title="Ataque combinado de Arhat",
)
result = analyze(request, ((4, 6), (3, 15, 19)), created_at=fixed_time)
```

Assert component subtotals `(10, 37)`, matches `((6,), (15, 19))`, global total `47`, order preservation and timestamp. Add a second test with `show_sum=False` asserting every subtotal and total are `None`.

- [ ] **Step 2: Write failing structural validation tests**

Assert `analyze()` rejects a different number of value groups, wrong value count within a group, values below 1, and values greater than that component's sides.

- [ ] **Step 3: Write failing clipboard tests**

Verify exact output for the combined example in the spec, a simple titled roll, an untitled roll, filters without sums, and a simple roll preserving `Suma: N` instead of redundant subtotal/global lines.

- [ ] **Step 4: Run tests and confirm RED**

```bash
python -m pytest tests/domain/test_analysis.py tests/services/test_clipboard.py -v
```

- [ ] **Step 5: Implement result types and analysis**

Add:

```python
@dataclass(frozen=True, slots=True)
class RollComponentResult:
    request: RollComponentRequest
    values: tuple[int, ...]
    subtotal: int | None
    matches: tuple[int, ...]

@dataclass(frozen=True, slots=True)
class RollResult:
    request: RollRequest
    components: tuple[RollComponentResult, ...]
    total: int | None
    created_at: datetime
```

Implement `analyze(request, values_by_component, created_at=None)` without calculating retained subtotal/total values when `show_sum` is false.

- [ ] **Step 6: Implement exact copy formatting**

Build lines from component results. Prefix the optional title, include per-component filters, use per-component subtotals only for combined rolls, and append one global sum for combinations.

- [ ] **Step 7: Verify and commit**

```bash
python -m pytest tests/domain tests/services/test_clipboard.py -q
git add src/oraculo_enom/domain src/oraculo_enom/services/clipboard.py tests/domain tests/services/test_clipboard.py
git commit -m "feat: analyze and format combined rolls"
```

---

### Task 3: Definitive versioned SQLite schema

**Files:**
- Modify: `src/oraculo_enom/persistence/database.py`
- Modify: `src/oraculo_enom/services/paths.py`
- Create: `tests/persistence/test_database.py`
- Modify: `tests/services/test_paths.py`

**Interfaces:**
- Consumes: standard `sqlite3` and portable database paths.
- Produces: `connect(database: Path) -> sqlite3.Connection`, `SCHEMA_VERSION = 1`, `SCHEMA_RESET_REQUIRED`.
- Consumed by: Task 4 repository.

- [ ] **Step 1: Write failing fresh-schema tests**

Assert a new connection creates `rolls` and `roll_components`, enables `PRAGMA foreign_keys`, sets `PRAGMA user_version` to `1`, applies the checks described by the spec, and creates indexes for date, title, `roll_id` and sides.

- [ ] **Step 2: Write failing incompatible-schema test**

Create the old `rolls` table with `count`, `sides` and `values_json`, leave `user_version = 0`, then assert `connect()` raises:

```text
El historial pertenece a una versión de prueba anterior. Cerrá la aplicación y mové o eliminá datos/historial.db antes de continuar.
```

Assert the old database file and its row remain unchanged after the failure.

- [ ] **Step 3: Write failing constraint and cascade tests**

Use direct SQL to prove invalid title length, invalid booleans, incomplete filters and inconsistent nullable sums are rejected; prove deleting a roll cascades to its components.

- [ ] **Step 4: Run focused tests and confirm RED**

```bash
python -m pytest tests/persistence/test_database.py tests/services/test_paths.py -v
```

- [ ] **Step 5: Implement schema creation and recognition**

On connect:

1. enable foreign keys;
2. inspect `user_version` and existing tables;
3. create version 1 only for an empty database;
4. reject version 0 with existing application tables;
5. reject versions greater than supported;
6. preserve the existing actionable wrapper for SQLite I/O errors.

Use a transaction and set `PRAGMA user_version = 1` only after all DDL succeeds.

- [ ] **Step 6: Verify and commit**

```bash
python -m pytest tests/persistence/test_database.py tests/services/test_paths.py -q
git add src/oraculo_enom/persistence/database.py src/oraculo_enom/services/paths.py tests/persistence/test_database.py tests/services/test_paths.py
git commit -m "feat: establish versioned roll history schema"
```

---

### Task 4: Atomic history repository and title editing

**Files:**
- Modify: `src/oraculo_enom/persistence/history.py`
- Modify: `tests/persistence/test_history.py`

**Interfaces:**
- Consumes: Task 2 result types and Task 3 schema.
- Produces: `HistoryRepository.add`, `recent`, `search`, `update_title`, `delete`, `clear`.
- Consumed by: Tasks 5–7.

- [ ] **Step 1: Replace repository fixture builders with component results**

Create one simple result and one combined result matching the approved examples. Ensure every test closes its repository.

- [ ] **Step 2: Write failing atomic-write tests**

Assert `add()` inserts one header and all components, returns the generated ID, round-trips all filters and nullable sums, and rolls back both tables if the second component insert or commit fails.

- [ ] **Step 3: Write failing query tests**

Cover:

```python
repository.search(title="Arhat")
repository.search(sides=20)
repository.search(date_from=start, date_to=end)
```

Title search is case-insensitive substring matching. Sides search returns a combined roll once even when it has multiple components.

- [ ] **Step 4: Write failing edit and deletion tests**

Define:

```python
def update_title(self, record_id: int, title: str) -> RollRecord: ...
```

Assert trimming, empty title acceptance, 151-character rejection, nonexistent-record error, cascade deletion and rollback preservation.

- [ ] **Step 5: Run focused tests and confirm RED**

```bash
python -m pytest tests/persistence/test_history.py -v
```

- [ ] **Step 6: Implement row mapping and transactions**

Insert the header, capture `lastrowid`, insert ordered components, and commit once. Reads must fetch headers without duplication and load components ordered by `position`. Reuse one `_write_transaction` error boundary that rolls back and translates `sqlite3.Error` to the existing storage `OSError`.

- [ ] **Step 7: Verify and commit**

```bash
python -m pytest tests/persistence -q
git add src/oraculo_enom/persistence tests/persistence
git commit -m "feat: persist combined roll histories atomically"
```

---

### Task 5: Main-window clarity and titled simple rolls

**Files:**
- Modify: `src/oraculo_enom/ui/main_window.py`
- Modify: `src/oraculo_enom/ui/theme.py`
- Modify: `tests/ui/test_main_window.py`

**Interfaces:**
- Consumes: aggregate roll engine, analyzer and repository.
- Produces: corrected simple-roll workflow, shared title state and contextual repeat label.
- Consumed by: Tasks 6–7.

- [ ] **Step 1: Write failing custom-quantity UI tests**

Assert the `Cantidad personalizada` label exists, the spin box starts disabled, `Personalizada` enables it, switching back disables without clearing, and restoring a request above 10 re-enables it.

- [ ] **Step 2: Write failing title tests**

Assert the line edit has `maxLength() == 150`, starts empty, the clear button is disabled when empty, typing enables it, clicking clears it, and a successful roll leaves the title intact.

- [ ] **Step 3: Write failing simple-roll and repeat tests**

Assert a simple UI action emits a one-component request, persists `total=None` when unchecked, copies the title, and changes the repeat label back to `Repetir tirada` after a simple roll.

- [ ] **Step 4: Run focused tests and confirm RED**

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/ui/test_main_window.py -v
```

- [ ] **Step 5: Reorganize controls and adapt the simple flow**

Add stable object names:

```text
customQuantityLabel
rollTitleEdit
clearRollTitleButton
combinedRollButton
```

Connect quantity selection to a dedicated `_set_custom_quantity_enabled()`. Build the aggregate request in `_current_simple_request()` and use the same `_execute_request(request)` path later consumed by the combined dialog.

- [ ] **Step 6: Style and verify**

Add compact clear-button and title-field rules without changing the approved palette. Run the main-window tests and inspect an offscreen screenshot or a local rendered window for alignment.

- [ ] **Step 7: Commit**

```bash
git add src/oraculo_enom/ui/main_window.py src/oraculo_enom/ui/theme.py tests/ui/test_main_window.py
git commit -m "feat: clarify and title simple rolls"
```

---

### Task 6: Advanced combined-roll dialog

**Files:**
- Create: `src/oraculo_enom/ui/combined_dialog.py`
- Modify: `src/oraculo_enom/ui/theme.py`
- Create: `tests/ui/test_combined_dialog.py`

**Interfaces:**
- Consumes: `RollComponentRequest`, `RollRequest`, limits and comparator enum.
- Produces: `CombinedRollDialog.roll_requested: Signal(RollRequest)` and in-memory builder state.
- Consumed by: Task 7 main-window integration.

- [ ] **Step 1: Write failing construction and layout tests**

Assert the dialog exposes title, sum, component table/editor, preview, total-count label, add, remove, clear, cancel and roll controls with stable object names. Assert its initial state has no components and disabled roll action.

- [ ] **Step 2: Write failing component-management tests**

Cover quick and custom dice, merging `2d6 + 3d6` into `5d6`, stable order, removal, exactly 10 distinct side counts, rejection of the eleventh, and rejection when total dice would exceed 1.000.

- [ ] **Step 3: Write failing per-component filter tests**

Assert toggling a row filter enables only that row's comparator and threshold controls, disabled rows produce `None` pairs, and each configured row maps to its own request filter.

- [ ] **Step 4: Write failing preview and clearing tests**

Assert exact preview `2d6 + 1d8 + 3d20`, summary `6 dados · 3 tipos diferentes`, title retention, and `Limpiar configuración` removes components and resets sum/filters without touching an externally supplied last completed request.

- [ ] **Step 5: Write failing submission tests**

Assert `Tirar combinación` emits one immutable validated request and accepts the dialog; invalid state emits nothing and displays an actionable message.

- [ ] **Step 6: Run focused tests and confirm RED**

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/ui/test_combined_dialog.py -v
```

- [ ] **Step 7: Implement the approved dense dialog**

Use a scrollable row container or table-like grid, but keep widget ownership inside the dialog. Provide methods:

```python
def set_title(self, title: str) -> None: ...
def add_component(self, component: RollComponentRequest) -> None: ...
def current_request(self) -> RollRequest: ...
def clear_configuration(self) -> None: ...
```

Store the draft widgets for the life of the dialog object; do not persist the draft in SQLite.

- [ ] **Step 8: Verify visual parity and commit**

Compare the rendered dialog with `docs/assets/combined-roll-dialog-mockup.png`: hierarchy, headings, table columns, disabled filters, preview and action order. Then:

```bash
git add src/oraculo_enom/ui/combined_dialog.py src/oraculo_enom/ui/theme.py tests/ui/test_combined_dialog.py
git commit -m "feat: add advanced combined roll builder"
```

---

### Task 7: Results, repetition and history integration

**Files:**
- Modify: `src/oraculo_enom/ui/main_window.py`
- Modify: `src/oraculo_enom/ui/history_dialog.py`
- Modify: `tests/ui/test_main_window.py`
- Modify: `tests/ui/test_history_dialog.py`

**Interfaces:**
- Consumes: Tasks 1–6 public interfaces.
- Produces: complete simple/combined user flow and editable history titles.

- [ ] **Step 1: Write failing combined integration test**

Open the builder from the main window, configure `2d6 + 1d8 + 3d20`, emit the request, and assert the dialog closes, one atomic history record is created, results are grouped in order, per-component matches are highlighted, subtotals/global sum follow `show_sum`, and the title synchronizes back to the main field.

- [ ] **Step 2: Write failing contextual-repeat tests**

After a combined roll, assert the label is `Repetir tirada combinada` and clicking it immediately executes fresh values without opening the dialog. Then perform a simple roll and assert the label and stored repeat request change back to the simple form.

- [ ] **Step 3: Write failing session-state tests**

Close/reopen the same dialog object and assert its draft remains. Clear the builder and assert it reopens empty while the main repeat button can still repeat the last completed combination.

- [ ] **Step 4: Write failing history rendering/search tests**

Assert recent and complete history show optional title plus canonical notation, title search is case-insensitive, sides filtering matches any component, and details/copy render every group.

- [ ] **Step 5: Write failing title-edit tests**

Select a record, invoke `Editar título`, accept corrected text, and assert repository, dialog detail and main recent-history panel update immediately. Add cancellation, empty title, 150-character limit and storage-failure preservation cases.

- [ ] **Step 6: Run focused tests and confirm RED**

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/ui/test_main_window.py tests/ui/test_history_dialog.py -v
```

- [ ] **Step 7: Implement one execution/rendering path**

Make `_execute_request(request)` perform generation, analysis, one repository add, grouped rendering and repeat-state update. Do not duplicate this work in dialog handlers. Adapt history record selection, copy and repeat to aggregate requests.

- [ ] **Step 8: Implement title editing with error preservation**

Use a bounded text-input dialog. Only refresh/emit `history_changed` after `update_title()` succeeds; on `OSError`, keep row, detail and selection unchanged.

- [ ] **Step 9: Verify and commit**

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/ui -q
git add src/oraculo_enom/ui/main_window.py src/oraculo_enom/ui/history_dialog.py tests/ui/test_main_window.py tests/ui/test_history_dialog.py
git commit -m "feat: integrate combined rolls with history"
```

---

### Task 8: Regression, packaging and acceptance handoff

**Files:**
- Modify: `README.md`
- Modify if required by actual data-file changes: `El-Oraculo-de-ENOM.spec`
- Modify if required by final commands: `.github/workflows/build-windows.yml`
- Modify: relevant regression tests only when a verified gap is found.

**Interfaces:**
- Consumes: complete application.
- Produces: tested Windows release candidate for manual acceptance.

- [ ] **Step 1: Run the complete automated verification**

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
python -m compileall -q src tests
git diff --check $(git merge-base HEAD main)..HEAD
```

Expected: zero failures, zero compilation errors and zero whitespace errors.

- [ ] **Step 2: Perform a requirements audit**

Map every acceptance criterion in the spec to at least one automated test. Add a specific regression test before changing code for any uncovered behavior, and record its red/green evidence.

- [ ] **Step 3: Update user documentation**

Document titled rolls, combined builder limits, independent filters, database reset required from the pre-release build, and the exact manual removal path `datos/historial.db`. Keep version `0.1.0`.

- [ ] **Step 4: Build a clean local bundle**

```bash
python -m PyInstaller El-Oraculo-de-ENOM.spec --clean --noconfirm
```

Inspect the output and assert it contains the executable and no `historial.db`, `tests/` or development source tree.

- [ ] **Step 5: Trigger and inspect Windows CI**

Push the reviewed branch, wait for **Build Windows portable**, confirm tests and packaging succeed, download the current artifact and inspect its ZIP contents.

- [ ] **Step 6: Prepare the manual Windows checklist**

Include:

1. remove or archive the experimental `datos/historial.db`;
2. launch from a writable extracted folder;
3. test standard and custom simple rolls;
4. test title persistence, clearing, copying and editing;
5. test a ten-component combination and the 1.000-dice boundary;
6. test independent filters, subtotals and global sum;
7. test combined repetition without reopening the dialog;
8. close/reopen and verify saved roll history but cleared draft combination;
9. move the complete portable folder and repeat the persistence check.

- [ ] **Step 7: Commit documentation/build adjustments**

```bash
git add README.md El-Oraculo-de-ENOM.spec .github/workflows/build-windows.yml tests src
git commit -m "docs: prepare combined roll acceptance build"
```

Stage only files actually changed; omit unchanged paths from the final `git add` command.

- [ ] **Step 8: Stop before `1.0.0` publication**

Report automated evidence and provide the Windows artifact. Do not merge, tag or create a release until manual acceptance succeeds and the separate professional-distribution work (third-party notices, licenses in ZIP, changelog, SBOM, hashes and signing decision) is completed.
