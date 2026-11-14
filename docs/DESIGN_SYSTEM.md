# SynthAI Studio — Visual Design System & Token Architecture (`v2-ux`)

**Document Status**: Gate 1 Canonical Specification  
**Author**: Staff Product & Visual Systems Designer (`@product-designer`)  
**Target Package**: `synthai_studio` (`src/synthai_studio/api/static/tokens.css`, `src/synthai_studio/api/static/components.css`)  
**Compliance Standard**: WCAG 2.2 Level AA, Zero-CLS Skeleton Geometry, Strict Tabular-Nums Telemetry

---

## 1. Aesthetic Direction — Precision Privacy Engineering & Statistical Laboratory

SynthAI Studio is an engineering workbench for differential privacy (`(epsilon, delta)` accounting), PII/PHI diagnostic scanning, multi-engine generative tabular synthesis (`GAUSSIAN_COPULA`, `CTGAN_LATENT`, `FAKER_HYBRID`, `SPARK_LLM_EDGE`), and statistical fidelity verification (`1-KS`, `1-TVD`, `DCR`, `NNDR`, Pearson correlation stability).

The visual system adopts a **Precision Privacy Engineering & Statistical Laboratory** aesthetic:
1. **High-Legibility Dark-Mode Instrument Console**: Engineered for sustained technical inspection in dark environments. Depth is communicated strictly through a 4-tier luminance surface hierarchy (`#070a12` -> `#0e1422` -> `#151e31` -> `#1e2b45`) paired with crisp `1px` structural hairlines rather than drop shadows or decorative consumer-SaaS gradients.
2. **Unambiguous Semantic Risk & Provenance Signaling**: Visual contrast immediately separates verified privacy guarantees (`--status-nominal-*`), active statistical engine metadata (`--status-info-*`), degraded compute fallback (`ComputeTier.CPU_WORKER` fallback from `SPARK_LLM_EDGE` via `--status-warn-*`), and unmasked PII / privacy budget exhaustion / record collision leaks (`--status-danger-*`).
3. **Zero Emojis & Scannable Data Density**: All status indicators, navigation tabs, and audit verdicts rely on structured typographic badges, geometric status pills, and monospace numeric tables with zero emojis in UI chrome, logs, or source code.

---

## 2. 4-Tier Surface Elevation & Semantic Color Tokens (`tokens.css`)

All visual stylesheets and UI templates must consume CSS custom properties declared in `src/synthai_studio/api/static/tokens.css`. Hardcoded hex values outside `tokens.css` are prohibited.

### 2.1 Surface Elevation Hierarchy

| Tier | Token | Hex | Role & Component Mapping |
| :--- | :--- | :--- | :--- |
| **Tier 0 (Canvas)** | `--bg-canvas` | `#070a12` | Root `body` viewport background |
| **Tier 1 (Primary Surface)** | `--bg-surface-1` | `#0e1422` | Primary `.card` containers, top `<header>`, `<nav>` step bar |
| **Tier 2 (Raised Element)** | `--bg-surface-2` | `#151e31` | `.stat-tile` containers, `th` table headers, form `input`/`select`/`textarea`, `<pre>` blocks, benchmark sub-cards |
| **Tier 3 (Interactive / Hover)** | `--bg-surface-3` | `#1e2b45` | Secondary button `:hover`, table row hover highlight, active tab surface tint, tooltips |
| **Recessed Console** | `--bg-console` | `#04070e` | `.log-console` recessed worker activity log terminal |

### 2.2 Backward-Compatible Legacy Token Aliases

To guarantee seamless compatibility with existing selectors and inline references during and after the `v2-ux` migration, `tokens.css` maps all legacy custom properties to the canonical 4-tier tokens:

* `--bg-dark`: `var(--bg-canvas)`
* `--bg-panel`: `var(--bg-surface-1)`
* `--bg-card`: `var(--bg-surface-2)`
* `--bg-hover`: `var(--bg-surface-3)`
* `--border-color`: `var(--border-default)`
* `--text-main`: `var(--text-primary)`
* `--accent-cyan`: `var(--accent-primary)`
* `--accent-emerald`: `var(--accent-secondary)`
* `--accent-blue`: `var(--status-info-fg)`
* `--accent-amber`: `var(--status-warn-fg)`
* `--accent-rose`: `var(--status-danger-fg)`

### 2.3 Border & Structural Hairline Tokens

