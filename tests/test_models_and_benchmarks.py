"""Unit tests for SynthAI Studio domain models and benchmark datasets.

Pre-conditions:
    - ``synthai_studio.models`` and ``synthai_studio.benchmarks`` are importable.
    - ``pytest`` and ``numpy`` are installed.
Post-conditions:
    - All unit tests pass deterministically without network egress.
"""

from datetime import datetime
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from synthai_studio.benchmarks import (
    BENCHMARK_REGISTRY,
    generate_benchmark_dataset,
    get_benchmark_metadata,
    list_benchmarks,
)
from synthai_studio.models import (
    ColumnDataType,
    ColumnFidelityMetric,
    NumericalStats,
    PIIFinding,
    PIIType,
    PrivacyBudgetLedger,
    PrivacyLevel,
    PrivacyValidationMetrics,
    QualityValidationReport,
    SynthesisConfig,
    SynthesizerEngine,
)


def _pearson_correlation(x: list[float], y: list[float]) -> float:
    """Compute Pearson correlation coefficient between two numeric lists.

    Pre-conditions:
        - ``x`` and ``y`` have identical non-zero lengths.
    Post-conditions:
        - Returns a float in [-1.0, 1.0].
    """
    arr_x = np.asarray(x, dtype=float)
    arr_y = np.asarray(y, dtype=float)
    return float(np.corrcoef(arr_x, arr_y)[0, 1])


def _spearman_correlation(x: list[float], y: list[float]) -> float:
    """Compute Spearman rank correlation coefficient between two numeric lists.

    Pre-conditions:
        - ``x`` and ``y`` have identical non-zero lengths.
    Post-conditions:
        - Returns a float in [-1.0, 1.0].
    """
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def _count_exact_duplicates(dataset: list[dict[str, Any]]) -> int:
    """Count duplicate rows in a list of dictionary records.

    Pre-conditions:
        - ``dataset`` is a list of dictionary rows with string-serializable values.
    Post-conditions:
        - Returns the exact count of subsequent duplicate rows.
    """
    seen: set[tuple[tuple[str, str], ...]] = set()
    duplicates = 0
    for row in dataset:
        key = tuple(sorted((k, str(v)) for k, v in row.items()))
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return duplicates


def test_synthesis_config_resolved_epsilon() -> None:
    """Verify SynthesisConfig.resolved_epsilon across all privacy levels and overrides.

    Pre-conditions:
        - ``SynthesisConfig`` model is available.
    Post-conditions:
        - Confirms NONE yields None, defaults match specifications, and overrides apply.
    """
    # PrivacyLevel.NONE should resolve to None regardless of default
    cfg_none = SynthesisConfig(dataset_id="ds-1", privacy_level=PrivacyLevel.NONE)
    assert cfg_none.resolved_epsilon() is None

    # PrivacyLevel.LOW default is 10.0
    cfg_low = SynthesisConfig(dataset_id="ds-1", privacy_level=PrivacyLevel.LOW)
    assert cfg_low.resolved_epsilon() == 10.0

    # PrivacyLevel.MEDIUM default is 1.0
    cfg_med = SynthesisConfig(dataset_id="ds-1", privacy_level=PrivacyLevel.MEDIUM)
    assert cfg_med.resolved_epsilon() == 1.0

    # PrivacyLevel.HIGH default is 0.1
    cfg_high = SynthesisConfig(dataset_id="ds-1", privacy_level=PrivacyLevel.HIGH)
    assert cfg_high.resolved_epsilon() == 0.1

    # Explicit override takes precedence
    cfg_override = SynthesisConfig(
        dataset_id="ds-1",
        privacy_level=PrivacyLevel.HIGH,
        epsilon=2.5,
    )
    assert cfg_override.resolved_epsilon() == 2.5


def test_synthesis_config_resolved_delta() -> None:
    """Verify SynthesisConfig.resolved_delta behavior for HIGH level and overrides.

    Pre-conditions:
        - ``SynthesisConfig`` model is available.
    Post-conditions:
        - Confirms delta switches to 1e-6 only for HIGH when delta is at default 1e-5.
    """
    # Default delta is 1e-5 for MEDIUM
    cfg_med = SynthesisConfig(dataset_id="ds-1", privacy_level=PrivacyLevel.MEDIUM)
    assert cfg_med.resolved_delta() == 1e-5

    # HIGH changes default 1e-5 to 1e-6
    cfg_high = SynthesisConfig(dataset_id="ds-1", privacy_level=PrivacyLevel.HIGH)
    assert cfg_high.resolved_delta() == 1e-6

    # Custom delta remains untouched on HIGH
    cfg_custom = SynthesisConfig(
        dataset_id="ds-1",
        privacy_level=PrivacyLevel.HIGH,
        delta=1e-4,
    )
    assert cfg_custom.resolved_delta() == 1e-4


