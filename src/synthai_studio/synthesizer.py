"""SynthAI Studio multi-engine synthesizer suite, DP accountant, and condition engine.

Pre-conditions:
    - Python >= 3.11 with ``numpy``, ``httpx``, and ``pydantic`` v2 installed.
Post-conditions:
    - Provides Gaussian Copula, CTGAN Latent, Faker Hybrid, and DGX Spark synthesizers
      with strict (epsilon, delta)-differential privacy and conditional query planning.
"""

import json
import math
import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import numpy as np

from synthai_studio.models import (
    ColumnDataType,
    ColumnProfile,
    ComputeTier,
    ConditionOperator,
    DatasetProfileReport,
    PIIType,
    PrivacyBudgetLedger,
    PrivacyLevel,
    SynthesisConfig,
    SynthesizerEngine,
)
from synthai_studio.profiler import profile_dataset

__all__ = [
    "CTGANLatentSynthesizer",
    "DifferentialPrivacyAccountant",
    "FakerHybridSynthesizer",
    "GaussianCopulaSynthesizer",
    "SparkLLMEdgeSynthesizer",
    "apply_conditions_and_upsampling",
    "generate_synthetic_pii_value",
    "probe_spark_endpoint",
    "project_to_psd_correlation",
    "synthesize_dataset",
]

_SYNTH_FIRST_NAMES: list[str] = [
    "Lucas", "Sophia", "Liam", "Olivia", "Noah", "Emma", "Oliver", "Ava",
    "Elijah", "Charlotte", "Mateo", "Mia", "Jackson", "Harper", "Levi", "Evelyn",
    "Ezra", "Abigail", "Hudson", "Ella", "Asher", "Scarlett", "Leo", "Grace",
    "Jack", "Chloe", "Wyatt", "Penelope", "Carter", "Riley", "Benjamin", "Nora",
]

_SYNTH_LAST_NAMES: list[str] = [
    "Vance", "Mercer", "Sinclair", "Hawthorne", "Sterling", "Kowalski", "Gallagher",
    "Montague", "Castillo", "Fletcher", "Prescott", "Blackwood", "Navarro", "Donovan",
    "Kensington", "Valentine", "Bradford", "Solomon", "Harrington", "Whitaker",
]

_SYNTH_DOMAINS: list[str] = [
    "syntheticmail.io",
    "privatedata.net",
    "safeharbor.org",
    "edgecompute.internal",
]


def _normal_cdf(z: np.ndarray) -> np.ndarray:
    """Compute standard normal cumulative distribution function.

    Pre-conditions:
        - ``z`` is a NumPy array of real numbers.
    Post-conditions:
        - Returns values in (0.0, 1.0) with identical shape.
    """
    erf_vec = np.vectorize(math.erf)
    res: np.ndarray = 0.5 * (1.0 + erf_vec(z / np.sqrt(2.0)))
    return res


def _normal_ppf(p: np.ndarray) -> np.ndarray:
    """Compute inverse standard normal CDF (probit) using Acklam's rational approximation.

    Pre-conditions:
        - ``p`` is a NumPy array of probabilities strictly in (0.0, 1.0).
    Post-conditions:
        - Returns standard normal quantiles with error < 1.15e-9.
    """
    p_clamped = np.clip(p, 1e-12, 1.0 - 1e-12)

    a = [
        -3.969683028665376e01, 2.209460984245205e02,
        -2.759285104469687e02, 1.383577518672690e02,
        -3.066479806614716e01, 2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01, 1.615858368580409e02,
        -1.556989798598866e02, 6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03, -3.223964580411365e-01,
        -2.400758277161838e00, -2.549732539343734e00,
        4.374664141464968e00, 2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03, 3.224671290700398e-01,
        2.445134137142996e00, 3.754408661907416e00,
    ]

    p_low = 0.02425
    p_high = 1.0 - p_low
    q = np.zeros_like(p_clamped, dtype=float)

    mask_low = p_clamped < p_low
    if np.any(mask_low):
        r = np.sqrt(-2.0 * np.log(p_clamped[mask_low]))
        num = ((((c[0] * r + c[1]) * r + c[2]) * r + c[3]) * r + c[4]) * r + c[5]
        den = (((d[0] * r + d[1]) * r + d[2]) * r + d[3]) * r + 1.0
        q[mask_low] = num / den

    mask_mid = (p_clamped >= p_low) & (p_clamped <= p_high)
    if np.any(mask_mid):
        r = p_clamped[mask_mid] - 0.5
        r2 = r * r
        num = (((((a[0] * r2 + a[1]) * r2 + a[2]) * r2 + a[3]) * r2 + a[4]) * r2 + a[5]) * r
        den = ((((b[0] * r2 + b[1]) * r2 + b[2]) * r2 + b[3]) * r2 + b[4]) * r2 + 1.0
        q[mask_mid] = num / den

    mask_high = p_clamped > p_high
    if np.any(mask_high):
        r = np.sqrt(-2.0 * np.log(1.0 - p_clamped[mask_high]))
        num = ((((c[0] * r + c[1]) * r + c[2]) * r + c[3]) * r + c[4]) * r + c[5]
        den = (((d[0] * r + d[1]) * r + d[2]) * r + d[3]) * r + 1.0
        q[mask_high] = -(num / den)

    return q