| Token | Hex | Usage |
| :--- | :--- | :--- |
| `--border-subtle` | `#1e293b` | Internal table cell dividers (`td`), subtle card section dividers |
| `--border-default` | `#283750` | Standard `1px solid` card borders, `<header>`, `<nav>`, `.stat-tile`, form inputs |
| `--border-strong` | `#3b5278` | Active card borders, hovered interactive control borders, table header bottom borders |
| `--border-focus` | `#22d3ee` | High-visibility `:focus-visible` keyboard focus ring (`2px solid` with `2px` offset) |

### 2.4 Typography & WCAG 2.2 AA Contrast Matrix

All foreground/background pairings are verified against WCAG 2.2 AA minimum contrast requirements (`>= 4.5:1` for normal text, `>= 3.0:1` for large text and UI components):

| Foreground Token | Hex | Target Background | Background Hex | Contrast Ratio | WCAG 2.2 Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `--text-primary` | `#f8fafc` | `--bg-canvas` | `#070a12` | `19.1 : 1` | AAA (`> 7.0:1`) |
| `--text-primary` | `#f8fafc` | `--bg-surface-1` | `#0e1422` | `17.4 : 1` | AAA (`> 7.0:1`) |
| `--text-primary` | `#f8fafc` | `--bg-surface-2` | `#151e31` | `15.2 : 1` | AAA (`> 7.0:1`) |
| `--text-secondary` | `#cbd5e1` | `--bg-surface-1` | `#0e1422` | `12.1 : 1` | AAA (`> 7.0:1`) |
| `--text-secondary` | `#cbd5e1` | `--bg-surface-2` | `#151e31` | `10.6 : 1` | AAA (`> 7.0:1`) |
| `--text-muted` | `#94a3b8` | `--bg-surface-1` | `#0e1422` | `6.1 : 1` | AA (`>= 4.5:1`) |
| `--text-muted` | `#94a3b8` | `--bg-surface-2` | `#151e31` | `5.3 : 1` | AA (`>= 4.5:1`) |
| `--text-on-accent` | `#041019` | `--accent-primary` | `#06b6d4` | `8.2 : 1` | AAA (`> 7.0:1`) |
| `--text-on-accent` | `#041019` | `--accent-secondary` | `#10b981` | `8.5 : 1` | AAA (`> 7.0:1`) |
| `--status-nominal-fg` | `#34d399` | `--status-nominal-bg` | `#052e24` | `7.9 : 1` | AAA (`> 7.0:1`) |
| `--status-info-fg` | `#38bdf8` | `--status-info-bg` | `#082f49` | `7.1 : 1` | AAA (`> 7.0:1`) |
| `--status-warn-fg` | `#fbbf24` | `--status-warn-bg` | `#451a03` | `7.4 : 1` | AAA (`> 7.0:1`) |
| `--status-danger-fg` | `#fb7185` | `--status-danger-bg` | `#4c0519` | `6.2 : 1` | AA (`>= 4.5:1`) |

### 2.5 Semantic Status & Privacy Risk Tokens

| Semantic Domain | Background Token | Foreground Token | Border Token | Domain Mapping (`models.py`) |
| :--- | :--- | :--- | :--- | :--- |
| **Nominal / Safe / Verified** | `--status-nominal-bg: #052e24` | `--status-nominal-fg: #34d399` | `--status-nominal-border: #059669` | `PIIType.NONE`, `JobStatus.COMPLETED`, `hipaa_gdpr_ready == True`, `is_cleansed == True`, `pii_leakage_detected == False`, positive Pearson correlation (`> 0.5`) |
| **Info / Engine / Ledger** | `--status-info-bg: #082f49` | `--status-info-fg: #38bdf8` | `--status-info-border: #0284c7` | `ColumnDataType`, `SynthesizerEngine`, `ComputeTier.GPU_SPARK_WORKER`, `JobStatus.RUNNING`, active `PrivacyBudgetLedger` |
| **Warning / Degraded / Medium Risk** | `--status-warn-bg: #451a03` | `--status-warn-fg: #fbbf24` | `--status-warn-border: #d97706` | `IssueSeverity.MEDIUM`, `IssueSeverity.HIGH`, `PrivacyLevel.LOW`, `ComputeTier.CPU_WORKER` fallback when `SPARK_LLM_EDGE` is unavailable, pre-signed capability tickets |
| **Danger / PII Leak / Exhausted** | `--status-danger-bg: #4c0519` | `--status-danger-fg: #fb7185` | `--status-danger-border: #e11d48` | Detected `PIIType` (`EMAIL`, `SSN`, `PHONE`, `CREDIT_CARD`, `MEDICAL_RECORD_NUMBER`, `PERSON_NAME`, `IP_ADDRESS`), `IssueSeverity.CRITICAL`, `DataQualityIssueType.UNMASKED_PII`, `JobStatus.FAILED`, `hipaa_gdpr_ready == False`, `exact_match_collision_rate > 0`, budget exhausted |

