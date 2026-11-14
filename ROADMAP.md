# SynthAI Studio Engineering Roadmap (`ROADMAP.md`)

## Overview

This roadmap tracks the sequential engineering milestones taking `synthai-studio` from initial repository bootstrap to production GitOps deployment on `mainframe`.

---

## Milestone Breakdown

| Milestone | Scope & Deliverables | Key Modules | Verification Gate |
| :--- | :--- | :--- | :--- |
| **Milestone 1** | PM PRD, Architecture ADR-0001, Pydantic v2 Domain Schemas, and 3 Deterministic Benchmark Seed Generators (Healthcare HIPAA, FinTech Fraud, B2B SaaS Churn). | `src/synthai_studio/models.py`<br/>`src/synthai_studio/benchmarks.py`<br/>`tests/test_models_and_benchmarks.py` | `pytest`, `ruff`, `mypy` clean; all models enforce DbC docstrings. |
| **Milestone 2** | Automated Schema Type Inference, Multi-Signal PII/PHI Scanner, Data Quality Defect Auditor, Dataset Cleanser/Anonymizer, and Statistical Distribution/Correlation Profiler. | `src/synthai_studio/profiler.py`<br/>`tests/test_profiler.py` | Detects planted PII and quality defects across all 3 benchmarks; cleansing raises quality score and masks PII. |
| **Milestone 3** | Differential Privacy Accountant ($\epsilon, \delta$-DP), Multivariate Gaussian Copula Synthesizer, CTGAN Latent Synthesizer, Faker Hybrid PII Synthesizer, DGX Spark LLM Edge Synthesizer (`< 2.0s` circuit breaker), and Conditional Minority Class Upsampler. | `src/synthai_studio/synthesizer.py`<br/>`tests/test_synthesizer.py` | Preserves correlations, respects condition filters and upsampling ratios, calibrates DP noise monotonically with $\epsilon$, and handles Spark fallback cleanly. |
| **Milestone 4** | Statistical Fidelity & Privacy Evaluator ($1 - D_{KS}$, $1 - \text{TVD}$, Frobenius Correlation Stability, Exact Collision, $DCR$, $NNDR$), DuckDB + Parquet/CSV Repository, Pre-signed Token Manager, and Temporal Workflows with Standalone Runner. | `src/synthai_studio/evaluator.py`<br/>`src/synthai_studio/repository.py`<br/>`src/synthai_studio/workflows.py`<br/>`tests/test_evaluator_and_repository.py` | End-to-end persistence in DuckDB, Parquet/CSV/JSON export, Markdown quality report generation, and workflow execution. |
| **Milestone 5** | FastAPI Service (`/healthz`, `/ready`, `/api/v1/*`), Interactive 5-Step SynthAI Studio Web UI (`GET /`), Multi-Stage Non-Root `Dockerfile`, Kustomize `deploy/base/` Manifests, and Pull Request Delivery. | `src/synthai_studio/api/main.py`<br/>`Dockerfile`<br/>`deploy/base/*`<br/>`tests/test_api.py` | Full API + UI integration test suite passing, `kubectl kustomize deploy/base` valid, PR opened on `paulojauregui/synthai-studio`. |
