# Milestone 3 Specification (`M3_SPEC.md`): Multi-Engine Synthesizer, Differential Privacy Mechanism & DGX Spark Edge Synthesizer

## 1. Objective

Implement the multi-engine tabular synthesizer suite (`GAUSSIAN_COPULA`, `CTGAN_LATENT`, `FAKER_HYBRID`, `SPARK_LLM_EDGE`), the formal $(\epsilon, \delta)$-Differential Privacy accountant (`DifferentialPrivacyAccountant`), and the declarative conditional filter & minority-class upsampler in `src/synthai_studio/synthesizer.py`, verified by `tests/test_synthesizer.py`.

---

## 2. Non-Negotiable Engineering Invariants

1. **Absolute Imports Only**: Use `from synthai_studio...` exclusively. Zero relative imports.
2. **Design by Contract (DbC)**: Every public class, method, and function MUST include a docstring with explicit `Pre-conditions:` and `Post-conditions:` sections.
3. **Zero Emojis**: Do not include any emoji characters in source code, docstrings, or tests.
4. **Strict Static Typing**: `poetry run ruff check .` and `poetry run mypy src tests` must pass cleanly.

---

## 3. Target Files & Public Contracts

### 3.1 `src/synthai_studio/synthesizer.py`

Expose the following public classes and functions:

1. `class DifferentialPrivacyAccountant`
   - `__init__(self, privacy_level: PrivacyLevel, epsilon: float | None = None, delta: float = 1e-5, seed: int = 42) -> None`
   - `perturb_quantiles(self, quantiles: np.ndarray, col_min: float, col_max: float, n_rows: int) -> np.ndarray`:
     - When `privacy_level == PrivacyLevel.NONE` or `resolved_epsilon is None`, returns `quantiles.copy()`.
     - Otherwise injects calibrated Laplace noise $\text{Lap}(b)$ where $b = \frac{\max(10^{-6}, \text{col\_max} - \text{col\_min})}{\max(1, n_{\text{rows}}) \cdot (0.45 \cdot \epsilon)}$, clips to `[col_min, col_max]` (with a tiny margin), and applies monotonic non-decreasing sorting (`np.maximum.accumulate` or `np.sort`).
   - `perturb_category_probabilities(self, counts: np.ndarray) -> np.ndarray`:
     - Injects Laplace noise with scale $b = \frac{1.0}{0.30 \cdot \epsilon}$ into raw category counts, clips at `1e-6`, and normalizes to sum to `1.0`.
   - `perturb_correlation_matrix(self, corr: np.ndarray, n_rows: int) -> np.ndarray`:
     - Injects symmetric Gaussian noise $\mathcal{N}(0, \sigma^2)$ with $\sigma = \frac{2.0 \sqrt{2 \ln(1.25 / \delta)}}{\max(10, n_{\text{rows}}) \cdot (0.25 \cdot \epsilon)}$ into off-diagonal entries of `corr` and projects onto the cone of symmetric Positive Semi-Definite (PSD) correlation matrices via `project_to_psd_correlation(matrix)`.
   - `build_ledger(self) -> PrivacyBudgetLedger`:
     - Returns a `PrivacyBudgetLedger` recording `privacy_level`, `epsilon_spent`, `delta`, `mechanism` (`"Laplace+Gaussian-Analytic"` or `"None (Unperturbed Empirical)"`), `noise_scale`, and `psd_projection_applied=True`.

2. `project_to_psd_correlation(matrix: np.ndarray, min_eigenvalue: float = 1e-5) -> np.ndarray`
   - **Pre-conditions**: `matrix` is a 2D square numeric NumPy array.
   - **Post-conditions**: Symmetrizes `matrix`, performs eigenvalue decomposition (`np.linalg.eigh`), floors eigenvalues at `min_eigenvalue`, reconstructs $A = V \text{diag}(\lambda) V^\top$, normalizes diagonal entries to `1.0`, and clamps off-diagonals to `[-0.9999, 0.9999]`. Guaranteed Cholesky-factorizable.

3. `generate_synthetic_pii_value(pii_type: PIIType, row_index: int, rng: np.random.Generator) -> str`
   - **Pre-conditions**: `row_index >= 0`.
   - **Post-conditions**: Deterministically generates realistic, non-colliding synthetic PII values (`EMAIL`, `SSN`, `PHONE`, `CREDIT_CARD`, `MEDICAL_RECORD_NUMBER`, `PERSON_NAME`, `IP_ADDRESS`) that never match real dataset records.

