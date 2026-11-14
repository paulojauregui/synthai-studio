# Milestone 07 Specification (`M07_SPEC.md`) — Semantic HTML5 5-Step Workbench Shell

## 1. Objective
Extract and upgrade the SynthAI Studio frontend markup into a clean, modular HTML5 template at `src/synthai_studio/api/templates/index.html` and validate all structural landmarks, WAI-ARIA tablist attributes, explicit form `<label for="...">` bindings, live status regions, and 5-step containers with `tests/test_ui_html_contract.py` in accordance with `docs/UX_SPEC.md` and `docs/DESIGN_SYSTEM.md`.

## 2. Target Files (1 Template File + 1 Test File)
1. `src/synthai_studio/api/templates/index.html`
2. `tests/test_ui_html_contract.py`

## 3. Design-by-Contract Specifications

### 3.1 `src/synthai_studio/api/templates/index.html`
- **Pre-conditions**: Served at `GET /` and styled by `/static/tokens.css` and `/static/components.css`, with interactive behavior provided by `/static/views.js` and `/static/app.js`.
- **Post-conditions**:
  - Valid HTML5 document (`<!DOCTYPE html>`, `<html lang="en">`) with zero emojis and zero inline `<style>` or `<script>` blocks:
    - Links `<link rel="stylesheet" href="/static/tokens.css">` and `<link rel="stylesheet" href="/static/components.css">`.
    - Loads `<script src="/static/views.js" defer></script>` and `<script src="/static/app.js" defer></script>`.
  - **Backward-Compatibility Invariants** (`tests/test_api.py::test_interactive_web_ui_endpoint`):
    - Contains exact substrings `"SYNTHAI STUDIO"`, `"DIFFERENTIAL PRIVACY"`, `"step-1"`, `"step-2"`, `"step-3"`, `"step-4"`, `"step-5"`.
  - **Accessibility Landmarks & Live Regions**:
    - First child of `<body>`: `<a href="#main-workbench" class="skip-link">Skip to main workbench</a>`.
    - Dedicated ARIA live status regions:
      - `<div id="aria-status-polite" class="sr-only" role="status" aria-live="polite" aria-atomic="true"></div>`
      - `<div id="aria-status-assertive" class="sr-only" role="alert" aria-live="assertive" aria-atomic="true"></div>`
    - `<header role="banner">` with `.brand-title` (`SYNTHAI STUDIO // AUTONOMOUS PRIVACY &amp; FIDELITY ENGINE`), `.brand-subtitle` (`DIFFERENTIAL PRIVACY (EPSILON, DELTA) // GENERATIVE MODELS // HIPAA &amp; GDPR COMPLIANCE`), and `.cluster-status` containing `#status-service`, `#status-catalog`, and `#status-temporal`.
    - `<nav aria-label="SynthAI Studio Workflow Steps">` wrapping `<div role="tablist" aria-label="5-Step Synthesis Pipeline" id="workflow-tablist">` with 5 `<button type="button" role="tab" class="nav-tab">` elements:
      - `#tab-step-1` (`aria-selected="true"`, `aria-controls="step-1"`, `tabindex="0"`, `data-step="1"`): `1. Connect &amp; Seed`
      - `#tab-step-2` (`aria-selected="false"`, `aria-controls="step-2"`, `tabindex="-1"`, `data-step="2"`): `2. Quality &amp; PII Audit`
      - `#tab-step-3` (`aria-selected="false"`, `aria-controls="step-3"`, `tabindex="-1"`, `data-step="3"`): `3. Engine &amp; DP Config`
      - `#tab-step-4` (`aria-selected="false"`, `aria-controls="step-4"`, `tabindex="-1"`, `data-step="4"`): `4. Worker Monitor`
      - `#tab-step-5` (`aria-selected="false"`, `aria-controls="step-5"`, `tabindex="-1"`, `data-step="5"`): `5. Fidelity &amp; Export`
    - `<main id="main-workbench" tabindex="-1">` containing:
      - Global error alert banner: `<div id="global-error-banner" class="error-banner state-error" role="alert" tabindex="-1" hidden>` with `#global-error-text` and `<button type="button" id="global-error-dismiss" class="btn btn-secondary">Dismiss Error</button>`.
      - **Step 1 (`<section id="step-1" class="step-panel active" role="tabpanel" aria-labelledby="tab-step-1">`)**:
        - `#benchmark-cards` container (`aria-live="polite"`).
        - `#upload-form` with explicit `<label for="upload-name">` + `<input type="text" id="upload-name" required>` and `<label for="upload-file">` + `<input type="file" id="upload-file" accept=".csv,.json" required>`, plus submit button `#btn-upload-dataset`.
        - Presigned capability card with `<label for="presign-name">` + `<input type="text" id="presign-name">`, `<button type="button" id="btn-generate-ticket" class="btn btn-secondary">Generate Ticket</button>`, and `#presign-result` (`hidden`) containing `<pre id="presign-text" class="tabular-nums"></pre>`.
      - **Step 2 (`<section id="step-2" class="step-panel" role="tabpanel" aria-labelledby="tab-step-2" hidden>`)**:
        - Dataset selector `<label for="profile-dataset-select">` + `<select id="profile-dataset-select"></select>` and `<button type="button" id="btn-cleanse-dataset" class="btn btn-emerald">[1-Click Cleanse &amp; Anonymize]</button>`.
        - `#profile-empty-state` (`hidden`) for empty state recovery.
        - 4 KPI stat tiles with `.tabular-nums`: `#prof-rows`, `#prof-cols`, `#prof-quality`, `#prof-privacy-risk`.
        - `.table-scroll-wrapper` wrapping `<table id="profile-columns-table">` with `<th scope="col">` headers (`Column Name`, `Inferred Type`, `PII Finding`, `Confidence & Remediation`, `Null Count`, `Outliers (|z|>3)`).
        - `#profile-issues-list` container for `DataQualityIssue` items.
        - `.table-scroll-wrapper` (`#profile-corr-wrapper`) wrapping `<table id="profile-corr-table">`.
      - **Step 3 (`<section id="step-3" class="step-panel" role="tabpanel" aria-labelledby="tab-step-3" hidden>`)**:
        - `<form id="synth-config-form">` with explicit `<label for="...">` for every control:
          - `#gen-dataset-id` (`<select required>`)
          - `#gen-target-rows` (`<input type="number" class="tabular-nums" value="250" min="10" max="200000" step="10" required>`)
          - `#gen-engine` (`<select>` with `GAUSSIAN_COPULA`, `CTGAN_LATENT`, `FAKER_HYBRID`, `SPARK_LLM_EDGE`)
          - `#gen-privacy-level` (`<select>` with `MEDIUM`, `LOW`, `HIGH`, `NONE`)
          - `#gen-epsilon` (`<input type="number" class="tabular-nums" value="1.0" min="0.01" max="100.0" step="0.05">`)
          - `#gen-delta` (`<input type="number" class="tabular-nums" value="0.00001" min="0.0000001" max="0.1" step="0.000001">`)
          - `#gen-target-col` (`<input type="text">`)
          - `#gen-minority-val` (`<input type="text">`)
          - `#gen-minority-ratio` (`<input type="number" class="tabular-nums" value="0.30" min="0.05" max="0.95" step="0.05">`)
          - `#gen-anonymize-pii` (`<input type="checkbox" checked>`)
          - `#dp-guarantee-preview` (`<div class="state-nominal" role="status">`)
          - `#btn-launch-synth` (`<button type="submit" class="btn btn-emerald">`)
      - **Step 4 (`<section id="step-4" class="step-panel" role="tabpanel" aria-labelledby="tab-step-4" hidden>`)**:
        - `#compute-fallback-banner` (`<div class="degraded-banner state-degraded" role="status" hidden>`) alerting operators when `SPARK_LLM_EDGE` falls back to `ComputeTier.CPU_WORKER` (`local_copula`) via the `< 2.0s` circuit breaker.
        - `#btn-refresh-jobs` (`<button type="button" class="btn btn-secondary">Refresh Jobs</button>`).
        - `.table-scroll-wrapper` wrapping `<table id="jobs-table">` with `<th scope="col">` headers (`Job ID`, `Dataset`, `Engine`, `Compute Tier`, `Status`, `Rows & Throughput`, `Action`).
        - `#privacy-ledger-card` with `#ledger-status`, `#ledger-spent` (`.stat-val.tabular-nums`), `#ledger-noise-scale` (`.stat-val.tabular-nums`), `#ledger-remaining` (`.stat-val.tabular-nums`), `#ledger-delta` (`.tabular-nums`), `#ledger-initial` (`.tabular-nums`), `#ledger-mechanism`, and `#ledger-psd`.
        - `#worker-console` (`<div class="log-console tabular-nums" role="log" aria-live="polite">`).
      - **Step 5 (`<section id="step-5" class="step-panel" role="tabpanel" aria-labelledby="tab-step-5" hidden>`)**:
        - `<label for="report-job-select">` + `<select id="report-job-select"></select>`.
        - `#compute-fallback-banner-step5` (`<div class="degraded-banner state-degraded" role="status" hidden>`).
        - `#report-empty-state` (`hidden`).
        - 4 KPI stat tiles with `.tabular-nums`: `#rep-quality`, `#rep-fidelity`, `#rep-corr`, `#rep-privacy`.
        - Executive Compliance Verdict card (`#rep-verdict`, `#rep-hipaa`, `#rep-dcr`, `#rep-nndr`, `#rep-collisions`, `#rep-pii-leaks` with `.tabular-nums`).
        - 1-Click Artifact Downloads (`#btn-dl-csv`, `#btn-dl-json`, `#btn-dl-parquet`, `#btn-dl-markdown`).
        - `.table-scroll-wrapper` wrapping `<table id="fidelity-columns-table">` with `<th scope="col">` headers (`Column Name`, `Type`, `Metric`, `Fidelity Score`, `Stat Distance`, `JS Similarity`).