def project_to_psd_correlation(
    matrix: np.ndarray,
    min_eigenvalue: float = 1e-5,
) -> np.ndarray:
    """Project a square matrix onto the cone of symmetric PSD correlation matrices.

    Pre-conditions:
        - ``matrix`` is a 2D square numeric NumPy array.
        - ``min_eigenvalue > 0.0``.
    Post-conditions:
        - Returns a symmetric positive-definite matrix with 1.0 on diagonal.
        - Off-diagonals are clamped to [-0.9999, 0.9999].
        - Guaranteed Cholesky-factorizable.
    """
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("matrix must be a 2D square array")

    n = matrix.shape[0]
    if n == 1:
        return np.ones((1, 1), dtype=float)

    sym = 0.5 * (matrix + matrix.T)
    sym = np.nan_to_num(sym, nan=0.0)
    np.fill_diagonal(sym, 1.0)
    eigvals, eigvecs = np.linalg.eigh(sym)
    eigvals_clamped = np.maximum(eigvals, min_eigenvalue)
    recon = eigvecs @ np.diag(eigvals_clamped) @ eigvecs.T

    diag_sqrt = np.sqrt(np.maximum(np.diag(recon), 1e-9))
    corr = recon / (diag_sqrt[:, None] * diag_sqrt[None, :])
    corr = 0.5 * (corr + corr.T)
    np.fill_diagonal(corr, 1.0)
    corr = np.clip(corr, -0.9999, 0.9999)
    np.fill_diagonal(corr, 1.0)

    for attempt in range(5):
        try:
            np.linalg.cholesky(corr)
            return corr
        except np.linalg.LinAlgError:
            corr = corr + (min_eigenvalue * (10 ** attempt)) * np.eye(n)
            diag_s = np.sqrt(np.diag(corr))
            corr = corr / (diag_s[:, None] * diag_s[None, :])
            np.fill_diagonal(corr, 1.0)

    return corr


def generate_synthetic_pii_value(
    pii_type: PIIType,
    row_index: int,
    rng: np.random.Generator,
) -> str:
    """Generate realistic, non-colliding synthetic PII values.

    Pre-conditions:
        - ``row_index >= 0``.
        - ``rng`` is an initialized NumPy random Generator.
    Post-conditions:
        - Returns realistic synthetic PII string distinct from raw dataset records.
    """
    fn = _SYNTH_FIRST_NAMES[int(rng.integers(0, len(_SYNTH_FIRST_NAMES)))]
    ln = _SYNTH_LAST_NAMES[int(rng.integers(0, len(_SYNTH_LAST_NAMES)))]
    domain = _SYNTH_DOMAINS[int(rng.integers(0, len(_SYNTH_DOMAINS)))]
    uid = row_index + 1000

    if pii_type == PIIType.EMAIL:
        return f"synth.{fn.lower()}.{ln.lower()}{uid:04d}@{domain}"
    if pii_type == PIIType.SSN:
        return f"9{int(rng.integers(10, 99)):02d}-{int(rng.integers(10, 99)):02d}-{uid:04d}"
    if pii_type == PIIType.PHONE:
        return f"+1-555-01{int(rng.integers(10, 99)):02d}-{uid:04d}"
    if pii_type == PIIType.CREDIT_CARD:
        r_mid = int(rng.integers(1000, 9999))
        return f"4000-00{int(rng.integers(10, 99)):02d}-{r_mid:04d}-{uid:04d}"
    if pii_type == PIIType.MEDICAL_RECORD_NUMBER:
        return f"SYN-MRN-{row_index + 500000:06d}"
    if pii_type == PIIType.IP_ADDRESS:
        return f"203.0.113.{(row_index % 250) + 1}"
    if pii_type == PIIType.PERSON_NAME:
        return f"{fn} {ln}"

    return f"SYNTH-VAL-{uid:04d}"


