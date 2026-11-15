# SynthAI Studio Engineering Roadmap (`ROADMAP.md`)

## Overview

This roadmap tracks the sequential engineering milestones taking `synthai-studio` from initial repository bootstrap to production GitOps deployment on `mainframe`.

---

## Milestone Breakdown

### Iteration 1 -- Backend Core Engine & Initial Prototype (Milestones 1--5)

| Milestone | Scope & Deliverables | Key Modules | Verification Gate |
| :--- | :--- | :--- | :--- |
| **Milestone 1** | PM PRD, Architecture ADR-0001, Pydantic v2 Domain Schemas, and 3 Deterministic Benchmark Seed Generators (Healthcare HIPAA, FinTech Fraud, B2B SaaS Churn). | `src/synthai_studio/models.py`<br/>`src/synthai_studio/benchmarks.py`<br/>`tests/test_models_and_benchmarks.py` | `pytest`, `ruff`, `mypy` clean; all models enforce DbC docstrings. |
| **Milestone 2** | Automated Schema Type Inference, Multi-Signal PII/PHI Scanner, Data Quality Defect Auditor, Dataset Cleanser/Anonymizer, and Statistical Distribution/Correlation Profiler. | `src/synthai_studio/profiler.py`<br/>`tests/test_profiler.py` | Detects planted PII and quality defects across all 3 benchmarks; cleansing raises quality score and masks PII. |
| **Milestone 3** | Differential Privacy Accountant ($\epsilon, \delta$-DP), Multivariate Gaussian Copula Synthesizer, CTGAN Latent Synthesizer, Faker Hybrid PII Synthesizer, DGX Spark LLM Edge Synthesizer (`< 2.0s` circuit breaker), and Conditional Minority Class Upsampler. | `src/synthai_studio/synthesizer.py`<br/>`tests/test_synthesizer.py` | Preserves correlations, respects condition filters and upsampling ratios, calibrates DP noise monotonically with $\epsilon$, and handles Spark fallback cleanly. |
| **Milestone 4** | Statistical Fidelity & Privacy Evaluator ($1 - D_{KS}$, $1 - \text{TVD}$, Frobenius Correlation Stability, Exact Collision, $DCR$, $NNDR$), DuckDB + Parquet/CSV Repository, Pre-signed Token Manager, and Temporal Workflows with Standalone Runner. | `src/synthai_studio/evaluator.py`<br/>`src/synthai_studio/repository.py`<br/>`src/synthai_studio/workflows.py`<br/>`tests/test_evaluator_and_repository.py` | End-to-end persistence in DuckDB, Parquet/CSV/JSON export, Markdown quality report generation, and workflow execution. |
| **Milestone 5** | FastAPI Service (`/healthz`, `/ready`, `/api/v1/*`), Interactive 5-Step SynthAI Studio Web UI (`GET /`), Multi-Stage Non-Root `Dockerfile`, Kustomize `deploy/base/` Manifests, and Pull Request Delivery. | `src/synthai_studio/api/main.py`<br/>`Dockerfile`<br/>`deploy/base/*`<br/>`tests/test_api.py` | Full API + UI integration test suite passing, `kubectl kustomize deploy/base` valid, PR opened on `paulojauregui/synthai-studio`. |

### Iteration 2 -- Production UI/UX Architecture & Design System Modernization (`v2-ux`)

| Milestone | Scope & Deliverables | Key Modules | Verification Gate |
| :--- | :--- | :--- | :--- |
| **Milestone 6** | Design Tokens Architecture (`tokens.css`), 4-tier dark surface elevation hierarchy, WCAG 2.2 AA contrast ink tokens, and modular 5-state stylesheet (`components.css`). | `src/synthai_studio/api/static/tokens.css`<br/>`src/synthai_studio/api/static/components.css`<br/>`tests/test_ui_assets.py` | 21/21 asset contract tests passing; zero hardcoded raw hex colors in `components.css`; programmatic WCAG relative luminance contrast $\ge 4.5:1$. |
| **Milestone 7** | Semantic HTML5 5-Step Workbench Shell (`templates/index.html`), WAI-ARIA tablist roving `tabindex`, dedicated `aria-live` announcer regions, and explicit `<label for="...">` bindings for 100% of inputs and selects. | `src/synthai_studio/api/templates/index.html`<br/>`tests/test_ui_html_contract.py` | 16/16 HTML contract tests passing; zero inline style/script tags; zero emojis; pure standard HTML5 landmarks and live regions. |
| **Milestone 8** | Typed UI Router, static asset mounting (`StaticFiles`), cached template loader (`ui.py`), and monolithic ~960-line HTML extraction from `main.py` with canonical route aliases. | `src/synthai_studio/api/ui.py`<br/>`src/synthai_studio/api/main.py`<br/>`tests/test_ui_serving.py` | 22/22 API & UI serving tests passing; `main.py` line count reduced to 506 lines ($< 550$ threshold); `/ready` latency $< 50\text{ms}$. |
| **Milestone 9** | Client-side application state store (`StudioState`), WAI-ARIA roving-`tabindex` keyboard controller, polite/assertive announcers, global error focus recovery, and end-to-end API workflow handlers. | `src/synthai_studio/api/static/app.js`<br/>`tests/test_ui_js_contract.py` | 9/9 JS contract tests passing; exact alignment with Pydantic v2 `models.py` schema fields; zero references to legacy non-existent fields. |
| **Milestone 10** | Deterministic 5-State Renderers (`state-empty`, `state-loading` zero-CLS skeletons, `state-nominal`, `state-degraded`, `state-error`), Pearson correlation heatmap, column-level fidelity table, and `ComputeTier.CPU_WORKER` degraded fallback banner controller. | `src/synthai_studio/api/static/views.js`<br/>`tests/test_ui_states.py` | 9/9 UI state tests passing; end-to-end simulated DGX Spark probe circuit breaker fallback verified against `ComputeTier.CPU_WORKER`. |
| **Milestone 11** | Tooling & Packaging Modernization (Python 3.13 target, explicit non-Python asset packaging in `pyproject.toml`), Engineering Documentation (`ROADMAP.md`, `README.md`), and Full Test Suite Verification. | `pyproject.toml`<br/>`ROADMAP.md`<br/>`README.md`<br/>`tests/test_api.py` | All 118+ tests passing across 7 test modules; clean `ruff check .` and `mypy src tests` under Python 3.13; Kustomize manifest validation. |
