"""Deterministic verification test suite for SynthAI Studio UI design tokens and components.

Pre-conditions:
    - tokens.css and components.css exist under src/synthai_studio/api/static/.
    - pytest, ruff, and mypy installed in active Python environment.
Post-conditions:
    - Formally validates design tokens, legacy aliases, and WCAG 2.2 AA contrast ratios.
    - Validates components.css for zero raw hex literals, tabular numbers, 5 states,
      zero-CLS skeletons, accessibility rules, and responsive media queries.
"""

import re
from pathlib import Path
from typing import Final

import pytest

STATIC_DIR: Final[Path] = (
    Path(__file__).resolve().parent.parent / "src" / "synthai_studio" / "api" / "static"
)
TOKENS_PATH: Final[Path] = STATIC_DIR / "tokens.css"
COMPONENTS_PATH: Final[Path] = STATIC_DIR / "components.css"


def load_css_file(file_path: Path) -> str:
    """Read and return content of specified CSS asset file.

    Pre-conditions:
        - file_path points to an existing readable file.
    Post-conditions:
        - Returns full text content as string.
    """
    assert file_path.is_file(), f"CSS file does not exist: {file_path}"
    return file_path.read_text(encoding="utf-8")


def parse_css_variables(css_content: str) -> dict[str, str]:
    """Extract custom CSS property declarations into a dictionary mapping.

    Pre-conditions:
        - css_content contains valid CSS declaration blocks.
    Post-conditions:
        - Returns dictionary mapping variable name (e.g. '--bg-canvas') to value string.
    """
    pattern = re.compile(r"(--[\w-]+)\s*:\s*([^;]+);")
    return {
        match.group(1).strip(): match.group(2).strip()
        for match in pattern.finditer(css_content)
    }


def resolve_token_value(token_name: str, tokens: dict[str, str]) -> str:
    """Recursively resolve token value if it references another CSS variable via var().

    Pre-conditions:
        - token_name is present in tokens mapping.
        - tokens mapping contains valid token strings.
    Post-conditions:
        - Returns terminal resolved string value.
    """
    val = tokens[token_name].strip()
    if val.startswith("var(") and val.endswith(")"):
        inner = val[4:-1].strip()
        return resolve_token_value(inner, tokens)
    return val


def srgb_to_linear(channel: float) -> float:
    """Convert an 8-bit normalized sRGB color channel into linear luminance per WCAG 2.2.

    Pre-conditions:
        - channel is a float in the range [0.0, 1.0].
    Post-conditions:
        - Returns linearized RGB component in range [0.0, 1.0].
    """
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def hex_to_relative_luminance(hex_code: str) -> float:
    """Calculate relative luminance for an sRGB hex color per WCAG 2.2 specification.

    Pre-conditions:
        - hex_code is a valid 6-character hex color string starting with '#'.
    Post-conditions:
        - Returns relative luminance L in the range [0.0, 1.0].
    """
    clean_hex = hex_code.strip().lstrip("#")
    r = int(clean_hex[0:2], 16) / 255.0
    g = int(clean_hex[2:4], 16) / 255.0
    b = int(clean_hex[4:6], 16) / 255.0
    return 0.2126 * srgb_to_linear(r) + 0.7152 * srgb_to_linear(g) + 0.0722 * srgb_to_linear(b)


def calculate_contrast_ratio(hex_fg: str, hex_bg: str) -> float:
    """Compute relative luminance contrast ratio between foreground and background colors.

    Pre-conditions:
        - hex_fg and hex_bg are valid 6-character hex color strings.
    Post-conditions:
        - Returns contrast ratio (L1 + 0.05) / (L2 + 0.05) in range [1.0, 21.0].
    """
    lum_fg = hex_to_relative_luminance(hex_fg)
    lum_bg = hex_to_relative_luminance(hex_bg)
    lighter = max(lum_fg, lum_bg)
    darker = min(lum_fg, lum_bg)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.fixture(scope="module")