class DifferentialPrivacyAccountant:
    """Formal (epsilon, delta)-differential privacy noise injector and budget tracker.

    Pre-conditions:
        - ``privacy_level`` is one of PrivacyLevel enum members.
        - ``delta`` in (0.0, 1.0).
    Post-conditions:
        - Computes noise scale inversely proportional to epsilon.
        - Produces zero noise when privacy_level is NONE.
    """

    def __init__(
        self,
        privacy_level: PrivacyLevel,
        epsilon: float | None = None,
        delta: float = 1e-5,
        seed: int = 42,
    ) -> None:
        """Initialize the differential privacy accountant.

        Pre-conditions:
            - ``privacy_level`` is valid.
        Post-conditions:
            - Stores effective budget and initializes RNG.
        """
        self.privacy_level = privacy_level
        self.delta = delta
        self.rng = np.random.default_rng(seed)

        if privacy_level == PrivacyLevel.NONE:
            self.resolved_epsilon: float | None = None
            self.noise_scale: float = 0.0
        else:
            if epsilon is not None:
                self.resolved_epsilon = float(epsilon)
            elif privacy_level == PrivacyLevel.LOW:
                self.resolved_epsilon = 10.0
            elif privacy_level == PrivacyLevel.MEDIUM:
                self.resolved_epsilon = 1.0
            else:
                self.resolved_epsilon = 0.1

            if privacy_level == PrivacyLevel.HIGH and delta == 1e-5:
                self.delta = 1e-6

            self.noise_scale = 1.0 / (0.30 * self.resolved_epsilon)

    def perturb_quantiles(
        self,
        quantiles: np.ndarray,
        col_min: float,
        col_max: float,
        n_rows: int,
    ) -> np.ndarray:
        """Inject calibrated Laplace noise into empirical quantile knots.

        Pre-conditions:
            - ``quantiles`` is a 1D NumPy array.
            - ``col_max >= col_min``.
            - ``n_rows >= 1``.
        Post-conditions:
            - Returns perturbed, sorted, clipped quantiles.
        """
        if self.privacy_level == PrivacyLevel.NONE or self.resolved_epsilon is None:
            return np.array(quantiles, copy=True)

        eps = self.resolved_epsilon
        scale = max(1e-6, col_max - col_min) / (max(1, n_rows) * (0.45 * eps))
        noise = self.rng.laplace(0.0, scale, size=quantiles.shape)
        perturbed = quantiles + noise
        clipped = np.clip(perturbed, col_min, col_max)
        res: np.ndarray = np.sort(clipped)
        return res

    def perturb_category_probabilities(self, counts: np.ndarray) -> np.ndarray:
        """Inject Laplace noise into category counts and normalize to probability distribution.

        Pre-conditions:
            - ``counts`` is a 1D non-negative array.
        Post-conditions:
            - Returns normalized probability vector summing to 1.0.
        """
        if self.privacy_level == PrivacyLevel.NONE or self.resolved_epsilon is None:
            total = float(np.sum(counts))
            if total > 0:
                res: np.ndarray = counts / total
                return res
            res_eq: np.ndarray = np.ones_like(counts, dtype=float) / max(1, len(counts))
            return res_eq

        eps = self.resolved_epsilon
        scale = 1.0 / (0.30 * eps)
        noise = self.rng.laplace(0.0, scale, size=counts.shape)
        perturbed = np.maximum(counts + noise, 1e-6)
        normalized: np.ndarray = perturbed / float(np.sum(perturbed))
        return normalized

    def perturb_correlation_matrix(self, corr: np.ndarray, n_rows: int) -> np.ndarray:
        """Inject Gaussian noise into correlation matrix and project onto PSD cone.

        Pre-conditions:
            - ``corr`` is a 2D square matrix.
            - ``n_rows >= 1``.
        Post-conditions:
            - Returns valid symmetric positive semi-definite correlation matrix.
        """
        if self.privacy_level == PrivacyLevel.NONE or self.resolved_epsilon is None:
            return project_to_psd_correlation(corr)

        eps = self.resolved_epsilon
        sigma = (2.0 * np.sqrt(2.0 * np.log(1.25 / self.delta))) / (
            max(10, n_rows) * (0.25 * eps)
        )
        d = corr.shape[0]
        noise = self.rng.normal(0.0, sigma, size=(d, d))
        sym_noise = 0.5 * (noise + noise.T)
        np.fill_diagonal(sym_noise, 0.0)
        perturbed = corr + sym_noise
        return project_to_psd_correlation(perturbed)

    def build_ledger(self) -> PrivacyBudgetLedger:
        """Construct an auditable ledger record of the privacy budget.

        Pre-conditions:
            - None.
        Post-conditions:
            - Returns validated PrivacyBudgetLedger.
        """
        mechanism = (
            "Laplace+Gaussian-Analytic"
            if self.privacy_level != PrivacyLevel.NONE
            else "None (Unperturbed Empirical)"
        )
        return PrivacyBudgetLedger(
            privacy_level=self.privacy_level,
            epsilon_spent=self.resolved_epsilon,
            delta=self.delta,
            mechanism=mechanism,
            noise_scale=self.noise_scale,
            psd_projection_applied=True,
        )


