# Milestone 10 Specification (`M10_SPEC.md`) — 5-State Renderers, `tabular-nums` Correlation & Fidelity Views, `ComputeTier` Degraded Fallback Banner & Error Recovery

## 1. Objective
Implement `src/synthai_studio/api/static/views.js` (`window.SynthAIViews`) providing deterministic 5-state DOM renderers (`.state-empty`, `.state-loading` zero-CLS skeletons, `.state-nominal`, `.state-degraded`, `.state-error`), `tabular-nums` Pearson correlation matrix and column-level fidelity table (`1 - KS`, `1 - TVD`, `JS Similarity`) renderers, `ComputeTier.CPU_WORKER` degraded fallback banner controller (`#compute-fallback-banner` and `#compute-fallback-banner-step5`), and Privacy Budget Ledger renderer, validated by `tests/test_ui_states.py`.

## 2. Target Files (1 JS File + 1 Test File)
1. `src/synthai_studio/api/static/views.js`
2. `tests/test_ui_states.py`

## 3. Design-by-Contract Specifications

### 3.1 `src/synthai_studio/api/static/views.js`
- **Pre-conditions**: Loaded before `app.js` in `templates/index.html` and exposes `window.SynthAIViews`.
- **Post-conditions**:
  - Zero emojis anywhere in `views.js`.
  - Exposes deterministic view rendering functions on `window.SynthAIViews`:
    1. `escapeHtml(val)`: Sanitizes dynamic strings against XSS before DOM insertion.
    2. `renderEmptyState(container, title, message, ctaLabel, ctaAction)`: Applies `.state-empty` and renders guided empty state with 1-click CTA button.
    3. `renderLoadingSkeleton(container, variant, count)`: Sets `aria-busy="true"`, applies `.state-loading`, and renders `.skeleton-card` (`min-height: 136px`), `.skeleton-tile` (`min-height: 84px`), or `.skeleton-row` (`height: 37px`) for `CLS = 0`.
    4. `renderErrorState(container, title, detail, retryLabel, retryAction)`: Applies `.state-error` and renders actionable retry button.
    5. `renderBenchmarkCards(container, benchmarks)`: Renders Step 1 benchmark cards with `b.domain`, `b.default_row_count` (`.tabular-nums`), `b.target_column` (`b.minority_label`), `b.pii_columns` badges (`.badge-danger`), `b.highlights` badges (`.badge-info`), and `[Seed Benchmark Dataset]` button.
    6. `renderProfileView(prof)`:
       - Updates `#prof-rows`, `#prof-cols`, `#prof-quality`, `#prof-privacy-risk` with `.tabular-nums`.
       - Joins `prof.columns` (`c.name`, `c.inferred_type`, `c.pii_type`, `c.null_count`, `c.null_ratio`, `c.numerical_stats`) with `prof.pii_findings` (`f.column_name === c.name`) to render `<th scope="row">` column names, semantic PII badges, confidence %, remediation guidance, null count/ratio (`td[data-numeric="true"]`), and z-score outlier count (`td[data-numeric="true"]`).
       - Renders `prof.quality_issues` into `#profile-issues-list` with severity badges (`CRITICAL`/`HIGH` -> `.badge-danger`, `MEDIUM` -> `.badge-warn`, `LOW` -> `.badge-info`).
       - Renders `prof.correlation_columns` and `prof.correlation_matrix` into `#profile-corr-table` with `<th scope="col">`, `<th scope="row">`, and `.corr-cell.tabular-nums` cells (`data-numeric="true"`), or `.state-degraded` when `correlation_columns.length === 0`.
    7. `renderJobsAndLedger(jobs, selectedJobId)`:
       - Renders `#jobs-table` with `<th scope="row">` `job_id`, `dataset_name`, `config.engine`, `compute_tier` badge (`GPU_SPARK_WORKER` -> `.badge-info`, `CPU_WORKER` -> `.badge-warn` when `config.engine === "SPARK_LLM_EDGE"` else `.badge-success`), `status`, `rows_generated` & `throughput_rows_per_sec` (`td[data-numeric="true"] .tabular-nums`), and `[Audit Report]` button.
       - Evaluates `updateComputeFallbackBanner(job, report)`: when `engine === "SPARK_LLM_EDGE"` and `compute_tier === "CPU_WORKER"`, unhides `#compute-fallback-banner` and `#compute-fallback-banner-step5` (`.degraded-banner.state-degraded`) explaining that the `< 2.0s` DGX Spark circuit breaker tripped and cleanly fell back to `ComputeTier.CPU_WORKER` (`local_copula`).
       - Updates `#privacy-ledger-card` (`#ledger-status`, `#ledger-spent`, `#ledger-noise-scale`, `#ledger-remaining`, `#ledger-delta`, `#ledger-initial`, `#ledger-mechanism`, `#ledger-psd`) from `PrivacyBudgetLedger`.
    8. `renderQualityReportView(report, job)`:
       - Updates `#rep-quality`, `#rep-fidelity`, `#rep-corr`, `#rep-privacy`, `#rep-verdict`, `#rep-hipaa` (`CERTIFIED READY` / `NOT READY`), `#rep-dcr` (`dcr_median`, `dcr_p05`), `#rep-nndr` (`nndr_median`, `nndr_p05`), `#rep-collisions` (`exact_match_collision_rate`), `#rep-pii-leaks` (`pii_leakage_detected`).
       - Renders `report.column_metrics` into `#fidelity-columns-table` with `<th scope="row">` `cm.column_name`, `cm.column_type`, `cm.metric_name` (`1 - KS` / `1 - TVD`), `cm.score` (`td[data-numeric="true"]`), `cm.statistic_distance` (`td[data-numeric="true"]`), and `cm.jensen_shannon_similarity` (`td[data-numeric="true"]`).

### 3.2 `tests/test_ui_states.py`
- **Pre-conditions**: `src/synthai_studio/api/static/views.js` exists and is served at `GET /static/views.js`.
- **Post-conditions**:
  - Verifies `GET /static/views.js` returns `200 OK` with `javascript` MIME type.
  - Verifies all 5 state renderers (`state-empty`, `state-loading` with `aria-busy="true"` and `.skeleton-tile`/`.skeleton-row`/`.skeleton-card`, `state-nominal`, `state-degraded` with `SPARK_LLM_EDGE` -> `CPU_WORKER` fallback detection, and `state-error` with retry recovery) are defined in `views.js`.
  - Verifies `data-numeric="true"`, `tabular-nums`, `<th scope="row">`, `<th scope="col">`, `escapeHtml`, and end-to-end API integration with a simulated `SPARK_LLM_EDGE` fallback job (`compute_tier == "CPU_WORKER"`).

## 4. Verification Command
```bash
poetry run ruff check tests/test_ui_states.py && poetry run mypy tests/test_ui_states.py && poetry run pytest tests/test_ui_states.py -v
```