def tokens_content() -> str:
    """Fixture providing raw text content of tokens.css.

    Pre-conditions:
        - tokens.css exists under static directory.
    Post-conditions:
        - Returns non-empty string content.
    """
    return load_css_file(TOKENS_PATH)


@pytest.fixture(scope="module")
def tokens_map(tokens_content: str) -> dict[str, str]:
    """Fixture providing parsed dictionary of CSS variables from tokens.css.

    Pre-conditions:
        - tokens_content is loaded.
    Post-conditions:
        - Returns dictionary of variable declarations.
    """
    return parse_css_variables(tokens_content)


@pytest.fixture(scope="module")
def components_content() -> str:
    """Fixture providing raw text content of components.css.

    Pre-conditions:
        - components.css exists under static directory.
    Post-conditions:
        - Returns non-empty string content.
    """
    return load_css_file(COMPONENTS_PATH)


def test_tokens_css_exists_and_non_empty(tokens_content: str) -> None:
    """Verify tokens.css exists and contains valid CSS content.

    Pre-conditions:
        - tokens_content fixture loaded.
    Post-conditions:
        - Asserts file length is positive and contains root selector.
    """
    assert len(tokens_content.strip()) > 0
    assert ":root" in tokens_content


def test_tokens_surface_elevations_present(tokens_map: dict[str, str]) -> None:
    """Verify 4-tier dark surface elevation tokens and console background are defined.

    Pre-conditions:
        - tokens_map contains parsed CSS custom properties.
    Post-conditions:
        - Asserts --bg-canvas, --bg-surface-1, --bg-surface-2, --bg-surface-3,
          and --bg-console exist.
    """
    expected_surfaces = {
        "--bg-canvas": "#070a12",
        "--bg-surface-1": "#0e1422",
        "--bg-surface-2": "#151e31",
        "--bg-surface-3": "#1e2b45",
        "--bg-console": "#04070e",
    }
    for token, expected_hex in expected_surfaces.items():
        assert token in tokens_map, f"Missing elevation token: {token}"
        assert tokens_map[token].lower() == expected_hex.lower()


def test_tokens_border_and_focus_tokens_present(tokens_map: dict[str, str]) -> None:
    """Verify structural hairlines and focus ring tokens are defined.

    Pre-conditions:
        - tokens_map contains parsed CSS custom properties.
    Post-conditions:
        - Asserts --border-subtle, --border-default, --border-strong, and --border-focus exist.
    """
    expected_borders = {
        "--border-subtle": "#1e293b",
        "--border-default": "#283750",
        "--border-strong": "#3b5278",
        "--border-focus": "#22d3ee",
    }
    for token, expected_hex in expected_borders.items():
        assert token in tokens_map, f"Missing border token: {token}"
        assert tokens_map[token].lower() == expected_hex.lower()


def test_tokens_typography_ink_present(tokens_map: dict[str, str]) -> None:
    """Verify typography ink tokens are defined.

    Pre-conditions:
        - tokens_map contains parsed CSS custom properties.
    Post-conditions:
        - Asserts --text-primary, --text-secondary, --text-muted, and --text-on-accent exist.
    """
    expected_ink = {
        "--text-primary": "#f8fafc",
        "--text-secondary": "#cbd5e1",
        "--text-muted": "#94a3b8",
        "--text-on-accent": "#041019",
    }
    for token, expected_hex in expected_ink.items():
        assert token in tokens_map, f"Missing typography ink token: {token}"
        assert tokens_map[token].lower() == expected_hex.lower()


def test_tokens_brand_accents_present(tokens_map: dict[str, str]) -> None:
    """Verify primary and secondary brand accent tokens are defined.

    Pre-conditions:
        - tokens_map contains parsed CSS custom properties.
    Post-conditions:
        - Asserts --accent-primary, --accent-primary-hover, --accent-secondary,
          and --accent-secondary-hover exist.
    """
    expected_accents = {
        "--accent-primary": "#06b6d4",
        "--accent-primary-hover": "#22d3ee",
        "--accent-secondary": "#10b981",
        "--accent-secondary-hover": "#34d399",
    }
    for token, expected_hex in expected_accents.items():
        assert token in tokens_map, f"Missing accent token: {token}"
        assert tokens_map[token].lower() == expected_hex.lower()


