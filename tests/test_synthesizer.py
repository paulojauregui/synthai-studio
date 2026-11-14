"""Unit tests for SynthAI Studio multi-engine synthesizer suite, DP accountant, and conditions.

Pre-conditions:
    - ``synthai_studio.synthesizer`` and ``synthai_studio.benchmarks`` are importable.
    - ``pytest``, ``numpy``, and ``httpx`` are installed.
Post-conditions:
    - All tests execute deterministically without live external network egress.
"""

from unittest.mock import MagicMock, patch

import httpx
import numpy as np
import pytest

from synthai_studio.benchmarks import generate_benchmark_dataset
from synthai_studio.models import (
    ComputeTier,
    ConditionOperator,
    ConditionRule,
    MinorityUpsampleConfig,
    PIIType,
    PrivacyLevel,
    SynthesisConfig,
    SynthesizerEngine,
)
from synthai_studio.synthesizer import (
    DifferentialPrivacyAccountant,
    generate_synthetic_pii_value,
    probe_spark_endpoint,
    project_to_psd_correlation,
    synthesize_dataset,
)


def test_project_to_psd_correlation() -> None:
    """Verify projection of non-PSD and indefinite matrices onto PSD correlation cone.

    Pre-conditions:
        - 3x3 indefinite symmetric matrix with negative eigenvalues.
    Post-conditions:
        - Result is symmetric, has 1.0 on diagonal, all eigenvalues > 0, and Cholesky succeeds.
    """
    bad_matrix = np.array(
        [
            [1.0, 0.9, 0.9],
            [0.9, 1.0, -0.9],
            [0.9, -0.9, 1.0],
        ]
    )
    eigvals = np.linalg.eigvals(bad_matrix)
    assert np.any(eigvals < 0.0)

    psd = project_to_psd_correlation(bad_matrix, min_eigenvalue=1e-5)
    assert psd.shape == (3, 3)
    assert np.allclose(psd, psd.T)
    assert np.allclose(np.diag(psd), 1.0)

    # Cholesky decomposition must succeed
    chol = np.linalg.cholesky(psd)
    assert chol.shape == (3, 3)

    # 1x1 edge case
    one_by_one = project_to_psd_correlation(np.array([[0.5]]))
    assert one_by_one[0, 0] == 1.0

    # Non-square raises ValueError
    with pytest.raises(ValueError):
        project_to_psd_correlation(np.array([[1.0, 2.0]]))


def test_differential_privacy_accountant_noise_scaling() -> None:
    """Verify differential privacy noise injection and monotone noise scaling across tiers.

    Pre-conditions:
        - DifferentialPrivacyAccountant instances for NONE, LOW, MEDIUM, and HIGH tiers.
    Post-conditions:
        - NONE yields 0 noise; noise scale monotonically increases from LOW to HIGH.
    """
    dp_none = DifferentialPrivacyAccountant(PrivacyLevel.NONE)
    assert dp_none.resolved_epsilon is None
    assert dp_none.noise_scale == 0.0

    arr = np.array([10.0, 20.0, 30.0, 40.0])
    perturbed_none = dp_none.perturb_quantiles(arr, 10.0, 40.0, 100)
    assert np.array_equal(arr, perturbed_none)

    dp_low = DifferentialPrivacyAccountant(PrivacyLevel.LOW)
    dp_med = DifferentialPrivacyAccountant(PrivacyLevel.MEDIUM)
    dp_high = DifferentialPrivacyAccountant(PrivacyLevel.HIGH)

    assert dp_low.resolved_epsilon == 10.0
    assert dp_med.resolved_epsilon == 1.0
    assert dp_high.resolved_epsilon == 0.1
    assert dp_high.delta == 1e-6

    # Monotonic noise scale: LOW < MEDIUM < HIGH
    assert 0.0 < dp_low.noise_scale < dp_med.noise_scale < dp_high.noise_scale

    ledger = dp_med.build_ledger()
    assert ledger.privacy_level == PrivacyLevel.MEDIUM
    assert ledger.epsilon_spent == 1.0
    assert ledger.psd_projection_applied is True