4. `class GaussianCopulaSynthesizer`
   - Fits empirical quantile knots (21 knots from $p=0.0$ to $p=1.0$) for numerical/datetime columns and empirical probability tables for categorical/boolean columns, perturbed via `DifferentialPrivacyAccountant`.
   - Estimates the rank correlation matrix across all non-PII columns, projects to PSD via `project_to_psd_correlation`, computes Cholesky factor $L = \text{cholesky}(\Sigma)$, draws $Z = X L^\top$, maps $U = \Phi(Z) = \frac{1}{2}\left(1 + \text{erf}\left(\frac{Z}{\sqrt{2}}\right)\right)$, and inverts numerical quantiles via `np.interp` and categorical cumulative probabilities via `np.searchsorted`.
   - Preserves integer vs float formatting, boolean types, and ISO date/datetime string formatting.

5. `class CTGANLatentSynthesizer`
   - Fits a 3-mode Gaussian Mixture representation $(\mu_k, \sigma_k, \pi_k)$ per numerical column alongside conditional categorical mode transition matrices and latent correlation coupling, honoring `DifferentialPrivacyAccountant` noise injection.

6. `class FakerHybridSynthesizer`
   - Combines semantic locale-aware synthetic PII generation for `IDENTIFIER_PII` columns with `GaussianCopulaSynthesizer` for correlated numerical, categorical, and datetime features.

7. `class SparkLLMEdgeSynthesizer`
   - Targets `SPARK_LLM_BASE_URL` (default `"http://happy.tail749110.ts.net:8000/v1"`, model `"nvidia/Qwen3.8-Flash-Next-FP4-Local"`) with a strict `< 2.0s` HTTP timeout (`connect=1.5`, `read=2.0`).
   - Provides `probe_spark_endpoint(base_url: str | None = None, timeout_sec: float = 1.8) -> bool` and `synthesize_with_spark_or_fallback(...)`.
   - If `SPARK_LLM_ENABLED` is not `"true"` in environment or the `< 2.0s` probe/call fails, falls back immediately without retry to `CTGANLatentSynthesizer` / `GaussianCopulaSynthesizer` edge-boosted synthesis and returns `(rows, ComputeTier.CPU_WORKER)`. When Spark responds with valid JSON edge cases, blends them and returns `ComputeTier.GPU_SPARK_WORKER`.

8. `apply_conditions_and_upsampling(real_rows: list[dict[str, Any]], config: SynthesisConfig, synthesize_fn: Callable[[list[dict[str, Any]], int, int], list[dict[str, Any]]]) -> list[dict[str, Any]]`
   - Handles `config.upsample_config` (fitting separate conditional models on minority vs majority subsets of `real_rows` so the output matches `target_ratio` for `minority_value`) and `config.conditions` (`EQ`, `NEQ`, `GT`, `GTE`, `LT`, `LTE`, `IN`), clamping/filtering or projecting generated rows so 100% of returned `target_rows` satisfy all `ConditionRule` constraints.

9. `synthesize_dataset(real_rows: list[dict[str, Any]], config: SynthesisConfig, profile: DatasetProfileReport | None = None) -> tuple[list[dict[str, Any]], PrivacyBudgetLedger, ComputeTier]`
   - **Pre-conditions**: `real_rows` is non-empty; `config.target_rows >= 10`.
   - **Post-conditions**: Executes the selected `config.engine`, applies DP noise according to `config.privacy_level`, enforces `config.upsample_config` and `config.conditions`, replaces PII when `config.anonymize_pii=True`, and returns `(synthetic_rows, privacy_ledger, compute_tier)` with `len(synthetic_rows) == config.target_rows`.

---

### 3.2 `tests/test_synthesizer.py`
Write comprehensive unit tests verifying:
- `project_to_psd_correlation` repairs non-PSD matrices with negative eigenvalues into valid Cholesky-factorizable correlation matrices.
- `DifferentialPrivacyAccountant` produces zero noise for `PrivacyLevel.NONE` and monotonically increasing `noise_scale` from `LOW` ($\epsilon=10.0$) to `MEDIUM` ($\epsilon=1.0$) to `HIGH` ($\epsilon=0.1$).
- `synthesize_dataset` succeeds across all 4 engines (`GAUSSIAN_COPULA`, `CTGAN_LATENT`, `FAKER_HYBRID`, `SPARK_LLM_EDGE` with mocked HTTP both succeeding and failing/timing out to verify the `< 2.0s` circuit breaker).
- Minority class upsampling (`upsample_config`) achieves the requested minority ratio within tolerance.
- Declarative `ConditionRule` constraints (`GTE`, `LTE`, `EQ`, `IN`, `NEQ`) are 100% satisfied on all generated rows.
- Synthetic PII values have zero overlap with raw real PII values when `anonymize_pii=True`.