### 2.6 Canonical `src/synthai_studio/api/static/tokens.css` Blueprint

```css
:root {
  /* 1. 4-Tier Surface Elevation Hierarchy */
  --bg-canvas: #070a12;
  --bg-surface-1: #0e1422;
  --bg-surface-2: #151e31;
  --bg-surface-3: #1e2b45;
  --bg-console: #04070e;

  /* 2. Structural Hairlines & Focus Borders */
  --border-subtle: #1e293b;
  --border-default: #283750;
  --border-strong: #3b5278;
  --border-focus: #22d3ee;

  /* 3. Typography & High-Contrast Ink Hierarchy (WCAG 2.2 AA Verified) */
  --text-primary: #f8fafc;
  --text-secondary: #cbd5e1;
  --text-muted: #94a3b8;
  --text-on-accent: #041019;

  /* 4. Primary & Secondary Brand Accents */
  --accent-primary: #06b6d4;
  --accent-primary-hover: #22d3ee;
  --accent-secondary: #10b981;
  --accent-secondary-hover: #34d399;

  /* 5. Semantic Status & Privacy Risk Tokens */
  --status-nominal-bg: #052e24;
  --status-nominal-fg: #34d399;
  --status-nominal-border: #059669;

  --status-info-bg: #082f49;
  --status-info-fg: #38bdf8;
  --status-info-border: #0284c7;

  --status-warn-bg: #451a03;
  --status-warn-fg: #fbbf24;
  --status-warn-border: #d97706;

  --status-danger-bg: #4c0519;
  --status-danger-fg: #fb7185;
  --status-danger-border: #e11d48;

  /* 6. Font Stacks */
  --font-sans: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;

  /* 7. Typographic Scale */
  --text-xs: 0.6875rem;   /* 11px - Badges, console logs, uppercase labels */
  --text-sm: 0.75rem;     /* 12px - Table cells, secondary metadata, nav tabs */
  --text-base: 0.875rem;  /* 14px - Body copy, form controls, card titles */
  --text-lg: 1rem;        /* 16px - Application brand header */
  --text-xl: 1.375rem;    /* 22px - Primary KPI stat values (.stat-val) */

  /* 8. Spatial Grid Scale (4px / 8px Rhythm) */
  --space-1: 0.25rem;     /* 4px */
  --space-2: 0.5rem;      /* 8px */
  --space-3: 0.75rem;     /* 12px */
  --space-4: 1rem;        /* 16px */
  --space-5: 1.25rem;     /* 20px */
  --space-6: 1.5rem;      /* 24px */
  --space-7: 2rem;        /* 32px */
  --space-8: 2.5rem;      /* 40px */

  /* 9. Border Radii */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;

  /* 10. Motion & Transition Timing */
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-fast: 140ms;

  /* 11. Backward-Compatible Legacy Aliases */
  --bg-dark: var(--bg-canvas);
  --bg-panel: var(--bg-surface-1);
  --bg-card: var(--bg-surface-2);
  --bg-hover: var(--bg-surface-3);
  --border-color: var(--border-default);
  --text-main: var(--text-primary);
  --accent-cyan: var(--accent-primary);
  --accent-emerald: var(--accent-secondary);
  --accent-blue: var(--status-info-fg);
  --accent-amber: var(--status-warn-fg);
  --accent-rose: var(--status-danger-fg);
}
```

---

## 3. Typography Scale & Strict `tabular-nums` Discipline

### 3.1 Font Pairing & Hierarchy
* **`--font-sans`**: Used for explanatory prose, benchmark descriptions, remediation guidance, and form help text.
* **`--font-mono`**: Used for application headers, step navigation tabs, table cells, column names, job identifiers, DP parameters (`epsilon`, `delta`), statistical telemetry, JSON/Markdown previews, and worker console logs.

