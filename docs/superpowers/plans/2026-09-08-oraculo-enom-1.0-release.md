# El Oráculo de ENOM — Plan de cierre y publicación 1.0.0

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Llevar el candidato funcional actual desde `0.1.0` hasta una GitHub Release `1.0.0` para Windows, con CI, aceptación manual, cumplimiento de distribución y artefactos verificables.

**Architecture:** El código funcional queda congelado salvo defectos demostrados. La promoción sigue una cadena trazable: commit local → pull request → artefacto de CI → aceptación → metadatos de distribución → candidato `1.0.0` → merge/tag/release. Cada tramo consume la evidencia del anterior y termina en una parada obligatoria.

**Tech Stack:** Python 3.12+, PySide6 6.8–6.x, pytest, pytest-qt, PyInstaller, GitHub Actions, GitHub CLI, CycloneDX JSON y SHA-256.

**Spec:** `docs/superpowers/specs/2026-09-08-oraculo-enom-1.0-release-design.md`

## Global Constraints

- Ejecutar únicamente el tramo autorizado por el usuario y detenerse al terminarlo.
- Antes de cada tramo, comprobar rama, HEAD, worktree, remoto y registro de avance.
- No agregar funciones nuevas durante el cierre de release.
- Aplicar TDD a toda corrección de comportamiento o automatización nueva.
- Ejecutar revisión de requisitos y de calidad antes del commit de cada tramo.
- Mantener `docs/release/1.0.0-status.md` como registro de SHA, run, artefacto, pruebas y resultado de cada puerta.
- No versionar `build/`, `dist/`, ZIP, ejecutables ni descargas temporales.
- No hacer merge, tag ni publicación antes del Tramo 17.
- No usar force-push ni reescribir historial remoto.
- Detenerse si la autenticación, permisos o una decisión externa bloquean el tramo.

---

## File Map

### Estado y aceptación

- `docs/release/1.0.0-status.md`: registro acumulativo de puertas y evidencia.
- `docs/acceptance/1.0.0-windows.md`: checklist manual asociado a un ZIP exacto.

### Cumplimiento y metadatos

- `THIRD_PARTY_NOTICES.md`: componentes redistribuidos, licencia y procedencia.
- `licenses/`: textos de licencia exigidos por los componentes realmente incluidos.
- `CHANGELOG.md`: cambios de `1.0.0` en formato Keep a Changelog.
- `docs/release/1.0.0-notes.md`: notas públicas de la GitHub Release.
- `scripts/verify_distribution.py`: inspección reutilizable de la carpeta/ZIP.
- `tests/release/test_distribution.py`: contrato automatizado de distribución.

### Build y versión

- `El-Oraculo-de-ENOM.spec`: inclusión de licencias y avisos en PyInstaller.
- `.github/workflows/build-windows.yml`: pruebas, bundle, validación, SBOM, hash y artefacto.
- `pyproject.toml`: dependencia de desarrollo para SBOM y versión final.
- `README.md`: versión, verificación del hash/SBOM y estado de firma.

---

### Tramo 10: Higiene del candidato local

**Files:**
- Create: `docs/release/1.0.0-status.md`
- Delete: `.superpowers/sdd/2026-09-07-oraculo-enom-general-dice-implementation/final-review-fix-report.md`
- Modify only if a verified regression is found: affected source and test files.

**Exit gate:** worktree limpio, candidato local reproducible y evidencia inicial registrada. La versión permanece `0.1.0`.

- [ ] **Step 1: Reconstruct and record the exact baseline**

Run:

```bash
git status --short --branch
git log --oneline --decorate -12
git remote -v
git branch -vv
git diff --stat main...HEAD
```

Confirm the branch is `feature/initial-app`, no upstream is configured, and no
unexpected user changes exist. If changes exist, stop instead of overwriting them.

- [ ] **Step 2: Remove the internal transient review report**

Delete only the tracked report under `.superpowers/sdd/`; keep the approved spec,
plans and user-facing documentation. Confirm `.superpowers/sdd/.gitignore` still
prevents future transient reports from being added.

