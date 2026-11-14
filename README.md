# SynthAI Studio

Autonomous Privacy-Preserving Synthetic Data Generation, Differential Privacy ($\epsilon, \delta$) Accounting, and Statistical Quality Auditing Engine.

---

## 1. Executive Summary & System Overview

**SynthAI Studio** is an enterprise-grade synthetic data platform engineered for high-security environments subject to HIPAA, GDPR, and PCI-DSS compliance mandates. It provides autonomous tabular data profiling, multi-signal PII/PHI redaction, multi-engine generative modeling, formal differential privacy budget accounting, and automated statistical fidelity certification.

The platform operates under the **Three-Tier Advisor-Executor Protocol**:
1. **Lead Architect (`Gemini 4 Argon`)**: Workspace topology analysis, formal specifications (`SPEC.md`), and Design-by-Contract verification.
2. **Local Autonomous Coder (`@spark-coder` on DGX Spark `happy.tail749110.ts.net`)**: High-speed, zero-cloud-token code synthesis using `nvidia/Qwen3.8-Flash-Next-FP4-Local` with a strict `< 2.0s` split-timeout pre-flight health probe.
3. **Cloud Fallback & Tactical Executor (`@flash-executor` on Gemini Flash)**: Automated multi-file synthesis failover, static typing, and sub-second verification loops when DGX Spark reports circuit-breaker tripping.

```mermaid
flowchart TD
    subgraph ClientLayer["Client & Ingestion Layer"]
        UI["5-Step Studio Web UI<br/>(GET / via ui.py & templates/index.html)"]
        CLI["API Clients & Presigned Tickets<br/>(S3 / SeaweedFS)"]
    end

    subgraph ServiceLayer["SynthAI Studio Core Service (:8000)"]
        API["FastAPI REST Application<br/>(synthai_studio.api.main)"]
        UIRouter["UI Router & Static Assets<br/>(synthai_studio.api.ui)"]
        Prof["Data Quality & PII Auditor<br/>(synthai_studio.profiler)"]
        Cleanse["Cleansing & Winsorization Engine<br/>(Z-Score Iterative Filter)"]
    end

    subgraph SynthesisLayer["Multi-Engine Synthesis Core"]
        GC["GaussianCopulaSynthesizer<br/>(High-Speed PSD Rank Coupling)"]
        CT["CTGANLatentSynthesizer<br/>(GMM Mode-Specific Normalization)"]
        FH["FakerHybridSynthesizer<br/>(Deterministic Token Masking)"]
        Spark["SparkLLMEdgeSynthesizer<br/>(< 2.0s DGX Spark Circuit Breaker)"]
        DP["Differential Privacy Accountant<br/>(Renyi / Gaussian Mechanism)"]
    end

    subgraph AuditLayer["Statistical Fidelity & Compliance Audit"]
        Eval["Quality & Privacy Evaluator<br/>(synthai_studio.evaluator)"]
        KS["1 - D_KS Marginal Fidelity"]
        TVD["1 - TVD Categorical Fidelity"]
        Corr["Frobenius Correlation Stability"]
        DCR["DCR & NNDR Privacy Proofs"]
    end

    subgraph StorageLayer["Persistence & Durable Execution"]
        DuckDB["DuckDB Embedded Catalog<br/>(Metadata, Profiles, Jobs, Tickets)"]
        Arrow["PyArrow IPC & Parquet Storage<br/>(Zero-Copy Streaming)"]
        Temporal["Temporal.io Durable Workflows<br/>(DatasetProfile & Generation)"]
    end

    UI --> UIRouter
    UIRouter --> API
    CLI --> API
    API --> Prof
    API --> Cleanse
    Prof --> DuckDB
    Cleanse --> DuckDB

    API --> Temporal
    Temporal --> GC
    Temporal --> CT
    Temporal --> FH
    Temporal --> Spark
    GC & CT & FH & Spark --> DP

    GC & CT & FH & Spark --> Eval
    Eval --> KS & TVD & Corr & DCR
    Eval --> DuckDB
    Eval --> Arrow
```