### 3.2 Mandatory `font-variant-numeric: tabular-nums` Enforcement
Every numeric readout, statistical counter, probability ratio, and matrix cell must enforce `font-variant-numeric: tabular-nums` so digits align vertically across rows and never jitter during polling or dataset switching.

The `.tabular-nums` utility class and automatic selector bindings in `components.css` apply `font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1, "zero" 1;` to:

1. **Class & Attribute Selectors**:
   * `.tabular-nums`
   * `.stat-val`
   * `.metric-value`
   * `td[data-numeric="true"]`
   * `.corr-cell`
   * `.badge-numeric`
   * `input[type="number"]`
   * `.log-console`
2. **Domain Metrics Covered (`src/synthai_studio/models.py`)**:
   * **Step 1 (Catalog & Benchmarks)**: `default_row_count`, `row_count`, `column_count`, `max_bytes`, `expires_at`.
   * **Step 2 (Quality & PII Audit)**: `row_count` (`#prof-rows`), `column_count` (`#prof-cols`), `data_quality_score` (`#prof-quality`), `privacy_risk_score` (`#prof-privacy-risk`), `PIIFinding.confidence`, `ColumnProfile.null_count`, `NumericalStats.outlier_count_zscore`, and all `correlation_matrix` Pearson cells (`.corr-cell`).
   * **Step 3 (Engine & DP Config)**: `target_rows` (`#gen-target-rows`), `epsilon` (`#gen-epsilon`), `delta` (`#gen-delta`), `target_ratio` (`#gen-minority-ratio`).
   * **Step 4 (Worker Monitor & DP Ledger)**: `rows_generated`, `throughput_rows_per_sec`, `epsilon_spent` (`#ledger-spent`), remaining epsilon (`#ledger-remaining`), initial epsilon (`#ledger-initial`), `delta` (`#ledger-delta`), `noise_scale`.
   * **Step 5 (Statistical Fidelity & Privacy Verification)**: `overall_quality_score` (`#rep-quality`), `marginal_fidelity_score` (`#rep-fidelity`), `correlation_stability_score` (`#rep-corr`), `privacy_score` (`#rep-privacy`), `ColumnFidelityMetric.score` (`1-KS` / `1-TVD`), `ColumnFidelityMetric.statistic_distance`, `jensen_shannon_similarity`, `dcr_median` / `dcr_p05` (`#rep-dcr`), `nndr_median` / `nndr_p05` (`#rep-nndr`), `exact_match_collision_rate` (`#rep-collisions`), and PII leakage count (`#rep-pii-leaks`).

---

## 4. Spatial Grid (`4px`/`8px` Rhythm), Responsive Breakpoints & Zero Horizontal Overflow

### 4.1 Spatial Grid Rhythm
All padding, margins, and grid gaps snap to the `4px` / `8px` spatial scale:
* Compact inline badge padding: `2px 8px` (`--space-1` vertical / `--space-2` horizontal)
* Standard form control & table cell padding: `8px 12px` (`--space-2` / `--space-3`)
* Stat tile padding: `16px` (`--space-4`)
* Card container padding: `20px` (`--space-5`)
* Main workbench container padding: `24px` (`--space-6`) on desktop, `16px` (`--space-4`) on mobile

### 4.2 Responsive Breakpoint Contract (`375px` to `2560px`)

| Viewport Range | Breakpoint Class | Layout Adaptation Rules |
| :--- | :--- | :--- |
| **Mobile (`375px - 767px`)** | `@media (max-width: 767px)` | `<header>` stacks brand title and `.cluster-status` vertically (`flex-direction: column; align-items: flex-start; gap: 10px`). `.grid-2`, `.grid-3`, and `.grid-4` collapse to a single column (`grid-template-columns: 1fr`). Card headers wrap action controls cleanly (`flex-wrap: wrap; gap: 10px`). |
| **Tablet (`768px - 1199px`)** | `@media (min-width: 768px) and (max-width: 1199px)` | `.grid-4` KPI strips render as a `2x2` matrix (`grid-template-columns: repeat(2, 1fr)`). `.grid-2` remains `1fr 1fr` where width permits or stacks form toolbars cleanly. |
| **Desktop (`1200px - 1919px`)** | Default desktop rules | `.grid-4` renders 4 equal columns (`repeat(4, 1fr)`). `.grid-3` renders 3 columns (`repeat(3, 1fr)`). `.grid-2` renders 2 equal columns (`1fr 1fr`). |
| **Ultrawide / 4K (`1920px - 2560px+`)** | `main` container constraint | `main` enforces `max-width: 1440px; margin: 0 auto;` centered over `--bg-canvas` so line lengths and table scan paths remain ergonomically bounded. |

