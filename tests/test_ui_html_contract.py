"""Deterministic HTML5 contract test suite for SynthAI Studio 5-step workbench shell.

Pre-conditions:
    - index.html exists under src/synthai_studio/api/templates/.
    - pytest, ruff, and mypy are installed in the active Python environment.
Post-conditions:
    - Asserts valid HTML5 document structure, landmarks, ARIA live regions, and tabs.
    - Verifies 100% of inputs and selects have matching explicit label bindings.
    - Validates zero emojis and zero inline style or script code blocks.
"""

from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Final

import pytest

TEMPLATES_DIR: Final[Path] = (
    Path(__file__).resolve().parent.parent / "src" / "synthai_studio" / "api" / "templates"
)
INDEX_HTML_PATH: Final[Path] = TEMPLATES_DIR / "index.html"


class DOMContractParser(HTMLParser):
    """Semantic HTML5 DOM parser verifying structural contracts, landmarks, and bindings.

    Pre-conditions:
        - Input text contains valid HTML5 syntax.
    Post-conditions:
        - Populates indexed registries of tags, IDs, form controls, labels, and scripts.
    """

    def __init__(self) -> None:
        """Initialize parser state collections.

        Pre-conditions:
            - None.
        Post-conditions:
            - Initializes empty collections for DOM elements and attributes.
        """
        super().__init__()
        self.tags: list[dict[str, Any]] = []
        self.elements_by_id: dict[str, dict[str, Any]] = {}
        self.inputs: list[dict[str, str | None]] = []
        self.selects: list[dict[str, str | None]] = []
        self.labels: list[dict[str, str | None]] = []
        self.links: list[dict[str, str | None]] = []
        self.scripts: list[dict[str, str | None]] = []
        self.style_tags: list[dict[str, str | None]] = []
        self.buttons: list[dict[str, str | None]] = []
        self.sections: list[dict[str, str | None]] = []
        self._current_tag: str | None = None
        self.inline_script_data: list[str] = []
        self.inline_style_data: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record element opening tag, registering ID and role attributes.

        Pre-conditions:
            - tag is a valid HTML tag name string.
            - attrs contains list of (name, value) attribute pairs.
        Post-conditions:
            - Appends element to appropriate registry.
        """
        self._current_tag = tag
        attr_dict = dict(attrs)
        tag_info = {"tag": tag, "attrs": attr_dict}
        self.tags.append(tag_info)

        elem_id = attr_dict.get("id")
        if elem_id:
            self.elements_by_id[elem_id] = tag_info

        if tag == "input":
            self.inputs.append(attr_dict)
        elif tag == "select":
            self.selects.append(attr_dict)
        elif tag == "label":
            self.labels.append(attr_dict)
        elif tag == "link":
            self.links.append(attr_dict)
        elif tag == "script":
            self.scripts.append(attr_dict)
        elif tag == "style":
            self.style_tags.append(attr_dict)
        elif tag == "button":
            self.buttons.append(attr_dict)
        elif tag == "section":
            self.sections.append(attr_dict)

    def handle_endtag(self, tag: str) -> None:
        """Reset current tag context on element close.

        Pre-conditions:
            - tag is element name being closed.
        Post-conditions:
            - Clears current tag tracker.
        """
        if self._current_tag == tag:
            self._current_tag = None

    def handle_data(self, data: str) -> None:
        """Capture text content inside current tag for inline script/style detection.

        Pre-conditions:
            - data is non-empty text node.
        Post-conditions:
            - Records inline script or style content if tag context matches.
        """
        stripped = data.strip()
        if not stripped:
            return
        if self._current_tag == "script":
            self.inline_script_data.append(stripped)
        elif self._current_tag == "style":
            self.inline_style_data.append(stripped)


@pytest.fixture(scope="module")
def html_content() -> str:
    """Fixture returning raw UTF-8 string content of templates/index.html.

    Pre-conditions:
        - index.html exists at INDEX_HTML_PATH.
    Post-conditions:
        - Returns non-empty string content.
    """
    assert INDEX_HTML_PATH.is_file(), f"Missing index.html at {INDEX_HTML_PATH}"
    return INDEX_HTML_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def parsed_dom(html_content: str) -> DOMContractParser:
    """Fixture parsing index.html into a structured DOMContractParser instance.

    Pre-conditions:
        - html_content is loaded.
    Post-conditions:
        - Returns fully populated DOMContractParser instance.
    """
    parser = DOMContractParser()
    parser.feed(html_content)
    return parser


def test_html_file_exists_and_is_valid_html5(html_content: str) -> None:
    """Verify index.html exists and contains valid HTML5 doctype and root lang attribute.

    Pre-conditions:
        - html_content loaded.
    Post-conditions:
        - Asserts DOCTYPE html and <html lang="en"> are declared.
    """
    assert "<!DOCTYPE html>" in html_content
    assert '<html lang="en">' in html_content


def test_zero_emojis_in_template(html_content: str) -> None:
    """Verify zero emojis or non-standard characters exist anywhere in index.html.

    Pre-conditions:
        - html_content loaded.
    Post-conditions:
        - Asserts all characters are strictly standard ASCII.
    """
    non_ascii = [ch for ch in html_content if ord(ch) > 127]
    assert not non_ascii, f"Forbidden non-ascii or emoji characters detected: {set(non_ascii)}"


def test_external_asset_links_and_no_inline_style_or_script(
    parsed_dom: DOMContractParser,
) -> None:
    """Verify index.html references external CSS/JS assets and contains zero inline code blocks.

    Pre-conditions:
        - parsed_dom fixture loaded.
    Post-conditions:
        - Asserts /static/tokens.css and /static/components.css are linked.
        - Asserts /static/views.js and /static/app.js are deferred.
        - Asserts 0 inline <style> tags and 0 inline <script> code blocks.
    """
    link_hrefs = [link.get("href") for link in parsed_dom.links]
    assert "/static/tokens.css" in link_hrefs
    assert "/static/components.css" in link_hrefs

    script_srcs = [script.get("src") for script in parsed_dom.scripts]
    assert "/static/views.js" in script_srcs
    assert "/static/app.js" in script_srcs

    for script in parsed_dom.scripts:
        assert "defer" in script, f"Script missing defer attribute: {script}"

    assert len(parsed_dom.style_tags) == 0, "Forbidden inline <style> tags found"
    assert len(parsed_dom.inline_script_data) == 0, (
        f"Forbidden inline script blocks found: {parsed_dom.inline_script_data}"
    )


def test_backward_compatibility_invariants(html_content: str) -> None:
    """Verify backward-compatible substrings expected by API integration tests.

    Pre-conditions:
        - html_content loaded.
    Post-conditions:
        - Asserts SYNTHAI STUDIO, DIFFERENTIAL PRIVACY, and step-1 through step-5 exist.
    """
    required_invariants = [
        "SYNTHAI STUDIO",
        "DIFFERENTIAL PRIVACY",
        "step-1",
        "step-2",
        "step-3",
        "step-4",
        "step-5",
    ]
    for inv in required_invariants:
        assert inv in html_content, f"Missing backward-compatibility invariant: {inv}"


def test_skip_navigation_link(parsed_dom: DOMContractParser) -> None:
    """Verify accessibility skip link is present as the first interactive landmark.

    Pre-conditions:
        - parsed_dom fixture loaded.
    Post-conditions:
        - Asserts .skip-link points to #main-workbench.
    """
    skip_links = [
        t for t in parsed_dom.tags
        if t["tag"] == "a" and "skip-link" in str(t["attrs"].get("class", ""))
    ]
    assert len(skip_links) == 1, "Expected exactly one .skip-link element"
    assert skip_links[0]["attrs"].get("href") == "#main-workbench"


def test_aria_live_status_regions(parsed_dom: DOMContractParser) -> None:
    """Verify both polite and assertive live announcer regions exist in the DOM.

    Pre-conditions:
        - parsed_dom fixture loaded.
    Post-conditions:
        - Asserts #aria-status-polite and #aria-status-assertive exist with expected ARIA roles.
    """
    polite = parsed_dom.elements_by_id.get("aria-status-polite")
    assert polite is not None, "Missing #aria-status-polite live region"
    assert polite["attrs"].get("role") == "status"
    assert polite["attrs"].get("aria-live") == "polite"
    assert polite["attrs"].get("aria-atomic") == "true"
    assert "sr-only" in str(polite["attrs"].get("class", ""))

    assertive = parsed_dom.elements_by_id.get("aria-status-assertive")
    assert assertive is not None, "Missing #aria-status-assertive live region"
    assert assertive["attrs"].get("role") == "alert"
    assert assertive["attrs"].get("aria-live") == "assertive"
    assert assertive["attrs"].get("aria-atomic") == "true"
    assert "sr-only" in str(assertive["attrs"].get("class", ""))


def test_semantic_header_and_cluster_status(parsed_dom: DOMContractParser) -> None:
    """Verify header landmark, brand titles, and cluster status telemetry pills.

    Pre-conditions:
        - parsed_dom fixture loaded.
    Post-conditions:
        - Asserts header has role='banner' and contains #status-service, #status-catalog,
          and #status-temporal.
    """
    headers = [t for t in parsed_dom.tags if t["tag"] == "header"]
    assert len(headers) == 1, "Expected exactly one <header> landmark"
    assert headers[0]["attrs"].get("role") == "banner"

    assert "status-service" in parsed_dom.elements_by_id
    assert "status-catalog" in parsed_dom.elements_by_id
    assert "status-temporal" in parsed_dom.elements_by_id


def test_workflow_navigation_and_tablist(parsed_dom: DOMContractParser) -> None:
    """Verify WAI-ARIA tablist navigation pattern and roving tabindex attributes.

    Pre-conditions:
        - parsed_dom fixture loaded.
    Post-conditions:
        - Asserts nav has aria-label, tablist has id='workflow-tablist', and contains
          5 button[role='tab'] elements with matching aria-controls and data-step values.
    """
    navs = [t for t in parsed_dom.tags if t["tag"] == "nav"]
    assert len(navs) == 1, "Expected exactly one <nav> element"
    assert navs[0]["attrs"].get("aria-label") == "SynthAI Studio Workflow Steps"

    tablist = parsed_dom.elements_by_id.get("workflow-tablist")
    assert tablist is not None, "Missing #workflow-tablist container"
    assert tablist["attrs"].get("role") == "tablist"

    for step_num in range(1, 6):
        tab_id = f"tab-step-{step_num}"
        panel_id = f"step-{step_num}"
        tab = parsed_dom.elements_by_id.get(tab_id)
        assert tab is not None, f"Missing tab button: #{tab_id}"
        assert tab["tag"] == "button"
        assert tab["attrs"].get("role") == "tab"
        assert tab["attrs"].get("aria-controls") == panel_id
        assert tab["attrs"].get("data-step") == str(step_num)

        if step_num == 1:
            assert tab["attrs"].get("aria-selected") == "true"
            assert tab["attrs"].get("tabindex") == "0"
            assert "active" in str(tab["attrs"].get("class", ""))
        else:
            assert tab["attrs"].get("aria-selected") == "false"
            assert tab["attrs"].get("tabindex") == "-1"


def test_main_workbench_and_panels(parsed_dom: DOMContractParser) -> None:
    """Verify main workbench landmark and 5 tabpanel sections.

    Pre-conditions:
        - parsed_dom fixture loaded.
    Post-conditions:
        - Asserts <main id='main-workbench' tabindex='-1'> contains 5 section panels
          with role='tabpanel' and aria-labelledby matching tab IDs.
    """
    main = parsed_dom.elements_by_id.get("main-workbench")
    assert main is not None, "Missing <main id='main-workbench'>"
    assert main["tag"] == "main"
    assert main["attrs"].get("tabindex") == "-1"

    for step_num in range(1, 6):
        panel_id = f"step-{step_num}"
        tab_id = f"tab-step-{step_num}"
        panel = parsed_dom.elements_by_id.get(panel_id)
        assert panel is not None, f"Missing panel section: #{panel_id}"
        assert panel["tag"] == "section"
        assert panel["attrs"].get("role") == "tabpanel"
        assert panel["attrs"].get("aria-labelledby") == tab_id

        if step_num == 1:
            assert "active" in str(panel["attrs"].get("class", ""))
            assert "hidden" not in panel["attrs"]
        else:
            assert "hidden" in panel["attrs"]


def test_every_form_control_has_explicit_label(parsed_dom: DOMContractParser) -> None:
    """Verify every input and select control has a corresponding label[for=id] in the DOM.

    Pre-conditions:
        - parsed_dom fixture loaded.
    Post-conditions:
        - Asserts no orphan input or select controls exist.
    """
    label_for_targets = {
        label.get("for") for label in parsed_dom.labels if label.get("for") is not None
    }

    input_ids = [inp.get("id") for inp in parsed_dom.inputs if inp.get("id")]
    select_ids = [sel.get("id") for sel in parsed_dom.selects if sel.get("id")]
    all_control_ids = input_ids + select_ids

    assert len(all_control_ids) > 0, "No form controls discovered"
    unlabeled = [cid for cid in all_control_ids if cid not in label_for_targets]
    assert not unlabeled, (
        f"Unlabeled form controls detected without matching label[for]: {unlabeled}"
    )


def test_error_and_fallback_banners_exist(parsed_dom: DOMContractParser) -> None:
    """Verify global error banner and compute fallback banners exist with correct ARIA attributes.

    Pre-conditions:
        - parsed_dom fixture loaded.
    Post-conditions:
        - Asserts #global-error-banner, #compute-fallback-banner, and
          #compute-fallback-banner-step5 exist and default to hidden.
    """
    global_err = parsed_dom.elements_by_id.get("global-error-banner")
    assert global_err is not None, "Missing #global-error-banner"
    assert global_err["attrs"].get("role") == "alert"
    assert global_err["attrs"].get("tabindex") == "-1"
    assert "hidden" in global_err["attrs"]
    assert "global-error-text" in parsed_dom.elements_by_id
    assert "global-error-dismiss" in parsed_dom.elements_by_id

    fallback_step4 = parsed_dom.elements_by_id.get("compute-fallback-banner")
    assert fallback_step4 is not None, "Missing #compute-fallback-banner in Step 4"
    assert fallback_step4["attrs"].get("role") == "status"
    assert "hidden" in fallback_step4["attrs"]

    fallback_step5 = parsed_dom.elements_by_id.get("compute-fallback-banner-step5")
    assert fallback_step5 is not None, "Missing #compute-fallback-banner-step5 in Step 5"
    assert fallback_step5["attrs"].get("role") == "status"
    assert "hidden" in fallback_step5["attrs"]


def test_step_1_controls_and_containers(parsed_dom: DOMContractParser) -> None:
    """Verify Step 1 containers, file upload form, and presigned ticket elements.

    Pre-conditions:
        - parsed_dom fixture loaded.
    Post-conditions:
        - Asserts #benchmark-cards, #upload-form, #upload-name, #upload-file,
          #btn-upload-dataset, #presign-name, #btn-generate-ticket, and #presign-result exist.
    """
    assert "benchmark-cards" in parsed_dom.elements_by_id
    assert "upload-form" in parsed_dom.elements_by_id
    assert "upload-name" in parsed_dom.elements_by_id
    assert "upload-file" in parsed_dom.elements_by_id
    assert "btn-upload-dataset" in parsed_dom.elements_by_id
    assert "presign-name" in parsed_dom.elements_by_id
    assert "btn-generate-ticket" in parsed_dom.elements_by_id
    assert "presign-result" in parsed_dom.elements_by_id
    assert "presign-text" in parsed_dom.elements_by_id


def test_step_2_controls_tables_and_stat_tiles(parsed_dom: DOMContractParser) -> None:
    """Verify Step 2 dataset selector, cleanse CTA, KPI tiles, columns table, and issues list.

    Pre-conditions:
        - parsed_dom fixture loaded.
    Post-conditions:
        - Asserts #profile-dataset-select, #btn-cleanse-dataset, #prof-rows, #prof-cols,
          #prof-quality, #prof-privacy-risk, #profile-columns-table, and #profile-issues-list exist.
    """
    assert "profile-dataset-select" in parsed_dom.elements_by_id
    assert "btn-cleanse-dataset" in parsed_dom.elements_by_id
    assert "profile-empty-state" in parsed_dom.elements_by_id
    assert "prof-rows" in parsed_dom.elements_by_id
    assert "prof-cols" in parsed_dom.elements_by_id
    assert "prof-quality" in parsed_dom.elements_by_id
    assert "prof-privacy-risk" in parsed_dom.elements_by_id
    assert "profile-columns-table" in parsed_dom.elements_by_id
    assert "profile-issues-list" in parsed_dom.elements_by_id
    assert "profile-corr-table" in parsed_dom.elements_by_id


def test_step_3_synthesis_form_controls_and_options(parsed_dom: DOMContractParser) -> None:
    """Verify Step 3 synthesis configuration form, controls, and launch button.

    Pre-conditions:
        - parsed_dom fixture loaded.
    Post-conditions:
        - Asserts #synth-config-form and all 10 generation parameters exist.
    """
    assert "synth-config-form" in parsed_dom.elements_by_id
    assert "gen-dataset-id" in parsed_dom.elements_by_id
    assert "gen-target-rows" in parsed_dom.elements_by_id
    assert "gen-engine" in parsed_dom.elements_by_id
    assert "gen-privacy-level" in parsed_dom.elements_by_id
    assert "gen-epsilon" in parsed_dom.elements_by_id
    assert "gen-delta" in parsed_dom.elements_by_id
    assert "gen-target-col" in parsed_dom.elements_by_id
    assert "gen-minority-val" in parsed_dom.elements_by_id
    assert "gen-minority-ratio" in parsed_dom.elements_by_id
    assert "gen-anonymize-pii" in parsed_dom.elements_by_id
    assert "dp-guarantee-preview" in parsed_dom.elements_by_id
    assert "btn-launch-synth" in parsed_dom.elements_by_id


def test_step_4_jobs_table_and_privacy_ledger(parsed_dom: DOMContractParser) -> None:
    """Verify Step 4 jobs table, refresh CTA, privacy budget ledger, and worker console.

    Pre-conditions:
        - parsed_dom fixture loaded.
    Post-conditions:
        - Asserts #jobs-table, #btn-refresh-jobs, #privacy-ledger-card, and #worker-console exist.
    """
    assert "jobs-table" in parsed_dom.elements_by_id
    assert "btn-refresh-jobs" in parsed_dom.elements_by_id
    assert "privacy-ledger-card" in parsed_dom.elements_by_id
    assert "ledger-status" in parsed_dom.elements_by_id
    assert "ledger-spent" in parsed_dom.elements_by_id
    assert "ledger-noise-scale" in parsed_dom.elements_by_id
    assert "ledger-remaining" in parsed_dom.elements_by_id
    assert "ledger-delta" in parsed_dom.elements_by_id
    assert "ledger-initial" in parsed_dom.elements_by_id
    assert "ledger-mechanism" in parsed_dom.elements_by_id
    assert "ledger-psd" in parsed_dom.elements_by_id
    assert "worker-console" in parsed_dom.elements_by_id


def test_step_5_fidelity_table_and_artifact_downloads(parsed_dom: DOMContractParser) -> None:
    """Verify Step 5 fidelity table, compliance verdict, and 1-click artifact downloads.

    Pre-conditions:
        - parsed_dom fixture loaded.
    Post-conditions:
        - Asserts #report-job-select, #rep-quality, #rep-fidelity, #rep-corr, #rep-privacy,
          #rep-verdict, #rep-hipaa, and download buttons (csv, json, parquet, md) exist.
    """
    assert "report-job-select" in parsed_dom.elements_by_id
    assert "report-empty-state" in parsed_dom.elements_by_id
    assert "rep-quality" in parsed_dom.elements_by_id
    assert "rep-fidelity" in parsed_dom.elements_by_id
    assert "rep-corr" in parsed_dom.elements_by_id
    assert "rep-privacy" in parsed_dom.elements_by_id
    assert "rep-verdict" in parsed_dom.elements_by_id
    assert "rep-hipaa" in parsed_dom.elements_by_id
    assert "rep-dcr" in parsed_dom.elements_by_id
    assert "rep-nndr" in parsed_dom.elements_by_id
    assert "rep-collisions" in parsed_dom.elements_by_id
    assert "rep-pii-leaks" in parsed_dom.elements_by_id
    assert "btn-dl-csv" in parsed_dom.elements_by_id
    assert "btn-dl-json" in parsed_dom.elements_by_id
    assert "btn-dl-parquet" in parsed_dom.elements_by_id
    assert "btn-dl-markdown" in parsed_dom.elements_by_id
    assert "fidelity-columns-table" in parsed_dom.elements_by_id
