"""SynthAI Studio Temporal.io Durable Workflows and Local Orchestration Harness.

Pre-conditions:
    - Python >= 3.11 with ``temporalio`` installed.
Post-conditions:
    - Defines Temporal durable workflows and activities with standalone in-process
      fallback orchestration and automatic benchmark seeding.
"""

import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

from temporalio import activity, workflow

from synthai_studio.benchmarks import generate_benchmark_dataset, get_benchmark_metadata
from synthai_studio.evaluator import evaluate_synthetic_quality
from synthai_studio.models import (
    DatasetMetadata,
    DatasetProfileReport,
    GenerationJob,
    JobStatus,
    PrivacyLevel,
    QualityValidationReport,
    SynthesisConfig,
    SynthesizerEngine,
)
from synthai_studio.profiler import cleanse_dataset, profile_dataset
from synthai_studio.repository import StudioRepository
from synthai_studio.synthesizer import synthesize_dataset

__all__ = [
    "DatasetProfileWorkflow",
    "StudioWorkflowOrchestrator",
    "SyntheticGenerationWorkflow",
    "generate_synthetic_activity",
    "profile_dataset_activity",
]

DEFAULT_TEMPORAL_HOST = "temporal-frontend.temporal-system.svc.cluster.local:7233"


@activity.defn
async def profile_dataset_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Temporal durable activity executing dataset profiling.

    Pre-conditions:
        - ``params`` contains 'dataset_id', 'dataset_name', and 'rows'.
    Post-conditions:
        - Computes DatasetProfileReport and returns dictionary representation.
    """
    dataset_id = str(params["dataset_id"])
    dataset_name = str(params["dataset_name"])
    rows = list(params["rows"])
    report = profile_dataset(dataset_id, dataset_name, rows)
    return report.model_dump()


@workflow.defn
class DatasetProfileWorkflow:
    """Temporal workflow definition for durable dataset profiling.

    Pre-conditions:
        - Python >= 3.11 with temporalio.
    Post-conditions:
        - Coordinates distributed profiling activity execution.
    """

    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute durable dataset profiling workflow.

        Pre-conditions:
            - ``params`` dictionary.
        Post-conditions:
            - Returns serialized profiling report.
        """
        res: dict[str, Any] = await workflow.execute_activity(
            profile_dataset_activity,
            params,
            start_to_close_timeout=timedelta(minutes=5),
        )
        return res


@activity.defn
async def generate_synthetic_activity(params: dict[str, Any]) -> dict[str, Any]:
    """Temporal durable activity executing synthetic generation and auditing.

    Pre-conditions:
        - ``params`` contains 'real_rows' and serialized 'config'.
    Post-conditions:
        - Returns dictionary with 'synthetic_rows', 'job', and 'quality_report'.
    """
    real_rows = list(params["real_rows"])
    config = SynthesisConfig.model_validate(params["config"])
    profile_data = params.get("profile")
    profile = DatasetProfileReport.model_validate(profile_data) if profile_data else None

    synth_rows, ledger, tier = synthesize_dataset(real_rows, config, profile)
    job_id = params.get("job_id", f"job-{uuid.uuid4().hex[:8]}")
    report = evaluate_synthetic_quality(
        job_id,
        config.dataset_id,
        real_rows,
        synth_rows,
        config,
        ledger,
        profile,
    )

    return {
        "synthetic_rows": synth_rows,
        "compute_tier": tier.value,
        "privacy_ledger": ledger.model_dump(),
        "quality_report": report.model_dump(),
    }