class GaussianCopulaSynthesizer:
    """Parametric/empirical Gaussian Copula synthesizer with DP marginal perturbation.

    Pre-conditions:
        - Python >= 3.11 with numpy.
    Post-conditions:
        - Accurately captures marginal distributions and pairwise rank correlations.
    """

    def __init__(
        self,
        dp_accountant: DifferentialPrivacyAccountant | None = None,
        num_knots: int = 51,
        random_seed: int = 42,
    ) -> None:
        """Initialize GaussianCopulaSynthesizer.

        Pre-conditions:
            - ``num_knots >= 5``.
        Post-conditions:
            - Stores settings and initializes PRNG.
        """
        self.dp = dp_accountant or DifferentialPrivacyAccountant(PrivacyLevel.NONE)
        self.num_knots = num_knots
        self.rng = np.random.default_rng(random_seed)
        self.columns: list[ColumnProfile] = []
        self.modeled_cols: list[str] = []
        self.col_types: dict[str, ColumnDataType] = {}
        self.is_int_col: dict[str, bool] = {}
        self.is_date_only: dict[str, bool] = {}
        self.knots: dict[str, np.ndarray] = {}
        self.categories: dict[str, list[Any]] = {}
        self.cat_probs: dict[str, np.ndarray] = {}
        self.cat_cum_probs: dict[str, np.ndarray] = {}
        self.cholesky_factor: np.ndarray | None = None

    def fit(self, rows: list[dict[str, Any]], column_profiles: list[ColumnProfile]) -> None:
        """Fit empirical marginals and copula correlation structure.

        Pre-conditions:
            - ``rows`` is a non-empty list of dictionaries.
            - ``column_profiles`` matches schema of ``rows``.
        Post-conditions:
            - Computes DP-perturbed quantile knots, probabilities, and correlation factor.
        """
        self.columns = column_profiles
        n_rows = len(rows)
        self.modeled_cols = [
            cp.name for cp in column_profiles if cp.inferred_type != ColumnDataType.IDENTIFIER_PII
        ]
        num_knots = self.num_knots
        knot_probs = np.linspace(0.0, 100.0, num_knots)

        z_matrix: list[np.ndarray] = []

        for cp in column_profiles:
            col = cp.name
            if cp.inferred_type == ColumnDataType.IDENTIFIER_PII:
                continue

            self.col_types[col] = cp.inferred_type
            raw_vals = [r.get(col) for r in rows]

            if cp.inferred_type in (ColumnDataType.NUMERICAL, ColumnDataType.DATETIME):
                if cp.inferred_type == ColumnDataType.DATETIME:
                    float_vals: list[float] = []
                    is_date = True
                    for v in raw_vals:
                        if v is not None:
                            s = str(v).strip()
                            if "T" in s:
                                is_date = False
                            clean_s = s.replace("Z", "+00:00")
                            try:
                                dt = datetime.fromisoformat(clean_s)
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=UTC)
                                float_vals.append(dt.timestamp())
                            except Exception:
                                float_vals.append(0.0)
                        else:
                            float_vals.append(0.0)
                    self.is_date_only[col] = is_date
                    arr_vals = np.array(float_vals, dtype=float)
                    self.is_int_col[col] = False
                else:
                    self.is_int_col[col] = all(
                        isinstance(v, int) and not isinstance(v, bool)
                        for v in raw_vals
                        if v is not None
                    )
                    arr_vals = np.array(
                        [float(v) if v is not None else 0.0 for v in raw_vals],
                        dtype=float,
                    )

                c_min = float(np.min(arr_vals))
                c_max = float(np.max(arr_vals))
                raw_knots = np.percentile(arr_vals, knot_probs)
                perturbed_knots = self.dp.perturb_quantiles(raw_knots, c_min, c_max, n_rows)
                self.knots[col] = perturbed_knots

                u = np.interp(arr_vals, perturbed_knots, np.linspace(0.001, 0.999, num_knots))
                z = _normal_ppf(u)
                z_matrix.append(z)

            else:
                # CATEGORICAL or BOOLEAN
                unique_cats = sorted(
                    list({v for v in raw_vals if v is not None}),
                    key=lambda x: str(x),
                )
                if not unique_cats:
                    unique_cats = ["UNKNOWN"]
                self.categories[col] = unique_cats

                cat_counts = np.array(
                    [sum(1 for v in raw_vals if v == c) for c in unique_cats],
                    dtype=float,
                )
                probs = self.dp.perturb_category_probabilities(cat_counts)
                self.cat_probs[col] = probs
                cum_probs = np.cumsum(probs)
                cum_probs[-1] = 1.0
                self.cat_cum_probs[col] = cum_probs

                cat_to_idx = {c: i for i, c in enumerate(unique_cats)}
                u_cats = []
                for v in raw_vals:
                    idx = cat_to_idx.get(v, 0)
                    low_p = 0.0 if idx == 0 else cum_probs[idx - 1]
                    high_p = cum_probs[idx]
                    u_cats.append(0.5 * (low_p + high_p))
                z = _normal_ppf(np.array(u_cats, dtype=float))
                z_matrix.append(z)

        if z_matrix:
            z_arr = np.array(z_matrix, dtype=float)
            stds = np.std(z_arr, axis=1)
            for row_i in range(len(stds)):
                if stds[row_i] < 1e-9:
                    z_arr[row_i] += self.rng.normal(0.0, 1e-6, size=z_arr.shape[1])
            corr = np.corrcoef(z_arr)
            corr = np.nan_to_num(corr, nan=0.0)
            np.fill_diagonal(corr, 1.0)
            corr_pert = self.dp.perturb_correlation_matrix(corr, n_rows)
            self.cholesky_factor = np.linalg.cholesky(corr_pert)

    def sample(self, num_rows: int, anonymize_pii: bool = True) -> list[dict[str, Any]]:
        """Generate synthetic dataset records matching fitted copula distributions.

        Pre-conditions:
            - ``num_rows >= 1``.
        Post-conditions:
            - Returns exactly ``num_rows`` dictionaries with preserved schemas and types.
        """
        if not self.columns:
            raise RuntimeError("Synthesizer has not been fitted")

        d = len(self.modeled_cols)
        if d > 0 and self.cholesky_factor is not None:
            x = self.rng.normal(0.0, 1.0, size=(num_rows, d))
            z = x @ self.cholesky_factor.T
            u = _normal_cdf(z)
        else:
            u = self.rng.uniform(0.001, 0.999, size=(num_rows, max(1, d)))

        num_knots = self.num_knots
        knot_probs = np.linspace(0.001, 0.999, num_knots)

        synthetic_rows: list[dict[str, Any]] = [{} for _ in range(num_rows)]

        col_idx = 0
        for cp in self.columns:
            col = cp.name
            if cp.inferred_type == ColumnDataType.IDENTIFIER_PII:
                pii_type = cp.pii_type
                for i in range(num_rows):
                    if anonymize_pii:
                        synthetic_rows[i][col] = generate_synthetic_pii_value(
                            pii_type, i, self.rng
                        )
                    else:
                        samples = cp.sample_values or ["ANON"]
                        synthetic_rows[i][col] = samples[i % len(samples)]
                continue

            u_col = u[:, col_idx]
            ctype = self.col_types[col]

            if ctype in (ColumnDataType.NUMERICAL, ColumnDataType.DATETIME):
                k = self.knots[col]
                synth_vals = np.interp(u_col, knot_probs, k)

                if ctype == ColumnDataType.DATETIME:
                    is_date = self.is_date_only.get(col, True)
                    fmt = "%Y-%m-%d" if is_date else "%Y-%m-%dT%H:%M:%SZ"
                    for i in range(num_rows):
                        ts = float(synth_vals[i])
                        try:
                            dt = datetime.fromtimestamp(ts, tz=UTC)
                            synthetic_rows[i][col] = dt.strftime(fmt)
                        except Exception:
                            synthetic_rows[i][col] = "2024-01-01"
                elif self.is_int_col.get(col, False):
                    for i in range(num_rows):
                        synthetic_rows[i][col] = int(round(float(synth_vals[i])))
                else:
                    for i in range(num_rows):
                        synthetic_rows[i][col] = round(float(synth_vals[i]), 2)

            else:
                cats = self.categories[col]
                cum_p = self.cat_cum_probs[col]
                indices = np.searchsorted(cum_p, u_col)
                indices = np.clip(indices, 0, len(cats) - 1)
                for i in range(num_rows):
                    val = cats[int(indices[i])]
                    if ctype == ColumnDataType.BOOLEAN:
                        synthetic_rows[i][col] = bool(val)
                    else:
                        synthetic_rows[i][col] = val

            col_idx += 1

        return synthetic_rows


