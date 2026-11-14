# Milestone 4 Specification (`M4_SPEC.md`): Statistical Fidelity & Privacy Validator + DuckDB/Parquet Repository & Temporal Workflows

## 1. Objective

Implement:
1. `src/synthai_studio/evaluator.py`: Statistical Fidelity & Privacy Quality Validator ($1 - D_{KS}$, $1 - \text{TVD}$, Jensen-Shannon similarity, Frobenius correlation stability, exact row collision rate, Euclidean $z$-normalized Distance to Closest Record ($DCR$) and Nearest-Neighbor Distance Ratio ($NNDR$), executive verdict, and Markdown report exporter).
2. `src/synthai_studio/repository.py`: DuckDB catalog & persistence store + PyArrow Parquet/CSV/JSON dataset export + pre-signed upload/download token manager.
3. `src/synthai_studio/workflows.py`: Temporal.io `DatasetProfileWorkflow` and `SyntheticGenerationWorkflow` with automatic in-process standalone execution fallback and startup auto-seeding of the 3 benchmark datasets + sample synthesis job.
4. `tests/test_evaluator_and_repository.py`: Unit and integration tests covering all M4 components.

---

## 2. Non-Negotiable Engineering Invariants

1. **Absolute Imports Only**: Use `from synthai_studio...` exclusively. Zero relative imports.
2. **Design by Contract (DbC)**: Every public class, method, and function MUST include a docstring with explicit `Pre-conditions:` and `Post-conditions:` sections.
3. **Zero Emojis**: Do not include any emoji characters in source code, docstrings, or tests.
4. **Strict Static Typing**: `poetry run ruff check .` and `poetry run mypy src tests` must pass cleanly.

---

## 3. Target Files & Public Contracts

### 3.1 `src/synthai_studio/evaluator.py`

Expose the following public functions:

1. `compute_ks_complement(real_values: list[float], synth_values: list[float]) -> tuple[float, float]`
   - **Pre-conditions**: `real_values` and `synth_values` are non-empty lists of finite floats.
   - **Post-conditions**: Computes the exact two-sample empirical CDF maximum vertical distance $D_{KS} \in [0.0, 1.0]$ and returns `(score, d_ks)` where `score = 1.0 - d_ks`.

2. `compute_tvd_and_js_similarity(real_values: list[str], synth_values: list[str]) -> tuple[float, float, float]`
   - **Pre-conditions**: `real_values` and `synth_values` are non-empty lists of strings.
   - **Post-conditions**: Computes Total Variation Distance $\text{TVD} = \frac{1}{2} \sum_x |P(x) - Q(x)| \in [0.0, 1.0]$, `tvd_score = 1.0 - tvd`, and Jensen-Shannon similarity $1.0 - \sqrt{D_{JS}(P \| Q)} \in [0.0, 1.0]$. Returns `(tvd_score, tvd, js_similarity)`.

3. `compute_correlation_stability(real_corr: list[list[float]], synth_corr: list[list[float]]) -> float`
   - **Pre-conditions**: `real_corr` and `synth_corr` are square matrices of identical dimension $d \times d$.
   - **Post-conditions**: If $d \le 1$, returns `1.0`. Otherwise computes Frobenius norm distance $\|R_{\text{real}} - R_{\text{synth}}\|_F$ normalized by $\sqrt{d(d-1)}$ and returns $\text{clamp}(1.0 - \text{dist}, 0.0, 1.0)$.

4. `compute_privacy_metrics(real_rows: list[dict[str, Any]], synth_rows: list[dict[str, Any]], pii_columns: list[str], numeric_columns: list[str]) -> PrivacyValidationMetrics`
   - **Pre-conditions**: `real_rows` and `synth_rows` are non-empty lists of dicts.
   - **Post-conditions**:
     - Computes `exact_match_collision_rate` across full row tuples, and checks whether any non-null value in `pii_columns` in `synth_rows` appears verbatim in `real_rows` (`pii_leakage_detected`).
     - Standardizes `numeric_columns` using real dataset means and standard deviations ($z$-score normalization).
     - Computes pairwise Euclidean distances between standardized synthetic rows and real rows, extracting each synthetic record's nearest neighbor distance ($d_1 = \text{DCR}$) and second-nearest neighbor distance ($d_2$), with $\text{NNDR} = d_1 / (d_2 + 10^{-6})$.
     - Returns `PrivacyValidationMetrics` with `dcr_median`, `dcr_p05`, `nndr_median`, `nndr_p05`, `exact_match_collision_rate`, `pii_leakage_detected`, and `privacy_protection_score` in `[0.0, 1.0]`.

