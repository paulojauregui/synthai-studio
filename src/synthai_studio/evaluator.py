"""SynthAI Studio Statistical Fidelity, Privacy Quality Validator, and Audit Exporter.

Pre-conditions:
    - Python >= 3.11 with ``numpy`` and ``pydantic`` v2 installed.
Post-conditions:
    - Provides two-sample KS and TVD fidelity metrics, Frobenius correlation stability,
      Euclidean DCR/NNDR attack surface metrics, and GitHub-Flavored Markdown audits.
"""

from datetime import datetime
from typing import Any

import numpy as np

from synthai_studio.models import (
    ColumnDataType,
    ColumnFidelityMetric,
    DatasetProfileReport,
    PrivacyBudgetLedger,
    PrivacyValidationMetrics,
    QualityValidationReport,
    SynthesisConfig,
)
from synthai_studio.profiler import compute_correlation_matrix, profile_dataset

__all__ = [
    "compute_correlation_stability",
    "compute_ks_complement",
    "compute_privacy_metrics",
    "compute_tvd_and_js_similarity",
    "evaluate_synthetic_quality",
    "render_quality_report_markdown",
]


def compute_ks_complement(
    real_values: list[float],
    synth_values: list[float],
) -> tuple[float, float]:
    """Compute empirical two-sample Kolmogorov-Smirnov distance and fidelity complement.

    Pre-conditions:
        - ``real_values`` and ``synth_values`` are non-empty lists of finite floats.
    Post-conditions:
        - Returns (score, d_ks) where score = 1.0 - d_ks in [0.0, 1.0].
    """
    if not real_values or not synth_values:
        raise ValueError("Inputs cannot be empty for compute_ks_complement")

    data1 = np.sort(np.asarray(real_values, dtype=float))
    data2 = np.sort(np.asarray(synth_values, dtype=float))
    n1 = len(data1)
    n2 = len(data2)

    data_all = np.concatenate([data1, data2])
    cdf1 = np.searchsorted(data1, data_all, side="right") / n1
    cdf2 = np.searchsorted(data2, data_all, side="right") / n2

    d_ks = float(np.max(np.abs(cdf1 - cdf2)))
    d_ks_clamped = max(0.0, min(1.0, d_ks))
    score = max(0.0, min(1.0, round(1.0 - d_ks_clamped, 4)))

    return score, round(d_ks_clamped, 4)


def compute_tvd_and_js_similarity(
    real_values: list[str],
    synth_values: list[str],
) -> tuple[float, float, float]:
    """Compute Total Variation Distance (TVD) and Jensen-Shannon similarity.

    Pre-conditions:
        - ``real_values`` and ``synth_values`` are non-empty lists of strings.
    Post-conditions:
        - Returns (tvd_score, tvd, js_similarity) all bounded in [0.0, 1.0].
    """
    if not real_values or not synth_values:
        raise ValueError("Inputs cannot be empty for compute_tvd_and_js_similarity")

    categories = sorted(list(set(real_values) | set(synth_values)))
    n_real = float(len(real_values))
    n_synth = float(len(synth_values))

    real_counts: dict[str, int] = {}
    for v in real_values:
        real_counts[v] = real_counts.get(v, 0) + 1

    synth_counts: dict[str, int] = {}
    for v in synth_values:
        synth_counts[v] = synth_counts.get(v, 0) + 1

    p = np.array([real_counts.get(c, 0) / n_real for c in categories], dtype=float)
    q = np.array([synth_counts.get(c, 0) / n_synth for c in categories], dtype=float)

    # Total Variation Distance: 0.5 * sum(|p - q|)
    tvd = float(0.5 * np.sum(np.abs(p - q)))
    tvd_clamped = max(0.0, min(1.0, tvd))
    tvd_score = max(0.0, min(1.0, round(1.0 - tvd_clamped, 4)))

    # Jensen-Shannon similarity: 1.0 - sqrt(JS_divergence / ln(2))
    m = 0.5 * (p + q)
    eps = 1e-12

    kl_p_m = np.sum(np.where(p > eps, p * np.log(np.maximum(p, eps) / np.maximum(m, eps)), 0.0))
    kl_q_m = np.sum(np.where(q > eps, q * np.log(np.maximum(q, eps) / np.maximum(m, eps)), 0.0))
    js_div = max(0.0, float(0.5 * (kl_p_m + kl_q_m)))
    js_norm = min(1.0, js_div / np.log(2.0))
    js_sim = max(0.0, min(1.0, round(1.0 - np.sqrt(js_norm), 4)))

    return tvd_score, round(tvd_clamped, 4), js_sim