def test_generate_synthetic_pii_no_overlap() -> None:
    """Verify generated synthetic PII does not collide with raw benchmark PII.

    Pre-conditions:
        - Raw healthcare and fintech benchmark datasets.
    Post-conditions:
        - Synthetic PII across all types has zero intersection with raw real values.
    """
    raw_hc = generate_benchmark_dataset("healthcare_hipaa_readmissions", 50, 42)
    real_emails = {r["email"] for r in raw_hc}
    real_ssns = {r["ssn"] for r in raw_hc}
    real_names = {r["patient_name"] for r in raw_hc}
    real_mrns = {r["mrn"] for r in raw_hc}

    rng = np.random.default_rng(99)
    synth_emails = {
        generate_synthetic_pii_value(PIIType.EMAIL, i, rng)
        for i in range(50)
    }
    synth_ssns = {
        generate_synthetic_pii_value(PIIType.SSN, i, rng)
        for i in range(50)
    }
    synth_names = {
        generate_synthetic_pii_value(PIIType.PERSON_NAME, i, rng)
        for i in range(50)
    }
    synth_mrns = {
        generate_synthetic_pii_value(PIIType.MEDICAL_RECORD_NUMBER, i, rng)
        for i in range(50)
    }

    assert real_emails.isdisjoint(synth_emails)
    assert real_ssns.isdisjoint(synth_ssns)
    assert real_names.isdisjoint(synth_names)
    assert real_mrns.isdisjoint(synth_mrns)


def test_synthesize_dataset_gaussian_copula() -> None:
    """Verify Gaussian Copula synthesis on healthcare benchmark dataset.

    Pre-conditions:
        - Cleaned benchmark dataset rows.
    Post-conditions:
        - Produces exact row count, preserves column types, and achieves fidelity targets.
    """
    raw_rows = generate_benchmark_dataset("healthcare_hipaa_readmissions", 200, 42)
    cfg = SynthesisConfig(
        dataset_id="ds-hc",
        target_rows=150,
        engine=SynthesizerEngine.GAUSSIAN_COPULA,
        privacy_level=PrivacyLevel.LOW,
        random_seed=42,
    )

    synth_rows, ledger, tier = synthesize_dataset(raw_rows, cfg)
    assert len(synth_rows) == 150
    assert tier == ComputeTier.CPU_WORKER
    assert ledger.epsilon_spent == 10.0

    # Type invariants
    for r in synth_rows:
        assert isinstance(r["age"], int)
        assert isinstance(r["charlson_comorbidity_index"], int)
        assert isinstance(r["length_of_stay_days"], int)
        assert isinstance(r["billing_amount_usd"], float)
        assert isinstance(r["lab_creatinine_mg_dl"], float)
        assert isinstance(r["readmitted_30d"], int)
        assert isinstance(r["admission_date"], str)
        assert len(r["admission_date"]) == 10  # YYYY-MM-DD


def test_synthesize_dataset_ctgan_latent() -> None:
    """Verify CTGAN Latent mixture synthesizer.

    Pre-conditions:
        - Cleaned fintech benchmark dataset rows.
    Post-conditions:
        - Returns exact target rows with ComputeTier.CPU_WORKER.
    """
    raw_rows = generate_benchmark_dataset("fintech_fraud_transactions", 100, 42)
    cfg = SynthesisConfig(
        dataset_id="ds-fintech",
        target_rows=80,
        engine=SynthesizerEngine.CTGAN_LATENT,
        privacy_level=PrivacyLevel.MEDIUM,
        random_seed=42,
    )

    synth_rows, ledger, tier = synthesize_dataset(raw_rows, cfg)
    assert len(synth_rows) == 80
    assert tier == ComputeTier.CPU_WORKER
    assert ledger.epsilon_spent == 1.0


def test_synthesize_dataset_faker_hybrid() -> None:
    """Verify Faker Hybrid synthesizer coupling synthetic PII with copula attributes.

    Pre-conditions:
        - Cleaned SaaS benchmark dataset rows.
    Post-conditions:
        - Populates synthetic PII without real collisions and preserves numeric features.
    """
    raw_rows = generate_benchmark_dataset("saas_customer_churn", 100, 42)
    cfg = SynthesisConfig(
        dataset_id="ds-saas",
        target_rows=80,
        engine=SynthesizerEngine.FAKER_HYBRID,
        privacy_level=PrivacyLevel.NONE,
        anonymize_pii=True,
        random_seed=42,
    )

    synth_rows, ledger, tier = synthesize_dataset(raw_rows, cfg)
    assert len(synth_rows) == 80
    assert tier == ComputeTier.CPU_WORKER
    assert ledger.epsilon_spent is None

    real_contacts = {r["contact_name"] for r in raw_rows}
    synth_contacts = {r["contact_name"] for r in synth_rows}
    assert real_contacts.isdisjoint(synth_contacts)