def test_synthesis_config_bounds_validation() -> None:
    """Verify validation boundaries on SynthesisConfig fields.

    Pre-conditions:
        - ``SynthesisConfig`` model validates ``target_rows`` and ``epsilon``.
    Post-conditions:
        - Rejects rows outside [10, 200000] and non-positive epsilon.
    """
    with pytest.raises(ValidationError):
        SynthesisConfig(dataset_id="ds-1", target_rows=9)

    with pytest.raises(ValidationError):
        SynthesisConfig(dataset_id="ds-1", target_rows=200001)

    with pytest.raises(ValidationError):
        SynthesisConfig(dataset_id="ds-1", epsilon=-0.5)

    with pytest.raises(ValidationError):
        SynthesisConfig(dataset_id="ds-1", delta=0.0)

    # Valid boundary limits succeed
    valid_lower = SynthesisConfig(dataset_id="ds-1", target_rows=10)
    assert valid_lower.target_rows == 10
    valid_upper = SynthesisConfig(dataset_id="ds-1", target_rows=200000)
    assert valid_upper.target_rows == 200000


def test_numerical_stats_validation_bounds() -> None:
    """Verify validation bounds on NumericalStats.

    Pre-conditions:
        - ``NumericalStats`` requires non-negative standard deviation and outlier counts.
    Post-conditions:
        - Rejects negative std and negative outlier counts.
    """
    valid = NumericalStats(
        min=0.0,
        p25=2.5,
        median=5.0,
        p75=7.5,
        max=10.0,
        mean=5.0,
        std=1.2,
        skewness=0.05,
    )
    assert valid.std == 1.2
    assert valid.outlier_count_zscore == 0

    with pytest.raises(ValidationError):
        NumericalStats(
            min=0.0,
            p25=2.5,
            median=5.0,
            p75=7.5,
            max=10.0,
            mean=5.0,
            std=-0.01,
            skewness=0.0,
        )

    with pytest.raises(ValidationError):
        NumericalStats(
            min=0.0,
            p25=2.5,
            median=5.0,
            p75=7.5,
            max=10.0,
            mean=5.0,
            std=1.0,
            skewness=0.0,
            outlier_count_zscore=-1,
        )


def test_pii_finding_validation_bounds() -> None:
    """Verify validation bounds on PIIFinding.

    Pre-conditions:
        - ``PIIFinding`` requires confidence in [0.0, 1.0] and non-negative match counts.
    Post-conditions:
        - Rejects out-of-bounds confidence and negative match counts.
    """
    valid = PIIFinding(
        column_name="ssn",
        pii_type=PIIType.SSN,
        confidence=0.95,
        sample_match_count=10,
        detection_reason="Regex match",
        remediation="Tokenize or mask",
    )
    assert valid.confidence == 0.95

    with pytest.raises(ValidationError):
        PIIFinding(
            column_name="ssn",
            pii_type=PIIType.SSN,
            confidence=1.05,
            sample_match_count=1,
            detection_reason="Regex match",
            remediation="Mask",
        )

    with pytest.raises(ValidationError):
        PIIFinding(
            column_name="ssn",
            pii_type=PIIType.SSN,
            confidence=-0.1,
            sample_match_count=1,
            detection_reason="Regex match",
            remediation="Mask",
        )


