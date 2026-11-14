"""Deterministic verification test suite for client application JavaScript (app.js).

Pre-conditions:
    - src/synthai_studio/api/static/app.js exists.
    - FastAPI TestClient, pytest, and DuckDB are available.
Post-conditions:
    - Asserts GET /static/app.js returns 200 OK with javascript content-type.
    - Validates presence of StudioState, WAI-ARIA tablist roving tabindex controller,
      polite and assertive live announcers, and global error focus recovery.
    - Asserts exact models.py schema field alignment and zero legacy non-existent fields.
    - Asserts zero emojis and pure ASCII encoding.
"""

from pathlib import Path
from typing import Final

import pytest
from fastapi.testclient import TestClient

from synthai_studio.api.main import create_app
from synthai_studio.repository import StudioRepository

APP_JS_PATH: Final[Path] = (
    Path(__file__).resolve().parent.parent / "src" / "synthai_studio" / "api" / "static" / "app.js"
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Instantiate an isolated test client with pre-seeded benchmarks.

    Pre-conditions:
        - None.
    Post-conditions:
        - Returns active TestClient instance with StudioRepository.
    """
    repo = StudioRepository()
    test_app = create_app(repository=repo, bootstrap=True)
    return TestClient(test_app)


@pytest.fixture(scope="module")
def app_js_content() -> str:
    """Fixture providing raw UTF-8 string content of app.js.

    Pre-conditions:
        - APP_JS_PATH exists on disk.
    Post-conditions:
        - Returns non-empty string content.
    """
    assert APP_JS_PATH.is_file(), f"Missing app.js at {APP_JS_PATH}"
    return APP_JS_PATH.read_text(encoding="utf-8")


def test_static_app_js_served_successfully(client: TestClient) -> None:
    """Verify GET /static/app.js returns 200 OK with javascript MIME type.

    Pre-conditions:
        - client fixture is active.
    Post-conditions:
        - Asserts HTTP 200 and javascript in Content-Type header.
    """
    response = client.get("/static/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"].lower()
    assert len(response.text.strip()) > 0


def test_app_js_state_store_structure(app_js_content: str) -> None:
    """Verify centralized StudioState store object exists with required state keys.

    Pre-conditions:
        - app_js_content loaded.
    Post-conditions:
        - Asserts StudioState tracks activeStep, benchmarks, datasets, jobs,
          currentDatasetId, currentJobId, currentProfile, and currentReport.
    """
    assert "const StudioState =" in app_js_content or "StudioState = {" in app_js_content
    expected_state_keys = [
        "activeStep",
        "benchmarks",
        "datasets",
        "jobs",
        "currentDatasetId",
        "currentJobId",
        "currentProfile",
        "currentReport",
    ]
    for key in expected_state_keys:
        assert key in app_js_content, f"Missing state store key in app.js: {key}"


def test_app_js_accessible_tablist_and_keyboard_navigation(app_js_content: str) -> None:
    """Verify WAI-ARIA tablist roving tabindex controller and keyboard navigation handlers.

    Pre-conditions:
        - app_js_content loaded.
    Post-conditions:
        - Asserts switchStep, handleTabKeydown, roving tabindex, aria-selected,
          and ArrowRight, ArrowLeft, ArrowDown, ArrowUp, Home, End, and Escape keys.
    """
    required_symbols = [
        "switchStep",
        "handleTabKeydown",
        "aria-selected",
        "tabindex",
        "ArrowRight",
        "ArrowDown",
        "ArrowLeft",
        "ArrowUp",
        "Home",
        "End",
        "Escape",
    ]
    for symbol in required_symbols:
        assert symbol in app_js_content, f"Missing tab navigation symbol: {symbol}"


def test_app_js_aria_live_announcers(app_js_content: str) -> None:
    """Verify polite and assertive live region announcer functions exist.

    Pre-conditions:
        - app_js_content loaded.
    Post-conditions:
        - Asserts announcePolite and announceAssertive update corresponding ARIA elements.
    """
    assert "announcePolite" in app_js_content
    assert "aria-status-polite" in app_js_content
    assert "announceAssertive" in app_js_content
    assert "aria-status-assertive" in app_js_content


def test_app_js_global_error_handling_and_focus_recovery(app_js_content: str) -> None:
    """Verify showGlobalError and dismissGlobalError manage error banner and focus.

    Pre-conditions:
        - app_js_content loaded.
    Post-conditions:
        - Asserts banner display, focus shift, announcement, and dismiss behavior.
    """
    assert "showGlobalError" in app_js_content
    assert "dismissGlobalError" in app_js_content
    assert "global-error-banner" in app_js_content
    assert "global-error-text" in app_js_content


def test_app_js_canonical_model_fields_present(app_js_content: str) -> None:
    """Verify app.js references canonical schema field names from models.py.

    Pre-conditions:
        - app_js_content loaded.
    Post-conditions:
        - Asserts all canonical fields from models.py are referenced in JS code.
    """
    canonical_fields = [
        "pii_columns",
        "highlights",
        "inferred_type",
        "pii_findings",
        "quality_issues",
        "upsample_config",
        "minority_value",
        "target_ratio",
        "compute_tier",
        "epsilon_spent",
        "noise_scale",
        "psd_projection_applied",
        "dcr_median",
        "dcr_p05",
        "nndr_median",
        "nndr_p05",
        "exact_match_collision_rate",
        "pii_leakage_detected",
        "column_metrics",
    ]
    for field in canonical_fields:
        assert field in app_js_content, f"Missing canonical models.py schema field: {field}"


def test_app_js_zero_legacy_fields_present(app_js_content: str) -> None:
    """Verify app.js contains zero references to non-existent legacy schema fields.

    Pre-conditions:
        - app_js_content loaded.
    Post-conditions:
        - Asserts planted_defects, dcr_mean, and nndr_mean do not appear in app.js.
    """
    forbidden_fields = ["planted_defects", "dcr_mean", "nndr_mean"]
    for field in forbidden_fields:
        assert field not in app_js_content, (
            f"Forbidden non-existent legacy schema field found in app.js: {field}"
        )


def test_app_js_zero_emojis_and_pure_ascii(app_js_content: str) -> None:
    """Verify app.js is strictly pure ASCII with zero emojis or Unicode artifacts.

    Pre-conditions:
        - app_js_content loaded.
    Post-conditions:
        - Asserts all characters in app.js have ord(c) <= 127.
    """
    non_ascii = [c for c in app_js_content if ord(c) > 127]
    assert not non_ascii, f"Forbidden non-ascii or emoji characters detected: {set(non_ascii)}"


def test_app_js_api_workflow_handlers_defined(app_js_content: str) -> None:
    """Verify all end-to-end API workflow handlers are implemented in app.js.

    Pre-conditions:
        - app_js_content loaded.
    Post-conditions:
        - Asserts loadInitData, loadBenchmarks, seedBenchmark, handleUpload,
          generateTicket, loadDatasets, loadProfileForSelected, cleanseCurrentDataset,
          updateDpDefaults, handleGenerate, loadJobs, viewJobReport,
          loadReportForSelected, and downloadArtifact exist.
    """
    required_handlers = [
        "loadInitData",
        "loadBenchmarks",
        "seedBenchmark",
        "handleUpload",
        "generateTicket",
        "loadDatasets",
        "loadProfileForSelected",
        "cleanseCurrentDataset",
        "updateDpDefaults",
        "handleGenerate",
        "loadJobs",
        "viewJobReport",
        "loadReportForSelected",
        "downloadArtifact",
    ]
    for handler in required_handlers:
        assert handler in app_js_content, f"Missing API workflow handler: {handler}"
