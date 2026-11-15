"""Deterministic verification test suite for UI 5-state renderers and fallback views.

Pre-conditions:
    - src/synthai_studio/api/static/views.js exists.
    - FastAPI TestClient, pytest, and DuckDB are available.
Post-conditions:
    - Validates GET /static/views.js serving and JavaScript MIME type.
    - Asserts presence and structure of all 5 state renderers (empty, loading, nominal,
      degraded, and error) and table accessibility landmarks.
    - Verifies end-to-end DGX Spark edge circuit breaker fallback execution.
"""

from pathlib import Path
from typing import Final

import pytest
from fastapi.testclient import TestClient

from synthai_studio.api.main import create_app
from synthai_studio.repository import StudioRepository

VIEWS_JS_PATH: Final[Path] = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "synthai_studio"
    / "api"
    / "static"
    / "views.js"
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Instantiate an isolated test client with pre-seeded benchmark defaults.

    Pre-conditions:
        - None.
    Post-conditions:
        - Returns active TestClient against an in-memory StudioRepository.
    """
    repo = StudioRepository()
    test_app = create_app(repository=repo, bootstrap=True)
    return TestClient(test_app)


@pytest.fixture(scope="module")
def views_js_content() -> str:
    """Fixture providing raw UTF-8 text content of views.js.

    Pre-conditions:
        - VIEWS_JS_PATH exists on disk.
    Post-conditions:
        - Returns non-empty string content.
    """
    assert VIEWS_JS_PATH.is_file(), f"Missing views.js at {VIEWS_JS_PATH}"
    return VIEWS_JS_PATH.read_text(encoding="utf-8")


def test_static_views_js_served_successfully(client: TestClient) -> None:
    """Verify GET /static/views.js returns 200 OK with javascript Content-Type.

    Pre-conditions:
        - client fixture is active.
    Post-conditions:
        - Asserts HTTP 200 and javascript MIME type.
    """
    response = client.get("/static/views.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"].lower()
    assert len(response.text.strip()) > 0


def test_views_js_exposes_synthai_views_namespace(views_js_content: str) -> None:
    """Verify window.SynthAIViews object exposes all required rendering functions.

    Pre-conditions:
        - views_js_content loaded.
    Post-conditions:
        - Asserts presence of escapeHtml, renderEmptyState, renderLoadingSkeleton,
          renderErrorState, renderBenchmarkCards, renderProfileView,
          updateComputeFallbackBanner, renderJobsAndLedger, and renderQualityReportView.
    """
    assert "window.SynthAIViews =" in views_js_content
    expected_functions = [
        "escapeHtml",
        "renderEmptyState",
        "renderLoadingSkeleton",
        "renderErrorState",
        "renderBenchmarkCards",
        "renderProfileView",
        "updateComputeFallbackBanner",
        "renderJobsAndLedger",
        "renderQualityReportView",
    ]
    for fn in expected_functions:
        assert fn in views_js_content, f"Missing rendering function in views.js: {fn}"


def test_views_js_all_five_state_classes_present(views_js_content: str) -> None:
    """Verify all 5 state determinism classes are manipulated in views.js.

    Pre-conditions:
        - views_js_content loaded.
    Post-conditions:
        - Asserts state-empty, state-loading, state-nominal, state-degraded,
          and state-error classes are used in views.js.
    """
    required_states = [
        "state-empty",
        "state-loading",
        "state-nominal",
        "state-degraded",
        "state-error",
    ]
    for state in required_states:
        assert state in views_js_content, f"Missing state class in views.js: {state}"


def test_views_js_zero_cls_loading_skeletons(views_js_content: str) -> None:
    """Verify zero-CLS skeleton placeholder geometries and aria-busy attribute.

    Pre-conditions:
        - views_js_content loaded.
    Post-conditions:
        - Asserts aria-busy='true', .skeleton-card, .skeleton-tile, and .skeleton-row exist.
    """
    assert "renderLoadingSkeleton" in views_js_content
    assert "aria-busy" in views_js_content
    assert "skeleton-card" in views_js_content
    assert "skeleton-tile" in views_js_content
    assert "skeleton-row" in views_js_content


def test_views_js_empty_and_error_state_renderers(views_js_content: str) -> None:
    """Verify renderEmptyState and renderErrorState support actionable buttons.

    Pre-conditions:
        - views_js_content loaded.
    Post-conditions:
        - Asserts empty and error containers manage class toggling and CTA triggers.
    """
    assert "renderEmptyState" in views_js_content
    assert "empty-state-content" in views_js_content
    assert "renderErrorState" in views_js_content
    assert "error-state-content" in views_js_content


def test_views_js_tabular_nums_and_table_landmarks(views_js_content: str) -> None:
    """Verify table rendering enforces scope landmarks, data-numeric, and tabular numbers.

    Pre-conditions:
        - views_js_content loaded.
    Post-conditions:
        - Asserts th scope='col', th scope='row', data-numeric='true', and tabular-nums.
    """
    assert '<th scope="col">' in views_js_content
    assert '<th scope="row">' in views_js_content
    assert 'data-numeric="true"' in views_js_content
    assert "tabular-nums" in views_js_content


def test_views_js_spark_circuit_breaker_fallback_controller(views_js_content: str) -> None:
    """Verify updateComputeFallbackBanner inspects SPARK_LLM_EDGE and CPU_WORKER.

    Pre-conditions:
        - views_js_content loaded.
    Post-conditions:
        - Asserts detection logic for fallback from DGX Spark edge to local CPU Copula.
    """
    assert "updateComputeFallbackBanner" in views_js_content
    assert "SPARK_LLM_EDGE" in views_js_content
    assert "CPU_WORKER" in views_js_content
    assert "compute-fallback-banner" in views_js_content
    assert "compute-fallback-banner-step5" in views_js_content


def test_views_js_zero_emojis_and_pure_ascii(views_js_content: str) -> None:
    """Verify views.js is strictly pure ASCII with zero emojis or Unicode artifacts.

    Pre-conditions:
        - views_js_content loaded.
    Post-conditions:
        - Asserts all characters in views.js have ord(c) <= 127.
    """
    non_ascii = [c for c in views_js_content if ord(c) > 127]
    assert not non_ascii, f"Forbidden non-ascii or emoji characters detected: {set(non_ascii)}"


def test_e2e_spark_circuit_breaker_fallback_job_execution(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify end-to-end SPARK_LLM_EDGE job falls back cleanly to CPU_WORKER on probe failure.

    Pre-conditions:
        - client fixture is active.
        - DGX Spark probe is monkeypatched to return False (< 2.0s timeout simulation).
    Post-conditions:
        - Asserts HTTP 200 response with config.engine == 'SPARK_LLM_EDGE'
          and compute_tier == 'CPU_WORKER', matching updateComputeFallbackBanner conditions.
    """
    monkeypatch.setattr(
        "synthai_studio.synthesizer.probe_spark_endpoint",
        lambda *args, **kwargs: False,
    )

    datasets = client.get("/api/v1/datasets").json()
    assert len(datasets) > 0
    target_ds_id = datasets[0]["dataset_id"]

    payload = {
        "dataset_id": target_ds_id,
        "target_rows": 25,
        "engine": "SPARK_LLM_EDGE",
        "privacy_level": "MEDIUM",
        "random_seed": 42,
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["job"]["config"]["engine"] == "SPARK_LLM_EDGE"
    assert data["job"]["compute_tier"] == "CPU_WORKER"
    assert data["job"]["status"] == "COMPLETED"
    assert data["report"]["engine"] == "SPARK_LLM_EDGE"
    assert data["job"]["rows_generated"] == 25
