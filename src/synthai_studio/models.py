"""SynthAI Studio domain schemas.

Pre-conditions:
    - Python >= 3.11 with ``pydantic`` v2 installed.
    - Callers construct models with JSON-serializable scalar payloads.
Post-conditions:
    - Every enumeration and model exported here is immutable-by-validation and
      rejects out-of-range numeric values, so downstream milestones can rely on
      the instances they receive without re-validating numeric bounds.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "BenchmarkMetadata",
    "CategoryFrequency",
    "ColumnDataType",
    "ColumnFidelityMetric",
    "ColumnProfile",
    "ComputeTier",
    "ConditionOperator",
    "ConditionRule",
    "DataQualityIssue",
    "DataQualityIssueType",
    "DatasetMetadata",
    "DatasetProfileReport",
    "ExportFormat",
    "GenerationJob",
    "HistogramBin",
    "IssueSeverity",
    "JobStatus",
    "MinorityUpsampleConfig",
    "NumericalStats",
    "PIIFinding",
    "PIIType",
    "PresignedUploadTicket",
    "PrivacyBudgetLedger",
    "PrivacyLevel",
    "PrivacyValidationMetrics",
    "QualityValidationReport",
    "SynthesizerEngine",
    "SynthesisConfig",
]


class ColumnDataType(StrEnum):
    """Inferred semantic type of a dataset column.

    Pre-conditions:
        - Value supplied is one of the declared members.
    Post-conditions:
        - Instance compares equal to its uppercase string value.
    """

    NUMERICAL = "NUMERICAL"
    CATEGORICAL = "CATEGORICAL"
    DATETIME = "DATETIME"
    BOOLEAN = "BOOLEAN"
    IDENTIFIER_PII = "IDENTIFIER_PII"


class PIIType(StrEnum):
    """Categories of personally identifiable information detected by scanning.

    Pre-conditions:
        - Value supplied is one of the declared members.
    Post-conditions:
        - ``PIIType.NONE`` is available to express "no PII detected".
    """

    NONE = "NONE"
    EMAIL = "EMAIL"
    SSN = "SSN"
    PHONE = "PHONE"
    CREDIT_CARD = "CREDIT_CARD"
    MEDICAL_RECORD_NUMBER = "MEDICAL_RECORD_NUMBER"
    PERSON_NAME = "PERSON_NAME"
    IP_ADDRESS = "IP_ADDRESS"


class DataQualityIssueType(StrEnum):
    """Taxonomy of data quality defects surfaced by the profiler.

    Pre-conditions:
        - Value supplied is one of the declared members.
    Post-conditions:
        - Each member maps one-to-one to a detectable defect family.
    """

    MISSING_VALUES = "MISSING_VALUES"
    DUPLICATE_ROWS = "DUPLICATE_ROWS"
    NUMERICAL_OUTLIERS = "NUMERICAL_OUTLIERS"
    INCONSISTENT_FORMATTING = "INCONSISTENT_FORMATTING"
    UNMASKED_PII = "UNMASKED_PII"


class IssueSeverity(StrEnum):
    """Severity ranking for a detected data quality issue.

    Pre-conditions:
        - Value supplied is one of the declared members.
    Post-conditions:
        - Severity ordering is monotonic from ``LOW`` to ``CRITICAL``.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SynthesizerEngine(StrEnum):
    """Available synthetic data generation engines.

    Pre-conditions:
        - Value supplied is one of the declared members.
    Post-conditions:
        - Engine selection is a stable string usable in job payloads.
    """

    GAUSSIAN_COPULA = "GAUSSIAN_COPULA"
    CTGAN_LATENT = "CTGAN_LATENT"
    FAKER_HYBRID = "FAKER_HYBRID"
    SPARK_LLM_EDGE = "SPARK_LLM_EDGE"


class PrivacyLevel(StrEnum):
    """Differential privacy enforcement tiers.

    Pre-conditions:
        - Value supplied is one of the declared members.
    Post-conditions:
        - ``NONE`` disables the privacy budget, all others require epsilon.
    """

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ConditionOperator(StrEnum):
    """Operators supported by conditional synthesis filters.

    Pre-conditions:
        - Value supplied is one of the declared members.
    Post-conditions:
        - Operator is directly translatable to a SQL predicate.
    """

    EQ = "EQ"
    NEQ = "NEQ"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    IN = "IN"