def test_tokens_semantic_status_tokens_present(tokens_map: dict[str, str]) -> None:
    """Verify semantic status tokens for nominal, info, warn, and danger are defined.

    Pre-conditions:
        - tokens_map contains parsed CSS custom properties.
    Post-conditions:
        - Asserts all 12 status bg, fg, and border tokens exist with expected hex values.
    """
    expected_status = {
        "--status-nominal-bg": "#052e24",
        "--status-nominal-fg": "#34d399",
        "--status-nominal-border": "#059669",
        "--status-info-bg": "#082f49",
        "--status-info-fg": "#38bdf8",
        "--status-info-border": "#0284c7",
        "--status-warn-bg": "#451a03",
        "--status-warn-fg": "#fbbf24",
        "--status-warn-border": "#d97706",
        "--status-danger-bg": "#4c0519",
        "--status-danger-fg": "#fb7185",
        "--status-danger-border": "#e11d48",
    }
    for token, expected_hex in expected_status.items():
        assert token in tokens_map, f"Missing semantic status token: {token}"
        assert tokens_map[token].lower() == expected_hex.lower()


def test_tokens_font_stacks_and_typography_scale_present(tokens_map: dict[str, str]) -> None:
    """Verify font stacks and typography scale tokens are defined.

    Pre-conditions:
        - tokens_map contains parsed CSS custom properties.
    Post-conditions:
        - Asserts --font-sans, --font-mono, and scale tokens (--text-xs through --text-xl) exist.
    """
    assert "--font-sans" in tokens_map
    assert "Inter" in tokens_map["--font-sans"]
    assert "--font-mono" in tokens_map
    assert "JetBrains Mono" in tokens_map["--font-mono"]

    scale_tokens = ["--text-xs", "--text-sm", "--text-base", "--text-lg", "--text-xl"]
    for token in scale_tokens:
        assert token in tokens_map, f"Missing typography scale token: {token}"


def test_tokens_spacing_grid_and_radii_present(tokens_map: dict[str, str]) -> None:
    """Verify 4px/8px rhythm spatial grid and border radius tokens are defined.

    Pre-conditions:
        - tokens_map contains parsed CSS custom properties.
    Post-conditions:
        - Asserts --space-1 through --space-8 and --radius-sm through --radius-lg exist.
    """
    for i in range(1, 9):
        token = f"--space-{i}"
        assert token in tokens_map, f"Missing spatial grid token: {token}"

    radii_tokens = ["--radius-sm", "--radius-md", "--radius-lg"]
    for token in radii_tokens:
        assert token in tokens_map, f"Missing radius token: {token}"


def test_tokens_motion_tokens_present(tokens_map: dict[str, str]) -> None:
    """Verify motion timing and easing curve tokens are defined.

    Pre-conditions:
        - tokens_map contains parsed CSS custom properties.
    Post-conditions:
        - Asserts --ease-out-expo and --duration-fast exist.
    """
    assert "--ease-out-expo" in tokens_map
    assert "--duration-fast" in tokens_map


def test_tokens_legacy_aliases_present(tokens_map: dict[str, str]) -> None:
    """Verify backward-compatible aliases for legacy theme integration.

    Pre-conditions:
        - tokens_map contains parsed CSS custom properties.
    Post-conditions:
        - Asserts all 11 legacy aliases resolve to valid canonical variables.
    """
    expected_aliases = {
        "--bg-dark": "--bg-canvas",
        "--bg-panel": "--bg-surface-1",
        "--bg-card": "--bg-surface-2",
        "--bg-hover": "--bg-surface-3",
        "--border-color": "--border-default",
        "--text-main": "--text-primary",
        "--accent-cyan": "--accent-primary",
        "--accent-emerald": "--accent-secondary",
        "--accent-blue": "--status-info-fg",
        "--accent-amber": "--status-warn-fg",
        "--accent-rose": "--status-danger-fg",
    }
    for alias, canonical in expected_aliases.items():
        assert alias in tokens_map, f"Missing legacy alias: {alias}"
        assert canonical in tokens_map[alias], (
            f"Alias {alias} expected to reference {canonical}, got {tokens_map[alias]}"
        )