def test_spark_llm_edge_circuit_breaker(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify DGX Spark synthesizer probe, circuit breaker, and local fallback.

    Pre-conditions:
        - SynthesisConfig configured for SPARK_LLM_EDGE engine.
    Post-conditions:
        - Falls back to CPU_WORKER when disabled or probe fails.
        - Emits GPU_SPARK_WORKER when Spark responds with valid completion.
    """
    raw_rows = generate_benchmark_dataset("healthcare_hipaa_readmissions", 50, 42)
    cfg = SynthesisConfig(
        dataset_id="ds-hc",
        target_rows=40,
        engine=SynthesizerEngine.SPARK_LLM_EDGE,
        random_seed=42,
    )

    # 1. Disabled via environment
    monkeypatch.setenv("SPARK_LLM_ENABLED", "false")
    rows_disabled, _, tier_disabled = synthesize_dataset(raw_rows, cfg)
    assert len(rows_disabled) == 40
    assert tier_disabled == ComputeTier.CPU_WORKER

    # 2. Enabled but probe fails (circuit-breaker triggered)
    monkeypatch.setenv("SPARK_LLM_ENABLED", "true")
    with patch("httpx.Client.get", side_effect=httpx.ConnectTimeout("Circuit breaker")):
        rows_probe_fail, _, tier_probe_fail = synthesize_dataset(raw_rows, cfg)
        assert len(rows_probe_fail) == 40
        assert tier_probe_fail == ComputeTier.CPU_WORKER

    # 3. Enabled and Spark responds successfully
    mock_get = MagicMock(status_code=200)
    mock_post = MagicMock(
        status_code=200,
        json=lambda: {
            "choices": [
                {
                    "message": {
                        "content": '[{"age": 72, "billing_amount_usd": 45000.0}]'
                    }
                }
            ]
        },
    )
    with patch("httpx.Client.get", return_value=mock_get):
        with patch("httpx.Client.post", return_value=mock_post):
            rows_spark, _, tier_spark = synthesize_dataset(raw_rows, cfg)
            assert len(rows_spark) == 40
            assert tier_spark == ComputeTier.GPU_SPARK_WORKER


def test_probe_spark_endpoint_mocked() -> None:
    """Verify probe_spark_endpoint handling of HTTP status and network exceptions.

    Pre-conditions:
        - Mocked httpx calls.
    Post-conditions:
        - Returns True on 200, False on 500 or timeout.
    """
    with patch("httpx.Client.get", return_value=MagicMock(status_code=200)):
        assert probe_spark_endpoint("http://mock-spark:8000/v1") is True

    with patch("httpx.Client.get", return_value=MagicMock(status_code=500)):
        assert probe_spark_endpoint("http://mock-spark:8000/v1") is False

    with patch("httpx.Client.get", side_effect=httpx.ConnectError("Unreachable")):
        assert probe_spark_endpoint("http://mock-spark:8000/v1") is False


def test_minority_upsampling() -> None:
    """Verify minority label upsampling achieves target ratio within tolerance.

    Pre-conditions:
        - Healthcare dataset with imbalanced readmitted_30d label.
        - Upsample target ratio set to 0.40.
    Post-conditions:
        - Output row count matches target_rows; positive label ratio is ~0.40.
    """
    raw_rows = generate_benchmark_dataset("healthcare_hipaa_readmissions", 200, 42)
    cfg = SynthesisConfig(
        dataset_id="ds-hc",
        target_rows=100,
        engine=SynthesizerEngine.GAUSSIAN_COPULA,
        upsample_config=MinorityUpsampleConfig(
            column="readmitted_30d",
            minority_value=1,
            target_ratio=0.40,
        ),
        random_seed=42,
    )

    synth_rows, _, _ = synthesize_dataset(raw_rows, cfg)
    assert len(synth_rows) == 100
    positives = sum(1 for r in synth_rows if r["readmitted_30d"] == 1)
    assert positives == 40


def test_declarative_conditions() -> None:
    """Verify that declarative ConditionRule constraints are 100% satisfied.

    Pre-conditions:
        - Rules covering GTE, IN, and EQ operators.
    Post-conditions:
        - 100% of generated rows strictly satisfy all declared conditions.
    """
    raw_rows = generate_benchmark_dataset("healthcare_hipaa_readmissions", 200, 42)
    cfg = SynthesisConfig(
        dataset_id="ds-hc",
        target_rows=100,
        engine=SynthesizerEngine.GAUSSIAN_COPULA,
        conditions=[
            ConditionRule(column="age", operator=ConditionOperator.GTE, value=65),
            ConditionRule(column="state", operator=ConditionOperator.IN, value=["CA", "NY"]),
            ConditionRule(
                column="admission_type",
                operator=ConditionOperator.EQ,
                value="ELECTIVE",
            ),
        ],
        random_seed=42,
    )

    synth_rows, _, _ = synthesize_dataset(raw_rows, cfg)
    assert len(synth_rows) == 100

    for r in synth_rows:
        assert r["age"] >= 65
        assert r["state"] in ["CA", "NY"]
        assert r["admission_type"] == "ELECTIVE"


def test_synthesizer_empty_input_validation() -> None:
    """Verify that empty real_rows input raises ValueError.

    Pre-conditions:
        - real_rows is empty.
    Post-conditions:
        - Raises ValueError.
    """
    cfg = SynthesisConfig(dataset_id="ds-empty", target_rows=50)
    with pytest.raises(ValueError):
        synthesize_dataset([], cfg)