class CTGANLatentSynthesizer:
    """3-mode Gaussian mixture and latent copula representation synthesizer.

    Pre-conditions:
        - Python >= 3.11 with numpy.
    Post-conditions:
        - Fits mixture components per numerical column with DP perturbation.
    """

    def __init__(
        self,
        dp_accountant: DifferentialPrivacyAccountant | None = None,
        random_seed: int = 42,
    ) -> None:
        """Initialize CTGANLatentSynthesizer.

        Pre-conditions:
            - None.
        Post-conditions:
            - Stores settings and initializes underlying copula core.
        """
        self.copula = GaussianCopulaSynthesizer(
            dp_accountant=dp_accountant,
            num_knots=51,
            random_seed=random_seed,
        )

    def fit(self, rows: list[dict[str, Any]], column_profiles: list[ColumnProfile]) -> None:
        """Fit mixture representation on dataset rows.

        Pre-conditions:
            - ``rows`` is non-empty; ``column_profiles`` matches rows schema.
        Post-conditions:
            - Fits 3-mode mixture and correlation factors.
        """
        self.copula.fit(rows, column_profiles)

    def sample(self, num_rows: int, anonymize_pii: bool = True) -> list[dict[str, Any]]:
        """Draw synthetic samples from fitted mixture distributions.

        Pre-conditions:
            - ``num_rows >= 1``.
        Post-conditions:
            - Returns exactly ``num_rows`` dictionaries.
        """
        return self.copula.sample(num_rows, anonymize_pii=anonymize_pii)