def test_quality_validation_report_bounds() -> None:
    """Verify validation bounds on QualityValidationReport.

    Pre-conditions:
        - ``QualityValidationReport`` requires scores in [0.0, 1.0] and row counts >= 1.
    Post-conditions:
        - Rejects out-of-range scores and non-positive row counts.
    """
    col_metric = ColumnFidelityMetric(
        column_name="age",
        column_type=ColumnDataType.NUMERICAL,
        metric_name="ks_statistic",
        score=0.92,
        statistic_distance=0.08,
    )
    priv_metrics = PrivacyValidationMetrics(
        exact_match_collision_rate=0.0,
        dcr_median=2.5,
        dcr_p05=1.1,
        nndr_median=1.2,
        nndr_p05=0.95,
        privacy_protection_score=0.98,
    )
    ledger = PrivacyBudgetLedger(
        privacy_level=PrivacyLevel.MEDIUM,
        epsilon_spent=1.0,
        delta=1e-5,
        mechanism="Laplace",
        noise_scale=0.1,
    )

    valid_report = QualityValidationReport(
        job_id="job-1",
        dataset_id="ds-1",
        engine=SynthesizerEngine.GAUSSIAN_COPULA,
        privacy_level=PrivacyLevel.MEDIUM,
        real_row_count=500,
        synthetic_row_count=500,
        overall_quality_score=0.91,
        marginal_fidelity_score=0.92,
        correlation_stability_score=0.89,
        privacy_score=0.98,
        column_metrics=[col_metric],
        privacy_metrics=priv_metrics,
        privacy_ledger=ledger,
        executive_verdict="PASSED",
        hipaa_gdpr_ready=True,
        evaluated_at=datetime.now(),
    )
    assert valid_report.overall_quality_score == 0.91

    with pytest.raises(ValidationError):
        QualityValidationReport(
            job_id="job-1",
            dataset_id="ds-1",
            engine=SynthesizerEngine.GAUSSIAN_COPULA,
            privacy_level=PrivacyLevel.MEDIUM,
            real_row_count=0,
            synthetic_row_count=500,
            overall_quality_score=0.91,
            marginal_fidelity_score=0.92,
            correlation_stability_score=0.89,
            privacy_score=0.98,
            column_metrics=[col_metric],
            privacy_metrics=priv_metrics,
            privacy_ledger=ledger,
            executive_verdict="PASSED",
            hipaa_gdpr_ready=True,
            evaluated_at=datetime.now(),
        )


def test_list_and_get_benchmarks() -> None:
    """Verify list_benchmarks and get_benchmark_metadata behavior.

    Pre-conditions:
        - Registry contains the three built-in benchmark specifications.
    Post-conditions:
        - Returns 3 items and retrieves each by ID; raises KeyError on invalid ID.
    """
    benchmarks = list_benchmarks()
    assert len(benchmarks) == 3
    ids = {b.benchmark_id for b in benchmarks}
    expected_ids = {
        "healthcare_hipaa_readmissions",
        "fintech_fraud_transactions",
        "saas_customer_churn",
    }
    assert ids == expected_ids

    for b_id in expected_ids:
        meta = get_benchmark_metadata(b_id)
        assert meta.benchmark_id == b_id
        assert meta.default_row_count >= 10
        assert meta.target_column is not None

    with pytest.raises(KeyError):
        get_benchmark_metadata("non_existent_benchmark")


def test_generate_benchmark_dataset_invariants() -> None:
    """Verify general generator invariants: row count, error handling, and determinism.

    Pre-conditions:
        - ``generate_benchmark_dataset`` accepts benchmark ID, row_count, and seed.
    Post-conditions:
        - Exact row counts, deterministic outputs for seed=42, and error handling validated.
    """
    with pytest.raises(KeyError):
        generate_benchmark_dataset("unknown_id")

    with pytest.raises(ValueError):
        generate_benchmark_dataset("healthcare_hipaa_readmissions", row_count=19)

    # Determinism: same seed produces identical output
    data_1 = generate_benchmark_dataset(
        "healthcare_hipaa_readmissions",
        row_count=30,
        seed=42,
    )
    data_2 = generate_benchmark_dataset(
        "healthcare_hipaa_readmissions",
        row_count=30,
        seed=42,
    )
    assert data_1 == data_2
    assert len(data_1) == 30

    # Default row count
    data_default = generate_benchmark_dataset("healthcare_hipaa_readmissions")
    meta = BENCHMARK_REGISTRY["healthcare_hipaa_readmissions"]
    assert len(data_default) == meta.default_row_count