### 3.2 `tests/test_ui_html_contract.py`
- **Pre-conditions**: `src/synthai_studio/api/templates/index.html` exists.
- **Post-conditions**:
  - Uses Python's standard library `html.parser.HTMLParser` to parse `index.html` and deterministically assert:
    - Presence of `.skip-link` pointing to `#main-workbench`.
    - Semantic landmarks `<header role="banner">`, `<nav>`, `<div role="tablist" id="workflow-tablist">`, 5 `<button role="tab">` tabs (`#tab-step-1`..`#tab-step-5`) with matching `aria-controls="step-1..5"`, `aria-selected`, and roving `tabindex`, `<main id="main-workbench">`, and 5 `<section role="tabpanel" id="step-1..5">` panels.
    - Every `<input>` and `<select>` has a matching `<label for="...">` element in the DOM.
    - Both `#aria-status-polite` and `#aria-status-assertive` live regions exist.
    - `#global-error-banner`, `#compute-fallback-banner`, and `#compute-fallback-banner-step5` exist.
    - External links `/static/tokens.css`, `/static/components.css`, `/static/views.js`, `/static/app.js` are present and zero inline `<style>` or `<script>` blocks exist.
    - Zero emojis appear anywhere in `index.html`.

## 4. Verification Command
```bash
poetry run ruff check tests/test_ui_html_contract.py && poetry run mypy tests/test_ui_html_contract.py && poetry run pytest tests/test_ui_html_contract.py -v
```