### 4.3 Zero Horizontal Page Overflow (`.table-scroll-wrapper`)
* `html, body` enforce `overflow-x: hidden; max-width: 100vw;`.
* Wide tabular views (`#profile-columns-table`, `#profile-corr-table`, `#jobs-table`, and column fidelity tables) are wrapped in `.table-scroll-wrapper` (`width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);`), confining horizontal scrolling strictly to the table container while keeping the page viewport locked.

---

## 5. 5-State Visual Specifications, Accessibility & Motion Rules (`components.css`)

Every interactive panel and data container across Steps 1–5 implements deterministic visual styling for all five operational states (`Empty`, `Loading`, `Nominal`, `Degraded`, `Error`), WCAG 2.2 AA focus visibility, and reduced-motion compliance.

### 5.1 Five-State Component Specifications

1. **State 1: Empty State (`.state-empty`)**:
   * Dashed `1px` border (`border: 1px dashed var(--border-strong)`), recessed `--bg-surface-2` background, centered monospace title and actionable guidance message, plus a direct CTA button (e.g., `[Seed Benchmark Dataset]` or `[Configure Generation Job]`).
2. **State 2: Loading State & Zero-CLS Geometry Skeletons (`.state-loading`, `.skeleton`, `.skeleton-tile`, `.skeleton-row`)**:
   * **Zero Cumulative Layout Shift (`CLS = 0`)**:
     * `.stat-tile` and `.skeleton-tile` enforce `min-height: 84px`.
     * `.skeleton-row` enforces `height: 37px` matching nominal `tr` table rows (`8px` top/bottom padding + `20px` line-height + `1px` border).
     * `.benchmark-card-skeleton` enforces `min-height: 118px` matching seeded benchmark cards.
3. **State 3: Nominal State (`.state-nominal`)**:
   * Populated cards, `tabular-nums` KPI strips, semantic status badges (`.badge-success`, `.badge-info`), and interactive controls.
4. **State 4: Degraded / Compute Tier Fallback Banner (`.state-degraded`, `.degraded-banner`)**:
   * High-contrast amber warning banner (`background: var(--status-warn-bg); color: var(--status-warn-fg); border: 1px solid var(--status-warn-border); border-left: 4px solid var(--status-warn-fg)`) surfaced when `SPARK_LLM_EDGE` (`ComputeTier.GPU_SPARK_WORKER`) trips the `< 2.0s` circuit breaker and falls back to local `ComputeTier.CPU_WORKER`, or when Temporal falls back to the in-process worker loop.
5. **State 5: Error / Privacy Violation Banner (`.state-error`, `.error-banner`)**:
   * High-contrast rose alert banner (`background: var(--status-danger-bg); color: var(--status-danger-fg); border: 1px solid var(--status-danger-border); border-left: 4px solid var(--status-danger-fg)`) with explicit error diagnostics (`role="alert"`) and a recoverable retry/remediation button.

### 5.2 Keyboard Navigation & Focus Visibility
* **Skip Link (`.skip-link`)**: Positioned off-screen by default (`top: -48px`) and slides into the top-left viewport corner (`top: 12px; left: 12px; z-index: 1000`) when focused via `Tab`, allowing keyboard users to bypass `<header>` and `<nav>` directly to `<main id="main-content">`.
* **Focus Ring (`:focus-visible`)**: All interactive elements (`button`, `.nav-tab`, `input`, `select`, `textarea`, `a`, `[tabindex="0"]`) display `outline: 2px solid var(--border-focus); outline-offset: 2px;` on `:focus-visible`.

### 5.3 Canonical `src/synthai_studio/api/static/components.css` Blueprint