5. `evaluate_synthetic_quality(job_id: str, dataset_id: str, real_rows: list[dict[str, Any]], synth_rows: list[dict[str, Any]], config: SynthesisConfig, privacy_ledger: PrivacyBudgetLedger, real_profile: DatasetProfileReport | None = None) -> QualityValidationReport`
   - **Pre-conditions**: `real_rows` and `synth_rows` are non-empty.
   - **Post-conditions**: Evaluates all columns, computes `marginal_fidelity_score`, `correlation_stability_score`, `privacy_score`, and weighted `overall_quality_score = 0.45 * marginal_fidelity_score + 0.30 * correlation_stability_score + 0.25 * privacy_score`, synthesizes an `executive_verdict`, determines `hipaa_gdpr_ready = (not privacy_metrics.pii_leakage_detected and privacy_score >= 0.70)`, and returns `QualityValidationReport`.

6. `render_quality_report_markdown(report: QualityValidationReport) -> str`
   - **Pre-conditions**: `report` is a valid `QualityValidationReport`.
   - **Post-conditions**: Returns a structured GitHub-Flavored Markdown audit report suitable for download or compliance review (zero emojis).

---

### 3.2 `src/synthai_studio/repository.py`

Expose `class StudioRepository`:
- `__init__(self, db_path: str | Path = ":memory:", storage_dir: str | Path | None = None) -> None`
  - Initializes DuckDB connection and creates tables `datasets`, `dataset_profiles`, `generation_jobs`, `quality_reports`, and `upload_tickets`.
  - Uses `storage_dir` (defaulting to a temporary or configured `data/exports` directory) to store dataset rows as Parquet/JSON and support fast retrieval.
- Dataset CRUD:
  - `save_dataset(self, name: str, rows: list[dict[str, Any]], description: str = "", source_type: str = "upload", benchmark_id: str | None = None, is_cleansed: bool = False, dataset_id: str | None = None) -> DatasetMetadata`
  - `get_dataset_metadata(self, dataset_id: str) -> DatasetMetadata` (raises `KeyError` if not found)
  - `get_dataset_rows(self, dataset_id: str) -> list[dict[str, Any]]` (raises `KeyError` if not found)
  - `list_datasets(self) -> list[DatasetMetadata]`
  - `save_profile(self, profile: DatasetProfileReport) -> None`
  - `get_profile(self, dataset_id: str) -> DatasetProfileReport | None`
- Job & Report CRUD:
  - `save_job(self, job: GenerationJob, synthetic_rows: list[dict[str, Any]] | None = None) -> None`
  - `get_job(self, job_id: str) -> GenerationJob` (raises `KeyError` if not found)
  - `get_job_rows(self, job_id: str) -> list[dict[str, Any]]` (raises `KeyError` if not found)
  - `list_jobs(self) -> list[GenerationJob]`
  - `save_quality_report(self, report: QualityValidationReport) -> None`
  - `get_quality_report(self, job_id: str) -> QualityValidationReport` (raises `KeyError` if not found)
- Export & Pre-signed Tickets:
  - `export_rows(self, rows: list[dict[str, Any]], fmt: ExportFormat) -> tuple[bytes, str, str]`
    - Returns `(payload_bytes, media_type, file_extension)` supporting `ExportFormat.CSV`, `ExportFormat.JSON`, and `ExportFormat.PARQUET` (via `pyarrow.parquet`).
  - `create_presigned_upload_ticket(self, dataset_name: str, base_url: str = "http://localhost:8000") -> PresignedUploadTicket`
  - `consume_presigned_upload_ticket(self, upload_token: str) -> PresignedUploadTicket` (raises `KeyError` if invalid/expired)

---

### 3.3 `src/synthai_studio/workflows.py`

Expose:
1. Temporal workflow definitions (`@workflow.defn` / `@activity.defn` from `temporalio`) for `DatasetProfileWorkflow` and `SyntheticGenerationWorkflow`.
2. `class StudioWorkflowOrchestrator`:
   - `__init__(self, repository: StudioRepository, temporal_host: str | None = None, temporal_enabled: bool = False) -> None`
   - `seed_benchmark(self, benchmark_id: str, row_count: int | None = None, seed: int = 42) -> tuple[DatasetMetadata, DatasetProfileReport]`
   - `ingest_dataset(self, name: str, rows: list[dict[str, Any]], description: str = "", source_type: str = "upload") -> tuple[DatasetMetadata, DatasetProfileReport]`
   - `cleanse_existing_dataset(self, dataset_id: str, anonymize_pii: bool = True) -> tuple[DatasetMetadata, DatasetProfileReport]`
   - `run_generation_job(self, config: SynthesisConfig) -> tuple[GenerationJob, QualityValidationReport]`
   - `bootstrap_default_Catalog(self) -> None` (or `bootstrap_defaults(self) -> None`): Idempotently seeds all 3 benchmark datasets if `repository.list_datasets()` is empty, and runs one initial sample synthesis job (`healthcare_hipaa_readmissions`, 150 rows, `GAUSSIAN_COPULA`, `PrivacyLevel.MEDIUM`) so the studio UI has rich telemetry immediately on startup.