def test_wcag_contrast_text_ink_on_surfaces(tokens_map: dict[str, str]) -> None:
    """Verify WCAG 2.2 AA contrast ratio (>= 4.5:1) for text ink on surface elevations.

    Pre-conditions:
        - tokens_map contains hex declarations for text ink and background surfaces.
    Post-conditions:
        - Validates all 9 combinations of text primary/secondary/muted against
          canvas, surface-1, and surface-2 exceed 4.5:1 contrast.
    """
    text_tokens = ["--text-primary", "--text-secondary", "--text-muted"]
    surface_tokens = ["--bg-canvas", "--bg-surface-1", "--bg-surface-2"]

    for text_token in text_tokens:
        fg_hex = tokens_map[text_token]
        for surface_token in surface_tokens:
            bg_hex = tokens_map[surface_token]
            ratio = calculate_contrast_ratio(fg_hex, bg_hex)
            assert ratio >= 4.5, (
                f"WCAG contrast failure: {text_token} ({fg_hex}) on {surface_token} ({bg_hex}) "
                f"yields {ratio:.2f}:1 (< 4.5:1)"
            )


def test_wcag_contrast_text_on_accent(tokens_map: dict[str, str]) -> None:
    """Verify WCAG 2.2 AA contrast ratio (>= 4.5:1) for text-on-accent on brand accents.

    Pre-conditions:
        - tokens_map contains hex declarations for --text-on-accent and brand accents.
    Post-conditions:
        - Validates --text-on-accent achieves >= 4.5:1 contrast on both
          --accent-primary and --accent-secondary.
    """
    fg_hex = tokens_map["--text-on-accent"]
    accent_tokens = ["--accent-primary", "--accent-secondary"]

    for accent_token in accent_tokens:
        bg_hex = tokens_map[accent_token]
        ratio = calculate_contrast_ratio(fg_hex, bg_hex)
        assert ratio >= 4.5, (
            f"WCAG contrast failure: --text-on-accent ({fg_hex}) on {accent_token} ({bg_hex}) "
            f"yields {ratio:.2f}:1 (< 4.5:1)"
        )


def test_wcag_contrast_semantic_status_badges(tokens_map: dict[str, str]) -> None:
    """Verify WCAG 2.2 AA contrast ratio (>= 4.5:1) for semantic status foreground on background.

    Pre-conditions:
        - tokens_map contains hex declarations for status fg and bg pairs.
    Post-conditions:
        - Validates all 4 status levels (nominal, info, warn, danger) achieve >= 4.5:1 contrast.
    """
    status_pairs = [
        ("--status-nominal-fg", "--status-nominal-bg"),
        ("--status-info-fg", "--status-info-bg"),
        ("--status-warn-fg", "--status-warn-bg"),
        ("--status-danger-fg", "--status-danger-bg"),
    ]
    for fg_token, bg_token in status_pairs:
        fg_hex = tokens_map[fg_token]
        bg_hex = tokens_map[bg_token]
        ratio = calculate_contrast_ratio(fg_hex, bg_hex)
        assert ratio >= 4.5, (
            f"WCAG contrast failure: {fg_token} ({fg_hex}) on {bg_token} ({bg_hex}) "
            f"yields {ratio:.2f}:1 (< 4.5:1)"
        )


def test_components_css_exists_and_non_empty(components_content: str) -> None:
    """Verify components.css exists and contains valid stylesheet content.

    Pre-conditions:
        - components_content fixture loaded.
    Post-conditions:
        - Asserts file length is positive and contains reset rules.
    """
    assert len(components_content.strip()) > 0
    assert "box-sizing: border-box;" in components_content


