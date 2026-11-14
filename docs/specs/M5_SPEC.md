# Milestone 5 Specification (`M5_SPEC.md`): FastAPI Service, 5-Step Interactive Studio Web UI, K8s GitOps Manifests & PR Delivery

## 1. Objective

Implement:
1. `src/synthai_studio/api/__init__.py` and `src/synthai_studio/api/main.py`: FastAPI REST API + Interactive 5-Step SynthAI Studio Web UI (`GET /`).
2. `Dockerfile`: Multi-stage non-root (`USER 10001:10001`) container build exposing port `8000` (`uvicorn synthai_studio.api.main:app --host 0.0.0.0 --port 8000`).
3. `deploy/base/*`: Base Kustomize manifests (`01-deployment.yaml`, `02-service.yaml`, `03-httproute.yaml`, `kustomizeconfig.yaml`, `kustomization.yaml`) configured for `synthai-studio` and attaching to `homelab-gateway` in namespace `argocd`.
4. `tests/test_api.py`: Comprehensive end-to-end API and UI test suite.

---

## 2. Non-Negotiable Engineering Invariants

1. **Absolute Imports Only**: Use `from synthai_studio...` exclusively. Zero relative imports.
2. **Design by Contract (DbC)**: Every public class, method, and function MUST include a docstring with explicit `Pre-conditions:` and `Post-conditions:` sections.
3. **Zero Emojis**: Do not include any emoji characters in source code, HTML/JS templates, docstrings, or tests.
4. **Strict Static Typing**: `poetry run ruff check .` and `poetry run mypy src tests` must pass cleanly.
5. **CI Workflow Untouched**: `.github/workflows/ci.yml` MUST NOT be modified.

---

## 3. Target Endpoints & Contracts (`src/synthai_studio/api/main.py`)

Expose `app: FastAPI` and `create_app(repository: StudioRepository | None = None, bootstrap: bool = True) -> FastAPI`:

1. **Health & Readiness Probes**:
   - `GET /healthz`: Returns `200 OK` with `{"status": "healthy", "service": "synthai-studio", "version": "0.1.0"}`.
   - `GET /ready`: Verifies DuckDB catalog connectivity and returns `200 OK` with `{"status": "ready", "datasets_count": int, "jobs_count": int, "temporal_host": str}`.
2. **Benchmarks & Dataset Ingestion**:
   - `GET /api/v1/benchmarks`: Returns `list[BenchmarkMetadata]`.
   - `POST /api/v1/datasets/seed/{benchmark_id}`: Accepts optional query/body `row_count: int | None = None`, seeds benchmark dataset, profiles it, and returns `{"dataset": DatasetMetadata, "profile": DatasetProfileReport}`. Returns `404` if `benchmark_id` is unknown.
   - `POST /api/v1/datasets/upload`: Supports both `multipart/form-data` file upload (`file: UploadFile`, `name: str | None`) and JSON payload (`{"name": str, "content": str, "filename": str}` or `{"name": str, "rows": list[dict]}`). Parses, saves, profiles, and returns `{"dataset": DatasetMetadata, "profile": DatasetProfileReport}`.
   - `POST /api/v1/datasets/presign-upload`: Accepts `{"dataset_name": str}`, returns `PresignedUploadTicket`.
3. **Datasets, Profiling & Cleansing**:
   - `GET /api/v1/datasets`: Returns `list[DatasetMetadata]`.
   - `GET /api/v1/datasets/{dataset_id}/profile`: Returns `DatasetProfileReport` (and sample rows if requested). Returns `404` if unknown.
   - `POST /api/v1/datasets/{dataset_id}/cleanse`: Accepts optional `{"anonymize_pii": bool = True}`, runs `cleanse_existing_dataset`, saves the new cleansed dataset + profile, and returns `{"dataset": DatasetMetadata, "profile": DatasetProfileReport}`.
4. **Synthetic Generation Jobs & Quality Reports**:
   - `POST /api/v1/jobs/generate`: Accepts `SynthesisConfig` body, executes `run_generation_job(config)`, and returns `{"job": GenerationJob, "report": QualityValidationReport}`. Returns `404` if `dataset_id` is not found.
   - `GET /api/v1/jobs`: Returns `list[GenerationJob]`.
   - `GET /api/v1/jobs/{job_id}`: Returns `GenerationJob`. Returns `404` if unknown.
   - `GET /api/v1/jobs/{job_id}/report`: Supports `format=json|markdown` query parameter (default `"json"`). When `format=markdown`, returns `PlainTextResponse` with rendered Markdown quality report; otherwise returns `QualityValidationReport` JSON.
   - `GET /api/v1/jobs/{job_id}/download`: Supports `format=csv|json|parquet` query parameter (default `"csv"`). Streams/returns the exported synthetic dataset bytes with appropriate `Content-Type` and `Content-Disposition: attachment; filename="synthai-{job_id}.{ext}"`.
5. **5-Step Interactive Studio Web UI (`GET /`)**:
   - Returns `HTMLResponse` rendering the interactive **SynthAI Studio** single-page console featuring all 5 steps:
     - Step 1: Connect & Seed Data (Benchmark selector cards + CSV/JSON upload & Pre-signed S3/SeaweedFS ticket generator)
     - Step 2: Automated Data Quality & PII/PHI Audit + Correlation Heatmap + 1-Click Cleanse & Anonymize action
     - Step 3: Synthesizer Engine (`GAUSSIAN_COPULA`, `CTGAN_LATENT`, `FAKER_HYBRID`, `SPARK_LLM_EDGE`), Differential Privacy ($\epsilon, \delta$) Slider, Minority Class Upsampling, and Condition Rules builder
     - Step 4: Temporal / Worker Job Monitor & Privacy Budget Ledger
     - Step 5: Statistical Fidelity ($1 - D_{KS}$, $1 - \text{TVD}$, Frobenius Correlation), Privacy Proof ($DCR$, $NNDR$, Zero Collision), Executive Verdict, and 1-Click CSV / JSON / Parquet / Markdown Report downloads.
