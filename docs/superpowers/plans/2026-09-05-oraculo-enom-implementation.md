# El Oráculo de ENOM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir una aplicación gráfica portable para Windows que realice tiradas de hasta `1000d1000`, aplique filtros, copie resultados y conserve un historial SQLite.

**Architecture:** El dominio de tiradas será Python puro y no dependerá de PySide6. La persistencia SQLite, las rutas portables y la interfaz gráfica consumirán interfaces tipadas separadas; `app.py` será únicamente el punto de composición.

**Tech Stack:** Python 3.12, PySide6 6.8+, SQLite estándar, pytest, pytest-qt, PyInstaller y GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-05-oraculo-enom-design.md`

## Global Constraints

- Nombre visible: **El Oráculo de ENOM**.
- Repositorio: `santiamaster/el-oraculo-de-enom`.
- Dados rápidos: d4, d6, d8, d10, d12, d16, d20, d50 y d100.
- Caras: enteros entre 2 y 1.000, ambos incluidos.
- Cantidad: enteros entre 1 y 1.000, ambos incluidos.
- El generador usa `secrets.randbelow(caras) + 1`.
- La primera distribución es un portable para Windows, sin conexión ni instalación.
- El historial se guarda en `datos/historial.db` junto al ejecutable.
- La lógica no debe depender de Windows para permitir versiones futuras en Linux y macOS.
- Las entradas inválidas nunca deben cerrar la aplicación ni borrar los valores ingresados.

## File Map

```text
el-oraculo-de-enom/
├── .github/workflows/build-windows.yml     # pruebas y artefacto portable
├── docs/superpowers/specs/...              # diseño aprobado
├── docs/superpowers/plans/...              # este plan
├── src/oraculo_enom/
│   ├── __init__.py
│   ├── app.py                              # composición y arranque
│   ├── domain/models.py                    # tipos inmutables
│   ├── domain/dice.py                      # validación y generación
│   ├── domain/analysis.py                  # suma y filtros
│   ├── persistence/database.py             # esquema y conexión
│   ├── persistence/history.py              # CRUD de tiradas
│   ├── services/paths.py                   # rutas portables
│   ├── services/clipboard.py               # texto exportable
│   └── ui/
│       ├── main_window.py                  # pantalla principal
│       ├── history_dialog.py               # historial completo
│       └── theme.py                        # paleta y estilos Qt
├── tests/
│   ├── domain/test_dice.py
│   ├── domain/test_analysis.py
│   ├── persistence/test_history.py
│   ├── services/test_paths.py
│   ├── services/test_clipboard.py
│   └── ui/test_main_window.py
├── El-Oraculo-de-ENOM.spec                 # configuración PyInstaller
├── pyproject.toml
├── README.md
└── .gitignore
```

---

### Task 1: Project skeleton and typed domain models

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/oraculo_enom/__init__.py`
- Create: `src/oraculo_enom/domain/models.py`
- Test: `tests/domain/test_models.py`

**Interfaces:**
- Consumes: none.
- Produces: `Comparator`, `RollRequest`, `RollResult`, `RollRecord`.

- [ ] **Step 1: Write the failing model tests**

```python
from datetime import datetime

from oraculo_enom.domain.models import Comparator, RollRequest, RollResult


def test_roll_request_keeps_filter_configuration() -> None:
    request = RollRequest(22, 20, True, Comparator.GREATER_THAN, 12)
    assert request.notation == "22d20"
    assert request.threshold == 12


def test_roll_result_is_immutable() -> None:
    result = RollResult(
        request=RollRequest(2, 6, True),
        values=(2, 5),
        total=7,
        matches=(),
        created_at=datetime(2026, 9, 5, 12, 0),
    )
    assert result.values == (2, 5)
```

- [ ] **Step 2: Run the tests and verify the missing module failure**

Run: `python -m pytest tests/domain/test_models.py -v`

Expected: collection fails because `oraculo_enom.domain.models` does not exist.

- [ ] **Step 3: Create packaging configuration and models**

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "el-oraculo-de-enom"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["PySide6>=6.8,<7"]