def test_components_css_zero_raw_hex_literals(components_content: str) -> None:
    """Verify components.css contains zero hardcoded raw hex color literals.

    Pre-conditions:
        - components_content fixture loaded.
    Post-conditions:
        - Asserts no regex matches for hex color literals (#[0-9a-fA-F]{3,8}) in components.css.
    """
    hex_pattern = re.compile(r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
    matches = hex_pattern.findall(components_content)
    assert not matches, f"Forbidden hardcoded hex colors found in components.css: {matches}"


def test_components_css_strict_tabular_nums(components_content: str) -> None:
    """Verify strict tabular-nums font configuration for zero telemetry jitter.

    Pre-conditions:
        - components_content fixture loaded.
    Post-conditions:
        - Asserts font-variant-numeric: tabular-nums and expected selector list exist.
    """
    assert "font-variant-numeric: tabular-nums;" in components_content
    assert 'font-feature-settings: "tnum" 1, "zero" 1;' in components_content

    expected_selectors = [
        ".tabular-nums",
        ".stat-val",
        ".metric-value",
        'td[data-numeric="true"]',
        ".corr-cell",
        ".badge-numeric",
        'input[type="number"]',
        ".log-console",
    ]
    for selector in expected_selectors:
        assert selector in components_content, (
            f"Missing tabular-nums target selector: {selector}"
        )


def test_components_css_five_state_determinism_classes(components_content: str) -> None:
    """Verify 5-state determinism classes exist in components.css.

    Pre-conditions:
        - components_content fixture loaded.
    Post-conditions:
        - Asserts empty, loading, nominal, degraded, and error state classes exist.
    """
    state_classes = [
        ".state-empty",
        ".state-loading",
        ".state-nominal",
        ".state-degraded",
        ".state-error",
        ".degraded-banner",
        ".error-banner",
    ]
    for cls in state_classes:
        assert cls in components_content, f"Missing state determinism class: {cls}"


def test_components_css_zero_cls_skeletons(components_content: str) -> None:
    """Verify zero-CLS skeleton placeholder classes match target widget geometry.

    Pre-conditions:
        - components_content fixture loaded.
    Post-conditions:
        - Asserts .skeleton-tile (84px), .skeleton-row (37px), and .skeleton-card (136px) exist.
    """
    assert ".skeleton-tile" in components_content
    assert "min-height: 84px;" in components_content
    assert ".skeleton-row" in components_content
    assert "height: 37px;" in components_content
    assert ".skeleton-card" in components_content
    assert "min-height: 136px;" in components_content
    assert "@keyframes synthai-shimmer" in components_content


def test_components_css_accessibility_and_focus_rules(components_content: str) -> None:
    """Verify accessibility landmarks, skip links, screen-reader class, and focus rings.

    Pre-conditions:
        - components_content fixture loaded.
    Post-conditions:
        - Asserts .skip-link, :focus-visible, .sr-only, and .table-scroll-wrapper are defined.
    """
    assert ".skip-link" in components_content
    assert ".skip-link:focus" in components_content
    assert ".skip-link:focus-visible" in components_content
    assert ":focus-visible" in components_content
    assert "outline: 2px solid var(--border-focus);" in components_content
    assert "outline-offset: 2px;" in components_content
    assert ".sr-only" in components_content
    assert ".table-scroll-wrapper" in components_content


def test_components_css_reduced_motion_media_query(components_content: str) -> None:
    """Verify WCAG 2.2 prefers-reduced-motion media query is defined.

    Pre-conditions:
        - components_content fixture loaded.
    Post-conditions:
        - Asserts @media (prefers-reduced-motion: reduce) disables animations.
    """
    assert "@media (prefers-reduced-motion: reduce)" in components_content
    assert "animation-duration: 0.01ms !important;" in components_content
    assert "animation: none !important;" in components_content


def test_components_css_responsive_breakpoints(components_content: str) -> None:
    """Verify responsive media query breakpoints for desktop, tablet, and mobile.

    Pre-conditions:
        - components_content fixture loaded.
    Post-conditions:
        - Asserts max-width: 1199px and max-width: 767px breakpoints exist.
    """
    assert "@media (max-width: 1199px)" in components_content
    assert "@media (max-width: 767px)" in components_content
