# Milestone 1 Specification (`M1_SPEC.md`): Domain Schemas & Built-in Benchmark Datasets

## 1. Objective

Implement the foundational Pydantic v2 domain models (`src/synthai_studio/models.py`), deterministic benchmark dataset generators (`src/synthai_studio/benchmarks.py`), and comprehensive unit tests (`tests/test_models_and_benchmarks.py`).

---

## 2. Non-Negotiable Engineering Invariants

1. **Absolute Imports Only**: Every import from the package MUST use `from synthai_studio...`. Relative imports are strictly forbidden.
2. **Design by Contract (DbC)**: Every public class, method, and function MUST include a docstring containing explicit `Pre-conditions:` and `Post-conditions:` sections.
3. **Zero Emojis**: Do not include any emoji characters in source code, docstrings, or tests.
4. **Strict Static Typing**: All functions, methods, and attributes must be fully typed so `poetry run mypy src tests` and `poetry run ruff check .` pass with zero errors or warnings.

---

## 3. Target Files & Contracts

### 3.1 `src/synthai_studio/__init__.py`
Expose `__version__ = "0.1.0"`.

### 3.2 `src/synthai_studio/models.py`
Define the following enumerations (all inheriting `str, Enum`) and Pydantic v2 `BaseModel` classes with `Pre-conditions:` and `Post-conditions:` docstrings:

- **Enumerations**:
  - `ColumnDataType`: `NUMERICAL = "NUMERICAL"`, `CATEGORICAL = "CATEGORICAL"`, `DATETIME = "DATETIME"`, `BOOLEAN = "BOOLEAN"`, `IDENTIFIER_PII = "IDENTIFIER_PII"`
  - `PIIType`: `NONE = "NONE"`, `EMAIL = "EMAIL"`, `SSN = "SSN"`, `PHONE = "PHONE"`, `CREDIT_CARD = "CREDIT_CARD"`, `MEDICAL_RECORD_NUMBER = "MEDICAL_RECORD_NUMBER"`, `PERSON_NAME = "PERSON_NAME"`, `IP_ADDRESS = "IP_ADDRESS"`
  - `DataQualityIssueType`: `MISSING_VALUES = "MISSING_VALUES"`, `DUPLICATE_ROWS = "DUPLICATE_ROWS"`, `NUMERICAL_OUTLIERS = "NUMERICAL_OUTLIERS"`, `INCONSISTENT_FORMATTING = "INCONSISTENT_FORMATTING"`, `UNMASKED_PII = "UNMASKED_PII"`
  - `IssueSeverity`: `LOW = "LOW"`, `MEDIUM = "MEDIUM"`, `HIGH = "HIGH"`, `CRITICAL = "CRITICAL"`
  - `SynthesizerEngine`: `GAUSSIAN_COPULA = "GAUSSIAN_COPULA"`, `CTGAN_LATENT = "CTGAN_LATENT"`, `FAKER_HYBRID = "FAKER_HYBRID"`, `SPARK_LLM_EDGE = "SPARK_LLM_EDGE"`
  - `PrivacyLevel`: `NONE = "NONE"`, `LOW = "LOW"`, `MEDIUM = "MEDIUM"`, `HIGH = "HIGH"`
  - `ConditionOperator`: `EQ = "EQ"`, `NEQ = "NEQ"`, `GT = "GT"`, `GTE = "GTE"`, `LT = "LT"`, `LTE = "LTE"`, `IN = "IN"`
  - `JobStatus`: `PENDING = "PENDING"`, `RUNNING = "RUNNING"`, `COMPLETED = "COMPLETED"`, `FAILED = "FAILED"`
  - `ComputeTier`: `CPU_WORKER = "CPU_WORKER"`, `GPU_SPARK_WORKER = "GPU_SPARK_WORKER"`
  - `ExportFormat`: `CSV = "csv"`, `JSON = "json"`, `PARQUET = "parquet"`