```css
/* ==========================================================================
   SynthAI Studio — Component & State Stylesheet (components.css)
   Requires: tokens.css loaded first
   ========================================================================== */

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  background-color: var(--bg-canvas);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: 1.5;
  overflow-x: hidden;
  max-width: 100vw;
  -webkit-font-smoothing: antialiased;
}

/* --------------------------------------------------------------------------
   1. Accessibility: Skip Link & Keyboard Focus Visibility (WCAG 2.2 AA)
   -------------------------------------------------------------------------- */
.skip-link {
  position: absolute;
  top: -48px;
  left: var(--space-3);
  background: var(--accent-primary);
  color: var(--text-on-accent);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 700;
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-sm);
  text-decoration: none;
  z-index: 1000;
  transition: top var(--duration-fast) var(--ease-out-expo);
}

.skip-link:focus,
.skip-link:focus-visible {
  top: var(--space-3);
  outline: 2px solid var(--text-primary);
  outline-offset: 2px;
}

:focus-visible {
  outline: 2px solid var(--border-focus);
  outline-offset: 2px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* --------------------------------------------------------------------------
   2. Strict Tabular-Nums Discipline
   -------------------------------------------------------------------------- */
.tabular-nums,
.stat-val,
.metric-value,
td[data-numeric="true"],
.corr-cell,
.badge-numeric,
input[type="number"],
.log-console {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1, "zero" 1;
}

/* --------------------------------------------------------------------------
   3. Top Application Header & Telemetry Bar
   -------------------------------------------------------------------------- */
header {
  background: var(--bg-surface-1);
  border-bottom: 1px solid var(--border-default);
  padding: 14px var(--space-6);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
}

.brand-title {
  font-family: var(--font-mono);
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--accent-primary);
  letter-spacing: 0.5px;
}

.brand-subtitle {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin-top: 2px;
}

.cluster-status {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}

/* --------------------------------------------------------------------------
   4. Step Navigation Bar (ARIA Tablist Compatible)
   -------------------------------------------------------------------------- */
nav {
  background: var(--bg-surface-1);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  overflow-x: auto;
  padding: 0 var(--space-6);
  gap: var(--space-1);
}

.nav-tab {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  padding: var(--space-3) 18px;
  color: var(--text-muted);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 600;
  white-space: nowrap;
  transition: color var(--duration-fast) var(--ease-out-expo),
              background-color var(--duration-fast) var(--ease-out-expo),
              border-color var(--duration-fast) var(--ease-out-expo);
}

.nav-tab:hover {
  color: var(--text-primary);
  background: var(--bg-surface-2);
}

.nav-tab.active,
.nav-tab[aria-selected="true"] {
  color: var(--accent-primary-hover);
  border-bottom-color: var(--accent-primary);
  background: var(--bg-surface-2);
}

/* --------------------------------------------------------------------------
   5. Workbench Layout & Responsive Grids
   -------------------------------------------------------------------------- */
main {
  padding: var(--space-6);
  max-width: 1440px;
  margin: 0 auto;
}

.step-panel {
  display: none;
}

.step-panel.active {
  display: block;
}

.grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-5);
}

.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-5);
}

.grid-4 {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
}

/* --------------------------------------------------------------------------
   6. Surface Cards, Stat Tiles & Semantic Badges
   -------------------------------------------------------------------------- */
.card {
  background: var(--bg-surface-1);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  margin-bottom: var(--space-5);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-subtle);
}

.card-title {
  font-family: var(--font-mono);
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--text-primary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.stat-tile {
  background: var(--bg-surface-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  text-align: center;
  min-height: 84px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.stat-val {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--accent-primary-hover);
  margin: var(--space-1) 0;
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
}

.badge {
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
  font-weight: 600;
  text-transform: uppercase;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  line-height: 1.4;
}

.badge-success {
  background: var(--status-nominal-bg);
  color: var(--status-nominal-fg);
  border: 1px solid var(--status-nominal-border);
}

.badge-info {
  background: var(--status-info-bg);
  color: var(--status-info-fg);
  border: 1px solid var(--status-info-border);
}

.badge-warn {
  background: var(--status-warn-bg);
  color: var(--status-warn-fg);
  border: 1px solid var(--status-warn-border);
}

.badge-danger {
  background: var(--status-danger-bg);
  color: var(--status-danger-fg);
  border: 1px solid var(--status-danger-border);
}

/* --------------------------------------------------------------------------
   7. Form Controls & Interactive Buttons
   -------------------------------------------------------------------------- */
label {
  display: block;
  font-size: var(--text-sm);
  font-family: var(--font-mono);
  color: var(--text-secondary);
  margin-bottom: 6px;
  text-transform: uppercase;
}

input, select, textarea {
  width: 100%;
  background: var(--bg-surface-2);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 13px;
  margin-bottom: 14px;
  transition: border-color var(--duration-fast) var(--ease-out-expo);
}

input:hover, select:hover, textarea:hover {
  border-color: var(--border-strong);
}

input:focus, select:focus, textarea:focus {
  outline: 2px solid var(--border-focus);
  outline-offset: 1px;
  border-color: var(--border-focus);
}

button.btn {
  background: var(--accent-primary);
  color: var(--text-on-accent);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-4);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 700;
  cursor: pointer;
  text-transform: uppercase;
  transition: background-color var(--duration-fast) var(--ease-out-expo),
              border-color var(--duration-fast) var(--ease-out-expo),
              opacity var(--duration-fast) var(--ease-out-expo);
}

button.btn:hover:not(:disabled) {
  background: var(--accent-primary-hover);
}

button.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

button.btn-emerald {
  background: var(--accent-secondary);
  color: var(--text-on-accent);
}

button.btn-emerald:hover:not(:disabled) {
  background: var(--accent-secondary-hover);
}

button.btn-secondary {
  background: var(--bg-surface-2);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
}

button.btn-secondary:hover:not(:disabled) {
  background: var(--bg-surface-3);
  border-color: var(--border-strong);
}

/* --------------------------------------------------------------------------
   8. Data Tables, Correlation Matrix & Console Logs
   -------------------------------------------------------------------------- */
.table-scroll-wrapper {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
}

table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

th, td {
  padding: var(--space-2) var(--space-3);
  text-align: left;
  border-bottom: 1px solid var(--border-subtle);
}

th {
  background: var(--bg-surface-2);
  color: var(--text-secondary);
  text-transform: uppercase;
  font-weight: 600;
  border-bottom: 1px solid var(--border-default);
  white-space: nowrap;
}

td[data-numeric="true"],
th[data-numeric="true"],
.corr-cell {
  text-align: right;
}

tbody tr:hover {
  background: var(--bg-surface-2);
}

pre {
  background: var(--bg-surface-2);
  border: 1px solid var(--border-default);
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--status-info-fg);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-console {
  background: var(--bg-console);
  border: 1px solid var(--border-default);
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--status-nominal-fg);
  max-height: 220px;
  overflow-y: auto;
}

/* --------------------------------------------------------------------------
   9. 5-State Determinism: Empty, Loading (CLS=0), Degraded, Error
   -------------------------------------------------------------------------- */
.state-empty {
  background: var(--bg-surface-2);
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  text-align: center;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

@keyframes synthai-shimmer {
  0% { opacity: 0.45; }
  50% { opacity: 0.85; }
  100% { opacity: 0.45; }
}

.skeleton,
.skeleton-tile,
.skeleton-row {
  background: var(--bg-surface-2);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  animation: synthai-shimmer 1.5s ease-in-out infinite;
}

.skeleton-tile {
  min-height: 84px;
}

.skeleton-row {
  height: 37px;
  margin-bottom: var(--space-1);
}

.degraded-banner,
.state-degraded {
  background: var(--status-warn-bg);
  color: var(--status-warn-fg);
  border: 1px solid var(--status-warn-border);
  border-left: 4px solid var(--status-warn-fg);
  border-radius: var(--radius-sm);
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-4);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
}

.error-banner,
.state-error {
  background: var(--status-danger-bg);
  color: var(--status-danger-fg);
  border: 1px solid var(--status-danger-border);
  border-left: 4px solid var(--status-danger-fg);
  border-radius: var(--radius-sm);
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-4);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
}

/* --------------------------------------------------------------------------
   10. Motion & Reduced-Motion Compliance
   -------------------------------------------------------------------------- */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }

  .skeleton,
  .skeleton-tile,
  .skeleton-row {
    animation: none !important;
    opacity: 0.7;
  }
}

/* --------------------------------------------------------------------------
   11. Responsive Breakpoints (375px Mobile -> 768px Tablet -> 2560px 4K)
   -------------------------------------------------------------------------- */
@media (max-width: 1199px) {
  .grid-4 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  header {
    flex-direction: column;
    align-items: flex-start;
    padding: var(--space-3) var(--space-4);
  }

  nav {
    padding: 0 var(--space-3);
  }

  main {
    padding: var(--space-4);
  }

  .grid-2,
  .grid-3,
  .grid-4 {
    grid-template-columns: 1fr;
  }

  .card {
    padding: var(--space-4);
  }
}
```
