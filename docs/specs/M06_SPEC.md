# Milestone 06 Specification (`M06_SPEC.md`) — Design Tokens & Component CSS

## 1. Objective
Create the modular CSS design token architecture (`src/synthai_studio/api/static/tokens.css`), the 5-state component and responsive layout stylesheet (`src/synthai_studio/api/static/components.css`), and the deterministic asset contract test suite (`tests/test_ui_assets.py`) in accordance with `docs/DESIGN_SYSTEM.md` and `docs/UX_SPEC.md`.

## 2. Target Files (2 Asset Files + 1 Test File)
1. `src/synthai_studio/api/static/tokens.css`
2. `src/synthai_studio/api/static/components.css`
3. `tests/test_ui_assets.py`

## 3. Design-by-Contract Specifications

### 3.1 `src/synthai_studio/api/static/tokens.css`
- **Pre-conditions**: Loaded before `components.css` in `index.html`.
- **Post-conditions**:
  - Declares `:root` CSS custom properties with zero emojis:
    - **4-Tier Dark Surface Elevation**:
      - `--bg-canvas: #070a12;`
      - `--bg-surface-1: #0e1422;`
      - `--bg-surface-2: #151e31;`
      - `--bg-surface-3: #1e2b45;`
      - `--bg-console: #04070e;`
    - **Structural Hairlines & Focus Ring**:
      - `--border-subtle: #1e293b;`
      - `--border-default: #283750;`
      - `--border-strong: #3b5278;`
      - `--border-focus: #22d3ee;`
    - **Typography & WCAG 2.2 AA Contrast Ink (`>= 4.5:1`)**:
      - `--text-primary: #f8fafc;`
      - `--text-secondary: #cbd5e1;`
      - `--text-muted: #94a3b8;`
      - `--text-on-accent: #041019;`
    - **Brand Accents**:
      - `--accent-primary: #06b6d4;`
      - `--accent-primary-hover: #22d3ee;`
      - `--accent-secondary: #10b981;`
      - `--accent-secondary-hover: #34d399;`
    - **Semantic Status & Privacy Risk Tokens**:
      - `--status-nominal-bg: #052e24;`
      - `--status-nominal-fg: #34d399;`
      - `--status-nominal-border: #059669;`
      - `--status-info-bg: #082f49;`
      - `--status-info-fg: #38bdf8;`
      - `--status-info-border: #0284c7;`
      - `--status-warn-bg: #451a03;`
      - `--status-warn-fg: #fbbf24;`
      - `--status-warn-border: #d97706;`
      - `--status-danger-bg: #4c0519;`
      - `--status-danger-fg: #fb7185;`
      - `--status-danger-border: #e11d48;`
    - **Typography & Spacing Rhythm (`4px` / `8px`)**:
      - `--font-sans: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;`
      - `--font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;`
      - `--text-xs: 0.6875rem;`, `--text-sm: 0.75rem;`, `--text-base: 0.875rem;`, `--text-lg: 1rem;`, `--text-xl: 1.375rem;`
      - `--space-1: 0.25rem;`, `--space-2: 0.5rem;`, `--space-3: 0.75rem;`, `--space-4: 1rem;`, `--space-5: 1.25rem;`, `--space-6: 1.5rem;`, `--space-7: 2rem;`, `--space-8: 2.5rem;`
      - `--radius-sm: 4px;`, `--radius-md: 6px;`, `--radius-lg: 8px;`
      - `--ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);`, `--duration-fast: 140ms;`
    - **Backward-Compatible Aliases**:
      - `--bg-dark: var(--bg-canvas);`
      - `--bg-panel: var(--bg-surface-1);`
      - `--bg-card: var(--bg-surface-2);`
      - `--bg-hover: var(--bg-surface-3);`
      - `--border-color: var(--border-default);`
      - `--text-main: var(--text-primary);`
      - `--accent-cyan: var(--accent-primary);`
      - `--accent-emerald: var(--accent-secondary);`
      - `--accent-blue: var(--status-info-fg);`
      - `--accent-amber: var(--status-warn-fg);`
      - `--accent-rose: var(--status-danger-fg);`