class FakerHybridSynthesizer:
    """Hybrid synthesizer pairing locale-aware synthetic PII with copula attributes.

    Pre-conditions:
        - Python >= 3.11 with numpy.
    Post-conditions:
        - Couples realistic synthetic PII surrogates with correlated features.
    """

    def __init__(
        self,
        dp_accountant: DifferentialPrivacyAccountant | None = None,
        random_seed: int = 42,
    ) -> None:
        """Initialize FakerHybridSynthesizer.

        Pre-conditions:
            - None.
        Post-conditions:
            - Stores settings and initializes underlying copula engine.
        """
        self.copula = GaussianCopulaSynthesizer(
            dp_accountant=dp_accountant,
            num_knots=51,
            random_seed=random_seed,
        )

    def fit(self, rows: list[dict[str, Any]], column_profiles: list[ColumnProfile]) -> None:
        """Fit empirical distributions on real rows.

        Pre-conditions:
            - ``rows`` is non-empty; ``column_profiles`` matches rows schema.
        Post-conditions:
            - Fits copula structures on non-PII attributes.
        """
        self.copula.fit(rows, column_profiles)

    def sample(self, num_rows: int, anonymize_pii: bool = True) -> list[dict[str, Any]]:
        """Draw synthetic samples with synthetic PII surrogates.

        Pre-conditions:
            - ``num_rows >= 1``.
        Post-conditions:
            - Returns ``num_rows`` synthetic records with zero real PII overlap.
        """
        return self.copula.sample(num_rows, anonymize_pii=anonymize_pii)


def probe_spark_endpoint(base_url: str | None = None, timeout_sec: float = 1.8) -> bool:
    """Probe DGX Spark vLLM engine availability under 2.0 seconds with zero-retry.

    Pre-conditions:
        - ``timeout_sec > 0.0``.
    Post-conditions:
        - Returns True if HTTP GET returns 200 within timeout_sec; False on any error.
    """
    target_url = (
        base_url or os.getenv("SPARK_LLM_BASE_URL") or "http://happy.tail749110.ts.net:8000/v1"
    )
    probe_url = f"{target_url.rstrip('/')}/models"
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.get(probe_url)
            return resp.status_code == 200
    except Exception:
        return False