@workflow.defn
class SyntheticGenerationWorkflow:
    """Temporal workflow definition for durable synthetic generation and quality auditing.

    Pre-conditions:
        - Python >= 3.11 with temporalio.
    Post-conditions:
        - Orchestrates multi-engine generation and quality audit activities.
    """

    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute durable synthesis and evaluation workflow.

        Pre-conditions:
            - ``params`` dictionary.
        Post-conditions:
            - Returns execution results.
        """
        res: dict[str, Any] = await workflow.execute_activity(
            generate_synthetic_activity,
            params,
            start_to_close_timeout=timedelta(minutes=15),
        )
        return res


class StudioWorkflowOrchestrator:
    """Orchestrator for dataset seeding, ingestion, cleansing, and generation jobs.

    Pre-conditions:
        - ``repository`` is an active StudioRepository.
    Post-conditions:
        - Supports standalone in-process execution and optional Temporal cluster dispatch.
    """

    def __init__(
        self,
        repository: StudioRepository,
        temporal_host: str | None = None,
        temporal_enabled: bool = False,
    ) -> None:
        """Initialize StudioWorkflowOrchestrator.

        Pre-conditions:
            - None.
        Post-conditions:
            - Stores repository and configuration settings.
        """
        self.repository = repository
        self.temporal_host = (
            temporal_host
            or os.getenv("TEMPORAL_HOST")
            or DEFAULT_TEMPORAL_HOST
        )
        self.temporal_enabled = temporal_enabled

    def seed_benchmark(
        self,
        benchmark_id: str,
        row_count: int | None = None,
        seed: int = 42,
    ) -> tuple[DatasetMetadata, DatasetProfileReport]:
        """Seed a built-in benchmark dataset into the catalog with its profile report.

        Pre-conditions:
            - ``benchmark_id`` exists in BENCHMARK_REGISTRY.
        Post-conditions:
            - Generates, persists, profiles, and registers the benchmark dataset.
        """
        meta_desc = get_benchmark_metadata(benchmark_id)
        resolved_count = row_count or meta_desc.default_row_count
        rows = generate_benchmark_dataset(benchmark_id, row_count=resolved_count, seed=seed)

        ds_id = f"ds-{benchmark_id}"
        meta = self.repository.save_dataset(
            name=meta_desc.name,
            rows=rows,
            description=meta_desc.description,
            source_type="benchmark",
            benchmark_id=benchmark_id,
            is_cleansed=False,
            dataset_id=ds_id,
        )

        profile = profile_dataset(ds_id, meta.name, rows)
        self.repository.save_profile(profile)

        return meta, profile

    def ingest_dataset(
        self,
        name: str,
        rows: list[dict[str, Any]],
        description: str = "",
        source_type: str = "upload",
    ) -> tuple[DatasetMetadata, DatasetProfileReport]:
        """Ingest and profile an uploaded dataset.

        Pre-conditions:
            - ``rows`` is non-empty.
        Post-conditions:
            - Persists dataset and profiling report into catalog.
        """
        meta = self.repository.save_dataset(
            name=name,
            rows=rows,
            description=description,
            source_type=source_type,
            is_cleansed=False,
        )
        profile = profile_dataset(meta.dataset_id, name, rows)
        self.repository.save_profile(profile)

        return meta, profile

    def cleanse_existing_dataset(
        self,
        dataset_id: str,
        anonymize_pii: bool = True,
    ) -> tuple[DatasetMetadata, DatasetProfileReport]:
        """Cleanse, deduplicate, normalize, and anonymize an existing catalog dataset.

        Pre-conditions:
            - ``dataset_id`` exists in catalog.
        Post-conditions:
            - Persists a new cleansed catalog record and re-profiled audit report.
        """
        raw_rows = self.repository.get_dataset_rows(dataset_id)
        raw_meta = self.repository.get_dataset_metadata(dataset_id)

        clean_rows = cleanse_dataset(raw_rows, anonymize_pii=anonymize_pii, seed=42)
        clean_name = f"{raw_meta.name} (Cleansed)"
        clean_desc = f"Cleansed and deduplicated derivation of {raw_meta.name}."

        clean_meta = self.repository.save_dataset(
            name=clean_name,
            rows=clean_rows,
            description=clean_desc,
            source_type="cleanse",
            benchmark_id=raw_meta.benchmark_id,
            is_cleansed=True,
        )

        clean_profile = profile_dataset(clean_meta.dataset_id, clean_name, clean_rows)
        self.repository.save_profile(clean_profile)

        return clean_meta, clean_profile

    def run_generation_job(
        self,
        config: SynthesisConfig,
    ) -> tuple[GenerationJob, QualityValidationReport]:
        """Execute a complete synthetic generation job and emit a quality audit report.

        Pre-conditions:
            - ``config.dataset_id`` exists in repository.
            - ``config.target_rows >= 10``.
        Post-conditions:
            - Generates synthetic rows, audits quality against real rows, and saves records.
        """
        real_rows = self.repository.get_dataset_rows(config.dataset_id)
        real_meta = self.repository.get_dataset_metadata(config.dataset_id)
        real_profile = self.repository.get_profile(config.dataset_id)

        job_id = f"job-{uuid.uuid4().hex[:8]}"
        job = GenerationJob(
            job_id=job_id,
            dataset_id=config.dataset_id,
            dataset_name=real_meta.name,
            status=JobStatus.RUNNING,
            config=config,
            created_at=datetime.now(),
        )
        self.repository.save_job(job)

        start_time = time.perf_counter()
        synth_rows, ledger, tier = synthesize_dataset(real_rows, config, real_profile)
        elapsed = max(0.001, time.perf_counter() - start_time)
        throughput = round(len(synth_rows) / elapsed, 2)

        report = evaluate_synthetic_quality(
            job_id=job_id,
            dataset_id=config.dataset_id,
            real_rows=real_rows,
            synth_rows=synth_rows,
            config=config,
            privacy_ledger=ledger,
            real_profile=real_profile,
        )

        now = datetime.now()
        job.status = JobStatus.COMPLETED
        job.compute_tier = tier
        job.rows_generated = len(synth_rows)
        job.throughput_rows_per_sec = throughput
        job.privacy_ledger = ledger
        job.overall_quality_score = report.overall_quality_score
        job.completed_at = now

        self.repository.save_job(job, synth_rows)
        self.repository.save_quality_report(report)

        return job, report

    def bootstrap_defaults(self) -> None:
        """Idempotently seed the 3 built-in benchmark datasets and an initial sample job.

        Pre-conditions:
            - None.
        Post-conditions:
            - If catalog is empty, seeds benchmarks and runs initial sample generation job.
        """
        existing = self.repository.list_datasets()
        if existing:
            return

        hc_meta, _ = self.seed_benchmark("healthcare_hipaa_readmissions")
        self.seed_benchmark("fintech_fraud_transactions")
        self.seed_benchmark("saas_customer_churn")

        sample_cfg = SynthesisConfig(
            dataset_id=hc_meta.dataset_id,
            target_rows=150,
            engine=SynthesizerEngine.GAUSSIAN_COPULA,
            privacy_level=PrivacyLevel.MEDIUM,
            random_seed=42,
        )
        self.run_generation_job(sample_cfg)

    def bootstrap_default_catalog(self) -> None:
        """Alias for bootstrap_defaults for backward and forward compatibility.

        Pre-conditions:
            - None.
        Post-conditions:
            - Executes bootstrap_defaults.
        """
        self.bootstrap_defaults()