[project.optional-dependencies]
dev = ["pytest>=8.3", "pytest-qt>=4.4", "pyinstaller>=6.11"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Comparator(StrEnum):
    GREATER_THAN = ">"
    GREATER_OR_EQUAL = ">="
    LESS_THAN = "<"
    LESS_OR_EQUAL = "<="
    EQUAL = "="


@dataclass(frozen=True, slots=True)
class RollRequest:
    count: int
    sides: int
    show_sum: bool
    comparator: Comparator | None = None
    threshold: int | None = None

    @property
    def notation(self) -> str:
        return f"{self.count}d{self.sides}"


@dataclass(frozen=True, slots=True)
class RollResult:
    request: RollRequest
    values: tuple[int, ...]
    total: int
    matches: tuple[int, ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RollRecord:
    id: int
    result: RollResult
```

Create `.gitignore` with `.venv/`, `__pycache__/`, `.pytest_cache/`, `build/`, `dist/`, `datos/`, `*.db` and `.superpowers/`.

- [ ] **Step 4: Install development dependencies and run tests**

Run: `python -m pip install -e ".[dev]" && python -m pytest tests/domain/test_models.py -v`

Expected: all model tests pass.

- [ ] **Step 5: Commit the skeleton**

```bash
git add pyproject.toml .gitignore src tests/domain/test_models.py
git commit -m "chore: initialize Oraculo de ENOM project"
```

---

### Task 2: Dice generation and request validation

**Files:**
- Create: `src/oraculo_enom/domain/dice.py`
- Test: `tests/domain/test_dice.py`

**Interfaces:**
- Consumes: `RollRequest`.
- Produces: `validate_request(request: RollRequest) -> None`, `roll_values(request: RollRequest, randbelow: Callable[[int], int] = secrets.randbelow) -> tuple[int, ...>`.

- [ ] **Step 1: Write failing boundary and deterministic tests**

```python
import pytest

from oraculo_enom.domain.dice import roll_values, validate_request
from oraculo_enom.domain.models import RollRequest


@pytest.mark.parametrize("request", [RollRequest(1, 2, False), RollRequest(1000, 1000, True)])
def test_valid_boundaries(request: RollRequest) -> None:
    validate_request(request)


@pytest.mark.parametrize(
    "request,message",
    [
        (RollRequest(0, 20, False), "dados debe estar entre 1 y 1.000"),
        (RollRequest(1001, 20, False), "dados debe estar entre 1 y 1.000"),
        (RollRequest(1, 1, False), "caras debe estar entre 2 y 1.000"),
        (RollRequest(1, 1001, False), "caras debe estar entre 2 y 1.000"),
    ],
)
def test_invalid_boundaries(request: RollRequest, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_request(request)


def test_roll_maps_zero_based_random_values_to_dice_values() -> None:
    generated = iter([0, 19, 9])
    assert roll_values(RollRequest(3, 20, False), lambda _: next(generated)) == (1, 20, 10)
```

- [ ] **Step 2: Verify the tests fail**

Run: `python -m pytest tests/domain/test_dice.py -v`

Expected: import failure for `domain.dice`.

- [ ] **Step 3: Implement validation and generation**

```python
import secrets
from collections.abc import Callable

from .models import RollRequest


def validate_request(request: RollRequest) -> None:
    if not 1 <= request.count <= 1000:
        raise ValueError("La cantidad de dados debe estar entre 1 y 1.000")
    if not 2 <= request.sides <= 1000:
        raise ValueError("La cantidad de caras debe estar entre 2 y 1.000")
    if (request.comparator is None) != (request.threshold is None):
        raise ValueError("El filtro necesita un comparador y un umbral")


def roll_values(
    request: RollRequest,
    randbelow: Callable[[int], int] = secrets.randbelow,
) -> tuple[int, ...]:
    validate_request(request)
    return tuple(randbelow(request.sides) + 1 for _ in range(request.count))
```

- [ ] **Step 4: Run the domain tests**

Run: `python -m pytest tests/domain/test_dice.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit the dice engine**

```bash
git add src/oraculo_enom/domain/dice.py tests/domain/test_dice.py
git commit -m "feat: add validated dice engine"
```

---

### Task 3: Roll analysis and clipboard formatting

**Files:**
- Create: `src/oraculo_enom/domain/analysis.py`
- Create: `src/oraculo_enom/services/clipboard.py`
- Test: `tests/domain/test_analysis.py`
- Test: `tests/services/test_clipboard.py`

**Interfaces:**
- Consumes: `RollRequest`, `RollResult`, `Comparator`.
- Produces: `analyze(request, values, created_at=None) -> RollResult`, `format_roll(result) -> str`.

- [ ] **Step 1: Write failing parameterized comparator tests**

```python
from datetime import datetime

import pytest

from oraculo_enom.domain.analysis import analyze
from oraculo_enom.domain.models import Comparator, RollRequest


@pytest.mark.parametrize(
    "comparator,expected",
    [
        (Comparator.GREATER_THAN, (15,)),
        (Comparator.GREATER_OR_EQUAL, (10, 15)),
        (Comparator.LESS_THAN, (2,)),
        (Comparator.LESS_OR_EQUAL, (2, 10)),
        (Comparator.EQUAL, (10,)),
    ],
)
def test_comparators(comparator: Comparator, expected: tuple[int, ...]) -> None:
    request = RollRequest(3, 20, True, comparator, 10)
    result = analyze(request, (2, 10, 15), datetime(2026, 9, 5, 12, 0))
    assert result.total == 27
    assert result.matches == expected
```

Add a clipboard test expecting:

```text
22d20: 7, 18, 20
Suma: 45
Filtro > 12: 2 de 3
```

when the sum is visible and the filter is active; verify that the sum line is omitted when `show_sum` is false.

- [ ] **Step 2: Verify both test modules fail**

Run: `python -m pytest tests/domain/test_analysis.py tests/services/test_clipboard.py -v`

Expected: imports fail for the new modules.

- [ ] **Step 3: Implement the analyzer**

Use an explicit mapping from each `Comparator` to the corresponding function in `operator`. Reject a number of values different from `request.count`. Calculate `total = sum(values)` and preserve matching values in original order.

```python
OPERATIONS = {
    Comparator.GREATER_THAN: operator.gt,
    Comparator.GREATER_OR_EQUAL: operator.ge,
    Comparator.LESS_THAN: operator.lt,
    Comparator.LESS_OR_EQUAL: operator.le,
    Comparator.EQUAL: operator.eq,
}
```

When `created_at` is omitted, use `datetime.now()`.

- [ ] **Step 4: Implement text formatting and run tests**

`format_roll()` must always include notation and individual values. It includes `Suma:` only when `show_sum` is true, and includes the filter line only when a comparator exists.

Run: `python -m pytest tests/domain tests/services/test_clipboard.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit analysis services**

```bash
git add src/oraculo_enom/domain/analysis.py src/oraculo_enom/services/clipboard.py tests/domain/test_analysis.py tests/services/test_clipboard.py
git commit -m "feat: analyze and format dice rolls"
```

---

### Task 4: Portable paths and SQLite history

**Files:**
- Create: `src/oraculo_enom/services/paths.py`
- Create: `src/oraculo_enom/persistence/database.py`
- Create: `src/oraculo_enom/persistence/history.py`
- Test: `tests/services/test_paths.py`
- Test: `tests/persistence/test_history.py`

**Interfaces:**
- Consumes: `RollResult`, `RollRecord`, `Comparator`.
- Produces: `application_dir() -> Path`, `database_path() -> Path`, `HistoryRepository` with `add`, `recent`, `search`, `delete`, `clear`.

- [ ] **Step 1: Write failing portable-path tests**

Use `monkeypatch` to verify that `application_dir()` returns `Path(sys.executable).parent` when `sys.frozen` is true and the repository root when running from source. Verify `database_path()` creates `datos/` and returns `datos/historial.db`.

- [ ] **Step 2: Write failing repository round-trip tests**

Create a repository with a temporary database, add a filtered `RollResult`, close and reopen the repository, and assert that notation, tuple values, sum, comparator, threshold and timestamp are preserved. Add separate tests for recent ordering, filters by sides/date, delete and clear.

- [ ] **Step 3: Verify the persistence tests fail**

Run: `python -m pytest tests/services/test_paths.py tests/persistence/test_history.py -v`

Expected: imports fail for the new modules.

- [ ] **Step 4: Implement paths and schema initialization**

Create the directory with `mkdir(parents=True, exist_ok=True)`. If it fails, raise `OSError` with: `No se puede guardar el historial en esta ubicación. Mové la aplicación a una carpeta con permisos de escritura.`

Create table `rolls` with columns `id`, `created_at`, `count`, `sides`, `values_json`, `total`, `show_sum`, `comparator`, `threshold`, and `match_count`. Store timestamps as ISO 8601 and values as JSON arrays. Set `sqlite3.Row` as row factory and create indices for `created_at` and `sides`.

- [ ] **Step 5: Implement repository CRUD and filtering**

Use parameterized SQL exclusively. `recent(limit=5)` sorts by `created_at DESC, id DESC`. `search(sides: int | None, date_from: date | None, date_to: date | None)` composes only the required `WHERE` clauses. Convert rows back into immutable domain models.

- [ ] **Step 6: Run persistence and complete unit tests**

Run: `python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 7: Commit persistence**

```bash
git add src/oraculo_enom/services/paths.py src/oraculo_enom/persistence tests/services/test_paths.py tests/persistence/test_history.py
git commit -m "feat: add portable SQLite history"
```

---

### Task 5: Main PySide6 window and ENOM theme

**Files:**
- Create: `src/oraculo_enom/ui/theme.py`
- Create: `src/oraculo_enom/ui/main_window.py`
- Create: `src/oraculo_enom/app.py`
- Test: `tests/ui/test_main_window.py`

**Interfaces:**
- Consumes: dice engine, analyzer, formatter and `HistoryRepository`.
- Produces: `MainWindow(repository: HistoryRepository)` and `main() -> int`.

- [ ] **Step 1: Write failing Qt interaction tests**

Instantiate `MainWindow` with a temporary repository. Test that d20 and quantity 22 produce label `TIRAR 22D20`; inject a deterministic roller and click the button; assert 22 result badges, correct sum, correct match summary and one saved record. Test that invalid custom sides shows the exact validation message while preserving the input.

- [ ] **Step 2: Verify UI tests fail**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/ui/test_main_window.py -v`

Expected: import failure for `ui.main_window`.

- [ ] **Step 3: Implement theme constants and stylesheet**

Use these base colors consistently:

```python
BACKGROUND = "#171311"
PANEL = "#231d19"
FIELD = "#151210"
GOLD = "#f2cf7b"
GOLD_DARK = "#8b6229"
BORDER = "#665237"
TEXT = "#efe2c3"
MUTED = "#a99b83"
```

Create a Qt stylesheet for `QMainWindow`, `QFrame`, buttons, spin boxes, combo boxes, check boxes, scroll areas and validation labels. Preserve strong focus indicators and readable disabled states.

- [ ] **Step 4: Implement the main layout**

Use a horizontal splitter: left main area and right recent-history panel. The left area contains quick-die buttons, custom sides `QSpinBox`, quantity combo 1–10 plus custom `QSpinBox`, sum checkbox, optional filter checkbox, comparator combo, threshold spin box, primary roll button, scrollable result badges, summary cards, repeat and copy actions.

Keep the filter controls disabled until its checkbox is active. Selected dice and filter matches use the gold highlight. Render at most one widget per generated value; 1.000 badges must remain inside a scroll area and must not resize the entire window.

- [ ] **Step 5: Connect the roll flow**

Build `RollRequest`, call the injected roller, call `analyze`, save through the repository, render results, refresh recent history and enable repeat/copy. Catch `ValueError` and `OSError`, showing their messages in the validation area without clearing inputs.

- [ ] **Step 6: Add application composition**

`main()` creates `QApplication`, applies metadata and theme, creates the database/repository, shows `MainWindow`, and returns `app.exec()`. Add a `__main__` guard.

- [ ] **Step 7: Run UI and complete tests**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 8: Commit the main application**

```bash
git add src/oraculo_enom/ui src/oraculo_enom/app.py tests/ui/test_main_window.py
git commit -m "feat: build ENOM dice roller interface"
```

---

### Task 6: Full history dialog

**Files:**
- Create: `src/oraculo_enom/ui/history_dialog.py`
- Modify: `src/oraculo_enom/ui/main_window.py`
- Test: `tests/ui/test_history_dialog.py`

**Interfaces:**
- Consumes: `HistoryRepository`, `RollRecord`, `format_roll`.
- Produces: `HistoryDialog(repository, parent=None)`, signal `repeat_requested(RollRequest)`.

- [ ] **Step 1: Write failing dialog tests**

Seed three records. Verify newest-first order, side filtering, date filtering, detail selection, copy, deletion and the emitted request when repeating. Verify **Borrar todo** changes nothing when confirmation is rejected and clears all rows when accepted.

- [ ] **Step 2: Verify dialog tests fail**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/ui/test_history_dialog.py -v`

Expected: import failure for `ui.history_dialog`.

- [ ] **Step 3: Implement history browsing**

Use a filter row with optional sides, start date and end date; a list or table for records; and a read-only detail panel. Connect **Copiar**, **Repetir**, **Eliminar** and **Borrar todo**. Use `QMessageBox.question` before destructive clearing.

- [ ] **Step 4: Connect main window and repeat flow**

Open the dialog from **Ver historial completo**. When `repeat_requested` fires, close the dialog, load the request into the main controls and immediately perform a new random roll. Do not reuse stored values.

- [ ] **Step 5: Run all tests**

Run: `QT_QPA_PLATFORM=offscreen python -m pytest -v`

Expected: all tests pass.

- [ ] **Step 6: Commit the history interface**

```bash
git add src/oraculo_enom/ui/history_dialog.py src/oraculo_enom/ui/main_window.py tests/ui/test_history_dialog.py
git commit -m "feat: add searchable roll history"
```

---

### Task 7: Windows portable packaging and CI

**Files:**
- Create: `El-Oraculo-de-ENOM.spec`
- Create: `.github/workflows/build-windows.yml`
- Create: `README.md`
- Test: package smoke check inside workflow.

**Interfaces:**
- Consumes: complete application and tests.
- Produces: downloadable GitHub Actions artifact `El-Oraculo-de-ENOM-Windows.zip`.

- [ ] **Step 1: Add a PyInstaller specification**

Configure a windowed one-directory build named `El Oraculo de ENOM`. Collect PySide6 plugins through PyInstaller hooks. The entry point is `src/oraculo_enom/app.py`; exclude test modules and do not bundle `datos/historial.db`.

- [ ] **Step 2: Add the Windows workflow**

The workflow triggers on pushes to `main`, pull requests and tags beginning with `v`. It must:

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
- run: python -m pip install -e ".[dev]"
- run: python -m pytest -v
- run: pyinstaller El-Oraculo-de-ENOM.spec --clean
- run: Compress-Archive -Path "dist/El Oraculo de ENOM/*" -DestinationPath "El-Oraculo-de-ENOM-Windows.zip"
- uses: actions/upload-artifact@v4
  with:
    name: El-Oraculo-de-ENOM-Windows
    path: El-Oraculo-de-ENOM-Windows.zip
```

Set the workflow runner to `windows-latest`. Add a PowerShell smoke step that verifies the executable and confirms that no development database was bundled.

- [ ] **Step 3: Document local use and releases**

README sections: purpose, features, requirements for source execution, test command, portable build command, data location, repository structure and instructions for downloading the latest Actions artifact. No se incluirá una captura hasta disponer de una imagen real de la aplicación terminada.

- [ ] **Step 4: Build locally where supported and run tests**

Run: `python -m pytest -v`

Run on Windows: `pyinstaller El-Oraculo-de-ENOM.spec --clean`

Expected: tests pass; `dist/El Oraculo de ENOM/El Oraculo de ENOM.exe` exists; starting it creates `datos/historial.db` beside the executable after the first saved roll.

- [ ] **Step 5: Commit packaging and CI**

```bash
git add El-Oraculo-de-ENOM.spec .github/workflows/build-windows.yml README.md
git commit -m "build: automate Windows portable releases"
```

---

### Task 8: Release-candidate verification

**Files:**
- Modify only files required by defects found during verification.
- Create a GitHub release only after every check passes.

**Interfaces:**
- Consumes: Windows artifact from Task 7.
- Produces: tagged release candidate `v0.1.0` and attached portable ZIP.

- [ ] **Step 1: Run automated verification**

Run locally: `QT_QPA_PLATFORM=offscreen python -m pytest -v`

Verify GitHub Actions passes on `main` and downloads the generated Windows artifact.

- [ ] **Step 2: Perform the Windows acceptance checklist**

On a Windows machine verify quick dice, `22d350`, `1d2`, `1000d1000`, all comparators, sum visibility, copy, repeat, history restart, search, individual deletion, confirmed full deletion and the protected-folder error message.

- [ ] **Step 3: Verify portability**

Make a roll, close the program, copy the complete portable folder to a different writable location, reopen it and verify that the saved roll remains in the history.

- [ ] **Step 4: Correct only verified defects**

For each failure, add or tighten a failing automated test when possible, make the smallest correction and rerun the complete test suite plus the affected acceptance check.

- [ ] **Step 5: Tag the accepted version**

```bash
git tag -a v0.1.0 -m "El Oraculo de ENOM v0.1.0"
git push origin main --tags
```

Confirm the tagged workflow succeeds and publish its ZIP as the `v0.1.0` release asset.
