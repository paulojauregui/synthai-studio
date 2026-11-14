"""SynthAI Studio Automated Data Quality Auditor, PII/PHI Scanner & Statistical Profiler.

Pre-conditions:
    - Python >= 3.11 with ``numpy`` and ``pydantic`` v2 installed.
Post-conditions:
    - Provides tabular payload parsing, PII/PHI pattern detection, schema inference,
      distribution & correlation profiling, defect auditing, and dataset cleansing.
"""

import csv
import io
import json
import re
from datetime import datetime
from typing import Any

import numpy as np

from synthai_studio.models import (
    CategoryFrequency,
    ColumnDataType,
    ColumnProfile,
    DataQualityIssue,
    DataQualityIssueType,
    DatasetProfileReport,
    HistogramBin,
    IssueSeverity,
    NumericalStats,
    PIIFinding,
    PIIType,
)

__all__ = [
    "cleanse_dataset",
    "compute_correlation_matrix",
    "compute_numerical_stats",
    "detect_column_pii",
    "infer_column_type",
    "parse_tabular_payload",
    "profile_dataset",
]

_EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_SSN_REGEX = re.compile(r"^\d{3}-\d{2}-\d{4}$")
_PHONE_REGEX = re.compile(r"^(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$")
_CREDIT_CARD_REGEX = re.compile(r"^\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}$")
_MRN_REGEX = re.compile(r"^MRN-?\d+$", re.IGNORECASE)
_IP_REGEX = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)
_PERSON_NAME_REGEX = re.compile(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+$")


def _is_anonymized_token(val: str) -> bool:
    """Check if a string represents an anonymized, redacted, or dummy token.

    Pre-conditions:
        - ``val`` is a string value.
    Post-conditions:
        - Returns True if the value matches known anonymization token formats.
    """
    v = val.strip()
    if (
        v.startswith(("ANON-", "REDACTED", "XXX-XX-", "XXXX-", "MASKED-"))
        or v.endswith(("@synthetic.invalid", "@example.invalid", "@masked.invalid"))
        or v in ("0.0.0.0", "XXX-XX-XXXX", "[REDACTED]", "ANONYMIZED")
        or v.startswith("+1-555-000-")
    ):
        return True
    return False


def _is_numeric_str(s: str) -> bool:
    """Check if string cleanly parses as a float.

    Pre-conditions:
        - ``s`` is a string.
    Post-conditions:
        - Returns True if float(s) succeeds without ValueError.
    """
    try:
        float(s.strip())
        return True
    except ValueError:
        return False


def parse_tabular_payload(
    raw_data: bytes | str,
    filename: str = "dataset.csv",
) -> list[dict[str, Any]]:
    """Parse raw CSV or JSON byte/string payloads into tabular row dictionaries.

    Pre-conditions:
        - ``raw_data`` is a non-empty UTF-8 encoded string or byte sequence.
        - ``filename`` indicates payload format via extension (e.g. .csv or .json).
    Post-conditions:
        - Returns a non-empty list of row dictionaries with type-cast scalars.
        - Empty string values and null sentinels are converted to ``None``.
        - Raises ``ValueError`` if payload is empty, invalid, or produces zero rows.
    """
    if isinstance(raw_data, bytes):
        try:
            text = raw_data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Payload failed UTF-8 decoding: {exc}") from exc
    else:
        text = raw_data

    text_stripped = text.strip()
    if not text_stripped:
        raise ValueError("Raw tabular payload is empty")

    fn_lower = filename.lower()
    is_json = fn_lower.endswith(".json") or text_stripped.startswith(("{", "["))

    if is_json:
        try:
            parsed = json.loads(text_stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON payload: {exc}") from exc

        if isinstance(parsed, list):
            raw_rows = parsed
        elif isinstance(parsed, dict):
            if "rows" in parsed and isinstance(parsed["rows"], list):
                raw_rows = parsed["rows"]
            elif "data" in parsed and isinstance(parsed["data"], list):
                raw_rows = parsed["data"]
            else:
                raise ValueError("JSON object must contain 'rows' or 'data' array")
        else:
            raise ValueError("JSON payload must be an array of objects or an object with rows")

        if not raw_rows:
            raise ValueError("Parsed JSON payload contains zero rows")

        cleaned_rows: list[dict[str, Any]] = []
        for r in raw_rows:
            if not isinstance(r, dict):
                raise ValueError("Each row in tabular payload must be a JSON object / dict")
            row_dict: dict[str, Any] = {}
            for k, v in r.items():
                if v is None:
                    row_dict[k] = None
                elif isinstance(v, str):
                    s = v.strip()
                    if s == "" or s.upper() in ("NULL", "NAN", "NONE", "NA"):
                        row_dict[k] = None
                    else:
                        row_dict[k] = v
                else:
                    row_dict[k] = v
            cleaned_rows.append(row_dict)
        return cleaned_rows

    reader = csv.DictReader(io.StringIO(text_stripped))
    if not reader.fieldnames:
        raise ValueError("CSV payload has no header columns")

    rows_csv: list[dict[str, Any]] = []
    for raw_row in reader:
        row: dict[str, Any] = {}
        for k, v in raw_row.items():
            if k is None:
                continue
            col_key = k.strip()
            if v is None:
                row[col_key] = None
                continue
            val_strip = v.strip()
            if val_strip == "" or val_strip.upper() in ("NULL", "NAN", "NONE", "NA"):
                row[col_key] = None
                continue

            if val_strip.lower() == "true":
                row[col_key] = True
            elif val_strip.lower() == "false":
                row[col_key] = False
            else:
                try:
                    row[col_key] = int(val_strip)
                    continue
                except ValueError:
                    pass
                try:
                    row[col_key] = float(val_strip)
                    continue
                except ValueError:
                    pass
                row[col_key] = v

        rows_csv.append(row)

    if not rows_csv:
        raise ValueError("Parsed CSV payload contains zero rows")

    return rows_csv


def detect_column_pii(column_name: str, values: list[Any]) -> PIIFinding | None:
    """Detect personally identifiable information (PII/PHI) in a column.

    Pre-conditions:
        - ``column_name`` is a non-empty string.
        - ``values`` is a list of column values.
    Post-conditions:
        - Returns a ``PIIFinding`` if PII is detected, or ``None`` otherwise.
        - Anonymized tokens (ANON-*, XXX-XX-*, etc.) do NOT trigger findings.
    """
    non_null_strs = [str(v).strip() for v in values if v is not None]
    if not non_null_strs:
        return None

    # Do not trigger findings if column is already anonymized
    anon_matches = sum(1 for v in non_null_strs if _is_anonymized_token(v))
    if anon_matches / len(non_null_strs) >= 0.5:
        return None

    col_lower = column_name.lower().strip()
    total = len(non_null_strs)

    # 1. Email detection
    email_matches = sum(1 for v in non_null_strs if _EMAIL_REGEX.match(v))
    is_email_col = "email" in col_lower
    if is_email_col or (email_matches / total >= 0.3):
        conf = min(1.0, round(0.5 + 0.5 * (email_matches / total), 2)) if is_email_col else 0.85
        return PIIFinding(
            column_name=column_name,
            pii_type=PIIType.EMAIL,
            confidence=conf,
            sample_match_count=max(email_matches, 1),
            detection_reason="Detected email address format and/or column naming heuristics.",
            remediation="Mask or tokenize email addresses with synthetic domain surrogates.",
        )

    # 2. SSN detection
    ssn_matches = sum(1 for v in non_null_strs if _SSN_REGEX.match(v))
    is_ssn_col = col_lower in ("ssn", "social_security") or col_lower.endswith("_ssn")
    if is_ssn_col or (ssn_matches / total >= 0.3):
        conf = min(1.0, round(0.5 + 0.5 * (ssn_matches / total), 2)) if is_ssn_col else 0.90
        return PIIFinding(
            column_name=column_name,
            pii_type=PIIType.SSN,
            confidence=conf,
            sample_match_count=max(ssn_matches, 1),
            detection_reason="Detected US Social Security Number pattern (XXX-XX-XXXX).",
            remediation="Redact or tokenize SSN identifiers with cryptographic surrogates.",
        )

    # 3. Phone detection
    phone_matches = sum(1 for v in non_null_strs if _PHONE_REGEX.match(v))
    is_phone_col = "phone" in col_lower or "mobile" in col_lower
    if is_phone_col or (phone_matches / total >= 0.3):
        conf = min(1.0, round(0.5 + 0.5 * (phone_matches / total), 2)) if is_phone_col else 0.85
        return PIIFinding(
            column_name=column_name,
            pii_type=PIIType.PHONE,
            confidence=conf,
            sample_match_count=max(phone_matches, 1),
            detection_reason="Detected telephone number formatting.",
            remediation="Mask telephone numbers with dummy digits or cryptographic hashes.",
        )

    # 4. Credit Card detection
    cc_matches = sum(1 for v in non_null_strs if _CREDIT_CARD_REGEX.match(v))
    is_cc_col = any(k in col_lower for k in ("card_number", "credit_card", "pan"))
    if is_cc_col or (cc_matches / total >= 0.3):
        conf = min(1.0, round(0.5 + 0.5 * (cc_matches / total), 2)) if is_cc_col else 0.90
        return PIIFinding(
            column_name=column_name,
            pii_type=PIIType.CREDIT_CARD,
            confidence=conf,
            sample_match_count=max(cc_matches, 1),
            detection_reason="Detected payment card sequence.",
            remediation="Truncate to last 4 digits or apply format-preserving tokenization.",
        )

    # 5. Medical Record Number (MRN) detection
    mrn_matches = sum(1 for v in non_null_strs if _MRN_REGEX.match(v))
    is_mrn_col = "mrn" in col_lower or "medical_record" in col_lower
    if is_mrn_col or (mrn_matches / total >= 0.3):
        conf = min(1.0, round(0.5 + 0.5 * (mrn_matches / total), 2)) if is_mrn_col else 0.90
        return PIIFinding(
            column_name=column_name,
            pii_type=PIIType.MEDICAL_RECORD_NUMBER,
            confidence=conf,
            sample_match_count=max(mrn_matches, 1),
            detection_reason="Detected Medical Record Number (MRN) format.",
            remediation="Pseudonymize MRN identifiers according to HIPAA Safe Harbor guidelines.",
        )

    # 6. IP Address detection
    ip_matches = sum(1 for v in non_null_strs if _IP_REGEX.match(v))
    is_ip_col = "ip_address" in col_lower or col_lower == "ip"
    if is_ip_col or (ip_matches / total >= 0.3):
        conf = min(1.0, round(0.5 + 0.5 * (ip_matches / total), 2)) if is_ip_col else 0.85
        return PIIFinding(
            column_name=column_name,
            pii_type=PIIType.IP_ADDRESS,
            confidence=conf,
            sample_match_count=max(ip_matches, 1),
            detection_reason="Detected IPv4 address formatting.",
            remediation="Zero the final subnet octet or substitute synthetic IP addresses.",
        )

    # 7. Person Name detection
    name_skips = ("dataset_name", "column_name", "filename", "merchant", "company", "file_name")
    is_name_col = "name" in col_lower and not any(skip in col_lower for skip in name_skips)
    name_matches = sum(1 for v in non_null_strs if _PERSON_NAME_REGEX.match(v))
    if is_name_col and (name_matches / total >= 0.2 or total <= 5):
        conf = min(1.0, round(0.5 + 0.5 * (name_matches / total), 2)) if name_matches > 0 else 0.75
        return PIIFinding(
            column_name=column_name,
            pii_type=PIIType.PERSON_NAME,
            confidence=conf,
            sample_match_count=max(name_matches, 1),
            detection_reason="Detected personal full name capitalization patterns and naming.",
            remediation="Replace personal names with synthetic pseudonymized names.",
        )

    return None


def infer_column_type(
    column_name: str,
    values: list[Any],
    pii_finding: PIIFinding | None = None,
) -> ColumnDataType:
    """Infer the statistical data type of a column.

    Pre-conditions:
        - ``column_name`` is a non-empty string.
    Post-conditions:
        - Returns one of ColumnDataType enum values.
        - Returns IDENTIFIER_PII when pii_finding is present.
        - Returns NUMERICAL for numeric columns (including binary integer flags).
        - Returns BOOLEAN for boolean types.
        - Returns DATETIME for ISO date/datetime strings.
        - Returns CATEGORICAL for generic categorical strings.
    """
    if pii_finding is not None:
        return ColumnDataType.IDENTIFIER_PII

    non_null = [v for v in values if v is not None]
    if not non_null:
        return ColumnDataType.CATEGORICAL

    # Check boolean
    bool_count = sum(
        1 for v in non_null
        if isinstance(v, bool) or (isinstance(v, str) and v.strip().lower() in ("true", "false"))
    )
    if bool_count == len(non_null):
        return ColumnDataType.BOOLEAN

    # Check datetime
    date_count = 0
    for v in non_null:
        if isinstance(v, str) and len(v.strip()) >= 8 and not v.strip().isdigit():
            clean_v = v.strip().replace("Z", "+00:00")
            try:
                datetime.fromisoformat(clean_v)
                date_count += 1
            except ValueError:
                pass
    if date_count / len(non_null) >= 0.8:
        return ColumnDataType.DATETIME

    # Check numerical (numeric integers, floats; excluding bool)
    num_count = sum(
        1 for v in non_null
        if (isinstance(v, (int, float)) and not isinstance(v, bool))
        or (isinstance(v, str) and _is_numeric_str(v))
    )
    if num_count / len(non_null) >= 0.8:
        return ColumnDataType.NUMERICAL

    return ColumnDataType.CATEGORICAL


def compute_numerical_stats(
    values: list[float],
    num_bins: int = 10,
) -> NumericalStats:
    """Compute summary statistics, outlier counts, and histogram for numerical values.

    Pre-conditions:
        - ``values`` is a non-empty list of finite floating-point numbers.
        - ``num_bins >= 2``.
    Post-conditions:
        - Returns validated ``NumericalStats`` with min, quartiles, mean, std, skewness,
          z-score and IQR outlier counts, and histogram bins.
    """
    if not values:
        raise ValueError("values cannot be empty for compute_numerical_stats")
    if num_bins < 2:
        raise ValueError("num_bins must be at least 2")

    arr = np.asarray(values, dtype=float)
    n = len(arr)

    val_min = float(np.min(arr))
    val_max = float(np.max(arr))
    p25 = float(np.percentile(arr, 25))
    median = float(np.median(arr))
    p75 = float(np.percentile(arr, 75))
    mean = float(np.mean(arr))
    std = float(np.std(arr))

    iqr = p75 - p25
    lower_iqr = p25 - 1.5 * iqr
    upper_iqr = p75 + 1.5 * iqr
    outlier_iqr = int(np.sum((arr < lower_iqr) | (arr > upper_iqr)))

    if std > 1e-9:
        z_scores = np.abs((arr - mean) / std)
        outlier_z = int(np.sum(z_scores > 3.0))
        m3 = float(np.mean((arr - mean) ** 3))
        skewness = float(m3 / (std ** 3))
    else:
        outlier_z = 0
        skewness = 0.0

    counts, bin_edges = np.histogram(arr, bins=num_bins)
    histogram: list[HistogramBin] = []
    for i in range(num_bins):
        b_start = float(bin_edges[i])
        b_end = float(bin_edges[i + 1])
        b_cnt = int(counts[i])
        b_freq = max(0.0, min(1.0, round(b_cnt / n, 6)))
        histogram.append(
            HistogramBin(
                bin_start=b_start,
                bin_end=b_end,
                count=b_cnt,
                frequency=b_freq,
            )
        )

    return NumericalStats(
        min=val_min,
        p25=p25,
        median=median,
        p75=p75,
        max=val_max,
        mean=mean,
        std=max(0.0, std),
        skewness=skewness,
        outlier_count_zscore=outlier_z,
        outlier_count_iqr=outlier_iqr,
        histogram=histogram,
    )


def compute_correlation_matrix(
    rows: list[dict[str, Any]],
    numeric_columns: list[str],
) -> tuple[list[str], list[list[float]]]:
    """Compute symmetric Pearson correlation matrix across numeric columns.

    Pre-conditions:
        - ``rows`` is a non-empty list of dictionaries.
        - ``numeric_columns`` lists numerical column names to correlate.
    Post-conditions:
        - Returns tuple of (numeric_columns, correlation_matrix).
        - Correlation matrix is symmetric d x d with 1.0 on diagonal.
        - Missing values are imputed with column means during correlation calculation.
    """
    if not rows or not numeric_columns:
        return ([], [])

    d = len(numeric_columns)
    matrix: list[list[float]] = [[0.0] * d for _ in range(d)]

    col_data: list[np.ndarray[Any, np.dtype[np.float64]]] = []
    for col in numeric_columns:
        raw_vals = [r.get(col) for r in rows]
        valid_vals = [
            float(v) for v in raw_vals
            if v is not None and isinstance(v, (int, float)) and not isinstance(v, bool)
        ]
        mean_val = float(np.mean(valid_vals)) if valid_vals else 0.0
        imputed_list = [
            float(v)
            if v is not None and isinstance(v, (int, float)) and not isinstance(v, bool)
            else mean_val
            for v in raw_vals
        ]
        imputed = np.asarray(imputed_list, dtype=np.float64)
        col_data.append(imputed)

    for i in range(d):
        matrix[i][i] = 1.0
        std_i = float(np.std(col_data[i]))
        for j in range(i + 1, d):
            std_j = float(np.std(col_data[j]))
            if std_i > 1e-9 and std_j > 1e-9:
                r = float(np.corrcoef(col_data[i], col_data[j])[0, 1])
                r_clamped = max(-1.0, min(1.0, round(r, 4)))
            else:
                r_clamped = 0.0
            matrix[i][j] = r_clamped
            matrix[j][i] = r_clamped

    return (numeric_columns, matrix)


def profile_dataset(
    dataset_id: str,
    dataset_name: str,
    rows: list[dict[str, Any]],
) -> DatasetProfileReport:
    """Analyze a dataset to compute quality metrics, PII findings, and distributions.

    Pre-conditions:
        - ``rows`` is a non-empty list of dictionaries.
        - ``dataset_id`` and ``dataset_name`` are non-empty strings.
    Post-conditions:
        - Returns comprehensive ``DatasetProfileReport``.
        - Identifies duplicates, missing values, outliers, formatting issues, and PII.
        - Computes bounded data_quality_score and privacy_risk_score in [0.0, 1.0].
    """
    if not rows:
        raise ValueError("Cannot profile an empty dataset")

    row_count = len(rows)
    column_names = list(rows[0].keys())
    column_count = len(column_names)

    # Exact duplicate row detection
    seen: set[tuple[tuple[str, str], ...]] = set()
    duplicate_row_count = 0
    for r in rows:
        key = tuple(sorted((k, str(v)) for k, v in r.items()))
        if key in seen:
            duplicate_row_count += 1
        else:
            seen.add(key)

    columns: list[ColumnProfile] = []
    pii_findings: list[PIIFinding] = []
    quality_issues: list[DataQualityIssue] = []

    # Duplicate rows quality issue
    if duplicate_row_count > 0:
        quality_issues.append(
            DataQualityIssue(
                issue_id="issue-duplicate-rows",
                issue_type=DataQualityIssueType.DUPLICATE_ROWS,
                severity=IssueSeverity.HIGH,
                column_name=None,
                affected_rows=duplicate_row_count,
                affected_ratio=round(duplicate_row_count / row_count, 4),
                description=f"Dataset contains {duplicate_row_count} duplicate row(s).",
                suggested_action="Deduplicate rows to prevent synthesizer density distortion.",
            )
        )

    for col in column_names:
        values = [r.get(col) for r in rows]
        total_count = len(values)
        null_count = sum(1 for v in values if v is None)
        null_ratio = round(null_count / total_count, 4)

        non_null = [v for v in values if v is not None]
        unique_set = set(str(v) for v in non_null)
        unique_count = len(unique_set)
        unique_ratio = round(unique_count / max(1, len(non_null)), 4)

        pii_finding = detect_column_pii(col, values)
        if pii_finding is not None:
            pii_findings.append(pii_finding)
            pii_type = pii_finding.pii_type
            # Unmasked PII issue
            quality_issues.append(
                DataQualityIssue(
                    issue_id=f"issue-pii-{col}",
                    issue_type=DataQualityIssueType.UNMASKED_PII,
                    severity=IssueSeverity.CRITICAL,
                    column_name=col,
                    affected_rows=len(non_null),
                    affected_ratio=round(len(non_null) / row_count, 4),
                    description=f"Column '{col}' contains unmasked {pii_type.value} identifiers.",
                    suggested_action="Anonymize or tokenize PII before synthetic model training.",
                )
            )
        else:
            pii_type = PIIType.NONE

        inferred_type = infer_column_type(col, values, pii_finding)

        # Missing values quality issue
        if null_count > 0:
            quality_issues.append(
                DataQualityIssue(
                    issue_id=f"issue-missing-{col}",
                    issue_type=DataQualityIssueType.MISSING_VALUES,
                    severity=IssueSeverity.HIGH if null_ratio >= 0.20 else IssueSeverity.MEDIUM,
                    column_name=col,
                    affected_rows=null_count,
                    affected_ratio=null_ratio,
                    description=(
                        f"Column '{col}' has {null_count} ({null_ratio:.1%}) missing value(s)."
                    ),
                    suggested_action=(
                        "Impute missing values using column median (numerical) "
                        "or mode (categorical)."
                    ),
                )
            )

        num_stats: NumericalStats | None = None
        top_cats: list[CategoryFrequency] = []

        if inferred_type == ColumnDataType.NUMERICAL:
            floats = [
                float(v) for v in non_null
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]
            if floats:
                num_stats = compute_numerical_stats(floats)
                if num_stats.outlier_count_zscore > 0:
                    quality_issues.append(
                        DataQualityIssue(
                            issue_id=f"issue-outlier-{col}",
                            issue_type=DataQualityIssueType.NUMERICAL_OUTLIERS,
                            severity=IssueSeverity.MEDIUM,
                            column_name=col,
                            affected_rows=num_stats.outlier_count_zscore,
                            affected_ratio=round(num_stats.outlier_count_zscore / row_count, 4),
                            description=(
                                f"Column '{col}' contains {num_stats.outlier_count_zscore} "
                                f"extreme outlier(s) (|z| > 3.0)."
                            ),
                            suggested_action=(
                                "Winsorize extreme outliers to IQR boundaries to stabilize models."
                            ),
                        )
                    )
        else:
            # Categorical frequency counts
            cat_counts: dict[str, int] = {}
            for v in non_null:
                s = str(v)
                cat_counts[s] = cat_counts.get(s, 0) + 1
            sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            top_cats = [
                CategoryFrequency(
                    value=item[0],
                    count=item[1],
                    frequency=round(item[1] / max(1, len(non_null)), 4),
                )
                for item in sorted_cats
            ]

            # Inconsistent formatting check on strings
            inconsistent_count = 0
            for v in non_null:
                if isinstance(v, str):
                    s = v.strip()
                    if v != s:
                        inconsistent_count += 1
                    elif len(s) == 2 and s.isalpha() and not s.isupper():
                        inconsistent_count += 1
            if inconsistent_count > 0:
                quality_issues.append(
                    DataQualityIssue(
                        issue_id=f"issue-format-{col}",
                        issue_type=DataQualityIssueType.INCONSISTENT_FORMATTING,
                        severity=IssueSeverity.LOW,
                        column_name=col,
                        affected_rows=inconsistent_count,
                        affected_ratio=round(inconsistent_count / row_count, 4),
                        description=(
                            f"Column '{col}' contains inconsistent casing or whitespace formatting."
                        ),
                        suggested_action="Normalize whitespace and uppercase standard codes.",
                    )
                )

        sample_vals = non_null[:5]
        columns.append(
            ColumnProfile(
                name=col,
                inferred_type=inferred_type,
                total_count=total_count,
                null_count=null_count,
                null_ratio=null_ratio,
                unique_count=unique_count,
                unique_ratio=unique_ratio,
                pii_type=pii_type,
                numerical_stats=num_stats,
                top_categories=top_cats,
                sample_values=sample_vals,
            )
        )

    # Compute correlation matrix over numeric columns
    num_cols = [c.name for c in columns if c.inferred_type == ColumnDataType.NUMERICAL]
    corr_cols, corr_matrix = compute_correlation_matrix(rows, num_cols)

    # Quality and privacy score formulas
    penalty = 0.0
    if duplicate_row_count > 0:
        penalty += 0.03 + 0.05 * min(1.0, duplicate_row_count / row_count)
    for c in columns:
        if c.null_count > 0:
            penalty += 0.02 + 0.05 * c.null_ratio
        if c.numerical_stats and c.numerical_stats.outlier_count_zscore > 0:
            penalty += 0.02 + 0.05 * (c.numerical_stats.outlier_count_zscore / row_count)
    for issue in quality_issues:
        if issue.issue_type == DataQualityIssueType.INCONSISTENT_FORMATTING:
            penalty += 0.01 + 0.03 * issue.affected_ratio

    data_quality_score = max(0.0, min(1.0, round(1.0 - penalty, 4)))
    privacy_risk_score = round(len(pii_findings) / max(1, column_count), 4)

    return DatasetProfileReport(
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        row_count=row_count,
        column_count=column_count,
        duplicate_row_count=duplicate_row_count,
        data_quality_score=data_quality_score,
        privacy_risk_score=privacy_risk_score,
        columns=columns,
        pii_findings=pii_findings,
        quality_issues=quality_issues,
        correlation_columns=corr_cols,
        correlation_matrix=corr_matrix,
        profiled_at=datetime.now(),
    )


def cleanse_dataset(
    rows: list[dict[str, Any]],
    anonymize_pii: bool = True,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Cleanse, deduplicate, normalize, impute, and anonymize a dataset.

    Pre-conditions:
        - ``rows`` is a non-empty list of dictionaries.
        - ``seed`` is an integer seed for deterministic processing.
    Post-conditions:
        - Returns a new list of cleansed dictionaries.
        - Exact duplicate rows are removed.
        - Inconsistent whitespace and 2-letter state codes are normalized.
        - Missing values are imputed (median for numerical, mode for categorical).
        - Numerical outliers are clamped via iterative z-score Winsorization.
        - If ``anonymize_pii=True``, PII columns are safely pseudonymized.
    """
    if not rows:
        return []

    # 1. Deduplicate rows while preserving order
    seen_keys: set[tuple[tuple[str, str], ...]] = set()
    cleaned_rows: list[dict[str, Any]] = []
    for r in rows:
        key = tuple(sorted((k, str(v)) for k, v in r.items()))
        if key not in seen_keys:
            seen_keys.add(key)
            cleaned_rows.append(dict(r))

    col_names = list(cleaned_rows[0].keys())

    # 2. Detect PII before modifying values
    pii_map: dict[str, PIIFinding] = {}
    for col in col_names:
        vals = [r.get(col) for r in cleaned_rows]
        finding = detect_column_pii(col, vals)
        if finding is not None:
            pii_map[col] = finding

    # 3. Anonymize PII if requested
    if anonymize_pii:
        for col, finding in pii_map.items():
            for i in range(len(cleaned_rows)):
                idx_str = f"{i + 1:04d}"
                if finding.pii_type == PIIType.EMAIL:
                    cleaned_rows[i][col] = f"anon{idx_str}@synthetic.invalid"
                elif finding.pii_type == PIIType.SSN:
                    cleaned_rows[i][col] = f"XXX-XX-{idx_str}"
                elif finding.pii_type == PIIType.PHONE:
                    cleaned_rows[i][col] = f"+1-555-000-{idx_str}"
                elif finding.pii_type == PIIType.CREDIT_CARD:
                    cleaned_rows[i][col] = f"XXXX-XXXX-XXXX-{idx_str}"
                elif finding.pii_type == PIIType.MEDICAL_RECORD_NUMBER:
                    cleaned_rows[i][col] = f"ANON-MRN-{i + 1:06d}"
                elif finding.pii_type == PIIType.IP_ADDRESS:
                    cleaned_rows[i][col] = "0.0.0.0"
                elif finding.pii_type == PIIType.PERSON_NAME:
                    cleaned_rows[i][col] = f"ANON-PERSON-{idx_str}"

    # 4. Normalize string whitespace and casing (state codes)
    for col in col_names:
        if col in pii_map and anonymize_pii:
            continue
        for row in cleaned_rows:
            v = row.get(col)
            if isinstance(v, str):
                s = v.strip()
                if len(s) == 2 and s.isalpha():
                    row[col] = s.upper()
                else:
                    row[col] = s

    # 5. Impute missing values
    for col in col_names:
        col_vals = [r.get(col) for r in cleaned_rows]
        null_count = sum(1 for v in col_vals if v is None)
        if null_count > 0:
            non_null = [v for v in col_vals if v is not None]
            if not non_null:
                continue
            is_num = all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                for v in non_null
            )
            if is_num:
                med = float(np.median([float(v) for v in non_null]))
                is_all_int = all(isinstance(v, int) for v in non_null)
                imputed = int(round(med)) if is_all_int else round(med, 2)
                for r in cleaned_rows:
                    if r.get(col) is None:
                        r[col] = imputed
            else:
                cat_counts: dict[Any, int] = {}
                for v in non_null:
                    cat_counts[v] = cat_counts.get(v, 0) + 1
                mode_val = max(cat_counts.items(), key=lambda x: x[1])[0]
                for r in cleaned_rows:
                    if r.get(col) is None:
                        r[col] = mode_val

    # 6. Clamp numerical outliers via iterative z-score Winsorization
    for col in col_names:
        if col in pii_map and anonymize_pii:
            continue
        col_vals = [r.get(col) for r in cleaned_rows]
        is_num = all(
            isinstance(v, (int, float)) and not isinstance(v, bool)
            for v in col_vals
        )
        if is_num and col_vals:
            num_list: list[float] = [
                float(v) for v in col_vals if isinstance(v, (int, float))
            ]
            arr = np.asarray(num_list, dtype=np.float64)
            for _ in range(10):
                mean_val = float(np.mean(arr))
                std_val = float(np.std(arr))
                if std_val < 1e-9:
                    break
                z_scores = np.abs((arr - mean_val) / std_val)
                if np.all(z_scores <= 3.0):
                    break
                lower_b = mean_val - 2.8 * std_val
                upper_b = mean_val + 2.8 * std_val
                arr = np.clip(arr, lower_b, upper_b)

            is_all_int = all(isinstance(v, int) for v in col_vals)
            for i in range(len(cleaned_rows)):
                if is_all_int:
                    cleaned_rows[i][col] = int(round(float(arr[i])))
                else:
                    cleaned_rows[i][col] = round(float(arr[i]), 2)

    return cleaned_rows