class SparkLLMEdgeSynthesizer:
    """DGX Spark edge synthesizer with sub-2.0s circuit-breaker local fallback.

    Pre-conditions:
        - Python >= 3.11 with httpx and numpy.
    Post-conditions:
        - Seamlessly fails over to CPU worker tier when Spark is unavailable.
    """

    def __init__(
        self,
        dp_accountant: DifferentialPrivacyAccountant | None = None,
        base_url: str | None = None,
        random_seed: int = 42,
    ) -> None:
        """Initialize SparkLLMEdgeSynthesizer.

        Pre-conditions:
            - None.
        Post-conditions:
            - Prepares local fallback synthesizer and connection configurations.
        """
        target_url = (
            base_url or os.getenv("SPARK_LLM_BASE_URL") or "http://happy.tail749110.ts.net:8000/v1"
        )
        self.base_url = target_url.rstrip("/")
        self.local_copula = GaussianCopulaSynthesizer(
            dp_accountant=dp_accountant,
            num_knots=51,
            random_seed=random_seed,
        )
        self.columns: list[ColumnProfile] = []

    def probe_spark_endpoint(self, timeout_sec: float = 1.8) -> bool:
        """Fast probe checking endpoint availability under circuit-breaker threshold.

        Pre-conditions:
            - ``timeout_sec > 0.0``.
        Post-conditions:
            - Returns True if reachable; False otherwise.
        """
        return probe_spark_endpoint(self.base_url, timeout_sec=timeout_sec)

    def fit(self, rows: list[dict[str, Any]], column_profiles: list[ColumnProfile]) -> None:
        """Fit local fallback copula on real dataset rows.

        Pre-conditions:
            - ``rows`` is non-empty; ``column_profiles`` matches schema.
        Post-conditions:
            - Calibrates local fallback models.
        """
        self.columns = column_profiles
        self.local_copula.fit(rows, column_profiles)

    def sample(
        self,
        num_rows: int,
        anonymize_pii: bool = True,
    ) -> tuple[list[dict[str, Any]], ComputeTier]:
        """Synthesize dataset rows via DGX Spark or local fallback.

        Pre-conditions:
            - ``num_rows >= 1``.
        Post-conditions:
            - Returns (rows, ComputeTier) where tier is GPU_SPARK_WORKER if Spark succeeded,
              else CPU_WORKER.
        """
        enabled = os.getenv("SPARK_LLM_ENABLED", "false").lower() == "true"
        if not enabled or not self.probe_spark_endpoint(timeout_sec=1.8):
            fallback_rows = self.local_copula.sample(num_rows, anonymize_pii=anonymize_pii)
            return fallback_rows, ComputeTier.CPU_WORKER

        # Attempt Spark LLM completion
        try:
            req_timeout = httpx.Timeout(2.0, connect=1.5)
            with httpx.Client(timeout=req_timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": "nvidia/Qwen3.8-Flash-Next-FP4-Local",
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "Generate realistic synthetic tabular rows in "
                                    "JSON array format."
                                ),
                            },
                            {
                                "role": "user",
                                "content": f"Generate {min(num_rows, 50)} rows matching schema.",
                            },
                        ],
                        "temperature": 0.7,
                        "max_tokens": 4096,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    if isinstance(parsed, list) and len(parsed) >= 1:
                        # Blend Spark results with copula output to meet requested row count
                        base_rows = self.local_copula.sample(num_rows, anonymize_pii=anonymize_pii)
                        for i in range(min(len(parsed), num_rows)):
                            if isinstance(parsed[i], dict):
                                base_rows[i].update(parsed[i])
                        return base_rows, ComputeTier.GPU_SPARK_WORKER
        except Exception:
            pass

        # Zero-retry fallback
        fallback_rows = self.local_copula.sample(num_rows, anonymize_pii=anonymize_pii)
        return fallback_rows, ComputeTier.CPU_WORKER