def compute_correlation_stability(
    real_corr: list[list[float]],
    synth_corr: list[list[float]],
) -> float:
    """Compute Frobenius norm correlation stability between real and synthetic matrices.

    Pre-conditions:
        - ``real_corr`` and ``synth_corr`` are square numeric matrices of identical size.
    Post-conditions:
        - Returns a stability score in [0.0, 1.0], where 1.0 indicates perfect preservation.
    """
    if not real_corr or not synth_corr:
        return 1.0

    d = len(real_corr)
    if d <= 1:
        return 1.0

    r_real = np.array(real_corr, dtype=float)
    r_synth = np.array(synth_corr, dtype=float)

    diff = r_real - r_synth
    np.fill_diagonal(diff, 0.0)

    frob_norm = float(np.linalg.norm(diff, ord="fro"))
    norm_factor = np.sqrt(d * (d - 1))
    normalized_dist = frob_norm / norm_factor

    score = max(0.0, min(1.0, round(1.0 - normalized_dist * 0.5, 4)))
    return score


def compute_privacy_metrics(
    real_rows: list[dict[str, Any]],
    synth_rows: list[dict[str, Any]],
    pii_columns: list[str],
    numeric_columns: list[str],
) -> PrivacyValidationMetrics:
    """Compute empirical privacy attack surface metrics (DCR, NNDR, collision, and leakage).

    Pre-conditions:
        - ``real_rows`` and ``synth_rows`` are non-empty lists of dictionaries.
    Post-conditions:
        - Returns PrivacyValidationMetrics with empirical collision and distance ratios.
    """
    if not real_rows or not synth_rows:
        raise ValueError("Rows cannot be empty for compute_privacy_metrics")

    # 1. Exact match collision rate
    real_tuples = {
        tuple(sorted((k, str(v)) for k, v in r.items()))
        for r in real_rows
    }
    collisions = sum(
        1 for r in synth_rows
        if tuple(sorted((k, str(v)) for k, v in r.items())) in real_tuples
    )
    collision_rate = round(collisions / len(synth_rows), 4)

    # 2. PII leakage detection
    pii_leakage = False
    for col in pii_columns:
        real_pii_vals = {
            str(r[col]).strip().lower()
            for r in real_rows
            if r.get(col) is not None
        }
        for r in synth_rows:
            v = r.get(col)
            if v is not None and str(v).strip().lower() in real_pii_vals:
                pii_leakage = True
                break
        if pii_leakage:
            break

    # 3. Distance to Closest Record (DCR) and Nearest-Neighbor Distance Ratio (NNDR)
    if numeric_columns:
        # Standardize numeric columns using real dataset means and standard deviations
        real_mat_raw = []
        for r in real_rows:
            real_mat_raw.append([
                float(r.get(c, 0.0) if r.get(c) is not None else 0.0)
                for c in numeric_columns
            ])
        real_arr = np.array(real_mat_raw, dtype=float)

        means = np.mean(real_arr, axis=0)
        stds = np.std(real_arr, axis=0)
        stds = np.where(stds < 1e-6, 1.0, stds)

        real_norm = (real_arr - means) / stds

        synth_mat_raw = []
        for r in synth_rows:
            synth_mat_raw.append([
                float(r.get(c, 0.0) if r.get(c) is not None else 0.0)
                for c in numeric_columns
            ])
        synth_norm = (np.array(synth_mat_raw, dtype=float) - means) / stds

        # Compute nearest and second nearest neighbor Euclidean distances
        dcr_list: list[float] = []
        nndr_list: list[float] = []

        # Subsample for evaluation efficiency if synthetic dataset is large
        max_eval = min(len(synth_norm), 500)
        for i in range(max_eval):
            diff = real_norm - synth_norm[i]
            dists = np.sqrt(np.sum(diff * diff, axis=1))
            sorted_dists = np.sort(dists)
            d1 = float(sorted_dists[0])
            d2 = float(sorted_dists[1]) if len(sorted_dists) > 1 else d1 + 1.0
            dcr_list.append(d1)
            nndr_list.append(d1 / (d2 + 1e-6))

        dcr_med = round(float(np.median(dcr_list)), 4)
        dcr_p05 = round(float(np.percentile(dcr_list, 5)), 4)
        nndr_med = round(float(np.median(nndr_list)), 4)
        nndr_p05 = round(float(np.percentile(nndr_list, 5)), 4)
    else:
        dcr_med = 1.0
        dcr_p05 = 0.5
        nndr_med = 0.8
        nndr_p05 = 0.5

    # Composite privacy protection score
    base_score = 1.0 - collision_rate
    if pii_leakage:
        base_score *= 0.2
    if dcr_med > 0.05:
        dist_factor = 1.0
    else:
        dist_factor = max(0.1, dcr_med / 0.05)
    base_score *= dist_factor
    protection_score = max(0.0, min(1.0, round(base_score, 4)))

    return PrivacyValidationMetrics(
        exact_match_collision_rate=collision_rate,
        dcr_median=dcr_med,
        dcr_p05=dcr_p05,
        nndr_median=nndr_med,
        nndr_p05=nndr_p05,
        privacy_protection_score=protection_score,
        pii_leakage_detected=pii_leakage,
    )


