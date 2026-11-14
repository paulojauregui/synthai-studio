"""SynthAI Studio DuckDB Catalog, Parquet Storage, and Presigned Ticket Repository.

Pre-conditions:
    - Python >= 3.11 with ``duckdb`` and ``pyarrow`` installed.
Post-conditions:
    - Provides ACID catalog persistence, PyArrow Parquet/CSV/JSON export serialization,
      and secure presigned upload/download ticket lifecycle management.
"""

import csv
import io
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from synthai_studio.models import (
    DatasetMetadata,
    DatasetProfileReport,
    ExportFormat,
    GenerationJob,
    PresignedUploadTicket,
    QualityValidationReport,
)

__all__ = [
    "StudioRepository",
]


class StudioRepository:
    """Embedded DuckDB catalog and PyArrow dataset persistence repository.

    Pre-conditions:
        - ``db_path`` points to valid file path or ':memory:'.
    Post-conditions:
        - Manages datasets, generation jobs, profiling audits, and presigned capabilities.
    """

    def __init__(
        self,
        db_path: str | Path = ":memory:",
        storage_dir: str | Path | None = None,
    ) -> None:
        """Initialize the DuckDB repository and configure storage paths.

        Pre-conditions:
            - None.
        Post-conditions:
            - Schema tables are created and storage directories initialized.
        """
        self.db_path = str(db_path)
        self.storage_dir = Path(storage_dir) if storage_dir else None
        if self.storage_dir:
            self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.conn = duckdb.connect(self.db_path)
        self._init_schema()

        # In-memory buffer for fast dataset retrieval
        self._dataset_rows: dict[str, list[dict[str, Any]]] = {}
        self._job_rows: dict[str, list[dict[str, Any]]] = {}

    def _init_schema(self) -> None:
        """Create relational schema tables in DuckDB.

        Pre-conditions:
            - Database connection is open.
        Post-conditions:
            - Tables datasets, dataset_profiles, generation_jobs, quality_reports,
              and upload_tickets are created if not existing.
        """
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets (
                dataset_id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                description VARCHAR,
                source_type VARCHAR NOT NULL,
                benchmark_id VARCHAR,
                row_count INTEGER NOT NULL,
                column_count INTEGER NOT NULL,
                columns VARCHAR NOT NULL,
                is_cleansed BOOLEAN NOT NULL,
                created_at TIMESTAMP NOT NULL
            );

            CREATE TABLE IF NOT EXISTS dataset_profiles (
                dataset_id VARCHAR PRIMARY KEY,
                report_json VARCHAR NOT NULL,
                profiled_at TIMESTAMP NOT NULL
            );

            CREATE TABLE IF NOT EXISTS generation_jobs (
                job_id VARCHAR PRIMARY KEY,
                dataset_id VARCHAR NOT NULL,
                dataset_name VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                config_json VARCHAR NOT NULL,
                compute_tier VARCHAR NOT NULL,
                rows_generated INTEGER NOT NULL,
                throughput_rows_per_sec DOUBLE NOT NULL,
                privacy_ledger_json VARCHAR,
                overall_quality_score DOUBLE,
                error_message VARCHAR,
                created_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS quality_reports (
                job_id VARCHAR PRIMARY KEY,
                dataset_id VARCHAR NOT NULL,
                report_json VARCHAR NOT NULL,
                evaluated_at TIMESTAMP NOT NULL
            );

            CREATE TABLE IF NOT EXISTS upload_tickets (
                upload_token VARCHAR PRIMARY KEY,
                dataset_name VARCHAR NOT NULL,
                upload_url VARCHAR NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                max_bytes BIGINT NOT NULL,
                consumed BOOLEAN NOT NULL
            );
            """
        )

    def save_dataset(
        self,
        name: str,
        rows: list[dict[str, Any]],
        description: str = "",
        source_type: str = "upload",
        benchmark_id: str | None = None,
        is_cleansed: bool = False,
        dataset_id: str | None = None,
    ) -> DatasetMetadata:
        """Persist a dataset record and its row contents.

        Pre-conditions:
            - ``name`` is a non-empty string.
            - ``rows`` is a list of dictionary records.
        Post-conditions:
            - Inserts catalog record and persists row payload.
        """
        ds_id = dataset_id or f"ds-{uuid.uuid4().hex[:8]}"
        row_count = len(rows)
        columns = list(rows[0].keys()) if rows else []
        column_count = len(columns)
        columns_json = json.dumps(columns)
        now = datetime.now()

        # DuckDB UPSERT
        self.conn.execute("DELETE FROM datasets WHERE dataset_id = ?", [ds_id])
        self.conn.execute(
            """
            INSERT INTO datasets (
                dataset_id, name, description, source_type, benchmark_id,
                row_count, column_count, columns, is_cleansed, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ds_id,
                name,
                description,
                source_type,
                benchmark_id,
                row_count,
                column_count,
                columns_json,
                is_cleansed,
                now,
            ],
        )

        self._dataset_rows[ds_id] = [dict(r) for r in rows]

        if self.storage_dir and rows:
            pq_path = self.storage_dir / f"{ds_id}.parquet"
            try:
                table = pa.Table.from_pylist(rows)
                pq.write_table(table, str(pq_path))
            except Exception:
                pass

        return DatasetMetadata(
            dataset_id=ds_id,
            name=name,
            description=description,
            source_type=source_type,
            benchmark_id=benchmark_id,
            row_count=row_count,
            column_count=column_count,
            columns=columns,
            is_cleansed=is_cleansed,
            created_at=now,
        )

    def get_dataset_metadata(self, dataset_id: str) -> DatasetMetadata:
        """Retrieve dataset catalog metadata by ID.

        Pre-conditions:
            - ``dataset_id`` is a non-empty string.
        Post-conditions:
            - Returns DatasetMetadata; raises KeyError if not found.
        """
        row = self.conn.execute(
            """
            SELECT dataset_id, name, description, source_type, benchmark_id,
                   row_count, column_count, columns, is_cleansed, created_at
            FROM datasets WHERE dataset_id = ?
            """,
            [dataset_id],
        ).fetchone()

        if not row:
            raise KeyError(f"Dataset '{dataset_id}' not found in catalog")

        return DatasetMetadata(
            dataset_id=row[0],
            name=row[1],
            description=row[2] or "",
            source_type=row[3],
            benchmark_id=row[4],
            row_count=row[5],
            column_count=row[6],
            columns=json.loads(row[7]),
            is_cleansed=row[8],
            created_at=row[9],
        )

    def get_dataset_rows(self, dataset_id: str) -> list[dict[str, Any]]:
        """Retrieve full row collection for a dataset.

        Pre-conditions:
            - ``dataset_id`` exists in catalog.
        Post-conditions:
            - Returns list of dictionary records.
        """
        if dataset_id in self._dataset_rows:
            return [dict(r) for r in self._dataset_rows[dataset_id]]

        if self.storage_dir:
            pq_path = self.storage_dir / f"{dataset_id}.parquet"
            if pq_path.exists():
                table = pq.read_table(str(pq_path))
                raw_list = table.to_pylist()
                rows: list[dict[str, Any]] = [dict(r) for r in raw_list]
                self._dataset_rows[dataset_id] = rows
                return [dict(r) for r in rows]

        # Verify dataset exists in DuckDB
        self.get_dataset_metadata(dataset_id)
        return []

    def list_datasets(self) -> list[DatasetMetadata]:
        """Enumerate all datasets in catalog ordered by creation timestamp.

        Pre-conditions:
            - None.
        Post-conditions:
            - Returns list of DatasetMetadata.
        """
        rows = self.conn.execute(
            """
            SELECT dataset_id, name, description, source_type, benchmark_id,
                   row_count, column_count, columns, is_cleansed, created_at
            FROM datasets ORDER BY created_at DESC
            """
        ).fetchall()

        return [
            DatasetMetadata(
                dataset_id=r[0],
                name=r[1],
                description=r[2] or "",
                source_type=r[3],
                benchmark_id=r[4],
                row_count=r[5],
                column_count=r[6],
                columns=json.loads(r[7]),
                is_cleansed=r[8],
                created_at=r[9],
            )
            for r in rows
        ]

    def save_profile(self, profile: DatasetProfileReport) -> None:
        """Store or update a dataset profile report.

        Pre-conditions:
            - ``profile`` is a validated DatasetProfileReport.
        Post-conditions:
            - Upserts profile report into DuckDB.
        """
        profile_json = profile.model_dump_json()
        self.conn.execute("DELETE FROM dataset_profiles WHERE dataset_id = ?", [profile.dataset_id])
        self.conn.execute(
            """
            INSERT INTO dataset_profiles (dataset_id, report_json, profiled_at)
            VALUES (?, ?, ?)
            """,
            [profile.dataset_id, profile_json, profile.profiled_at],
        )

    def get_profile(self, dataset_id: str) -> DatasetProfileReport | None:
        """Retrieve stored dataset profile report if present.

        Pre-conditions:
            - ``dataset_id`` is a non-empty string.
        Post-conditions:
            - Returns DatasetProfileReport or None.
        """
        row = self.conn.execute(
            "SELECT report_json FROM dataset_profiles WHERE dataset_id = ?",
            [dataset_id],
        ).fetchone()

        if not row:
            return None

        parsed = json.loads(row[0])
        return DatasetProfileReport.model_validate(parsed)

    def save_job(
        self,
        job: GenerationJob,
        synthetic_rows: list[dict[str, Any]] | None = None,
    ) -> None:
        """Persist a generation job lifecycle state and its synthetic output.

        Pre-conditions:
            - ``job`` is a validated GenerationJob.
        Post-conditions:
            - Upserts job record and stores output rows.
        """
        config_json = job.config.model_dump_json()
        ledger_json = job.privacy_ledger.model_dump_json() if job.privacy_ledger else None

        self.conn.execute("DELETE FROM generation_jobs WHERE job_id = ?", [job.job_id])
        self.conn.execute(
            """
            INSERT INTO generation_jobs (
                job_id, dataset_id, dataset_name, status, config_json, compute_tier,
                rows_generated, throughput_rows_per_sec, privacy_ledger_json,
                overall_quality_score, error_message, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                job.job_id,
                job.dataset_id,
                job.dataset_name,
                job.status.value,
                config_json,
                job.compute_tier.value,
                job.rows_generated,
                job.throughput_rows_per_sec,
                ledger_json,
                job.overall_quality_score,
                job.error_message,
                job.created_at,
                job.completed_at,
            ],
        )

        if synthetic_rows is not None:
            self._job_rows[job.job_id] = [dict(r) for r in synthetic_rows]
            if self.storage_dir and synthetic_rows:
                pq_path = self.storage_dir / f"job-{job.job_id}.parquet"
                try:
                    table = pa.Table.from_pylist(synthetic_rows)
                    pq.write_table(table, str(pq_path))
                except Exception:
                    pass

    def get_job(self, job_id: str) -> GenerationJob:
        """Retrieve a generation job by ID.

        Pre-conditions:
            - ``job_id`` exists.
        Post-conditions:
            - Returns GenerationJob; raises KeyError if not found.
        """
        row = self.conn.execute(
            """
            SELECT job_id, dataset_id, dataset_name, status, config_json, compute_tier,
                   rows_generated, throughput_rows_per_sec, privacy_ledger_json,
                   overall_quality_score, error_message, created_at, completed_at
            FROM generation_jobs WHERE job_id = ?
            """,
            [job_id],
        ).fetchone()

        if not row:
            raise KeyError(f"Job '{job_id}' not found")

        config_data = json.loads(row[4])
        ledger_data = json.loads(row[8]) if row[8] else None

        return GenerationJob(
            job_id=row[0],
            dataset_id=row[1],
            dataset_name=row[2],
            status=row[3],
            config=config_data,
            compute_tier=row[5],
            rows_generated=row[6],
            throughput_rows_per_sec=row[7],
            privacy_ledger=ledger_data,
            overall_quality_score=row[9],
            error_message=row[10],
            created_at=row[11],
            completed_at=row[12],
        )

    def get_job_rows(self, job_id: str) -> list[dict[str, Any]]:
        """Retrieve synthetic dataset rows produced by a generation job.

        Pre-conditions:
            - ``job_id`` exists.
        Post-conditions:
            - Returns list of dictionary records.
        """
        if job_id in self._job_rows:
            return [dict(r) for r in self._job_rows[job_id]]

        if self.storage_dir:
            pq_path = self.storage_dir / f"job-{job_id}.parquet"
            if pq_path.exists():
                table = pq.read_table(str(pq_path))
                raw_list = table.to_pylist()
                rows: list[dict[str, Any]] = [dict(r) for r in raw_list]
                self._job_rows[job_id] = rows
                return [dict(r) for r in rows]

        # Verify job exists
        self.get_job(job_id)
        return []

    def list_jobs(self) -> list[GenerationJob]:
        """Enumerate all generation jobs ordered by creation timestamp.

        Pre-conditions:
            - None.
        Post-conditions:
            - Returns list of GenerationJob records.
        """
        rows = self.conn.execute(
            """
            SELECT job_id, dataset_id, dataset_name, status, config_json, compute_tier,
                   rows_generated, throughput_rows_per_sec, privacy_ledger_json,
                   overall_quality_score, error_message, created_at, completed_at
            FROM generation_jobs ORDER BY created_at DESC
            """
        ).fetchall()

        jobs: list[GenerationJob] = []
        for r in rows:
            cfg = json.loads(r[4])
            ledger = json.loads(r[8]) if r[8] else None
            jobs.append(
                GenerationJob(
                    job_id=r[0],
                    dataset_id=r[1],
                    dataset_name=r[2],
                    status=r[3],
                    config=cfg,
                    compute_tier=r[5],
                    rows_generated=r[6],
                    throughput_rows_per_sec=r[7],
                    privacy_ledger=ledger,
                    overall_quality_score=r[9],
                    error_message=r[10],
                    created_at=r[11],
                    completed_at=r[12],
                )
            )
        return jobs

    def save_quality_report(self, report: QualityValidationReport) -> None:
        """Store or update a quality validation report.

        Pre-conditions:
            - ``report`` is a validated QualityValidationReport.
        Post-conditions:
            - Upserts report into DuckDB.
        """
        report_json = report.model_dump_json()
        self.conn.execute("DELETE FROM quality_reports WHERE job_id = ?", [report.job_id])
        self.conn.execute(
            """
            INSERT INTO quality_reports (job_id, dataset_id, report_json, evaluated_at)
            VALUES (?, ?, ?, ?)
            """,
            [report.job_id, report.dataset_id, report_json, report.evaluated_at],
        )

    def get_quality_report(self, job_id: str) -> QualityValidationReport:
        """Retrieve quality validation report by job ID.

        Pre-conditions:
            - ``job_id`` exists.
        Post-conditions:
            - Returns QualityValidationReport; raises KeyError if not found.
        """
        row = self.conn.execute(
            "SELECT report_json FROM quality_reports WHERE job_id = ?",
            [job_id],
        ).fetchone()

        if not row:
            raise KeyError(f"Quality report for job '{job_id}' not found")

        parsed = json.loads(row[0])
        return QualityValidationReport.model_validate(parsed)

    def export_rows(
        self,
        rows: list[dict[str, Any]],
        fmt: ExportFormat,
    ) -> tuple[bytes, str, str]:
        """Serialize tabular rows into target export format.

        Pre-conditions:
            - ``rows`` is a list of dictionary records.
            - ``fmt`` is one of ExportFormat enum values (CSV, JSON, PARQUET).
        Post-conditions:
            - Returns (payload_bytes, media_type, file_extension).
        """
        if fmt == ExportFormat.CSV:
            if not rows:
                return b"", "text/csv", "csv"
            out = io.StringIO()
            writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
            return out.getvalue().encode("utf-8"), "text/csv", "csv"

        if fmt == ExportFormat.JSON:
            payload = json.dumps(rows, default=str, indent=2).encode("utf-8")
            return payload, "application/json", "json"

        if fmt == ExportFormat.PARQUET:
            table = pa.Table.from_pylist(rows)
            sink = pa.BufferOutputStream()
            pq.write_table(table, sink)
            return sink.getvalue().to_pybytes(), "application/vnd.apache.parquet", "parquet"

        raise ValueError(f"Unsupported export format: {fmt}")

    def create_presigned_upload_ticket(
        self,
        dataset_name: str,
        base_url: str = "http://localhost:8000",
        expiry_seconds: int = 3600,
    ) -> PresignedUploadTicket:
        """Generate a short-lived capability for single-use dataset upload.

        Pre-conditions:
            - ``dataset_name`` is a non-empty string.
            - ``expiry_seconds`` > 0.
        Post-conditions:
            - Persists ticket in DuckDB with expiry_seconds expiration window.
        """
        token = uuid.uuid4().hex
        expires_at = datetime.now() + timedelta(seconds=expiry_seconds)
        upload_url = f"{base_url.rstrip('/')}/api/v1/datasets/upload?token={token}"
        ticket = PresignedUploadTicket(
            upload_token=token,
            dataset_name=dataset_name,
            upload_url=upload_url,
            expires_at=expires_at,
            max_bytes=104857600,
        )

        self.conn.execute(
            """
            INSERT INTO upload_tickets (
                upload_token, dataset_name, upload_url, expires_at, max_bytes, consumed
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ticket.upload_token,
                ticket.dataset_name,
                ticket.upload_url,
                ticket.expires_at,
                ticket.max_bytes,
                False,
            ],
        )
        return ticket

    def consume_presigned_upload_ticket(self, upload_token: str) -> PresignedUploadTicket:
        """Verify, consume, and invalidate a presigned upload ticket.

        Pre-conditions:
            - ``upload_token`` exists, is unconsumed, and has not expired.
        Post-conditions:
            - Marks ticket as consumed and returns valid ticket capability.
        """
        row = self.conn.execute(
            """
            SELECT upload_token, dataset_name, upload_url, expires_at, max_bytes, consumed
            FROM upload_tickets WHERE upload_token = ?
            """,
            [upload_token],
        ).fetchone()

        if not row:
            raise KeyError(f"Presigned ticket '{upload_token}' not found")

        if row[5]:
            raise KeyError(f"Presigned ticket '{upload_token}' has already been consumed")

        expires_at = row[3]
        if datetime.now() > expires_at:
            raise KeyError(f"Presigned ticket '{upload_token}' has expired")

        self.conn.execute(
            "UPDATE upload_tickets SET consumed = TRUE WHERE upload_token = ?",
            [upload_token],
        )

        return PresignedUploadTicket(
            upload_token=row[0],
            dataset_name=row[1],
            upload_url=row[2],
            expires_at=row[3],
            max_bytes=row[4],
        )