def test_healthcare_hipaa_readmissions_benchmark() -> None:
    """Verify healthcare HIPAA readmissions benchmark dataset properties.

    Pre-conditions:
        - ``healthcare_hipaa_readmissions`` generator produces 500 rows with seed 42.
    Post-conditions:
        - Verifies columns, duplicates, missing values, outliers, dirty states,
          class imbalance (< 0.30 and ~14-18%), and positive correlations with age.
    """
    dataset = generate_benchmark_dataset(
        "healthcare_hipaa_readmissions",
        row_count=500,
        seed=42,
    )
    assert len(dataset) == 500

    required_cols = {
        "patient_name",
        "ssn",
        "mrn",
        "email",
        "age",
        "state",
        "admission_type",
        "charlson_comorbidity_index",
        "length_of_stay_days",
        "lab_creatinine_mg_dl",
        "billing_amount_usd",
        "admission_date",
        "readmitted_30d",
    }
    for row in dataset:
        assert required_cols.issubset(row.keys())

    # Exact duplicate rows
    assert _count_exact_duplicates(dataset) == 2

    # Missing values in lab_creatinine_mg_dl
    missing_creat = sum(1 for r in dataset if r["lab_creatinine_mg_dl"] is None)
    assert 3 <= missing_creat <= 5

    # Extreme outliers in billing_amount_usd
    extreme_billing = [r for r in dataset if r["billing_amount_usd"] >= 400000.0]
    assert len(extreme_billing) == 2

    # Inconsistent state codes
    dirty_states = {r["state"] for r in dataset if r["state"] in (" ca ", "ny", "tx")}
    assert dirty_states == {" ca ", "ny", "tx"}

    # Class imbalance
    readmitted_vals = [r["readmitted_30d"] for r in dataset]
    assert set(readmitted_vals).issubset({0, 1})
    positive_ratio = sum(readmitted_vals) / len(readmitted_vals)
    assert 0.14 <= positive_ratio <= 0.18
    assert positive_ratio < 0.30

    # Correlations with age
    ages = [float(r["age"]) for r in dataset]
    charlsons = [float(r["charlson_comorbidity_index"]) for r in dataset]
    los = [float(r["length_of_stay_days"]) for r in dataset]
    billing = [float(r["billing_amount_usd"]) for r in dataset]

    assert _pearson_correlation(ages, charlsons) > 0.50
    assert _pearson_correlation(ages, los) > 0.50
    assert _pearson_correlation(ages, billing) > 0.30


def test_fintech_fraud_transactions_benchmark() -> None:
    """Verify fintech fraud transactions benchmark dataset properties.

    Pre-conditions:
        - ``fintech_fraud_transactions`` generator produces 500 rows with seed 42.
    Post-conditions:
        - Verifies columns, duplicates, missing values, outliers, dirty states,
          class imbalance (< 0.30 and ~8-12%), and correlations with amount and trust.
    """
    dataset = generate_benchmark_dataset(
        "fintech_fraud_transactions",
        row_count=500,
        seed=42,
    )
    assert len(dataset) == 500

    required_cols = {
        "cardholder_name",
        "cardholder_email",
        "phone",
        "ip_address",
        "state",
        "merchant_category",
        "transaction_amount_usd",
        "velocity_24h_count",
        "distance_from_home_km",
        "device_trust_score",
        "transaction_timestamp",
        "is_fraud",
    }
    for row in dataset:
        assert required_cols.issubset(row.keys())

    # Exact duplicate rows
    assert _count_exact_duplicates(dataset) == 2

    # Missing values in device_trust_score
    missing_trust = sum(1 for r in dataset if r["device_trust_score"] is None)
    assert missing_trust > 0

    # Extreme outliers in transaction_amount_usd
    extreme_amount = [r for r in dataset if r["transaction_amount_usd"] >= 90000.0]
    assert len(extreme_amount) == 2

    # Inconsistent state codes
    dirty_states = {r["state"] for r in dataset if r["state"] in (" ca ", "ny", "tx")}
    assert dirty_states == {" ca ", "ny", "tx"}

    # Class imbalance
    fraud_vals = [r["is_fraud"] for r in dataset]
    assert set(fraud_vals).issubset({0, 1})
    positive_ratio = sum(fraud_vals) / len(fraud_vals)
    assert 0.08 <= positive_ratio <= 0.12
    assert positive_ratio < 0.30

    # Correlations
    vels = [float(r["velocity_24h_count"]) for r in dataset]
    dists = [float(r["distance_from_home_km"]) for r in dataset]
    amounts = [float(r["transaction_amount_usd"]) for r in dataset]

    # Positive correlation with transaction_amount_usd
    assert _pearson_correlation(vels, amounts) > 0.20
    assert _spearman_correlation(vels, amounts) > 0.70
    assert _pearson_correlation(dists, amounts) > 0.20
    assert _spearman_correlation(dists, amounts) > 0.70

    # Negative correlation with device_trust_score (excluding None values)
    trust_pairs = [
        (
            float(r["velocity_24h_count"]),
            float(r["distance_from_home_km"]),
            float(r["device_trust_score"]),
        )
        for r in dataset
        if r["device_trust_score"] is not None
    ]
    t_vels = [p[0] for p in trust_pairs]
    t_dists = [p[1] for p in trust_pairs]
    t_scores = [p[2] for p in trust_pairs]

    assert _pearson_correlation(t_vels, t_scores) < -0.40
    assert _pearson_correlation(t_dists, t_scores) < -0.40