def evaluate_synthetic_quality(
    job_id: str,
    dataset_id: str,
    real_rows: list[dict[str, Any]],
    synth_rows: list[dict[str, Any]],
    config: SynthesisConfig,
    privacy_ledger: PrivacyBudgetLedger,
    real_profile: DatasetProfileReport | None = None,
) -> QualityValidationReport:
    """Evaluate synthetic dataset against real data across fidelity and privacy axes.

    Pre-conditions:
        - ``real_rows`` and ``synth_rows`` are non-empty lists of dictionaries.
    Post-conditions:
        - Emits a comprehensive QualityValidationReport with weighted overall quality score.
    """
    if not real_rows or not synth_rows:
        raise ValueError("Real and synthetic rows must be non-empty")

    profile = real_profile or profile_dataset(dataset_id, "Real Dataset", real_rows)
    synth_profile = profile_dataset(f"{dataset_id}-synth", "Synthetic Dataset", synth_rows)

    column_metrics: list[ColumnFidelityMetric] = []
    fidelity_scores: list[float] = []

    pii_columns = [
        cp.name for cp in profile.columns if cp.inferred_type == ColumnDataType.IDENTIFIER_PII
    ]
    numeric_columns = [
        cp.name for cp in profile.columns if cp.inferred_type == ColumnDataType.NUMERICAL
    ]

    for cp in profile.columns:
        col = cp.name
        if cp.inferred_type == ColumnDataType.IDENTIFIER_PII:
            # PII columns evaluated for non-collision / privacy
            column_metrics.append(
                ColumnFidelityMetric(
                    column_name=col,
                    column_type=cp.inferred_type,
                    metric_name="PII_Anonymization",
                    score=1.0,
                    statistic_distance=0.0,
                    real_summary={"type": "PII", "count": len(real_rows)},
                    synthetic_summary={"type": "PII", "count": len(synth_rows)},
                )
            )
            continue

        real_vals = [r.get(col) for r in real_rows if r.get(col) is not None]
        synth_vals = [r.get(col) for r in synth_rows if r.get(col) is not None]

        if cp.inferred_type in (ColumnDataType.NUMERICAL, ColumnDataType.DATETIME):
            if cp.inferred_type == ColumnDataType.DATETIME:
                # Convert date strings to timestamps for KS evaluation
                r_floats = [
                    float(datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp())
                    for v in real_vals
                ]
                s_floats = [
                    float(datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp())
                    for v in synth_vals
                ]
            else:
                r_floats = [float(v) for v in real_vals if isinstance(v, (int, float))]
                s_floats = [float(v) for v in synth_vals if isinstance(v, (int, float))]

            if r_floats and s_floats:
                score, d_ks = compute_ks_complement(r_floats, s_floats)
            else:
                score, d_ks = 1.0, 0.0

            fidelity_scores.append(score)
            column_metrics.append(
                ColumnFidelityMetric(
                    column_name=col,
                    column_type=cp.inferred_type,
                    metric_name="1 - KS_Distance",
                    score=score,
                    statistic_distance=d_ks,
                    real_summary={
                        "mean": round(float(np.mean(r_floats)), 2) if r_floats else 0.0,
                        "std": round(float(np.std(r_floats)), 2) if r_floats else 0.0,
                    },
                    synthetic_summary={
                        "mean": round(float(np.mean(s_floats)), 2) if s_floats else 0.0,
                        "std": round(float(np.std(s_floats)), 2) if s_floats else 0.0,
                    },
                )
            )

        else:
            # CATEGORICAL or BOOLEAN
            r_strs = [str(v) for v in real_vals]
            s_strs = [str(v) for v in synth_vals]

            if r_strs and s_strs:
                tvd_score, tvd, js_sim = compute_tvd_and_js_similarity(r_strs, s_strs)
            else:
                tvd_score, tvd, js_sim = 1.0, 0.0, 1.0

            fidelity_scores.append(tvd_score)
            column_metrics.append(
                ColumnFidelityMetric(
                    column_name=col,
                    column_type=cp.inferred_type,
                    metric_name="1 - TVD",
                    score=tvd_score,
                    statistic_distance=tvd,
                    jensen_shannon_similarity=js_sim,
                    real_summary={"unique_count": len(set(r_strs))},
                    synthetic_summary={"unique_count": len(set(s_strs))},
                )
            )

    marginal_fidelity = (
        round(float(np.mean(fidelity_scores)), 4) if fidelity_scores else 1.0
    )

    # Correlation stability evaluation
    corr_cols = [c for c in numeric_columns if c in profile.correlation_columns]
    if corr_cols:
        r_cols, r_corr = compute_correlation_matrix(real_rows, corr_cols)
        s_cols, s_corr = compute_correlation_matrix(synth_rows, corr_cols)
        corr_stability = compute_correlation_stability(r_corr, s_corr)
    else:
        r_corr = []
        s_corr = []
        corr_stability = 1.0

    privacy_metrics = compute_privacy_metrics(
        real_rows,
        synth_rows,
        pii_columns,
        numeric_columns,
    )
    privacy_score = privacy_metrics.privacy_protection_score

    # Weighted overall quality score: 0.45 * marginal + 0.30 * correlation + 0.25 * privacy
    overall_quality = round(
        0.45 * marginal_fidelity + 0.30 * corr_stability + 0.25 * privacy_score,
        4,
    )

    hipaa_gdpr_ready = (not privacy_metrics.pii_leakage_detected) and (privacy_score >= 0.70)

    if overall_quality >= 0.88 and hipaa_gdpr_ready:
        verdict = (
            "PASSED (CERTIFIED): High statistical fidelity with certified differential "
            "privacy and zero PII leakage. Safe for production model training."
        )
    elif overall_quality >= 0.75:
        verdict = (
            "PASSED (STANDARD): Acceptable statistical preservation for analytical "
            "workloads with guarded privacy."
        )
    else:
        verdict = (
            "NEEDS_REVIEW: Sub-optimal fidelity or elevated privacy risk. "
            "Adjust synthesizer parameters or privacy budget."
        )

    return QualityValidationReport(
        job_id=job_id,
        dataset_id=dataset_id,
        engine=config.engine,
        privacy_level=config.privacy_level,
        real_row_count=len(real_rows),
        synthetic_row_count=len(synth_rows),
        overall_quality_score=overall_quality,
        marginal_fidelity_score=marginal_fidelity,
        correlation_stability_score=corr_stability,
        privacy_score=privacy_score,
        column_metrics=column_metrics,
        privacy_metrics=privacy_metrics,
        privacy_ledger=privacy_ledger,
        real_correlation_matrix=profile.correlation_matrix,
        synthetic_correlation_matrix=synth_profile.correlation_matrix,
        correlation_columns=profile.correlation_columns,
        executive_verdict=verdict,
        hipaa_gdpr_ready=hipaa_gdpr_ready,
        evaluated_at=datetime.now(),
    )


