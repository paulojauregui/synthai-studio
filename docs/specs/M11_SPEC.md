# Milestone 11 Specification (`M11_SPEC.md`) — Tooling/Packaging Modernization & Documentation Update

## 1. Objective
Align `pyproject.toml` with Python 3.13 (`target-version = "py313"`, `python_version = "3.13"`) and explicitly declare non-Python package assets (`templates/*.html`, `static/*.css`, `static/*.js`) under `[tool.poetry] include`, update `ROADMAP.md` and `README.md` with Iteration 2 (`v2-ux`) architecture and milestones (`M06`–`M11`), and verify the complete test suite (`tests/test_api.py` + all new UI contract suites).

## 2. Target Files (3 Project/Doc Files + 1 Test File)
1. `pyproject.toml`
2. `ROADMAP.md`
3. `README.md`
4. `tests/test_api.py`

## 3. Design-by-Contract Specifications

### 3.1 `pyproject.toml`
- **Pre-conditions**: Existing Poetry configuration in `/home/tron/workspace/synthai-studio/pyproject.toml`.
- **Post-conditions**:
  - Under `[tool.poetry]`, declares `include = ["src/synthai_studio/api/templates/*.html", "src/synthai_studio/api/static/*.css", "src/synthai_studio/api/static/*.js"]` so wheel/sdist builds package all extracted frontend assets.
  - Under `[tool.ruff]`, updates `target-version = "py313"`.
  - Under `[tool.mypy]`, updates `python_version = "3.13"`.

### 3.2 `ROADMAP.md` & `README.md`
- **Pre-conditions**: Existing documentation from Milestone 5.
- **Post-conditions**:
  - Zero emojis anywhere in `ROADMAP.md` or `README.md`.
  - `ROADMAP.md` documents Milestones 6 through 11 (`v2-ux` UI/UX Architecture, Design System Tokens, Semantic HTML5 Workbench, Typed UI Router, Accessible JS Controller, 5-State Renderers & ComputeTier Provenance, and Packaging Modernization).
  - `README.md` reflects the modular `src/synthai_studio/api/{ui.py,templates/index.html,static/{tokens.css,components.css,views.js,app.js}}` architecture, `docs/UX_SPEC.md`, and `docs/DESIGN_SYSTEM.md`.

### 3.3 `tests/test_api.py`
- **Pre-conditions**: All 14 existing integration tests in `tests/test_api.py` must remain intact and passing.
- **Post-conditions**:
  - Preserves all 14 existing tests in `tests/test_api.py` and adds verification that package asset inclusion in `pyproject.toml` and `py313` tooling configuration are active.

## 4. Verification Command
```bash
poetry run ruff check . && poetry run mypy src tests && poetry run pytest -v && kubectl kustomize deploy/base >/dev/null
```