- [ ] **Step 3: Run the complete local gate**

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests
git diff --check main...HEAD
.venv/bin/python -m PyInstaller El-Oraculo-de-ENOM.spec --clean --noconfirm
```

Inspect `dist/El Oraculo de ENOM/`: executable present; zero `historial.db`,
`tests/`, `src/` directories and `.py` files. A defect requires a failing
regression test before its fix and a repeat of the full gate.

- [ ] **Step 4: Create the release status record**

Record date, branch, HEAD, version `0.1.0`, test counts, build command, bundle
inspection and the states `local-ready` / `remote-pending`. Do not claim Windows
validation from the Linux bundle.

- [ ] **Step 5: Review and commit**

```bash
git diff --check
git diff --stat
git status --short
git add docs/release/1.0.0-status.md
git add -u .superpowers/sdd
git commit -m "chore: clean 1.0 release candidate"
```

- [ ] **Step 6: Stop**

Report the new SHA, test/build evidence and changed files. Do not push or begin
Tramo 11.

---

### Tramo 11: Rama remota y Pull Request

**Files:**
- Modify: `docs/release/1.0.0-status.md`
- Modify only on a demonstrated CI defect: affected workflow/source/test files.

**Exit gate:** branch published without history rewrite, pull request open, and
the Windows workflow green on the PR HEAD.

- [ ] **Step 1: Verify local and GitHub preconditions**

```bash
git status --short --branch
git log -1 --format='%H %s'
gh auth status
gh repo view --json nameWithOwner,defaultBranchRef,url
gh pr list --head feature/initial-app --state all
```

Stop on a dirty worktree, wrong repository, missing authentication or an existing
conflicting PR.

- [ ] **Step 2: Publish the branch and create the PR**

```bash
git push --set-upstream origin feature/initial-app
gh pr create --base main --head feature/initial-app --title "feat: prepare El Oráculo de ENOM desktop app" --body "Implementa tiradas simples y combinadas, títulos, filtros por componente, historial SQLite definitivo y empaquetado portable de Windows. La publicación 1.0.0 queda sujeta a las puertas documentadas en docs/release/1.0.0-status.md."
```

Capture the PR URL and verify its base/head and displayed diff with `gh pr view`.

- [ ] **Step 3: Wait for and inspect CI**

```bash
gh pr checks --watch
gh pr view --json headRefOid,url,statusCheckRollup
```

If CI fails, inspect the failing run with `gh run view --log-failed`, reproduce
locally where possible, add a failing regression test, fix, review, commit, push
and wait again. Do not merge.

- [ ] **Step 4: Record and commit the remote evidence**

Add PR URL, PR head SHA, workflow run URL/ID and check conclusions to the status
file, then:

```bash
git add docs/release/1.0.0-status.md
git commit -m "docs: record pull request validation"
git push
gh pr checks --watch
```

Update the recorded final SHA/run if this documentation commit creates a newer
run only in the user-facing tranche report. Do not create an endless sequence of
documentation-only commits trying to record the run caused by the previous record.

- [ ] **Step 5: Stop**

Report PR and CI links. Do not download the artifact or begin Tramo 12.

---

### Tramo 12: Inspección del artefacto Windows

**Files:**
- Modify: `docs/release/1.0.0-status.md`

**Exit gate:** ZIP produced by Windows CI for the exact PR HEAD inspected and
identified by SHA-256; no downloaded binary is committed.

- [ ] **Step 1: Resolve the exact successful run**

```bash
git status --short --branch
gh pr checks
gh pr view --json headRefOid,url
gh run list --workflow "Build Windows portable" --branch feature/initial-app --event pull_request --status success --limit 5 --json databaseId,headSha,url,conclusion
```

Select only the run whose `headSha` equals the current remote PR HEAD.

- [ ] **Step 2: Download into an isolated temporary directory**

```bash
ARTIFACT_DIR=$(mktemp -d)
PR_HEAD_SHA=$(gh pr view --json headRefOid --jq .headRefOid)
RELEASE_RUN_ID=$(gh run list --workflow "Build Windows portable" --branch feature/initial-app --event pull_request --status success --limit 20 --json databaseId,headSha --jq ".[] | select(.headSha == \"$PR_HEAD_SHA\") | .databaseId" | head -1)
test -n "$RELEASE_RUN_ID"
gh run download "$RELEASE_RUN_ID" --name El-Oraculo-de-ENOM-Windows --dir "$ARTIFACT_DIR"
find "$ARTIFACT_DIR" -maxdepth 2 -type f -print
sha256sum "$ARTIFACT_DIR/El-Oraculo-de-ENOM-Windows.zip"
unzip -l "$ARTIFACT_DIR/El-Oraculo-de-ENOM-Windows.zip"
```

- [ ] **Step 3: Inspect the archive contract**

Extract under the same temporary directory. Assert one portable root, exactly one
`El Oraculo de ENOM.exe`, required PyInstaller runtime files, and zero
`historial.db`, source `.py`, `tests/`, `src/`, secrets or repository metadata.
Reject path traversal, absolute ZIP entries and duplicate filenames.

- [ ] **Step 4: Record evidence and commit**

Record run ID/URL, PR head SHA, ZIP filename, byte size, SHA-256 and inspection
counts. Then:

```bash
git add docs/release/1.0.0-status.md
git commit -m "docs: record Windows artifact inspection"
git push
gh pr checks --watch
```

- [ ] **Step 5: Stop**

Report the exact artifact hash and findings. Do not perform or claim manual
acceptance and do not begin Tramo 13.

---

### Tramo 13: Aceptación manual en Windows

**Files:**
- Create: `docs/acceptance/1.0.0-windows.md`
- Modify: `docs/release/1.0.0-status.md`
- Modify only for a reproduced defect: affected source and regression test files.

**Exit gate:** every approved manual scenario passes on Windows using the exact
ZIP hash from Tramo 12.

- [ ] **Step 1: Prepare the acceptance record**

Create fields for Windows edition/build, architecture, tester, date, workflow run,
commit SHA, ZIP SHA-256, extraction path type and one `Expected / Actual / Result`
entry for each of the nine scenarios already documented in `README.md`.

- [ ] **Step 2: Execute the nine scenarios on Windows**

Use the downloaded ZIP, not a local rebuild. Cover database removal/archive,
launch from writable extraction, standard/custom simple rolls, title lifecycle,
ten components, 1,000-dice boundary, independent filters/sums, combined repeat,
restart persistence with cleared draft, and relocation of the complete portable
folder.

- [ ] **Step 3: Handle failures without masking them**

For any failure, preserve reproduction steps and relevant logs. Add an automated
regression test before changing behavior where automation is feasible; otherwise
document the manual red/green reproduction. Re-run the full suite and Windows CI,
then repeat all affected manual cases on the new ZIP. A changed ZIP invalidates the
old hash and acceptance evidence.

- [ ] **Step 4: Commit accepted evidence**

Only after all rows are PASS, mark the manual gate complete in the status file:

```bash
git add docs/acceptance/1.0.0-windows.md docs/release/1.0.0-status.md
git commit -m "docs: record Windows acceptance"
git push
gh pr checks --watch
```

- [ ] **Step 5: Stop**

Report tester/environment, accepted SHA/hash and any defects corrected. Do not
begin compliance work in Tramo 14.

---

### Tramo 14: Licencias y avisos de terceros

**Files:**
- Create: `THIRD_PARTY_NOTICES.md`
- Create: `licenses/` with the license texts required by the audited bundle.
- Create: `scripts/verify_distribution.py`
- Create: `tests/release/test_distribution.py`
- Modify: `El-Oraculo-de-ENOM.spec`
- Modify: `.github/workflows/build-windows.yml`
- Modify: `README.md`
- Modify: `docs/release/1.0.0-status.md`

**Exit gate:** the actual Windows bundle's redistributed components are inventoried,
notices are traceable to authoritative sources, and CI proves the required files
are inside the portable package.

- [ ] **Step 1: Inventory the built bundle before writing notices**

Use the PyInstaller analysis TOC and the accepted Windows ZIP to enumerate Python,
PySide6/Shiboken, Qt libraries/plugins and any additional redistributed native
library. Compare installed distribution metadata with the bundled files. Do not
list pytest, pytest-qt, PyInstaller or CycloneDX as runtime components unless their
files are actually present in the portable folder.

- [ ] **Step 2: Write failing compliance tests**

Test that the verifier rejects a distribution missing `LICENSE`,
`THIRD_PARTY_NOTICES.md` or `licenses/`; rejects notices that reference absent
license files; and rejects `historial.db`, `.py`, `tests/` or `src/`. Add a passing
fixture with the required portable layout.

Run and confirm RED:

```bash
.venv/bin/python -m pytest tests/release/test_distribution.py -v
```

- [ ] **Step 3: Implement the reusable verifier**

Expose a CLI accepting either a directory or ZIP and returning non-zero with a
specific message for every contract violation. Use `zipfile.Path`/`ZipInfo`
inspection without extracting unsafe paths. Keep pure validation functions callable
from pytest.

- [ ] **Step 4: Create notices from authoritative license texts**

For every inventoried runtime component, record name, bundled version, copyright,
license identifier, upstream URL and local license path. Copy the corresponding
license text into `licenses/`. Explicitly document that PyInstaller is a build tool
and why its bootloader license does not impose a runtime notice beyond its terms.
Perform a manual comparison against Qt for Python and PyInstaller's current
official licensing pages; record the review date in the status file.

- [ ] **Step 5: Bundle and enforce the material**

Set PyInstaller `datas` to include repository `LICENSE`,
`THIRD_PARTY_NOTICES.md` and `licenses/` at the portable root. In the workflow,
run the verifier against `dist/El Oraculo de ENOM` before compression.

- [ ] **Step 6: Run RED/GREEN and complete gates**

```bash
.venv/bin/python -m pytest tests/release/test_distribution.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests scripts
.venv/bin/python -m PyInstaller El-Oraculo-de-ENOM.spec --clean --noconfirm
.venv/bin/python scripts/verify_distribution.py "dist/El Oraculo de ENOM"
git diff --check
```

- [ ] **Step 7: Review, commit, push and inspect Windows CI**

```bash
git add THIRD_PARTY_NOTICES.md licenses scripts/verify_distribution.py tests/release/test_distribution.py El-Oraculo-de-ENOM.spec .github/workflows/build-windows.yml README.md docs/release/1.0.0-status.md
git commit -m "build: include third-party license notices"
git push
gh pr checks --watch
```

Download the new Windows ZIP and run the verifier against it. Update the recorded
run/hash in a follow-up documentation commit because packaging changes invalidate
the Tramo 13 ZIP; repeat a focused manual launch/persistence smoke test.

- [ ] **Step 8: Stop**

Report the audited component list, authoritative sources, tests and new artifact
hash. Do not begin Tramo 15.

---

### Tramo 15: Metadatos profesionales de distribución

**Files:**
- Create: `CHANGELOG.md`
- Create: `docs/release/1.0.0-notes.md`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/build-windows.yml`
- Modify: `scripts/verify_distribution.py`
- Modify: `tests/release/test_distribution.py`
- Modify: `README.md`
- Modify: `docs/release/1.0.0-status.md`

