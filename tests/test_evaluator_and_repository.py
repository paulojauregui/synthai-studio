"""Unit tests for SynthAI Studio evaluator, repository, and workflow orchestrator.

Pre-conditions:
    - ``synthai_studio.evaluator``, ``repository``, and ``workflows`` are importable.
    - ``pytest`` and ``duckdb`` are installed.
Post-conditions:
    - All tests pass deterministically without external network egress.
"""

from tempfile import TemporaryDirectory

import pytest

from synthai_studio.benchmarks import generate_benchmark_dataset
from synthai_studio.evaluator import (
    compute_correlation_stability,
    compute_ks_complement,
    compute_privacy_metrics,
    compute_tvd_and_js_similarity,
    evaluate_synthetic_quality,
    render_quality_report_markdown,
)
from synthai_studio.models import (
    ExportFormat,
    JobStatus,
    PrivacyLevel,
    SynthesisConfig,
    SynthesizerEngine,
)
from synthai_studio.profiler import profile_dataset
from synthai_studio.repository import StudioRepository
from synthai_studio.synthesizer import synthesize_dataset
from synthai_studio.workflows import StudioWorkflowOrchestrator


def test_compute_ks_complement() -> None:
    """Verify Kolmogorov-Smirnov distance and complement calculation.

    Pre-conditions:
        - Numerical lists with identical and differing distributions.
    Post-conditions:
        - Identical lists return KS near 0.0 and score near 1.0; bounds respected.
    """
    real = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    score_ident, d_ks_ident = compute_ks_complement(real, real)
    assert d_ks_ident == 0.0
    assert score_ident == 1.0

    synth_diff = [50.0, 60.0, 70.0, 80.0, 90.0]
    score_diff, d_ks_diff = compute_ks_complement(real, synth_diff)
    assert d_ks_diff == 1.0
    assert score_diff == 0.0

    with pytest.raises(ValueError):
        compute_ks_complement([], [1.0])


def test_compute_tvd_and_js_similarity() -> None:
    """Verify Total Variation Distance and Jensen-Shannon similarity calculations.

    Pre-conditions:
        - Categorical lists with identical and disjoint categories.
    Post-conditions:
        - Accurately computes TVD and bounded JS similarity in [0.0, 1.0].
    """
    cats = ["A", "B", "A", "C", "B", "A"]
    tvd_score, tvd, js_sim = compute_tvd_and_js_similarity(cats, cats)
    assert tvd == 0.0
    assert tvd_score == 1.0
    assert js_sim == 1.0

    disjoint = ["X", "Y", "Z"]
    tvd_score_d, tvd_d, js_sim_d = compute_tvd_and_js_similarity(cats, disjoint)
    assert tvd_d == 1.0
    assert tvd_score_d == 0.0
    assert js_sim_d < 0.20

    with pytest.raises(ValueError):
        compute_tvd_and_js_similarity([], ["A"])


def test_compute_correlation_stability() -> None:
    """Verify Frobenius norm correlation stability scoring.

    Pre-conditions:
        - Identical, perturbed, and edge case correlation matrices.
    Post-conditions:
        - Returns 1.0 on identical matrices and bounded scores on perturbed matrices.
    """
    corr = [
        [1.0, 0.5, 0.2],
        [0.5, 1.0, -0.4],
        [0.2, -0.4, 1.0],
    ]
    assert compute_correlation_stability(corr, corr) == 1.0

    perturbed = [
        [1.0, 0.45, 0.25],
        [0.45, 1.0, -0.35],
        [0.25, -0.35, 1.0],
    ]
    stab = compute_correlation_stability(corr, perturbed)
    assert 0.90 <= stab <= 1.0

    assert compute_correlation_stability([], []) == 1.0
    assert compute_correlation_stability([[1.0]], [[1.0]]) == 1.0