---

## 2. Directory Structure

```text
synthai-studio/
├── docs/
│   ├── PRD.md                       <-- Product Requirements Document
│   ├── UX_SPEC.md                   <-- Principal UI/UX & Interaction Architecture
│   ├── DESIGN_SYSTEM.md             <-- Dark elevation, tokens, typography & components
│   ├── adr/                         <-- Architecture Decision Records
│   └── specs/                       <-- Granular milestone execution specs (M01-M11)
├── src/
│   └── synthai_studio/
│       ├── __init__.py
│       ├── models.py                <-- Pydantic v2 domain models & schemas
│       ├── benchmarks.py            <-- Reference domain dataset generators
│       ├── profiler.py              <-- PII scanner, defect auditor & cleanser
│       ├── synthesizer.py           <-- Copula, CTGAN, Faker & Spark synthesizers
│       ├── evaluator.py             <-- KS/TVD fidelity, Frobenius & privacy proofs
│       ├── repository.py            <-- DuckDB persistence & PyArrow streaming
│       ├── workflows.py             <-- Temporal.io durable workflow orchestrator
│       └── api/
│           ├── __init__.py
│           ├── main.py              <-- FastAPI application & REST endpoint routes
│           ├── ui.py                <-- Typed UI router & static asset loader
│           ├── templates/
│           │   └── index.html       <-- Semantic HTML5 5-step workbench shell
│           └── static/
│               ├── tokens.css       <-- 4-tier dark elevation & design tokens
│               ├── components.css   <-- 5-state component styles & responsive grid
│               ├── views.js         <-- 5-state DOM renderers & fallback banners
│               └── app.js           <-- State store, ARIA controller & API client
├── tests/
│   ├── test_models_and_benchmarks.py
│   ├── test_profiler.py
│   ├── test_synthesizer.py
│   ├── test_evaluator_and_repository.py
│   ├── test_api.py                  <-- Comprehensive API & packaging integration tests
│   ├── test_ui_assets.py            <-- Design tokens & WCAG contrast verification
│   ├── test_ui_html_contract.py     <-- HTML5 landmarks, ARIA & label contracts
│   ├── test_ui_serving.py           <-- Static mounting, latency & route aliases
│   ├── test_ui_js_contract.py       <-- JS state store, WAI-ARIA & schema contracts
│   └── test_ui_states.py            <-- 5-state renderers & Spark fallback E2E
├── deploy/
│   └── base/                        <-- Kubernetes GitOps manifests
├── pyproject.toml                   <-- Poetry dependencies & Python 3.13 configuration
├── Dockerfile                       <-- Multi-stage non-root container build
├── ROADMAP.md                       <-- Milestone tracking & execution log
└── README.md
```

---

## 3. Core Architectural Pillars

### 3.1 Multi-Signal PII/PHI Scanner & Adaptive Cleanser
- **Regex & Checksum Validators**: Scans for SSN (Luhn/prefix rules), credit cards (Luhn algorithm), email addresses, phone numbers, IPv4/IPv6 addresses, dates of birth, MRNs, and bank routing numbers.
- **Anonymization Invariant**: Tokens matching `ANON-...`, `REDACTED-...`, `...@synthetic.invalid`, and `XXX-XX-...` do not trigger PII alerts. Cleansing with `anonymize_pii=True` reduces the dataset's `privacy_risk_score` to `0.0`.
- **Iterative Z-Score Winsorizing**: Numerical outliers with $|z| > 3.0$ and interquartile boundary violations ($1.5 \times IQR$) are iteratively clamped, ensuring cleansed derivations yield zero outlier defects and high data quality scores ($\ge 0.95$).