**Exit gate:** CI emits the Windows ZIP, un SBOM CycloneDX JSON validado y un
archivo SHA-256 coherente, junto con changelog/notas revisados.

- [ ] **Step 1: Write changelog and release notes**

Create `CHANGELOG.md` with a `1.0.0` section grouped into Added, Changed and Fixed,
based only on committed functionality. Create concise public notes with features,
portable usage, mandatory removal of the experimental database, verification
instructions and known limitation: no Authenticode signature.

- [ ] **Step 2: Write failing metadata tests**

Extend distribution tests to reject a missing/invalid CycloneDX JSON, a BOM without
the root application/PySide6 runtime components, and a SHA-256 file that does not
match the ZIP bytes. Confirm RED.

- [ ] **Step 3: Add the SBOM build dependency and workflow steps**

Add bounded `cyclonedx-bom>=7.3,<8` to the `dev` extra. In Windows CI create a
separate runtime-only virtual environment, install `.` into it, then generate:

```powershell
python -m cyclonedx_py environment --pyproject pyproject.toml --output-reproducible --output-format JSON --output-file El-Oraculo-de-ENOM-Windows.sbom.cdx.json .sbom-venv
```

Validate the generated BOM. Generate `El-Oraculo-de-ENOM-Windows.zip.sha256` with
`Get-FileHash -Algorithm SHA256`, using lowercase hex and the ZIP basename. Upload
the ZIP, SBOM and hash in one Actions artifact.

