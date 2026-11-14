# Milestone 09 Specification (`M09_SPEC.md`) — Client JS State Store, Accessible Tab/Form Controller, `aria-live` Announcer & API Handlers

## 1. Objective
Implement the modular client-side state store, WAI-ARIA roving-`tabindex` keyboard controller, `aria-live` polite/assertive announcer, global error banner focus manager, and end-to-end API workflow handlers (`loadInitData`, `loadBenchmarks`, `seedBenchmark`, `handleUpload`, `generateTicket`, `loadDatasets`, `loadProfileForSelected`, `cleanseCurrentDataset`, `updateDpDefaults`, `handleGenerate`, `loadJobs`, `viewJobReport`, `loadReportForSelected`, `downloadArtifact`) in `src/synthai_studio/api/static/app.js`, and verify contracts in `tests/test_ui_js_contract.py`.

## 2. Target Files (1 JS File + 1 Test File)
1. `src/synthai_studio/api/static/app.js`
2. `tests/test_ui_js_contract.py`

## 3. Design-by-Contract Specifications

### 3.1 `src/synthai_studio/api/static/app.js`
- **Pre-conditions**: Loaded in `index.html` alongside `views.js` (`window.SynthAIViews` or fallback inline helpers when `window.SynthAIViews` is loaded).
- **Post-conditions**:
  - Zero emojis anywhere in `app.js`.
  - **Centralized State Store (`StudioState`)**:
    - Tracks `activeStep` (`1..5`), `benchmarks` (`BenchmarkMetadata[]`), `datasets` (`DatasetMetadata[]`), `jobs` (`GenerationJob[]`), `currentDatasetId`, `currentJobId`, `currentProfile` (`DatasetProfileReport | null`), `currentReport` (`QualityValidationReport | null`).
  - **ARIA Live Announcer (`announcePolite(message)`, `announceAssertive(message)`)**:
    - Updates `#aria-status-polite` (`role="status"`, `aria-live="polite"`) and `#aria-status-assertive` (`role="alert"`, `aria-live="assertive"`).
  - **Global Error Banner & Focus Recovery (`showGlobalError(title, detail, retryCallback)`, `dismissGlobalError()`)**:
    - Populates `#global-error-banner`, removes `hidden`, announces via `announceAssertive`, and moves focus to `#global-error-banner` (`el.focus()`).
    - Pressing `Escape` or clicking `#global-error-dismiss` hides `#global-error-banner` and returns focus to `#tab-step-${StudioState.activeStep}`.
  - **Accessible Tablist & Roving `tabindex` Controller (`switchStep(step, focusTab = false)`, `handleTabKeydown(evt)`)**:
    - Updates `.step-panel` (`classList.toggle('active', isTarget)` and `panel.hidden = !isTarget`).
    - Updates `#tab-step-1..5` (`classList.toggle('active', isTarget)`, `aria-selected="true|false"`, `tabindex="0|-1"`).
    - Supports `ArrowRight` / `ArrowDown` (next tab wrapping 5 -> 1), `ArrowLeft` / `ArrowUp` (prev tab wrapping 1 -> 5), `Home` (Step 1), `End` (Step 5), `Enter` / `Space`, and `Escape`.
  - **Exact Pydantic v2 Schema Field Alignment (`models.py`)**:
    - **Step 1**: Uses `b.benchmark_id`, `b.name`, `b.domain`, `b.description`, `b.default_row_count`, `b.target_column`, `b.minority_label`, `b.pii_columns`, `b.highlights` (never `b.planted_defects`).
    - **Step 2**: Joins `prof.columns` (`c.name`, `c.inferred_type`, `c.pii_type`, `c.null_count`, `c.null_ratio`, `c.numerical_stats`) with `prof.pii_findings` (`f.column_name`, `f.confidence`, `f.remediation`) and renders `prof.quality_issues` (`issue.severity`, `issue.issue_type`, `issue.column_name`, `issue.affected_rows`, `issue.description`, `issue.suggested_action`).
    - **Step 3 (`SynthesisConfig`)**:
      - `updateDpDefaults()` maps `HIGH -> epsilon: 0.1, delta: 1e-6`, `MEDIUM -> epsilon: 1.0, delta: 1e-5`, `LOW -> epsilon: 10.0, delta: 1e-5`, `NONE -> epsilon disabled (null), delta: 1e-5`, and updates `#dp-guarantee-preview` (`.state-degraded` when `NONE` or `SPARK_LLM_EDGE` circuit-breaker info).
      - `handleGenerate(evt)` builds `upsample_config: { column: targetCol, minority_value: parsedVal, target_ratio: minorityRatio }` when `targetCol` is non-empty, or `upsample_config: null` when empty, matching `SynthesisConfig` in `models.py`.
    - **Step 4 & Step 5**: Delegates rendering to `window.SynthAIViews` (with safe fallback if needed) for `#jobs-table`, `#compute-fallback-banner`, `#privacy-ledger-card`, `#fidelity-columns-table`, and `QualityValidationReport`.

### 3.2 `tests/test_ui_js_contract.py`
- **Pre-conditions**: `src/synthai_studio/api/static/app.js` exists and is served at `GET /static/app.js`.
- **Post-conditions**:
  - Verifies `GET /static/app.js` returns `200 OK` with `javascript` content-type.
  - Verifies `app.js` implements `switchStep`, `handleTabKeydown`, `ArrowRight`, `ArrowLeft`, `Home`, `End`, `Escape`, `aria-selected`, `tabindex`, `announcePolite`, `announceAssertive`, `showGlobalError`, `dismissGlobalError`.
  - Verifies `app.js` uses the exact `models.py` schema fields (`pii_columns`, `highlights`, `inferred_type`, `pii_findings`, `quality_issues`, `upsample_config`, `minority_value`, `target_ratio`, `compute_tier`, `epsilon_spent`, `dcr_median`, `nndr_median`, `exact_match_collision_rate`, `pii_leakage_detected`, `column_metrics`) and never references legacy non-existent fields (`planted_defects`, `dcr_mean`, `nndr_mean`).

## 4. Verification Command
```bash
poetry run ruff check tests/test_ui_js_contract.py && poetry run mypy tests/test_ui_js_contract.py && poetry run pytest tests/test_ui_js_contract.py -v
```