- **Pydantic v2 Models**:
  - `HistogramBin`: `bin_start: float`, `bin_end: float`, `count: int = Field(ge=0)`, `frequency: float = Field(ge=0.0, le=1.0)`
  - `CategoryFrequency`: `value: str`, `count: int = Field(ge=0)`, `frequency: float = Field(ge=0.0, le=1.0)`
  - `NumericalStats`: `min: float`, `p25: float`, `median: float`, `p75: float`, `max: float`, `mean: float`, `std: float = Field(ge=0.0)`, `skewness: float`, `outlier_count_zscore: int = Field(default=0, ge=0)`, `outlier_count_iqr: int = Field(default=0, ge=0)`, `histogram: list[HistogramBin] = Field(default_factory=list)`
  - `PIIFinding`: `column_name: str`, `pii_type: PIIType`, `confidence: float = Field(ge=0.0, le=1.0)`, `sample_match_count: int = Field(ge=0)`, `detection_reason: str`, `remediation: str`
  - `DataQualityIssue`: `issue_id: str`, `issue_type: DataQualityIssueType`, `severity: IssueSeverity`, `column_name: str | None = None`, `affected_rows: int = Field(ge=0)`, `affected_ratio: float = Field(ge=0.0, le=1.0)`, `description: str`, `suggested_action: str`
  - `ColumnProfile`: `name: str`, `inferred_type: ColumnDataType`, `total_count: int = Field(ge=0)`, `null_count: int = Field(ge=0)`, `null_ratio: float = Field(ge=0.0, le=1.0)`, `unique_count: int = Field(ge=0)`, `unique_ratio: float = Field(ge=0.0, le=1.0)`, `pii_type: PIIType = PIIType.NONE`, `numerical_stats: NumericalStats | None = None`, `top_categories: list[CategoryFrequency] = Field(default_factory=list)`, `sample_values: list[Any] = Field(default_factory=list)`
  - `DatasetProfileReport`: `dataset_id: str`, `dataset_name: str`, `row_count: int = Field(ge=0)`, `column_count: int = Field(ge=0)`, `duplicate_row_count: int = Field(ge=0)`, `data_quality_score: float = Field(ge=0.0, le=1.0)`, `privacy_risk_score: float = Field(ge=0.0, le=1.0)`, `columns: list[ColumnProfile]`, `pii_findings: list[PIIFinding] = Field(default_factory=list)`, `quality_issues: list[DataQualityIssue] = Field(default_factory=list)`, `correlation_columns: list[str] = Field(default_factory=list)`, `correlation_matrix: list[list[float]] = Field(default_factory=list)`, `profiled_at: datetime`
  - `DatasetMetadata`: `dataset_id: str`, `name: str`, `description: str = ""`, `source_type: str = "upload"`, `benchmark_id: str | None = None`, `row_count: int = Field(ge=0)`, `column_count: int = Field(ge=0)`, `columns: list[str]`, `is_cleansed: bool = False`, `created_at: datetime`
  - `BenchmarkMetadata`: `benchmark_id: str`, `name: str`, `domain: str`, `description: str`, `default_row_count: int = Field(ge=10)`, `target_column: str`, `minority_label: str | int`, `pii_columns: list[str]`, `highlights: list[str]`
  - `ConditionRule`: `column: str`, `operator: ConditionOperator`, `value: Any`
  - `MinorityUpsampleConfig`: `column: str`, `minority_value: Any`, `target_ratio: float = Field(gt=0.0, lt=1.0)`
  - `SynthesisConfig`:
    - Fields: `dataset_id: str`, `target_rows: int = Field(default=500, ge=10, le=200000)`, `engine: SynthesizerEngine = SynthesizerEngine.GAUSSIAN_COPULA`, `privacy_level: PrivacyLevel = PrivacyLevel.MEDIUM`, `epsilon: float | None = Field(default=None, gt=0.0)`, `delta: float = Field(default=1e-5, gt=0.0, lt=1.0)`, `random_seed: int = 42`, `anonymize_pii: bool = True`, `upsample_config: MinorityUpsampleConfig | None = None`, `conditions: list[ConditionRule] = Field(default_factory=list)`
    - Method `resolved_epsilon(self) -> float | None`: If `self.privacy_level == PrivacyLevel.NONE`, returns `None`. If `self.epsilon is not None`, returns `float(self.epsilon)`. Otherwise returns `10.0` for `LOW`, `1.0` for `MEDIUM`, and `0.1` for `HIGH`.
    - Method `resolved_delta(self) -> float`: Returns `1e-6` if `self.privacy_level == PrivacyLevel.HIGH` and `self.delta == 1e-5`, otherwise `float(self.delta)`.
  - `PrivacyBudgetLedger`: `privacy_level: PrivacyLevel`, `epsilon_spent: float | None = None`, `delta: float`, `mechanism: str`, `noise_scale: float = Field(ge=0.0)`, `psd_projection_applied: bool = True`
  - `ColumnFidelityMetric`: `column_name: str`, `column_type: ColumnDataType`, `metric_name: str`, `score: float = Field(ge=0.0, le=1.0)`, `statistic_distance: float = Field(ge=0.0)`, `jensen_shannon_similarity: float | None = None`, `real_summary: dict[str, Any] = Field(default_factory=dict)`, `synthetic_summary: dict[str, Any] = Field(default_factory=dict)`
  - `PrivacyValidationMetrics`: `exact_match_collision_rate: float = Field(ge=0.0, le=1.0)`, `dcr_median: float = Field(ge=0.0)`, `dcr_p05: float = Field(ge=0.0)`, `nndr_median: float = Field(ge=0.0)`, `nndr_p05: float = Field(ge=0.0)`, `privacy_protection_score: float = Field(ge=0.0, le=1.0)`, `pii_leakage_detected: bool = False`
  - `QualityValidationReport`: `job_id: str`, `dataset_id: str`, `engine: SynthesizerEngine`, `privacy_level: PrivacyLevel`, `real_row_count: int = Field(ge=1)`, `synthetic_row_count: int = Field(ge=1)`, `overall_quality_score: float = Field(ge=0.0, le=1.0)`, `marginal_fidelity_score: float = Field(ge=0.0, le=1.0)`, `correlation_stability_score: float = Field(ge=0.0, le=1.0)`, `privacy_score: float = Field(ge=0.0, le=1.0)`, `column_metrics: list[ColumnFidelityMetric]`, `privacy_metrics: PrivacyValidationMetrics`, `privacy_ledger: PrivacyBudgetLedger`, `real_correlation_matrix: list[list[float]] = Field(default_factory=list)`, `synthetic_correlation_matrix: list[list[float]] = Field(default_factory=list)`, `correlation_columns: list[str] = Field(default_factory=list)`, `executive_verdict: str`, `hipaa_gdpr_ready: bool`, `evaluated_at: datetime`
  - `GenerationJob`: `job_id: str`, `dataset_id: str`, `dataset_name: str`, `status: JobStatus`, `config: SynthesisConfig`, `compute_tier: ComputeTier = ComputeTier.CPU_WORKER`, `rows_generated: int = Field(default=0, ge=0)`, `throughput_rows_per_sec: float = Field(default=0.0, ge=0.0)`, `privacy_ledger: PrivacyBudgetLedger | None = None`, `overall_quality_score: float | None = None`, `error_message: str | None = None`, `created_at: datetime`, `completed_at: datetime | None = None`
  - `PresignedUploadTicket`: `upload_token: str`, `dataset_name: str`, `upload_url: str`, `expires_at: datetime`, `max_bytes: int = 104857600`