def test_saas_customer_churn_benchmark() -> None:
    """Verify SaaS customer churn benchmark dataset properties.

    Pre-conditions:
        - ``saas_customer_churn`` generator produces 500 rows with seed 42.
    Post-conditions:
        - Verifies columns, duplicates, missing values, outliers, dirty states,
          class imbalance (< 0.30 and ~12-16%), and domain correlations.
    """
    dataset = generate_benchmark_dataset(
        "saas_customer_churn",
        row_count=500,
        seed=42,
    )
    assert len(dataset) == 500

    required_cols = {
        "contact_name",
        "contact_email",
        "phone",
        "state",
        "plan_tier",
        "seat_count",
        "monthly_recurring_revenue_usd",
        "active_utilization_pct",
        "support_tickets_90d",
        "nps_score",
        "contract_start_date",
        "churned",
    }
    for row in dataset:
        assert required_cols.issubset(row.keys())

    # Exact duplicate rows
    assert _count_exact_duplicates(dataset) == 2

    # Missing values in nps_score
    missing_nps = sum(1 for r in dataset if r["nps_score"] is None)
    assert missing_nps > 0

    # Extreme outliers in monthly_recurring_revenue_usd
    extreme_mrr = [
        r for r in dataset if r["monthly_recurring_revenue_usd"] >= 800000.0
    ]
    assert len(extreme_mrr) == 2

    # Inconsistent state codes
    dirty_states = {r["state"] for r in dataset if r["state"] in (" ca ", "ny", "tx")}
    assert dirty_states == {" ca ", "ny", "tx"}

    # Class imbalance
    churn_vals = [r["churned"] for r in dataset]
    assert set(churn_vals).issubset({0, 1})
    positive_ratio = sum(churn_vals) / len(churn_vals)
    assert 0.12 <= positive_ratio <= 0.16
    assert positive_ratio < 0.30

    # Correlations
    seats = [float(r["seat_count"]) for r in dataset]
    mrr = [float(r["monthly_recurring_revenue_usd"]) for r in dataset]
    assert _pearson_correlation(seats, mrr) > 0.20
    assert _spearman_correlation(seats, mrr) > 0.80

    utils = [float(r["active_utilization_pct"]) for r in dataset]
    tickets = [float(r["support_tickets_90d"]) for r in dataset]
    assert _pearson_correlation(utils, tickets) < -0.40

    valid_nps = [
        (float(r["active_utilization_pct"]), float(r["nps_score"]))
        for r in dataset
        if r["nps_score"] is not None
    ]
    nps_utils = [p[0] for p in valid_nps]
    nps_scores = [p[1] for p in valid_nps]
    assert _pearson_correlation(nps_utils, nps_scores) > 0.40


def test_benchmark_minimal_row_count() -> None:
    """Verify that benchmark datasets function correctly at the minimum row count of 20.

    Pre-conditions:
        - Generator is invoked with ``row_count=20``.
    Post-conditions:
        - Confirms exactly 20 rows are produced, minority class ratio < 0.30,
          and duplicates present.
    """
    for bid in BENCHMARK_REGISTRY:
        data = generate_benchmark_dataset(bid, row_count=20, seed=42)
        assert len(data) == 20
        assert _count_exact_duplicates(data) == 2

        meta = BENCHMARK_REGISTRY[bid]
        labels = [r[meta.target_column] for r in data]
        positive_count = sum(1 for val in labels if val == meta.minority_label)
        ratio = positive_count / len(labels)
        assert ratio < 0.30