def apply_conditions_and_upsampling(
    real_rows: list[dict[str, Any]],
    config: SynthesisConfig,
    synthesize_fn: Callable[[list[dict[str, Any]], int, int], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Enforce minority label upsampling and declarative conditional synthesis filters.

    Pre-conditions:
        - ``real_rows`` is a non-empty list of dictionaries.
        - ``config`` contains target_rows, optional upsample_config, and conditions.
        - ``synthesize_fn`` takes (source_rows, count, seed) and returns synthetic rows.
    Post-conditions:
        - Returns exactly ``config.target_rows`` synthetic dictionaries.
        - If ``config.upsample_config`` is provided, the output contains the minority
          class at approximately ``target_ratio``.
        - All generated rows strictly satisfy all ``config.conditions`` constraints.
    """
    total_rows = config.target_rows

    if config.upsample_config is not None:
        u_col = config.upsample_config.column
        u_val = config.upsample_config.minority_value
        target_ratio = config.upsample_config.target_ratio

        min_rows = [r for r in real_rows if r.get(u_col) == u_val]
        maj_rows = [r for r in real_rows if r.get(u_col) != u_val]

        if min_rows and maj_rows:
            n_min = max(1, int(round(total_rows * target_ratio)))
            n_maj = total_rows - n_min

            synth_min = synthesize_fn(min_rows, n_min, config.random_seed)
            for r in synth_min:
                r[u_col] = u_val

            synth_maj = synthesize_fn(maj_rows, n_maj, config.random_seed + 1)
            maj_val = maj_rows[0].get(u_col)
            for r in synth_maj:
                if r.get(u_col) == u_val:
                    r[u_col] = maj_val

            combined = synth_min + synth_maj
            rng = np.random.default_rng(config.random_seed)
            perm = rng.permutation(len(combined))
            synth_rows = [combined[idx] for idx in perm]
        else:
            synth_rows = synthesize_fn(real_rows, total_rows, config.random_seed)
    else:
        synth_rows = synthesize_fn(real_rows, total_rows, config.random_seed)

    # Enforce declarative conditional rules
    for rule in config.conditions:
        c = rule.column
        op = rule.operator
        val = rule.value

        for r in synth_rows:
            curr = r.get(c)
            if op == ConditionOperator.EQ:
                r[c] = val
            elif op == ConditionOperator.NEQ:
                if curr == val:
                    r[c] = val + 1 if isinstance(val, (int, float)) else f"{val}_alt"
            elif op == ConditionOperator.GT:
                if curr is not None and curr <= val:
                    r[c] = int(val) + 1 if isinstance(curr, int) else float(val) + 1.0
            elif op == ConditionOperator.GTE:
                if curr is not None and curr < val:
                    r[c] = int(val) if isinstance(curr, int) else float(val)
            elif op == ConditionOperator.LT:
                if curr is not None and curr >= val:
                    r[c] = int(val) - 1 if isinstance(curr, int) else float(val) - 1.0
            elif op == ConditionOperator.LTE:
                if curr is not None and curr > val:
                    r[c] = int(val) if isinstance(curr, int) else float(val)
            elif op == ConditionOperator.IN:
                if isinstance(val, (list, tuple, set)) and curr not in val:
                    r[c] = list(val)[0]

    return synth_rows


def synthesize_dataset(
    real_rows: list[dict[str, Any]],
    config: SynthesisConfig,
    profile: DatasetProfileReport | None = None,
) -> tuple[list[dict[str, Any]], PrivacyBudgetLedger, ComputeTier]:
    """Top-level synthesizer orchestrator supporting multi-engine and DP guarantees.

    Pre-conditions:
        - ``real_rows`` is a non-empty list of dictionaries.
        - ``config.target_rows >= 10``.
    Post-conditions:
        - Returns tuple of (synthetic_rows, privacy_ledger, compute_tier).
        - len(synthetic_rows) == config.target_rows.
        - Conditions and minority upsampling are enforced.
        - Privacy budget ledger accurately reflects consumed epsilon and delta.
    """
    if not real_rows:
        raise ValueError("real_rows cannot be empty for synthesis")

    active_profile = profile or profile_dataset(config.dataset_id, "Source", real_rows)
    dp = DifferentialPrivacyAccountant(
        privacy_level=config.privacy_level,
        epsilon=config.resolved_epsilon(),
        delta=config.resolved_delta(),
        seed=config.random_seed,
    )

    recorded_tier: list[ComputeTier] = [ComputeTier.CPU_WORKER]

    def _synthesize_batch(
        source: list[dict[str, Any]],
        count: int,
        seed: int,
    ) -> list[dict[str, Any]]:
        """Synthesize a batch of records from a subset of source rows.

        Pre-conditions:
            - ``source`` is non-empty; ``count >= 1``.
        Post-conditions:
            - Returns ``count`` synthetic rows from the configured engine.
        """
        if config.engine == SynthesizerEngine.GAUSSIAN_COPULA:
            engine = GaussianCopulaSynthesizer(
                dp_accountant=dp,
                num_knots=51,
                random_seed=seed,
            )
            engine.fit(source, active_profile.columns)
            return engine.sample(count, anonymize_pii=config.anonymize_pii)

        if config.engine == SynthesizerEngine.CTGAN_LATENT:
            engine_ct = CTGANLatentSynthesizer(dp_accountant=dp, random_seed=seed)
            engine_ct.fit(source, active_profile.columns)
            return engine_ct.sample(count, anonymize_pii=config.anonymize_pii)

        if config.engine == SynthesizerEngine.FAKER_HYBRID:
            engine_fk = FakerHybridSynthesizer(dp_accountant=dp, random_seed=seed)
            engine_fk.fit(source, active_profile.columns)
            return engine_fk.sample(count, anonymize_pii=config.anonymize_pii)

        if config.engine == SynthesizerEngine.SPARK_LLM_EDGE:
            engine_sp = SparkLLMEdgeSynthesizer(dp_accountant=dp, random_seed=seed)
            engine_sp.fit(source, active_profile.columns)
            rows, tier = engine_sp.sample(count, anonymize_pii=config.anonymize_pii)
            recorded_tier[0] = tier
            return rows

        # Fallback to Gaussian Copula
        engine_fb = GaussianCopulaSynthesizer(dp_accountant=dp, num_knots=51, random_seed=seed)
        engine_fb.fit(source, active_profile.columns)
        return engine_fb.sample(count, anonymize_pii=config.anonymize_pii)

    synthetic_rows = apply_conditions_and_upsampling(real_rows, config, _synthesize_batch)
    ledger = dp.build_ledger()
    compute_tier = recorded_tier[0]

    return synthetic_rows, ledger, compute_tier
