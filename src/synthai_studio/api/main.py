"""SynthAI Studio FastAPI REST Service and 5-Step Interactive Web UI.

Pre-conditions:
    - Python >= 3.11 with FastAPI, Pydantic, and DuckDB installed.
Post-conditions:
    - Exposes REST endpoints for benchmarks, dataset ingestion, profiling,
      cleansing, synthetic generation, quality auditing, and file downloads.
    - Exposes interactive 5-step single-page HTML5 console at GET /.
"""

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

from synthai_studio.api.ui import load_studio_index_html, mount_studio_ui
from synthai_studio.benchmarks import BENCHMARK_REGISTRY, list_benchmarks
from synthai_studio.evaluator import render_quality_report_markdown
from synthai_studio.models import (
    BenchmarkMetadata,
    DatasetMetadata,
    DatasetProfileReport,
    ExportFormat,
    GenerationJob,
    PresignedUploadTicket,
    SynthesisConfig,
)
from synthai_studio.profiler import parse_tabular_payload
from synthai_studio.repository import StudioRepository
from synthai_studio.workflows import StudioWorkflowOrchestrator

__all__ = [
    "CleanseRequest",
    "PresignRequest",
    "SeedRequest",
    "UploadPayloadRequest",
    "_build_studio_ui_html",
    "app",
    "create_app",
]


class SeedRequest(BaseModel):
    """Payload for seeding a benchmark dataset with a custom row count.

    Pre-conditions:
        - row_count must be positive if supplied.
    Post-conditions:
        - Encapsulates benchmark seeding request parameters.
    """

    row_count: int | None = Field(default=None, ge=10, le=100000)


class UploadPayloadRequest(BaseModel):
    """JSON payload model for direct tabular dataset upload.

    Pre-conditions:
        - Must supply either 'rows' list or raw 'content' string.
    Post-conditions:
        - Encapsulates tabular data ingestion parameters.
    """

    name: str = "custom_dataset"
    content: str | None = None
    filename: str = "dataset.csv"
    rows: list[dict[str, Any]] | None = None


class PresignRequest(BaseModel):
    """Payload for requesting an S3/SeaweedFS presigned upload ticket.

    Pre-conditions:
        - dataset_name is a non-empty string.
    Post-conditions:
        - Encapsulates capability ticket configuration.
    """

    dataset_name: str
    expiry_seconds: int = Field(default=3600, ge=60, le=86400)


class CleanseRequest(BaseModel):
    """Payload configuring dataset cleansing and PII anonymization.

    Pre-conditions:
        - None.
    Post-conditions:
        - Encapsulates cleansing execution preferences.
    """

    anonymize_pii: bool = True


def _build_studio_ui_html() -> str:
    """Generate self-contained HTML5 single-page application for SynthAI Studio.

    Pre-conditions:
        - templates/index.html exists under synthai_studio/api/templates.
    Post-conditions:
        - Returns high-density, terminal-inspired HTML string with zero emojis.
    """
    return load_studio_index_html()