### 3.2 `src/synthai_studio/api/static/components.css`
- **Pre-conditions**: Consumes CSS custom properties from `tokens.css` (zero hardcoded hex colors in `components.css`).
- **Post-conditions**:
  - Implements:
    1. Accessibility & Focus: `.skip-link`, `.skip-link:focus`, `.skip-link:focus-visible`, `:focus-visible` (`outline: 2px solid var(--border-focus); outline-offset: 2px;`), `.sr-only`.
    2. Strict `tabular-nums`: `.tabular-nums`, `.stat-val`, `.metric-value`, `td[data-numeric="true"]`, `.corr-cell`, `.badge-numeric`, `input[type="number"]`, `.log-console` with `font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1, "zero" 1;`.
    3. Layout & Landmarks: `header`, `.brand-title`, `.brand-subtitle`, `.cluster-status`, `nav`, `#workflow-tablist`, `.nav-tab`, `.nav-tab.active`, `.nav-tab[aria-selected="true"]`, `main`, `.step-panel`, `.step-panel.active`, `.grid-2`, `.grid-3`, `.grid-4`, `.table-scroll-wrapper`.
    4. Cards, Tiles, Forms, Buttons & Badges: `.card`, `.card-header`, `.card-title`, `.stat-tile` (`min-height: 84px`), `.stat-val`, `.stat-label`, `.badge`, `.badge-success`, `.badge-info`, `.badge-warn`, `.badge-danger`, `label`, `input`, `select`, `textarea`, `button.btn`, `button.btn-emerald`, `button.btn-secondary`, `.benchmark-card`, `.issue-item`.
    5. 5-State Determinism Classes:
       - `.state-empty`
       - `.state-loading`, `.skeleton`, `.skeleton-tile` (`min-height: 84px`), `.skeleton-row` (`height: 37px`), `.skeleton-card` (`min-height: 136px`)
       - `.state-nominal`
       - `.state-degraded`, `.degraded-banner`
       - `.state-error`, `.error-banner`
    6. Motion & Responsive Media Queries:
       - `@media (prefers-reduced-motion: reduce)`
       - `@media (max-width: 1199px)`
       - `@media (max-width: 767px)`

### 3.3 `tests/test_ui_assets.py`
- **Pre-conditions**: `tokens.css` and `components.css` exist under `src/synthai_studio/api/static/`.
- **Post-conditions**:
  - Every test function and helper includes structured `Pre-conditions:` and `Post-conditions:` docstrings and full Python type annotations.
  - Verifies:
    - `tokens.css` exists, is non-empty, contains all 4 surface elevation tokens (`--bg-canvas`, `--bg-surface-1`, `--bg-surface-2`, `--bg-surface-3`), border tokens, semantic status tokens (`--status-nominal-*`, `--status-info-*`, `--status-warn-*`, `--status-danger-*`), font tokens (`--font-sans`, `--font-mono`), spacing tokens (`--space-1`..`--space-8`), and legacy aliases.
    - WCAG 2.2 AA contrast ratio calculation in Python (relative luminance formula per WCAG 2.2) confirming `--text-primary`, `--text-secondary`, `--text-muted` on `--bg-canvas`, `--bg-surface-1`, and `--bg-surface-2`, `--text-on-accent` on `--accent-primary` and `--accent-secondary`, and all 4 `--status-*-fg` on `--status-*-bg` meet `>= 4.5:1` contrast.
    - `components.css` exists, contains zero raw hex color literals (`#[0-9a-fA-F]{3,8}`), enforces `font-variant-numeric: tabular-nums`, defines all 5 state classes (`.state-empty`, `.state-loading`, `.state-nominal`, `.state-degraded`, `.state-error`), zero-CLS skeleton classes (`.skeleton-tile`, `.skeleton-row`), accessibility rules (`.skip-link`, `:focus-visible`, `.sr-only`), `@media (prefers-reduced-motion: reduce)`, and responsive breakpoints.

## 4. Verification Command
```bash
poetry run ruff check tests/test_ui_assets.py && poetry run mypy tests/test_ui_assets.py && poetry run pytest tests/test_ui_assets.py -v
```
