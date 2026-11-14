"""Deterministic verification test suite for UI serving, static assets, and route aliases.

Pre-conditions:
    - synthai_studio.api.ui and synthai_studio.api.main are implemented.
    - FastAPI TestClient, pytest, and DuckDB are available.
Post-conditions:
    - Validates static directory resolution, /static mount, GET / HTML serving,
      fast /ready latency (< 50ms), route aliases, and main.py file compactness.
"""

import time
from pathlib import Path
from typing import Final

import pytest
from fastapi.testclient import TestClient

from synthai_studio.api.main import create_app
from synthai_studio.api.ui import (
    API_PACKAGE_DIR,
    STATIC_DIR,
    TEMPLATES_DIR,
    get_static_dir,
    get_templates_dir,
    load_studio_index_html,
)
from synthai_studio.repository import StudioRepository

MAIN_PY_PATH: Final[Path] = (
    Path(__file__).resolve().parent.parent / "src" / "synthai_studio" / "api" / "main.py"
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Provide an isolated FastAPI TestClient instance with pre-seeded benchmark data.

    Pre-conditions:
        - None.
    Post-conditions:
        - Returns active TestClient against an in-memory StudioRepository.
    """
    repo = StudioRepository()
    test_app = create_app(repository=repo, bootstrap=True)
    return TestClient(test_app)


def test_directory_resolvers_and_index_loader() -> None:
    """Verify get_templates_dir, get_static_dir, and load_studio_index_html resolve properly.

    Pre-conditions:
        - ui.py constants and functions are accessible.
    Post-conditions:
        - Asserts paths exist, are directories/files, and load non-empty HTML text.
    """
    assert API_PACKAGE_DIR.is_dir()
    assert get_templates_dir() == TEMPLATES_DIR
    assert get_static_dir() == STATIC_DIR
    assert TEMPLATES_DIR.is_dir()
    assert STATIC_DIR.is_dir()

    index_html = load_studio_index_html()
    assert len(index_html.strip()) > 0
    assert "<!DOCTYPE html>" in index_html
    assert "SYNTHAI STUDIO" in index_html


def test_ui_root_endpoint_serves_modular_html(client: TestClient) -> None:
    """Verify GET / returns 200 OK with text/html matching load_studio_index_html content.

    Pre-conditions:
        - client fixture is active.
    Post-conditions:
        - Asserts HTTP 200, Content-Type text/html, and exact match with template text.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert response.text == load_studio_index_html()


def test_static_assets_serving(client: TestClient) -> None:
    """Verify GET /static/tokens.css and /static/components.css return 200 OK with text/css.

    Pre-conditions:
        - client fixture is active.
    Post-conditions:
        - Asserts HTTP 200 and text/css Content-Type for core design system stylesheets.
    """
    resp_tokens = client.get("/static/tokens.css")
    assert resp_tokens.status_code == 200
    assert "text/css" in resp_tokens.headers["content-type"]
    assert "--bg-canvas:" in resp_tokens.text

    resp_components = client.get("/static/components.css")
    assert resp_components.status_code == 200
    assert "text/css" in resp_components.headers["content-type"]
    assert ".tabular-nums" in resp_components.text


def test_ready_endpoint_latency_under_50ms(client: TestClient) -> None:
    """Verify GET /ready responds in under 50ms and returns status ready without blocking.

    Pre-conditions:
        - client fixture is active.
    Post-conditions:
        - Asserts HTTP 200, status == 'ready', and latency < 0.050 seconds.
    """
    start = time.perf_counter()
    response = client.get("/ready")
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["datasets_count"] >= 3
    assert elapsed < 0.050, f"Readiness probe exceeded 50ms: {elapsed * 1000:.2f}ms"


def test_benchmark_seed_route_alias(client: TestClient) -> None:
    """Verify POST /api/v1/benchmarks/{benchmark_id}/seed alias delegates identically.

    Pre-conditions:
        - client fixture is active.
    Post-conditions:
        - Asserts HTTP 200 and structured dataset and profile payload.
    """
    alias_url = "/api/v1/benchmarks/healthcare_hipaa_readmissions/seed"
    response = client.post(alias_url, json={"row_count": 50})
    assert response.status_code == 200
    data = response.json()
    assert "dataset" in data
    assert "profile" in data
    assert data["dataset"]["benchmark_id"] == "healthcare_hipaa_readmissions"


def test_presign_route_alias(client: TestClient) -> None:
    """Verify POST /api/v1/presign alias delegates identically to canonical route.

    Pre-conditions:
        - client fixture is active.
    Post-conditions:
        - Asserts HTTP 200 and valid PresignedUploadTicket response structure.
    """
    alias_url = "/api/v1/presign"
    payload = {"dataset_name": "alias_presign_test", "expiry_seconds": 1800}
    response = client.post(alias_url, json=payload)
    assert response.status_code == 200
    ticket = response.json()
    assert ticket["dataset_name"] == "alias_presign_test"
    assert "upload_token" in ticket
    assert "upload_url" in ticket


def test_generate_jobs_route_alias(client: TestClient) -> None:
    """Verify POST /api/v1/jobs alias delegates identically to /api/v1/jobs/generate.

    Pre-conditions:
        - client fixture is active.
    Post-conditions:
        - Asserts HTTP 200 and returns dictionary containing job and report objects.
    """
    datasets = client.get("/api/v1/datasets").json()
    assert len(datasets) > 0
    target_dataset_id = datasets[0]["dataset_id"]

    alias_url = "/api/v1/jobs"
    payload = {
        "dataset_id": target_dataset_id,
        "target_rows": 30,
        "engine": "GAUSSIAN_COPULA",
        "privacy_level": "MEDIUM",
        "random_seed": 101,
    }
    response = client.post(alias_url, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "job" in data
    assert "report" in data
    assert data["job"]["dataset_id"] == target_dataset_id
    assert data["job"]["status"] == "COMPLETED"


def test_main_py_compactness_under_550_lines() -> None:
    """Verify main.py line count is under 550 lines following UI extraction to ui.py.

    Pre-conditions:
        - main.py exists at MAIN_PY_PATH.
    Post-conditions:
        - Asserts line count is strictly less than 550.
    """
    assert MAIN_PY_PATH.is_file(), f"main.py not found at {MAIN_PY_PATH}"
    line_count = len(MAIN_PY_PATH.read_text(encoding="utf-8").splitlines())
    assert line_count < 550, f"main.py line count ({line_count}) exceeds threshold of 550"