class JobStatus(StrEnum):
    """Lifecycle states of a synthetic data generation job.

    Pre-conditions:
        - Value supplied is one of the declared members.
    Post-conditions:
        - Terminal states are ``COMPLETED`` and ``FAILED``.
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ComputeTier(StrEnum):
    """Worker tier used to execute a generation job.

    Pre-conditions:
        - Value supplied is one of the declared members.
    Post-conditions:
        - Tier is a stable scheduling hint for the worker pool.
    """

    CPU_WORKER = "CPU_WORKER"
    GPU_SPARK_WORKER = "GPU_SPARK_WORKER"


class ExportFormat(StrEnum):
    """Supported export serializations for synthetic datasets.

    Pre-conditions:
        - Value supplied is one of the declared members.
    Post-conditions:
        - Member value equals the canonical lowercase file extension.
    """

    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"


class HistogramBin(BaseModel):
    """A single histogram bin of a numerical column profile.

    Pre-conditions:
        - ``count`` is non-negative and ``frequency`` is a normalized ratio.
    Post-conditions:
        - All fields are stored validated; ``frequency`` lies in ``[0.0, 1.0]``.
    """

    bin_start: float
    bin_end: float
    count: int = Field(ge=0)
    frequency: float = Field(ge=0.0, le=1.0)


class CategoryFrequency(BaseModel):
    """Occurrence count and normalized frequency of a categorical value.

    Pre-conditions:
        - ``value`` is the raw categorical string.
    Post-conditions:
        - ``count`` is non-negative and ``frequency`` lies in ``[0.0, 1.0]``.
    """

    value: str
    count: int = Field(ge=0)
    frequency: float = Field(ge=0.0, le=1.0)


class NumericalStats(BaseModel):
    """Summary statistics for a numerical column.

    Pre-conditions:
        - Quantiles are supplied in ascending order by the profiler.
        - ``std`` is non-negative.
    Post-conditions:
        - Outlier counters default to zero when not computed.
        - ``histogram`` defaults to an empty list rather than ``None``.
    """

    min: float
    p25: float
    median: float
    p75: float
    max: float
    mean: float
    std: float = Field(ge=0.0)
    skewness: float
    outlier_count_zscore: int = Field(default=0, ge=0)
    outlier_count_iqr: int = Field(default=0, ge=0)
    histogram: list[HistogramBin] = Field(default_factory=list)


class PIIFinding(BaseModel):
    """A single PII detection result for one column.

    Pre-conditions:
        - ``confidence`` is a probability in ``[0.0, 1.0]``.
    Post-conditions:
        - The finding carries both a human readable reason and a remediation.
    """

    column_name: str
    pii_type: PIIType
    confidence: float = Field(ge=0.0, le=1.0)
    sample_match_count: int = Field(ge=0)
    detection_reason: str
    remediation: str


class DataQualityIssue(BaseModel):
    """A detected data quality defect affecting a dataset or a single column.

    Pre-conditions:
        - ``column_name`` is ``None`` only for dataset-wide issues.
    Post-conditions:
        - ``affected_ratio`` lies in ``[0.0, 1.0]`` and ``affected_rows`` is
          non-negative.
    """

    issue_id: str
    issue_type: DataQualityIssueType
    severity: IssueSeverity
    column_name: str | None = None
    affected_rows: int = Field(ge=0)
    affected_ratio: float = Field(ge=0.0, le=1.0)
    description: str
    suggested_action: str


class ColumnProfile(BaseModel):
    """Profile of a single dataset column.

    Pre-conditions:
        - ``null_count`` and ``unique_count`` do not exceed ``total_count``.
        - ``numerical_stats`` is populated only for numerical columns.
    Post-conditions:
        - Ratios are normalized against ``total_count`` and lie in ``[0, 1]``.
        - ``pii_type`` defaults to ``PIIType.NONE`` when no PII was detected.
    """

    name: str
    inferred_type: ColumnDataType
    total_count: int = Field(ge=0)
    null_count: int = Field(ge=0)
    null_ratio: float = Field(ge=0.0, le=1.0)
    unique_count: int = Field(ge=0)
    unique_ratio: float = Field(ge=0.0, le=1.0)
    pii_type: PIIType = PIIType.NONE
    numerical_stats: NumericalStats | None = None
    top_categories: list[CategoryFrequency] = Field(default_factory=list)
    sample_values: list[Any] = Field(default_factory=list)


class DatasetProfileReport(BaseModel):
    """Aggregate profiling report for an uploaded or benchmark dataset.

    Pre-conditions:
        - ``columns`` contains exactly one entry per dataset column.
        - Correlation matrix, when present, is square over ``correlation_columns``.
    Post-conditions:
        - Both score fields lie in ``[0.0, 1.0]``.
        - ``pii_findings`` and ``quality_issues`` default to empty lists.
    """

    dataset_id: str
    dataset_name: str
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    duplicate_row_count: int = Field(ge=0)
    data_quality_score: float = Field(ge=0.0, le=1.0)
    privacy_risk_score: float = Field(ge=0.0, le=1.0)
    columns: list[ColumnProfile]
    pii_findings: list[PIIFinding] = Field(default_factory=list)
    quality_issues: list[DataQualityIssue] = Field(default_factory=list)
    correlation_columns: list[str] = Field(default_factory=list)
    correlation_matrix: list[list[float]] = Field(default_factory=list)
    profiled_at: datetime


class DatasetMetadata(BaseModel):
    """Catalog record describing a stored dataset.

    Pre-conditions:
        - ``columns`` lists the dataset headers in storage order.
    Post-conditions:
        - ``column_count`` and ``row_count`` are non-negative.
        - ``benchmark_id`` is populated only for seeded benchmark datasets.
    """

    dataset_id: str
    name: str
    description: str = ""
    source_type: str = "upload"
    benchmark_id: str | None = None
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    columns: list[str]
    is_cleansed: bool = False
    created_at: datetime


class BenchmarkMetadata(BaseModel):
    """Descriptor of a built-in benchmark seed dataset.

    Pre-conditions:
        - ``target_column`` and ``minority_label`` identify the imbalanced label.
    Post-conditions:
        - ``default_row_count`` is at least 10 rows.
        - ``pii_columns`` and ``highlights`` are populated for UI rendering.
    """

    benchmark_id: str
    name: str
    domain: str
    description: str
    default_row_count: int = Field(ge=10)
    target_column: str
    minority_label: str | int
    pii_columns: list[str]
    highlights: list[str]


class ConditionRule(BaseModel):
    """A single conditional synthesis predicate.

    Pre-conditions:
        - ``column`` exists in the source dataset schema.
    Post-conditions:
        - ``value`` is retained verbatim for the query planner.
    """

    column: str
    operator: ConditionOperator
    value: Any


class MinorityUpsampleConfig(BaseModel):
    """Configuration for rebalancing an under-represented label value.

    Pre-conditions:
        - ``column`` is the label column of the dataset.
    Post-conditions:
        - ``target_ratio`` lies strictly between 0.0 and 1.0.
    """

    column: str
    minority_value: Any
    target_ratio: float = Field(gt=0.0, lt=1.0)


class SynthesisConfig(BaseModel):
    """User supplied configuration for one synthetic data generation job.

    Pre-conditions:
        - ``dataset_id`` references an existing catalog dataset.
        - ``target_rows`` is between 10 and 200000 inclusive.
    Post-conditions:
        - Defaults yield the Gaussian Copula engine at medium privacy with a
          deterministic random seed of 42.
        - ``resolved_epsilon`` and ``resolved_delta`` return budget parameters
          consistent with ``privacy_level``.
    """

    dataset_id: str
    target_rows: int = Field(default=500, ge=10, le=200000)
    engine: SynthesizerEngine = SynthesizerEngine.GAUSSIAN_COPULA
    privacy_level: PrivacyLevel = PrivacyLevel.MEDIUM
    epsilon: float | None = Field(default=None, gt=0.0)
    delta: float = Field(default=1e-5, gt=0.0, lt=1.0)
    random_seed: int = 42
    anonymize_pii: bool = True
    upsample_config: MinorityUpsampleConfig | None = None
    conditions: list[ConditionRule] = Field(default_factory=list)

    _EPSILON_BY_LEVEL: dict[PrivacyLevel, float] = {
        PrivacyLevel.LOW: 10.0,
        PrivacyLevel.MEDIUM: 1.0,
        PrivacyLevel.HIGH: 0.1,
    }

    def resolved_epsilon(self) -> float | None:
        """Return the effective epsilon budget for this configuration.

        Pre-conditions:
            - ``epsilon`` is either ``None`` or a strictly positive float.
        Post-conditions:
            - Returns ``None`` when ``privacy_level`` is ``PrivacyLevel.NONE``.
            - Returns the explicit ``epsilon`` when the caller supplied one.
            - Otherwise returns the level default: 10.0 (LOW), 1.0 (MEDIUM),
              0.1 (HIGH).
        """
        if self.privacy_level == PrivacyLevel.NONE:
            return None
        if self.epsilon is not None:
            return float(self.epsilon)
        return self._EPSILON_BY_LEVEL[self.privacy_level]

    def resolved_delta(self) -> float:
        """Return the effective delta budget for this configuration.

        Pre-conditions:
            - ``delta`` is strictly between 0.0 and 1.0.
        Post-conditions:
            - Returns ``1e-6`` when ``privacy_level`` is ``PrivacyLevel.HIGH``
              and ``delta`` was left at the default ``1e-5``.
            - Otherwise returns ``float(self.delta)`` unchanged.
        """
        if self.privacy_level == PrivacyLevel.HIGH and self.delta == 1e-5:
            return 1e-6
        return float(self.delta)


class PrivacyBudgetLedger(BaseModel):
    """Auditable record of differential privacy budget consumed by a job.

    Pre-conditions:
        - ``mechanism`` names the noise mechanism actually applied.
    Post-conditions:
        - ``noise_scale`` is non-negative and ``epsilon_spent`` is ``None``
          only for non-private runs.
    """

    privacy_level: PrivacyLevel
    epsilon_spent: float | None = None
    delta: float
    mechanism: str
    noise_scale: float = Field(ge=0.0)
    psd_projection_applied: bool = True


class ColumnFidelityMetric(BaseModel):
    """Fidelity score of one synthetic column against its real counterpart.

    Pre-conditions:
        - ``metric_name`` identifies the statistic compared (KS, TVD, ...).
    Post-conditions:
        - ``score`` lies in ``[0.0, 1.0]`` and ``statistic_distance`` is
          non-negative.
    """

    column_name: str
    column_type: ColumnDataType
    metric_name: str
    score: float = Field(ge=0.0, le=1.0)
    statistic_distance: float = Field(ge=0.0)
    jensen_shannon_similarity: float | None = None
    real_summary: dict[str, Any] = Field(default_factory=dict)
    synthetic_summary: dict[str, Any] = Field(default_factory=dict)


class PrivacyValidationMetrics(BaseModel):
    """Privacy attack surface measurements for a synthetic dataset.

    Pre-conditions:
        - Distance based metrics (DCR, NNDR) are computed on numeric columns.
    Post-conditions:
        - Rates and protection score lie in ``[0.0, 1.0]``; distances are
          non-negative.
    """

    exact_match_collision_rate: float = Field(ge=0.0, le=1.0)
    dcr_median: float = Field(ge=0.0)
    dcr_p05: float = Field(ge=0.0)
    nndr_median: float = Field(ge=0.0)
    nndr_p05: float = Field(ge=0.0)
    privacy_protection_score: float = Field(ge=0.0, le=1.0)
    pii_leakage_detected: bool = False


class QualityValidationReport(BaseModel):
    """Full statistical and privacy audit of one generation job output.

    Pre-conditions:
        - ``column_metrics`` covers every evaluated column.
        - Correlation matrices, when present, share ``correlation_columns``.
    Post-conditions:
        - All four aggregate scores lie in ``[0.0, 1.0]``.
        - ``real_row_count`` and ``synthetic_row_count`` are at least 1.
    """

    job_id: str
    dataset_id: str
    engine: SynthesizerEngine
    privacy_level: PrivacyLevel
    real_row_count: int = Field(ge=1)
    synthetic_row_count: int = Field(ge=1)
    overall_quality_score: float = Field(ge=0.0, le=1.0)
    marginal_fidelity_score: float = Field(ge=0.0, le=1.0)
    correlation_stability_score: float = Field(ge=0.0, le=1.0)
    privacy_score: float = Field(ge=0.0, le=1.0)
    column_metrics: list[ColumnFidelityMetric]
    privacy_metrics: PrivacyValidationMetrics
    privacy_ledger: PrivacyBudgetLedger
    real_correlation_matrix: list[list[float]] = Field(default_factory=list)
    synthetic_correlation_matrix: list[list[float]] = Field(default_factory=list)
    correlation_columns: list[str] = Field(default_factory=list)
    executive_verdict: str
    hipaa_gdpr_ready: bool
    evaluated_at: datetime


class GenerationJob(BaseModel):
    """Persistent state of an asynchronous synthetic data generation job.

    Pre-conditions:
        - ``config`` references the dataset identified by ``dataset_id``.
    Post-conditions:
        - ``completed_at`` and ``privacy_ledger`` are populated only for
          terminal successful jobs; ``error_message`` only for failed jobs.
    """

    job_id: str
    dataset_id: str
    dataset_name: str
    status: JobStatus
    config: SynthesisConfig
    compute_tier: ComputeTier = ComputeTier.CPU_WORKER
    rows_generated: int = Field(default=0, ge=0)
    throughput_rows_per_sec: float = Field(default=0.0, ge=0.0)
    privacy_ledger: PrivacyBudgetLedger | None = None
    overall_quality_score: float | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class PresignedUploadTicket(BaseModel):
    """Short lived capability for uploading a raw dataset.

    Pre-conditions:
        - ``upload_url`` is a single-use URL bound to ``upload_token``.
    Post-conditions:
        - ``max_bytes`` defaults to 104857600 (100 MiB) and ``expires_at``
          bounds the ticket validity window.
    """

    upload_token: str
    dataset_name: str
    upload_url: str
    expires_at: datetime
    max_bytes: int = 104857600
