"""Comprehensive end-to-end unit and integration tests for SynthAI Studio REST API.

Pre-conditions:
    - FastAPI TestClient, pytest, and DuckDB installed.
Post-conditions:
    - Verifies health probes, benchmark catalog, dataset uploads, presigned tickets,
      cleansing, multi-engine synthetic generation, reports, and downloads.
"""

import io
from typing import Any

import pytest
from fastapi.testclient import TestClient

from synthai_studio.api.main import create_app
from synthai_studio.models import PrivacyLevel, SynthesizerEngine
from synthai_studio.repository import StudioRepository


@pytest.fixture
def client() -> TestClient:
    """Instantiate an isolated test client with pre-seeded benchmark defaults.

    Pre-conditions:
        - None.
    Post-conditions:
        - Returns active TestClient against an in-memory repository.
    """
    repo = StudioRepository()
    test_app = create_app(repository=repo, bootstrap=True)
    return TestClient(test_app)


def test_healthz_endpoint(client: TestClient) -> None:
    """Verify health liveness probe returns healthy status.

    Pre-conditions:
        - Active TestClient.
    Post-conditions:
        - Validates HTTP 200 and expected payload structure.
    """
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "synthai-studio"
    assert data["version"] == "0.1.0"


def test_ready_endpoint(client: TestClient) -> None:
    """Verify readiness check inspects DuckDB catalog state.

    Pre-conditions:
        - Active TestClient with bootstrapped benchmarks.
    Post-conditions:
        - Validates HTTP 200 and non-empty dataset/job metrics.
    """
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["datasets_count"] >= 3
    assert data["jobs_count"] >= 1
    assert "temporal_host" in data


def test_list_benchmarks(client: TestClient) -> None:
    """Verify enumeration of built-in domain reference benchmarks.

    Pre-conditions:
        - Active TestClient.
    Post-conditions:
        - Returns 3 benchmark metadata descriptors.
    """
    response = client.get("/api/v1/benchmarks")
    assert response.status_code == 200
    benchmarks = response.json()
    assert len(benchmarks) == 3
    ids = [b["benchmark_id"] for b in benchmarks]
    assert "healthcare_hipaa_readmissions" in ids
    assert "fintech_fraud_transactions" in ids
    assert "saas_customer_churn" in ids


def test_seed_benchmark_success_and_not_found(client: TestClient) -> None:
    """Verify benchmark dataset seeding endpoint.

    Pre-conditions:
        - Active TestClient.
    Post-conditions:
        - HTTP 200 on valid benchmark ID; HTTP 404 on invalid benchmark ID.
    """
    resp_valid = client.post(
        "/api/v1/datasets/seed/healthcare_hipaa_readmissions",
        json={"row_count": 25},
    )
    assert resp_valid.status_code == 200
    data = resp_valid.json()
    assert data["dataset"]["dataset_id"] == "ds-healthcare_hipaa_readmissions"
    assert data["dataset"]["row_count"] == 25
    assert data["profile"]["row_count"] == 25

    resp_invalid = client.post("/api/v1/datasets/seed/unknown_benchmark_id")
    assert resp_invalid.status_code == 404