def create_app(
    repository: StudioRepository | None = None,
    bootstrap: bool = True,
) -> FastAPI:
    """Create and configure the SynthAI Studio FastAPI application.

    Pre-conditions:
        - Python >= 3.11 with FastAPI.
    Post-conditions:
        - Returns a configured FastAPI application with all routes, health checks,
          static assets, and interactive web console mounted.
    """
    repo = repository if repository is not None else StudioRepository()
    orchestrator = StudioWorkflowOrchestrator(repo)

    if bootstrap:
        orchestrator.bootstrap_defaults()

    application = FastAPI(
        title="SynthAI Studio",
        description="Privacy-Preserving Synthetic Data & Differential Privacy Quality Auditing",
        version="0.1.0",
    )

    # Attach instances to application state for test and inspection access
    application.state.repository = repo
    application.state.orchestrator = orchestrator

    # Mount UI static assets and GET / root template route
    mount_studio_ui(application)

    @application.get("/healthz")
    async def healthz() -> dict[str, str]:
        """Health check liveness probe.

        Pre-conditions:
            - Service process is responsive.
        Post-conditions:
            - Returns healthy status indicator.
        """
        return {"status": "healthy", "service": "synthai-studio", "version": "0.1.0"}

    @application.get("/ready")
    async def ready() -> dict[str, Any]:
        """Readiness check probe validating DuckDB catalog and orchestrator.

        Pre-conditions:
            - Repository and Orchestrator are initialized.
        Post-conditions:
            - Returns ready status with dataset and job counts in < 50ms.
        """
        datasets = repo.list_datasets()
        jobs = repo.list_jobs()
        return {
            "status": "ready",
            "datasets_count": len(datasets),
            "jobs_count": len(jobs),
            "temporal_host": orchestrator.temporal_host,
        }

    @application.get("/api/v1/benchmarks", response_model=list[BenchmarkMetadata])
    async def list_benchmarks_endpoint() -> list[BenchmarkMetadata]:
        """Enumerate built-in reference benchmark dataset descriptors.

        Pre-conditions:
            - None.
        Post-conditions:
            - Returns list of available BenchmarkMetadata items.
        """
        return list_benchmarks()

    @application.post("/api/v1/datasets/seed/{benchmark_id}")
    async def seed_benchmark_endpoint(
        benchmark_id: str,
        row_count: int | None = None,
        payload: SeedRequest | None = None,
    ) -> dict[str, Any]:
        """Seed a built-in benchmark dataset into the catalog.

        Pre-conditions:
            - benchmark_id exists in BENCHMARK_REGISTRY.
        Post-conditions:
            - Returns dictionary with 'dataset' and 'profile'.
        """
        if benchmark_id not in BENCHMARK_REGISTRY:
            raise HTTPException(
                status_code=404,
                detail=f"Benchmark '{benchmark_id}' not found",
            )

        resolved_count = row_count
        if resolved_count is None and payload is not None:
            resolved_count = payload.row_count

        meta, profile = orchestrator.seed_benchmark(
            benchmark_id=benchmark_id,
            row_count=resolved_count,
        )
        return {"dataset": meta, "profile": profile}

    @application.post("/api/v1/benchmarks/{benchmark_id}/seed")
    async def seed_benchmark_alias_endpoint(
        benchmark_id: str,
        row_count: int | None = None,
        payload: SeedRequest | None = None,
    ) -> dict[str, Any]:
        """Route alias delegating to seed_benchmark_endpoint.

        Pre-conditions:
            - benchmark_id exists in BENCHMARK_REGISTRY.
        Post-conditions:
            - Returns dictionary with 'dataset' and 'profile'.
        """
        return await seed_benchmark_endpoint(
            benchmark_id=benchmark_id,
            row_count=row_count,
            payload=payload,
        )

    @application.post("/api/v1/datasets/presign-upload", response_model=PresignedUploadTicket)
    async def presign_upload_endpoint(req: PresignRequest) -> PresignedUploadTicket:
        """Create a presigned upload capability ticket for SeaweedFS/S3 streaming.

        Pre-conditions:
            - req.dataset_name is non-empty.
        Post-conditions:
            - Generates and persists a PresignedUploadTicket.
        """
        return repo.create_presigned_upload_ticket(
            dataset_name=req.dataset_name,
            expiry_seconds=req.expiry_seconds,
        )

    @application.post("/api/v1/presign", response_model=PresignedUploadTicket)
    async def presign_alias_endpoint(req: PresignRequest) -> PresignedUploadTicket:
        """Route alias delegating to presign_upload_endpoint.

        Pre-conditions:
            - req.dataset_name is non-empty.
        Post-conditions:
            - Generates and persists a PresignedUploadTicket.
        """
        return await presign_upload_endpoint(req=req)

    @application.post("/api/v1/datasets/upload")
    async def upload_dataset_endpoint(
        request: Request,
        token: str | None = None,
    ) -> dict[str, Any]:
        """Ingest and profile a custom tabular dataset via multipart file or JSON.

        Pre-conditions:
            - Valid multipart form file or JSON payload containing tabular rows.
        Post-conditions:
            - Ingests, persists, and profiles dataset into DuckDB catalog.
        """
        ticket: PresignedUploadTicket | None = None
        if token:
            try:
                ticket = repo.consume_presigned_upload_ticket(token)
            except KeyError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        content_type = request.headers.get("content-type", "")
        name = ticket.dataset_name if ticket else "uploaded_dataset"
        rows: list[dict[str, Any]] = []

        if "multipart/form-data" in content_type:
            form = await request.form()
            file_item = form.get("file")
            if file_item is None or not hasattr(file_item, "read"):
                raise HTTPException(
                    status_code=400,
                    detail="Missing 'file' field in multipart form upload",
                )
            form_name = form.get("name")
            if form_name and isinstance(form_name, str) and not ticket:
                name = form_name
            filename = getattr(file_item, "filename", "upload.csv") or "upload.csv"
            raw_bytes = await file_item.read()
            rows = parse_tabular_payload(raw_bytes, filename=filename)
        elif "application/json" in content_type:
            body = await request.json()
            if not isinstance(body, dict):
                raise HTTPException(
                    status_code=400,
                    detail="JSON payload must be a JSON object",
                )
            if "name" in body and body["name"] and not ticket:
                name = str(body["name"])
            if "rows" in body and isinstance(body["rows"], list):
                rows = [dict(r) for r in body["rows"]]
            elif "content" in body:
                fname = str(body.get("filename", "upload.csv"))
                rows = parse_tabular_payload(str(body["content"]), filename=fname)
            else:
                raise HTTPException(
                    status_code=400,
                    detail="JSON payload must contain 'rows' list or 'content' string",
                )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported Content-Type '{content_type}'",
            )

        if not rows:
            raise HTTPException(
                status_code=400,
                detail="Tabular dataset contains zero parseable rows",
            )

        meta, profile = orchestrator.ingest_dataset(
            name=name,
            rows=rows,
            description=f"User ingested dataset '{name}' ({len(rows)} records)",
            source_type="upload",
        )
        return {"dataset": meta, "profile": profile}

    @application.get("/api/v1/datasets", response_model=list[DatasetMetadata])
    async def list_datasets_endpoint() -> list[DatasetMetadata]:
        """List all datasets in the DuckDB catalog.

        Pre-conditions:
            - None.
        Post-conditions:
            - Returns list of DatasetMetadata records.
        """
        return repo.list_datasets()

    @application.get("/api/v1/datasets/{dataset_id}/profile", response_model=DatasetProfileReport)
    async def get_dataset_profile_endpoint(dataset_id: str) -> DatasetProfileReport:
        """Retrieve the statistical profiling and PII report for a dataset.

        Pre-conditions:
            - dataset_id exists.
        Post-conditions:
            - Returns DatasetProfileReport; raises 404 if not found.
        """
        profile = repo.get_profile(dataset_id)
        if profile is None:
            raise HTTPException(
                status_code=404,
                detail=f"Profile for dataset '{dataset_id}' not found",
            )
        return profile

    @application.post("/api/v1/datasets/{dataset_id}/cleanse")
    async def cleanse_dataset_endpoint(
        dataset_id: str,
        payload: CleanseRequest | None = None,
    ) -> dict[str, Any]:
        """Cleanse, deduplicate, normalize, and anonymize an existing dataset.

        Pre-conditions:
            - dataset_id exists in catalog.
        Post-conditions:
            - Persists and returns cleansed dataset and newly profiled report.
        """
        anonymize = True if payload is None else payload.anonymize_pii
        try:
            clean_meta, clean_profile = orchestrator.cleanse_existing_dataset(
                dataset_id=dataset_id,
                anonymize_pii=anonymize,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"dataset": clean_meta, "profile": clean_profile}

    @application.post("/api/v1/jobs/generate")
    async def generate_synthetic_job_endpoint(config: SynthesisConfig) -> dict[str, Any]:
        """Execute a synthetic generation job and emit a quality audit report.

        Pre-conditions:
            - config.dataset_id exists in catalog.
            - config.target_rows >= 10.
        Post-conditions:
            - Returns dictionary with 'job' (GenerationJob) and 'report' (QualityValidationReport).
        """
        try:
            repo.get_dataset_metadata(config.dataset_id)
        except KeyError as exc:
            raise HTTPException(
                status_code=404,
                detail=f"Dataset '{config.dataset_id}' not found in catalog",
            ) from exc

        job, report = orchestrator.run_generation_job(config)
        return {"job": job, "report": report}

    @application.post("/api/v1/jobs")
    async def generate_synthetic_job_alias_endpoint(
        config: SynthesisConfig,
    ) -> dict[str, Any]:
        """Route alias delegating to generate_synthetic_job_endpoint.

        Pre-conditions:
            - config.dataset_id exists in catalog.
            - config.target_rows >= 10.
        Post-conditions:
            - Returns dictionary with 'job' and 'report'.
        """
        return await generate_synthetic_job_endpoint(config=config)

    @application.get("/api/v1/jobs", response_model=list[GenerationJob])
    async def list_jobs_endpoint() -> list[GenerationJob]:
        """Enumerate all historical synthetic generation jobs.

        Pre-conditions:
            - None.
        Post-conditions:
            - Returns list of GenerationJob records.
        """
        return repo.list_jobs()

    @application.get("/api/v1/jobs/{job_id}", response_model=GenerationJob)
    async def get_job_endpoint(job_id: str) -> GenerationJob:
        """Retrieve details of a single generation job.

        Pre-conditions:
            - job_id exists.
        Post-conditions:
            - Returns GenerationJob; raises 404 if not found.
        """
        try:
            return repo.get_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @application.get("/api/v1/jobs/{job_id}/report")
    async def get_job_report_endpoint(
        job_id: str,
        format: str = "json",
    ) -> Response:
        """Retrieve synthetic quality validation report in JSON or Markdown format.

        Pre-conditions:
            - job_id exists and has a validated report.
            - format is 'json' or 'markdown'.
        Post-conditions:
            - Returns JSON or Markdown content.
        """
        try:
            report = repo.get_quality_report(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        if format.lower() == "markdown":
            md_text = render_quality_report_markdown(report)
            return Response(content=md_text, media_type="text/markdown")

        return Response(
            content=report.model_dump_json(),
            media_type="application/json",
        )

    @application.get("/api/v1/jobs/{job_id}/download")
    async def download_synthetic_dataset_endpoint(
        job_id: str,
        format: str = "csv",
    ) -> Response:
        """Download generated synthetic rows in CSV, JSON, or Parquet format.

        Pre-conditions:
            - job_id exists.
            - format is 'csv', 'json', or 'parquet'.
        Post-conditions:
            - Returns binary payload with Content-Disposition attachment header.
        """
        try:
            repo.get_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        rows = repo.get_job_rows(job_id)
        try:
            export_fmt = ExportFormat(format.lower())
        except ValueError as exc:
            allowed = [f.value for f in ExportFormat]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format '{format}'. Allowed: {allowed}",
            ) from exc

        payload, media_type, ext = repo.export_rows(rows, export_fmt)
        filename = f"synthai-{job_id}.{ext}"
        return Response(
            content=payload,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return application


# Global application instance for uvicorn runtime
app: FastAPI = create_app(
    bootstrap=os.getenv("SYNTHAI_BOOTSTRAP", "true").lower() in ("true", "1", "yes")
)