def test_compute_privacy_metrics() -> None:
    """Verify privacy attack surface metrics (collision rate, PII leakage, DCR, NNDR).

    Pre-conditions:
        - Sample real and synthetic rows with and without exact row overlaps.
    Post-conditions:
        - Accurately tracks collisions, flags direct PII leakage, computes DCR/NNDR.
    """
    real_rows = [
        {"name": "Alice", "age": 30.0, "amount": 100.0},
        {"name": "Bob", "age": 40.0, "amount": 200.0},
        {"name": "Charlie", "age": 50.0, "amount": 300.0},
    ]
    synth_clean = [
        {"name": "ANON-1", "age": 31.0, "amount": 105.0},
        {"name": "ANON-2", "age": 41.0, "amount": 195.0},
    ]

    metrics = compute_privacy_metrics(
        real_rows,
        synth_clean,
        pii_columns=["name"],
        numeric_columns=["age", "amount"],
    )
    assert metrics.exact_match_collision_rate == 0.0
    assert metrics.pii_leakage_detected is False
    assert metrics.privacy_protection_score > 0.70
    assert metrics.dcr_median > 0.0

    # Leakage case
    synth_leaked = [
        {"name": "Alice", "age": 30.0, "amount": 100.0},
    ]
    metrics_leaked = compute_privacy_metrics(
        real_rows,
        synth_leaked,
        pii_columns=["name"],
        numeric_columns=["age", "amount"],
    )
    assert metrics_leaked.exact_match_collision_rate == 1.0
    assert metrics_leaked.pii_leakage_detected is True
    assert metrics_leaked.privacy_protection_score < 0.50


def test_evaluate_synthetic_quality_and_markdown_render() -> None:
    """Verify end-to-end evaluation report synthesis and markdown generation.

    Pre-conditions:
        - Real benchmark rows and synthesized rows from Gaussian Copula.
    Post-conditions:
        - Emits validated QualityValidationReport and clean Markdown audit report.
    """
    raw_rows = generate_benchmark_dataset("healthcare_hipaa_readmissions", 100, 42)
    cfg = SynthesisConfig(
        dataset_id="ds-hc",
        target_rows=80,
        engine=SynthesizerEngine.GAUSSIAN_COPULA,
        privacy_level=PrivacyLevel.LOW,
        random_seed=42,
    )
    synth_rows, ledger, _ = synthesize_dataset(raw_rows, cfg)

    report = evaluate_synthetic_quality(
        job_id="job-eval-1",
        dataset_id="ds-hc",
        real_rows=raw_rows,
        synth_rows=synth_rows,
        config=cfg,
        privacy_ledger=ledger,
    )

    assert report.job_id == "job-eval-1"
    assert report.real_row_count == 100
    assert report.synthetic_row_count == 80
    assert 0.0 <= report.overall_quality_score <= 1.0
    assert 0.0 <= report.marginal_fidelity_score <= 1.0
    assert 0.0 <= report.correlation_stability_score <= 1.0
    assert 0.0 <= report.privacy_score <= 1.0
    assert len(report.column_metrics) > 0

    md = render_quality_report_markdown(report)
    assert "# SynthAI Studio Quality Validation Report" in md
    assert "Differential Privacy Budget Ledger" in md
    assert "Privacy Attack Surface Metrics" in md
    assert "Column-Level Distribution Fidelity" in md
    # Ensure zero emojis in generated markdown
    assert all(ord(c) <= 127 for c in md)