- [ ] **Step 4: Document consumer verification**

Add PowerShell commands to README for `Get-FileHash` comparison and identify the
SBOM as CycloneDX JSON. State accurately that hashes detect mismatch but are not a
substitute for Authenticode signing.

- [ ] **Step 5: Run local tests and review**

```bash
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest tests/release/test_distribution.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests scripts
git diff --check
```

- [ ] **Step 6: Commit, push and validate generated files**

```bash
git add CHANGELOG.md docs/release/1.0.0-notes.md pyproject.toml .github/workflows/build-windows.yml scripts/verify_distribution.py tests/release/test_distribution.py README.md docs/release/1.0.0-status.md
git commit -m "build: generate release metadata"
git push
gh pr checks --watch
```

Download the exact run artifact. Validate the ZIP, recompute SHA-256, parse the
SBOM, verify recorded versions, and update the status record with run/SHA/hash.

- [ ] **Step 7: Stop**

Report the three artifact filenames and verification evidence. Do not bump the
version or begin Tramo 16.

---

### Tramo 16: Candidato final 1.0.0

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/release/1.0.0-notes.md`
- Modify: `docs/release/1.0.0-status.md`
- Modify only if version assertions require it: `tests/release/test_distribution.py`

**Exit gate:** one immutable candidate commit consistently reports `1.0.0`, has all
local/Windows gates green, and its final pre-merge artifact is verified.

- [ ] **Step 1: Write/adjust the failing version consistency test**

Assert the PEP 621 version, README current version, changelog heading, release notes
and SBOM root component all equal `1.0.0`. Run it first against `0.1.0` and confirm
RED.

- [ ] **Step 2: Apply the version bump**

Change only release metadata from `0.1.0` to `1.0.0`; do not introduce application
features. Use the calendar date of the candidate for the changelog release heading.

- [ ] **Step 3: Run the full local candidate gate**

```bash
.venv/bin/python -m pip install -e '.[dev]'
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src tests scripts
git diff --check main...HEAD
.venv/bin/python -m PyInstaller El-Oraculo-de-ENOM.spec --clean --noconfirm
.venv/bin/python scripts/verify_distribution.py "dist/El Oraculo de ENOM"
```

- [ ] **Step 4: Review and commit the candidate**

```bash
git add pyproject.toml README.md CHANGELOG.md docs/release/1.0.0-notes.md docs/release/1.0.0-status.md tests/release/test_distribution.py
git commit -m "release: prepare version 1.0.0"
git push
gh pr checks --watch
```

Omit unchanged paths from `git add`.

- [ ] **Step 5: Verify the final PR artifact and freeze the SHA**

Download the run whose head SHA equals the candidate commit. Verify ZIP contract,
SHA-256 and SBOM, then perform a focused Windows launch, roll, persistence and
restart smoke test. Record candidate SHA, run URL and hashes in the status file;
commit/push that record and repeat CI so the recorded final PR HEAD itself is green.

- [ ] **Step 6: Final pre-merge review and stop**

Run `gh pr diff`, confirm no unresolved review threads or failing checks, and report
the exact candidate SHA. Do not merge, tag or publish; wait for explicit Tramo 17
authorization.

---

### Tramo 17: Integración y publicación

**Files:**
- No source changes expected.
- Modify only if evidence must be corrected before merge: `docs/release/1.0.0-status.md`.

**Exit gate:** reviewed PR merged, annotated `v1.0.0` tag points to the merge commit,
tag workflow green, and GitHub Release public with verified ZIP/SBOM/hash assets.

- [ ] **Step 1: Perform the irreversible-action preflight**

```bash
git status --short --branch
gh pr view --json state,mergeable,reviewDecision,headRefOid,statusCheckRollup,url
gh release view v1.0.0
git ls-remote --tags origin refs/tags/v1.0.0
```

Require clean state, green checks, expected candidate SHA, mergeable PR, and no
existing tag/release. Reconfirm that explicit authorization covers merge, tag and
public release. Stop on any mismatch.

- [ ] **Step 2: Merge without deleting or rewriting the local branch**

```bash
gh pr merge --merge
gh pr view --json state,mergedAt,mergeCommit,url
git fetch origin main
MERGE_COMMIT_SHA=$(gh pr view --json mergeCommit --jq .mergeCommit.oid)
git merge-base --is-ancestor "$MERGE_COMMIT_SHA" origin/main
```

Capture the merge commit SHA and confirm it is reachable from `origin/main`.

- [ ] **Step 3: Create and push the annotated tag**

```bash
git tag -a v1.0.0 "$MERGE_COMMIT_SHA" -m "El Oráculo de ENOM 1.0.0"
git push origin v1.0.0
git ls-remote --tags origin refs/tags/v1.0.0 refs/tags/v1.0.0^{}
```

- [ ] **Step 4: Validate the tag-triggered Windows build**

Find the `push` workflow run whose `headSha` is the merge commit and whose
`headBranch` is `v1.0.0`. Wait for success, download its artifact into a new
temporary directory, verify the ZIP with `scripts/verify_distribution.py`,
recompute SHA-256 and validate the SBOM. Use these exact shell variables and do
not reuse PR artifacts for publication:

```bash
RELEASE_DIR=$(mktemp -d)
TAG_RUN_ID=$(gh run list --workflow "Build Windows portable" --event push --status success --limit 20 --json databaseId,headBranch,headSha --jq ".[] | select(.headBranch == \"v1.0.0\" and .headSha == \"$MERGE_COMMIT_SHA\") | .databaseId" | head -1)
test -n "$TAG_RUN_ID"
gh run download "$TAG_RUN_ID" --name El-Oraculo-de-ENOM-Windows --dir "$RELEASE_DIR"
.venv/bin/python scripts/verify_distribution.py "$RELEASE_DIR/El-Oraculo-de-ENOM-Windows.zip"
sha256sum "$RELEASE_DIR/El-Oraculo-de-ENOM-Windows.zip"
```

- [ ] **Step 5: Publish the GitHub Release from the verified files**

```bash
gh release create v1.0.0 \
  "$RELEASE_DIR/El-Oraculo-de-ENOM-Windows.zip" \
  "$RELEASE_DIR/El-Oraculo-de-ENOM-Windows.zip.sha256" \
  "$RELEASE_DIR/El-Oraculo-de-ENOM-Windows.sbom.cdx.json" \
  --verify-tag \
  --title "El Oráculo de ENOM 1.0.0" \
  --notes-file docs/release/1.0.0-notes.md
```

- [ ] **Step 6: Verify the public release**

```bash
gh release view v1.0.0 --json url,tagName,targetCommitish,assets,publishedAt
```

Confirm the three asset names and sizes, download them from the release into a
second temporary directory, recompute the hash and re-run ZIP/SBOM validation.

- [ ] **Step 7: Stop and hand off**

Report merge SHA, tag target, workflow URL, release URL, asset hashes and final
verification. Do not create follow-up versions or alter `main`.