### 3.3 `src/synthai_studio/benchmarks.py`
Provide deterministic benchmark seed dataset generators:
- `BENCHMARK_REGISTRY: dict[str, BenchmarkMetadata]` containing:
  1. `healthcare_hipaa_readmissions`:
     - Columns: `patient_name`, `ssn`, `mrn`, `email`, `age`, `state`, `admission_type`, `charlson_comorbidity_index`, `length_of_stay_days`, `lab_creatinine_mg_dl`, `billing_amount_usd`, `admission_date`, `readmitted_30d`
     - Correlations: `age` positively correlated with `charlson_comorbidity_index`, `length_of_stay_days`, and `billing_amount_usd`.
     - Class imbalance: `readmitted_30d` in `{0, 1}` with ~14-18% positive (`1`) rate.
     - Planted defects: 3-5 missing values (`None`) in `lab_creatinine_mg_dl`, 2 exact duplicate rows, 2 extreme outliers in `billing_amount_usd` (e.g. `450000.0`), and inconsistent state codes (`" ca "`, `"ny"`, `"tx"` alongside `"CA"`, `"NY"`, `"TX"`).
  2. `fintech_fraud_transactions`:
     - Columns: `cardholder_name`, `cardholder_email`, `phone`, `ip_address`, `state`, `merchant_category`, `transaction_amount_usd`, `velocity_24h_count`, `distance_from_home_km`, `device_trust_score`, `transaction_timestamp`, `is_fraud`
     - Correlations: `velocity_24h_count` and `distance_from_home_km` positively correlated with `transaction_amount_usd` and negatively correlated with `device_trust_score`.
     - Class imbalance: `is_fraud` in `{0, 1}` with ~8-12% positive (`1`) rate.
     - Planted defects: missing values in `device_trust_score`, 2 duplicate rows, extreme `transaction_amount_usd` outliers, and inconsistent state codes.
  3. `saas_customer_churn`:
     - Columns: `contact_name`, `contact_email`, `phone`, `state`, `plan_tier`, `seat_count`, `monthly_recurring_revenue_usd`, `active_utilization_pct`, `support_tickets_90d`, `nps_score`, `contract_start_date`, `churned`
     - Correlations: `seat_count` strongly positively correlated with `monthly_recurring_revenue_usd`; `active_utilization_pct` positively correlated with `nps_score` and negatively correlated with `support_tickets_90d`.
     - Class imbalance: `churned` in `{0, 1}` with ~12-16% positive (`1`) rate.
     - Planted defects: missing values in `nps_score`, 2 duplicate rows, extreme `monthly_recurring_revenue_usd` outliers, and inconsistent state codes.
- Functions:
  - `list_benchmarks() -> list[BenchmarkMetadata]`
  - `get_benchmark_metadata(benchmark_id: str) -> BenchmarkMetadata` (raises `KeyError` if unknown)
  - `generate_benchmark_dataset(benchmark_id: str, row_count: int | None = None, seed: int = 42) -> list[dict[str, Any]]` (raises `KeyError` if unknown `benchmark_id` or `ValueError` if `row_count < 20`)

### 3.4 `tests/test_models_and_benchmarks.py`
Test suite verifying:
- `SynthesisConfig.resolved_epsilon()` and `resolved_delta()` across all `PrivacyLevel` variants (`NONE`, `LOW`, `MEDIUM`, `HIGH`) and custom `epsilon` override.
- Validation bounds on `NumericalStats`, `PIIFinding`, `QualityValidationReport`.
- `list_benchmarks()` returns all 3 benchmark datasets with valid metadata.
- `generate_benchmark_dataset()` is 100% deterministic for fixed `seed=42`, produces exact requested `row_count`, includes planted duplicates, missing values, extreme outliers, inconsistent state codes, positive correlations between correlated features, and minority class ratio `< 0.30`.