def test_repository_lifecycle_and_exports() -> None:
    """Verify StudioRepository persistence, DuckDB CRUD, and PyArrow exports.

    Pre-conditions:
        - StudioRepository initialized with temporary directory storage.
    Post-conditions:
        - Datasets, jobs, reports, and tickets persist and export across formats.
    """
    with TemporaryDirectory() as tmpdir:
        repo = StudioRepository(db_path=":memory:", storage_dir=tmpdir)

        # 1. Dataset CRUD
        rows = [{"id": 1, "val": "alpha"}, {"id": 2, "val": "beta"}]
        meta = repo.save_dataset("Test Dataset", rows, description="Unit test")
        assert meta.row_count == 2
        assert meta.name == "Test Dataset"

        retrieved_meta = repo.get_dataset_metadata(meta.dataset_id)
        assert retrieved_meta.dataset_id == meta.dataset_id

        retrieved_rows = repo.get_dataset_rows(meta.dataset_id)
        assert retrieved_rows == rows

        datasets = repo.list_datasets()
        assert len(datasets) == 1

        # 2. Profile CRUD
        profile = profile_dataset(meta.dataset_id, meta.name, rows)
        repo.save_profile(profile)
        retrieved_profile = repo.get_profile(meta.dataset_id)
        assert retrieved_profile is not None
        assert retrieved_profile.row_count == 2

        # 3. Export formats
        csv_bytes, csv_media, csv_ext = repo.export_rows(rows, ExportFormat.CSV)
        assert b"alpha" in csv_bytes
        assert csv_media == "text/csv"
        assert csv_ext == "csv"

        json_bytes, json_media, json_ext = repo.export_rows(rows, ExportFormat.JSON)
        assert b"beta" in json_bytes
        assert json_media == "application/json"
        assert json_ext == "json"

        pq_bytes, pq_media, pq_ext = repo.export_rows(rows, ExportFormat.PARQUET)
        assert len(pq_bytes) > 0
        assert pq_media == "application/vnd.apache.parquet"
        assert pq_ext == "parquet"

        # 4. Presigned tickets
        ticket = repo.create_presigned_upload_ticket("Upload Dataset")
        assert ticket.upload_token is not None
        assert "Upload Dataset" == ticket.dataset_name

        consumed = repo.consume_presigned_upload_ticket(ticket.upload_token)
        assert consumed.upload_token == ticket.upload_token

        # Second consumption must fail
        with pytest.raises(KeyError):
            repo.consume_presigned_upload_ticket(ticket.upload_token)

        # Invalid token must fail
        with pytest.raises(KeyError):
            repo.consume_presigned_upload_ticket("invalid_token_123")


def test_workflow_orchestrator_bootstrap_and_pipeline() -> None:
    """Verify StudioWorkflowOrchestrator seeding, ingestion, cleansing, and synthesis.

    Pre-conditions:
        - StudioWorkflowOrchestrator wrapping a clean StudioRepository.
    Post-conditions:
        - Bootstrap seeds 3 benchmarks and sample job; cleansing and jobs succeed.
    """
    repo = StudioRepository(db_path=":memory:")
    orch = StudioWorkflowOrchestrator(repository=repo)

    # 1. Bootstrap defaults
    orch.bootstrap_defaults()
    datasets = repo.list_datasets()
    assert len(datasets) == 3

    jobs = repo.list_jobs()
    assert len(jobs) == 1
    assert jobs[0].status == JobStatus.COMPLETED

    # 2. Idempotent bootstrap
    orch.bootstrap_defaults()
    assert len(repo.list_datasets()) == 3
    assert len(repo.list_jobs()) == 1

    # 3. Cleanse existing dataset
    hc_ds = [d for d in datasets if d.benchmark_id == "healthcare_hipaa_readmissions"][0]
    clean_meta, clean_profile = orch.cleanse_existing_dataset(hc_ds.dataset_id)
    assert clean_meta.is_cleansed is True
    assert clean_profile.duplicate_row_count == 0
    assert clean_profile.privacy_risk_score == 0.0

    # 4. Ingest new dataset
    custom_rows = [{"user": "Alice", "score": 90}, {"user": "Bob", "score": 85}]
    in_meta, in_prof = orch.ingest_dataset("Custom", custom_rows)
    assert in_meta.row_count == 2
    assert in_prof.row_count == 2

    # 5. Run generation job
    gen_cfg = SynthesisConfig(
        dataset_id=clean_meta.dataset_id,
        target_rows=60,
        engine=SynthesizerEngine.GAUSSIAN_COPULA,
        privacy_level=PrivacyLevel.LOW,
        random_seed=42,
    )
    job, report = orch.run_generation_job(gen_cfg)
    assert job.status == JobStatus.COMPLETED
    assert job.rows_generated == 60
    assert report.synthetic_row_count == 60
    assert repo.get_quality_report(job.job_id).job_id == job.job_id