### 3.2 Generative Synthesis Engines
- **Gaussian Copula (`GAUSSIAN_COPULA`)**: Transforms empirical marginal distributions to standard normal space via 51 quantile knots, computes covariance with PSD eigenvalue clipping ($\lambda_{min} \ge 10^{-5}$), and couples joint distributions.
- **CTGAN Latent (`CTGAN_LATENT`)**: Multi-modal latent representation with Gaussian Mixture Model (GMM) mode normalization for complex numerical columns and conditional softmax categorical sampling.
- **Faker Hybrid (`FAKER_HYBRID`)**: Combines parametric numerical sampling with deterministic, format-preserving pseudo-anonymized synthetic tokens for PII columns.
- **DGX Spark Edge (`SPARK_LLM_EDGE`)**: On-premise vLLM edge synthesis on DGX Spark GB10 (`happy.tail749110.ts.net:8000`). Features a hard `< 2.0s` split-timeout probe with zero retry loops, falling back automatically to in-process synthesis if the node is unavailable.

### 3.3 Differential Privacy & Rényi Accounting
- **Gaussian Mechanism**: Adds calibrated Gaussian noise $\sigma = \Delta_f \frac{\sqrt{2 \ln(1.25 / \delta)}}{\epsilon}$ to numerical quantile boundaries and correlation estimates.
- **Budget Ledger**: Manages $(\epsilon, \delta)$ budgets across synthesis runs, tracking initial allocation, spent epsilon, and remaining privacy headroom.

### 3.4 Statistical Fidelity & Privacy Auditing
- **Marginal Fidelity**: Evaluates continuous columns via Kolmogorov-Smirnov complement ($1 - D_{KS}$) and discrete columns via Total Variation Distance complement ($1 - \text{TVD}$) and Jensen-Shannon similarity.
- **Correlation Stability**: Measures matrix distortion via Frobenius norm difference:
  $$\text{Stability} = \max\left(0.0, 1.0 - \frac{\|R_{real} - R_{synth}\|_F}{\sqrt{2} \cdot d}\right)$$
- **Privacy Verification Proofs**:
  - Distance to Closest Record ($DCR$): Minimum Euclidean distance between synthetic and real records in normalized feature space.
  - Nearest Neighbor Distance Ratio ($NNDR$): Ratio of distance to 1st nearest neighbor over 2nd nearest neighbor.
  - Exact Record Collisions: Strict zero-collision verification.
  - Identifiable PII Leakage: Guarantees zero unmasked real PII values in synthetic output.

---

## 4. Pre-Engineered Reference Benchmarks

SynthAI Studio ships with 3 pre-engineered reference domain datasets for benchmarking:

| Benchmark ID | Domain | Default Rows | Characteristics & Planted Defects |
|---|---|---|---|
| `healthcare_hipaa_readmissions` | Healthcare | 150 | Planted unmasked SSNs, MRNs, duplicates, high blood pressure outliers ($z > 3.0$), 30-day readmission class imbalance (18%). |
| `fintech_fraud_transactions` | FinTech | 200 | Severe class imbalance (2.5% fraud), unmasked card numbers, foreign IP addresses, extreme transaction amounts. |
| `saas_customer_churn` | SaaS | 150 | Churn class imbalance (8%), unmasked phone numbers, subscription renewal correlations, NPS distribution anomalies. |

---

## 5. REST API & Endpoint Reference

The REST service exposes OpenAPI documentation at `/docs` and the following primary endpoints:

| Method | Path | Description | Response Model |
|---|---|---|---|
| `GET` | `/healthz` | Kubernetes liveness probe | `{"status": "healthy", ...}` |
| `GET` | `/ready` | Database & orchestrator readiness probe ($< 50\text{ms}$) | `{"status": "ready", ...}` |
| `GET` | `/api/v1/benchmarks` | Enumerate reference benchmarks | `list[BenchmarkMetadata]` |
| `POST` | `/api/v1/datasets/seed/{id}` | Seed reference benchmark into catalog | `{"dataset": ..., "profile": ...}` |
| `POST` | `/api/v1/benchmarks/{id}/seed` | Canonical route alias for benchmark seeding | `{"dataset": ..., "profile": ...}` |
| `POST` | `/api/v1/datasets/upload` | Ingest CSV/JSON tabular dataset | `{"dataset": ..., "profile": ...}` |
| `POST` | `/api/v1/datasets/presign-upload`| Generate S3/SeaweedFS capability ticket | `PresignedUploadTicket` |
| `POST` | `/api/v1/presign` | Canonical route alias for capability ticket | `PresignedUploadTicket` |
| `GET` | `/api/v1/datasets` | List all catalog datasets | `list[DatasetMetadata]` |
| `GET` | `/api/v1/datasets/{id}/profile` | Retrieve statistical profile & PII findings| `DatasetProfileReport` |
| `POST` | `/api/v1/datasets/{id}/cleanse` | Cleanse, normalize, and anonymize dataset | `{"dataset": ..., "profile": ...}` |
| `POST` | `/api/v1/jobs/generate` | Dispatch synthetic generation job | `{"job": ..., "report": ...}` |
| `POST` | `/api/v1/jobs` | Canonical route alias for generation job | `{"job": ..., "report": ...}` |
| `GET` | `/api/v1/jobs` | Enumerate historical generation jobs | `list[GenerationJob]` |
| `GET` | `/api/v1/jobs/{id}` | Retrieve individual job execution details | `GenerationJob` |
| `GET` | `/api/v1/jobs/{id}/report` | Retrieve audit report (JSON or Markdown) | `QualityValidationReport` or text/md |
| `GET` | `/api/v1/jobs/{id}/download` | Export synthetic records (CSV, JSON, Parquet) | Binary download stream |
| `GET` | `/` | 5-Step Interactive Studio Single-Page UI | HTML5 console |
| `GET` | `/static/*` | Static design tokens, styles, and client scripts | CSS / JavaScript assets |

---

## 6. Frontend Architecture & Design System (`v2-ux`)

The SynthAI Studio frontend operates under a decoupled, modular static asset pipeline designed in accordance with `docs/UX_SPEC.md` and `docs/DESIGN_SYSTEM.md`:

### 6.1 Modular Asset Pipeline
- **`src/synthai_studio/api/ui.py`**: Typed UI router and cached asset loader (`load_studio_index_html`), mounting `/static` via FastAPI `StaticFiles` and serving `GET /`.
- **`src/synthai_studio/api/templates/index.html`**: Clean semantic HTML5 workbench shell with zero inline style/script blocks, zero emojis, and explicit `<label for="...">` bindings for all form controls.
- **`src/synthai_studio/api/static/tokens.css`**: Design token architecture implementing the 4-tier dark surface elevation hierarchy (`--bg-canvas`, `--bg-surface-1`, `--bg-surface-2`, `--bg-surface-3`), structural hairlines, semantic status colors, and verified WCAG 2.2 AA contrast inks ($\ge 4.5:1$).
- **`src/synthai_studio/api/static/components.css`**: Component styles implementing strict `tabular-nums` formatting, responsive grid layouts, and zero-CLS skeleton blocks.
- **`src/synthai_studio/api/static/views.js` (`window.SynthAIViews`)**: Deterministic 5-state renderers (`.state-empty`, `.state-loading`, `.state-nominal`, `.state-degraded`, `.state-error`), Pearson correlation heatmap, and column-level fidelity tables.
- **`src/synthai_studio/api/static/app.js`**: Centralized state store (`StudioState`), WAI-ARIA roving-`tabindex` controller, polite/assertive live region announcers (`#aria-status-polite`, `#aria-status-assertive`), and asynchronous API handlers.