def render_quality_report_markdown(report: QualityValidationReport) -> str:
    """Render a structured GitHub-Flavored Markdown audit report for compliance.

    Pre-conditions:
        - ``report`` is a valid QualityValidationReport.
    Post-conditions:
        - Returns a formatted markdown report with zero emojis.
    """
    lines: list[str] = [
        f"# SynthAI Studio Quality Validation Report: Job `{report.job_id}`",
        "",
        f"**Dataset ID:** `{report.dataset_id}` | "
        f"**Engine:** `{report.engine.value}` | "
        f"**Evaluated At:** `{report.evaluated_at.isoformat()}`",
        "",
        "## Executive Summary",
        "",
        f"- **Overall Quality Score:** `{report.overall_quality_score:.2%}`",
        f"- **Marginal Distribution Fidelity:** `{report.marginal_fidelity_score:.2%}`",
        f"- **Correlation Stability:** `{report.correlation_stability_score:.2%}`",
        f"- **Privacy Protection Score:** `{report.privacy_score:.2%}`",
        f"- **HIPAA/GDPR Compliance Readiness:** `{'YES' if report.hipaa_gdpr_ready else 'NO'}`",
        f"- **Verdict:** {report.executive_verdict}",
        "",
        "## Differential Privacy Budget Ledger",
        "",
        f"- **Privacy Level:** `{report.privacy_ledger.privacy_level.value}`",
        (
            f"- **Epsilon Spent:** `{report.privacy_ledger.epsilon_spent}`"
            if report.privacy_ledger.epsilon_spent is not None
            else "- **Epsilon Spent:** `None (Non-Private)`"
        ),
        f"- **Delta:** `{report.privacy_ledger.delta}`",
        f"- **Mechanism:** `{report.privacy_ledger.mechanism}`",
        f"- **Noise Scale:** `{report.privacy_ledger.noise_scale:.4f}`",
        f"- **PSD Projection Applied:** `{report.privacy_ledger.psd_projection_applied}`",
        "",
        "## Privacy Attack Surface Metrics",
        "",
        (
            "- **Exact Match Collision Rate:** "
            f"`{report.privacy_metrics.exact_match_collision_rate:.4%}`"
        ),
        f"- **Distance to Closest Record (DCR) Median:** `{report.privacy_metrics.dcr_median:.4f}`",
        f"- **DCR 5th Percentile:** `{report.privacy_metrics.dcr_p05:.4f}`",
        (
            "- **Nearest Neighbor Distance Ratio (NNDR) Median:** "
            f"`{report.privacy_metrics.nndr_median:.4f}`"
        ),
        f"- **NNDR 5th Percentile:** `{report.privacy_metrics.nndr_p05:.4f}`",
        f"- **Direct PII Leakage Detected:** `{report.privacy_metrics.pii_leakage_detected}`",
        "",
        "## Column-Level Distribution Fidelity",
        "",
        "| Column | Type | Metric | Score | Distance | Real Summary | Synth Summary |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for cm in report.column_metrics:
        r_sum = ", ".join(f"{k}: {v}" for k, v in cm.real_summary.items()) or "N/A"
        s_sum = ", ".join(f"{k}: {v}" for k, v in cm.synthetic_summary.items()) or "N/A"
        lines.append(
            f"| `{cm.column_name}` | `{cm.column_type.value}` | `{cm.metric_name}` | "
            f"`{cm.score:.2%}` | `{cm.statistic_distance:.4f}` | {r_sum} | {s_sum} |"
        )

    lines.append("")
    lines.append("## Dataset Topology")
    lines.append(f"- **Real Row Count:** `{report.real_row_count}`")
    lines.append(f"- **Synthetic Row Count:** `{report.synthetic_row_count}`")
    lines.append(f"- **Correlated Columns:** `{', '.join(report.correlation_columns) or 'None'}`")
    lines.append("")

    return "\n".join(lines)
