# Milestone 08 Specification (`M08_SPEC.md`) — Typed UI Router, Static Asset Loader & Route Aliases

## 1. Objective
Create the typed UI asset loader and router helper `src/synthai_studio/api/ui.py`, refactor `src/synthai_studio/api/main.py` to remove the monolithic ~960-line inline `_build_studio_ui_html()` string while mounting `/static` via FastAPI `StaticFiles` and preserving all REST API contracts (plus canonical route aliases `/api/v1/benchmarks/{benchmark_id}/seed`, `/api/v1/presign`, `POST /api/v1/jobs`), and verify with `tests/test_ui_serving.py`.

## 2. Target Files (2 Source Files + 1 Test File)
1. `src/synthai_studio/api/ui.py`
2. `src/synthai_studio/api/main.py`
3. `tests/test_ui_serving.py`

## 3. Design-by-Contract Specifications

### 3.1 `src/synthai_studio/api/ui.py`
- **Pre-conditions**: `templates/index.html` and `static/` reside relative to `Path(__file__).resolve().parent`.
- **Post-conditions**:
  - Uses `pathlib.Path`, `functools.lru_cache`, `fastapi.FastAPI`, `fastapi.responses.HTMLResponse`, and `fastapi.staticfiles.StaticFiles`.
  - Exports (`__all__`):
    - `API_PACKAGE_DIR: Path`
    - `TEMPLATES_DIR: Path`
    - `STATIC_DIR: Path`
    - `get_templates_dir() -> Path` (with `Pre-conditions:` / `Post-conditions:` docstring)
    - `get_static_dir() -> Path` (with `Pre-conditions:` / `Post-conditions:` docstring)
    - `load_studio_index_html() -> str` (reads `TEMPLATES_DIR / "index.html"` as UTF-8, with `Pre-conditions:` / `Post-conditions:` docstring)
    - `mount_studio_ui(application: FastAPI) -> None` (mounts `StaticFiles(directory=str(get_static_dir()))` at `"/static"` with `name="static"` and registers `GET /` returning `HTMLResponse(content=load_studio_index_html(), status_code=200)`).

### 3.2 `src/synthai_studio/api/main.py`
- **Pre-conditions**: All domain modules and `synthai_studio.api.ui` are available.
- **Post-conditions**:
  - Removes the monolithic inline `_build_studio_ui_html()` function body (~960 lines) and delegates UI rendering and `/static` mounting to `mount_studio_ui(application)` from `synthai_studio.api.ui` (may also re-export `load_studio_index_html` as `_build_studio_ui_html` alias if any caller imports it).
  - Preserves ALL existing REST endpoints and response schemas cleanly:
    - `GET /healthz`
    - `GET /ready` (fast `< 50ms` DuckDB catalog check; never probes external Spark)
    - `GET /api/v1/benchmarks`
    - `POST /api/v1/datasets/seed/{benchmark_id}` AND alias `POST /api/v1/benchmarks/{benchmark_id}/seed`
    - `POST /api/v1/datasets/presign-upload` AND alias `POST /api/v1/presign`
    - `POST /api/v1/datasets/upload`
    - `GET /api/v1/datasets`
    - `GET /api/v1/datasets/{dataset_id}/profile`
    - `POST /api/v1/datasets/{dataset_id}/cleanse`
    - `POST /api/v1/jobs/generate` AND alias `POST /api/v1/jobs`
    - `GET /api/v1/jobs`
    - `GET /api/v1/jobs/{job_id}`
    - `GET /api/v1/jobs/{job_id}/report`
    - `GET /api/v1/jobs/{job_id}/download`
    - `GET /` and `GET /static/*`

### 3.3 `tests/test_ui_serving.py`
- **Pre-conditions**: `src/synthai_studio/api/ui.py` and `src/synthai_studio/api/main.py` are implemented.
- **Post-conditions**:
  - Verifies `get_templates_dir()`, `get_static_dir()`, and `load_studio_index_html()` resolve relative to `Path(__file__)` inside the package.
  - Verifies `GET /` returns `200 OK` with `text/html` MIME type and the modular HTML template content.
  - Verifies `GET /static/tokens.css` and `GET /static/components.css` return `200 OK` with `text/css` MIME type.
  - Verifies `/ready` responds in `< 50ms` and does not block on network calls.
  - Verifies route aliases `POST /api/v1/benchmarks/{benchmark_id}/seed`, `POST /api/v1/presign`, and `POST /api/v1/jobs` work identically to their canonical counterparts.
  - Verifies `src/synthai_studio/api/main.py` line count is `< 550` lines (confirming extraction of inline HTML/CSS/JS).

## 4. Verification Command
```bash
poetry run ruff check src/synthai_studio/api/ui.py src/synthai_studio/api/main.py tests/test_ui_serving.py tests/test_api.py && poetry run mypy src/synthai_studio/api/ui.py src/synthai_studio/api/main.py tests/test_ui_serving.py tests/test_api.py && poetry run pytest tests/test_ui_serving.py tests/test_api.py -v
```