def test_upload_dataset_json_rows(client: TestClient) -> None:
    """Verify dataset ingestion via JSON rows payload.

    Pre-conditions:
        - Active TestClient.
    Post-conditions:
        - Dataset is parsed, saved, and profiled into catalog.
    """
    sample_rows: list[dict[str, Any]] = [
        {"id": 1, "feature": 10.5, "flag": 1},
        {"id": 2, "feature": 20.1, "flag": 0},
        {"id": 3, "feature": 15.3, "flag": 1},
        {"id": 4, "feature": 18.0, "flag": 0},
    ]
    resp = client.post(
        "/api/v1/datasets/upload",
        json={"name": "custom_json_rows", "rows": sample_rows},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["dataset"]["name"] == "custom_json_rows"
    assert payload["dataset"]["row_count"] == 4
    assert payload["profile"]["column_count"] == 3


def test_upload_dataset_json_raw_csv_content(client: TestClient) -> None:
    """Verify dataset ingestion via JSON raw CSV string content.

    Pre-conditions:
        - Active TestClient.
    Post-conditions:
        - Parses raw CSV string and returns dataset metadata and profile.
    """
    csv_str = "user_id,amount,label\nu101,45.5,0\nu102,120.0,1\nu103,88.2,0\n"
    resp = client.post(
        "/api/v1/datasets/upload",
        json={"name": "custom_csv_str", "content": csv_str, "filename": "data.csv"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["dataset"]["name"] == "custom_csv_str"
    assert payload["dataset"]["row_count"] == 3


def test_upload_dataset_multipart_form(client: TestClient) -> None:
    """Verify dataset ingestion via standard multipart/form-data file upload.

    Pre-conditions:
        - Active TestClient.
    Post-conditions:
        - Handles uploaded binary CSV file and returns profile.
    """
    file_content = b"col_a,col_b,col_c\n1,10.0,alpha\n2,20.0,beta\n3,30.0,gamma\n"
    files = {"file": ("test.csv", io.BytesIO(file_content), "text/csv")}
    data = {"name": "multipart_dataset"}

    resp = client.post("/api/v1/datasets/upload", files=files, data=data)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["dataset"]["name"] == "multipart_dataset"
    assert res_data["dataset"]["row_count"] == 3


def test_presign_and_upload_ticket_workflow(client: TestClient) -> None:
    """Verify issuing and consuming presigned capability upload tickets.

    Pre-conditions:
        - Active TestClient.
    Post-conditions:
        - Validates ticket creation, single-use consumption, and double-spend rejection.
    """
    presign_resp = client.post(
        "/api/v1/datasets/presign-upload",
        json={"dataset_name": "s3_ticket_dataset", "expiry_seconds": 1800},
    )
    assert presign_resp.status_code == 200
    ticket = presign_resp.json()
    token = ticket["upload_token"]
    assert ticket["dataset_name"] == "s3_ticket_dataset"
    assert f"token={token}" in ticket["upload_url"]

    # Consume ticket with upload
    csv_bytes = b"metric_x,metric_y\n1.2,3.4\n5.6,7.8\n"
    files = {"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")}
    upload_resp = client.post(f"/api/v1/datasets/upload?token={token}", files=files)
    assert upload_resp.status_code == 200
    meta = upload_resp.json()["dataset"]
    assert meta["name"] == "s3_ticket_dataset"
    assert meta["row_count"] == 2

    # Attempt double-consumption (must be rejected with HTTP 400)
    double_spend_resp = client.post(f"/api/v1/datasets/upload?token={token}", files=files)
    assert double_spend_resp.status_code == 400


def test_dataset_listing_and_profile_endpoint(client: TestClient) -> None:
    """Verify enumeration of catalog datasets and profile inspection.

    Pre-conditions:
        - Active TestClient with bootstrapped datasets.
    Post-conditions:
        - Retrieves dataset list, dataset profile, and verifies 404 on missing dataset.
    """
    list_resp = client.get("/api/v1/datasets")
    assert list_resp.status_code == 200
    datasets = list_resp.json()
    assert len(datasets) >= 3
    target_id = datasets[0]["dataset_id"]

    prof_resp = client.get(f"/api/v1/datasets/{target_id}/profile")
    assert prof_resp.status_code == 200
    prof = prof_resp.json()
    assert prof["dataset_id"] == target_id
    assert prof["data_quality_score"] > 0.0

    missing_resp = client.get("/api/v1/datasets/non_existent_dataset/profile")
    assert missing_resp.status_code == 404


def test_cleanse_dataset_endpoint(client: TestClient) -> None:
    """Verify 1-click dataset cleansing, deduplication, and PII anonymization.

    Pre-conditions:
        - Seeded benchmark dataset with unmasked PII.
    Post-conditions:
        - Creates new cleansed dataset with anonymized tokens and zero UNMASKED_PII.
    """
    # Seed healthcare benchmark
    seed_resp = client.post("/api/v1/datasets/seed/healthcare_hipaa_readmissions")
    assert seed_resp.status_code == 200
    raw_id = seed_resp.json()["dataset"]["dataset_id"]

    cleanse_resp = client.post(
        f"/api/v1/datasets/{raw_id}/cleanse",
        json={"anonymize_pii": True},
    )
    assert cleanse_resp.status_code == 200
    payload = cleanse_resp.json()
    clean_meta = payload["dataset"]
    clean_prof = payload["profile"]

    assert clean_meta["is_cleansed"] is True
    assert clean_prof["privacy_risk_score"] == 0.0

    # 404 check
    missing_cleanse = client.post("/api/v1/datasets/non_existent_id/cleanse")
    assert missing_cleanse.status_code == 404


def test_generate_synthetic_job_and_retrieval(client: TestClient) -> None:
    """Verify synthetic data generation job execution, auditing, and queries.

    Pre-conditions:
        - Seeded dataset available.
    Post-conditions:
        - Executes synthesis job, audits statistical fidelity, and persists records.
    """
    seed_resp = client.post("/api/v1/datasets/seed/saas_customer_churn")
    ds_id = seed_resp.json()["dataset"]["dataset_id"]

    job_cfg = {
        "dataset_id": ds_id,
        "target_rows": 50,
        "engine": SynthesizerEngine.GAUSSIAN_COPULA.value,
        "privacy_level": PrivacyLevel.LOW.value,
        "epsilon": 5.0,
        "delta": 0.00001,
        "anonymize_pii": True,
        "random_seed": 42,
    }

    gen_resp = client.post("/api/v1/jobs/generate", json=job_cfg)
    assert gen_resp.status_code == 200
    data = gen_resp.json()
    job = data["job"]
    report = data["report"]

    assert job["status"] == "COMPLETED"
    assert job["rows_generated"] == 50
    assert report["overall_quality_score"] > 0.60
    assert report["executive_verdict"]

    job_id = job["job_id"]

    # Retrieve individual job
    get_job_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert get_job_resp.status_code == 200
    assert get_job_resp.json()["job_id"] == job_id

    # Retrieve job list
    list_jobs_resp = client.get("/api/v1/jobs")
    assert list_jobs_resp.status_code == 200
    assert any(j["job_id"] == job_id for j in list_jobs_resp.json())

    # Invalid job ID
    assert client.get("/api/v1/jobs/non_existent_job").status_code == 404

    # Generate with missing dataset ID -> 404
    missing_cfg = dict(job_cfg)
    missing_cfg["dataset_id"] = "unknown_dataset_id"
    assert client.post("/api/v1/jobs/generate", json=missing_cfg).status_code == 404


def test_job_quality_report_json_and_markdown(client: TestClient) -> None:
    """Verify quality report endpoint returns JSON and rendered Markdown formats.

    Pre-conditions:
        - Bootstrapped job exists.
    Post-conditions:
        - Returns QualityValidationReport JSON and PlainText Markdown content.
    """
    jobs = client.get("/api/v1/jobs").json()
    assert len(jobs) > 0
    job_id = jobs[0]["job_id"]

    # JSON report
    rep_json = client.get(f"/api/v1/jobs/{job_id}/report?format=json")
    assert rep_json.status_code == 200
    assert rep_json.headers["content-type"].startswith("application/json")
    data = rep_json.json()
    assert data["job_id"] == job_id
    assert "overall_quality_score" in data

    # Markdown report
    rep_md = client.get(f"/api/v1/jobs/{job_id}/report?format=markdown")
    assert rep_md.status_code == 200
    assert "text/markdown" in rep_md.headers["content-type"]
    assert "# SynthAI Studio Quality Validation Report" in rep_md.text

    # Missing job
    assert client.get("/api/v1/jobs/missing_job/report").status_code == 404


def test_job_download_formats(client: TestClient) -> None:
    """Verify artifact download streams CSV, JSON, and Parquet data with headers.

    Pre-conditions:
        - Bootstrapped generation job with synthetic records.
    Post-conditions:
        - Validates CSV, JSON, and Parquet exports and attachment filenames.
    """
    jobs = client.get("/api/v1/jobs").json()
    job_id = jobs[0]["job_id"]

    # CSV download
    csv_resp = client.get(f"/api/v1/jobs/{job_id}/download?format=csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    assert f'filename="synthai-{job_id}.csv"' in csv_resp.headers["content-disposition"]
    assert len(csv_resp.content) > 0

    # JSON download
    json_resp = client.get(f"/api/v1/jobs/{job_id}/download?format=json")
    assert json_resp.status_code == 200
    assert "application/json" in json_resp.headers["content-type"]
    assert f'filename="synthai-{job_id}.json"' in json_resp.headers["content-disposition"]
    assert len(json_resp.content) > 0

    # Parquet download
    pq_resp = client.get(f"/api/v1/jobs/{job_id}/download?format=parquet")
    assert pq_resp.status_code == 200
    assert "parquet" in pq_resp.headers["content-type"]
    assert f'filename="synthai-{job_id}.parquet"' in pq_resp.headers["content-disposition"]
    assert len(pq_resp.content) > 0

    # Invalid format error
    bad_fmt_resp = client.get(f"/api/v1/jobs/{job_id}/download?format=xlsx")
    assert bad_fmt_resp.status_code == 400

    # Missing job error
    missing_resp = client.get("/api/v1/jobs/missing_job_id/download?format=csv")
    assert missing_resp.status_code == 404


def test_interactive_web_ui_endpoint(client: TestClient) -> None:
    """Verify GET / returns complete 5-step interactive single-page studio application.

    Pre-conditions:
        - Active TestClient.
    Post-conditions:
        - Returns 200 OK HTML document containing all five workflow tabs and sections.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text

    # Verify brand and step titles
    assert "SYNTHAI STUDIO" in html
    assert "step-1" in html
    assert "step-2" in html
    assert "step-3" in html
    assert "step-4" in html
    assert "step-5" in html
    assert "DIFFERENTIAL PRIVACY" in html