### 6.2 5-State Component Determinism
Every interactive container across all 5 workflow steps implements five standardized visual and semantic states:
1. **`Empty` (`.state-empty`)**: Guided empty state with explanatory message and actionable 1-click CTA button.
2. **`Loading` (`.state-loading`)**: Sets `aria-busy="true"` and renders geometry-matched skeleton blocks (`.skeleton-card`, `.skeleton-tile`, `.skeleton-row`) to guarantee zero Cumulative Layout Shift (`CLS = 0`).
3. **`Nominal` (`.state-nominal`)**: High-density scannable metric tiles and tables with `<th scope="col">`, `<th scope="row">`, and `font-variant-numeric: tabular-nums`.
4. **`Degraded / Fallback` (`.state-degraded`)**: Explicit amber provenance banner (`#compute-fallback-banner`, `#compute-fallback-banner-step5`) displayed when `SPARK_LLM_EDGE` falls back to `ComputeTier.CPU_WORKER` (`local_copula`) via the `< 2.0s` circuit breaker.
5. **`Error` (`.state-error`)**: Actionable rose banner (`#global-error-banner`) with programmatic keyboard focus recovery.

### 6.3 Accessibility & WCAG 2.2 AA Compliance
- **Skip Navigation**: First focusable element `<a href="#main-workbench" class="skip-link">` slides into viewport on keyboard focus.
- **Roving `tabindex` Navigation**: Step navigation tabs support `ArrowRight`, `ArrowDown`, `ArrowLeft`, `ArrowUp`, `Home`, `End`, and `Escape` shortcuts.
- **Live Announcers**: Asynchronous background state changes broadcast through `#aria-status-polite` and `#aria-status-assertive` without stealing keyboard focus.
- **Reduced Motion**: Honored via `@media (prefers-reduced-motion: reduce)`, disabling CSS animations and shimmer effects.

---

## 7. Quickstart & Local Execution

### 7.1 Prerequisites
- Python 3.11+ (targeting Python 3.13)
- Poetry 2.0+

### 7.2 Setup Virtual Environment
```bash
poetry install
```

### 7.3 Run Test & Verification Suite
```bash
# Static typing and code style (Python 3.13 target)
poetry run ruff check .
poetry run mypy src tests

# Comprehensive test suite (118+ unit, integration, and UI contract tests)
poetry run pytest -v

# Verify Kubernetes Kustomize manifests
kubectl kustomize deploy/base
```

### 7.4 Launch Local Development Server
```bash
poetry run uvicorn synthai_studio.api.main:app --host 0.0.0.0 --port 8000 --reload
```
Navigate to `http://localhost:8000` to interact with the 5-Step Studio UI.

---

## 8. Container Build & Kubernetes GitOps Deployment

### 8.1 Container Image Build
The multi-stage container build produces a minimal, hardened runtime image running as unprivileged user `10001:10001`:
```bash
docker build -t ghcr.io/paulojauregui/synthai-studio:latest .
```

### 8.2 Kubernetes GitOps Architecture (`deploy/base/`)
The service is declaratively managed via Kustomize:
- **Deployment (`01-deployment.yaml`)**: Non-root security context (`runAsUser: 10001`), resource requests and limits, HTTP liveness (`/healthz`) and readiness (`/ready`) probes.
- **Service (`02-service.yaml`)**: Exposes port 80 routing to container targetPort 8000.
- **HTTPRoute (`03-httproute.yaml`)**: Gateway API HTTPRoute attaching to `homelab-gateway` in namespace `argocd`, routing traffic for `synthai-studio.paulojauregui.com`.
- **Kustomization (`kustomization.yaml`)**: Base resource assembly and name reference tracking.

Render manifests locally:
```bash
kubectl kustomize deploy/base
```

---

## 9. Engineering Invariants & Coding Standards

All components strictly uphold the following invariants:
- **Absolute Imports Exclusively**: Zero relative imports. All modules use `from synthai_studio...`.
- **Design by Contract (DbC)**: Every public class, function, and method documents explicit `Pre-conditions:` and `Post-conditions:`.
- **Zero Emojis**: Source code, docstrings, Markdown reports, and UI templates contain zero emoji characters.
- **Deterministic Unit Testing**: Core business logic, generative models, and UI contract suites execute deterministically without live internet dependencies.
