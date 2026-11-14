"""Unit tests for SynthAI Studio dataset profiler, PII scanner, and cleanser.

Pre-conditions:
    - ``synthai_studio.profiler`` and ``synthai_studio.benchmarks`` are importable.
    - ``pytest`` and ``numpy`` are installed.
Post-conditions:
    - All tests pass deterministically without network egress.
"""

import pytest

from synthai_studio.benchmarks import generate_benchmark_dataset
from synthai_studio.models import (
    ColumnDataType,
    DataQualityIssueType,
    PIIType,
)
from synthai_studio.profiler import (
    cleanse_dataset,
    compute_correlation_matrix,
    compute_numerical_stats,
    detect_column_pii,
    infer_column_type,
    parse_tabular_payload,
    profile_dataset,
)


def test_parse_tabular_payload_csv() -> None:
    """Verify parsing of valid and invalid CSV payloads.

    Pre-conditions:
        - Tabular CSV payloads with various scalar types and null sentinels.
    Post-conditions:
        - Accurately converts types, maps null sentinels to None, raises on empty input.
    """
    csv_text = """patient_name,age,active,billing,state
Alice Smith,30,true,1200.50,CA
Bob Jones,,false,NULL, ca 
Charlie Brown,45,true,NaN,NY
"""
    rows = parse_tabular_payload(csv_text, filename="patients.csv")
    assert len(rows) == 3
    assert rows[0] == {
        "patient_name": "Alice Smith",
        "age": 30,
        "active": True,
        "billing": 1200.5,
        "state": "CA",
    }
    assert rows[1]["age"] is None
    assert rows[1]["active"] is False
    assert rows[1]["billing"] is None
    assert rows[1]["state"] == " ca "
    assert rows[2]["billing"] is None

    # Test bytes input with UTF-8
    csv_bytes = csv_text.encode("utf-8")
    rows_bytes = parse_tabular_payload(csv_bytes, filename="patients.csv")
    assert len(rows_bytes) == 3

    # Test empty payload raises ValueError
    with pytest.raises(ValueError):
        parse_tabular_payload("", filename="empty.csv")
    with pytest.raises(ValueError):
        parse_tabular_payload("   \n  ", filename="empty.csv")


def test_parse_tabular_payload_json() -> None:
    """Verify parsing of JSON array and object payloads.

    Pre-conditions:
        - JSON payloads with direct array and wrapped rows/data keys.
    Post-conditions:
        - Successfully parses records and handles nulls and malformed structures.
    """
    json_array = '[{"id": 1, "name": "Alice"}, {"id": 2, "name": null}]'
    rows_arr = parse_tabular_payload(json_array, filename="data.json")
    assert len(rows_arr) == 2
    assert rows_arr[0] == {"id": 1, "name": "Alice"}
    assert rows_arr[1]["name"] is None

    json_wrapped = '{"rows": [{"id": 3, "status": "active"}]}'
    rows_wrapped = parse_tabular_payload(json_wrapped, filename="data.json")
    assert len(rows_wrapped) == 1
    assert rows_wrapped[0] == {"id": 3, "status": "active"}

    # Malformed JSON raises ValueError
    with pytest.raises(ValueError):
        parse_tabular_payload("{not-valid-json", filename="data.json")

    # Empty array raises ValueError
    with pytest.raises(ValueError):
        parse_tabular_payload("[]", filename="data.json")

    # Object without rows/data raises ValueError
    with pytest.raises(ValueError):
        parse_tabular_payload('{"foo": "bar"}', filename="data.json")


def test_detect_column_pii_all_types() -> None:
    """Verify PII detection across all 7 supported PII categories.

    Pre-conditions:
        - Synthetic sample lists matching each PII pattern.
    Post-conditions:
        - Correctly returns a PIIFinding with corresponding PIIType.
    """
    # 1. Email
    emails = ["john.doe@example.com", "jane.smith@corp.org", "support@test.io"]
    res_email = detect_column_pii("contact_email", emails)
    assert res_email is not None
    assert res_email.pii_type == PIIType.EMAIL

    # 2. SSN
    ssns = ["123-45-6789", "987-65-4321", "555-12-3456"]
    res_ssn = detect_column_pii("ssn", ssns)
    assert res_ssn is not None
    assert res_ssn.pii_type == PIIType.SSN

    # 3. Phone
    phones = ["+1-555-123-4567", "555-987-6543", "+1-555-444-2222"]
    res_phone = detect_column_pii("phone", phones)
    assert res_phone is not None
    assert res_phone.pii_type == PIIType.PHONE

    # 4. Credit Card
    cards = ["4111-2222-3333-4444", "5500-0000-1111-2222"]
    res_card = detect_column_pii("credit_card", cards)
    assert res_card is not None
    assert res_card.pii_type == PIIType.CREDIT_CARD

    # 5. MRN
    mrns = ["MRN-12345678", "MRN-87654321", "MRN-00012345"]
    res_mrn = detect_column_pii("mrn", mrns)
    assert res_mrn is not None
    assert res_mrn.pii_type == PIIType.MEDICAL_RECORD_NUMBER

    # 6. IP Address
    ips = ["192.168.1.1", "10.0.0.254", "198.51.100.42"]
    res_ip = detect_column_pii("ip_address", ips)
    assert res_ip is not None
    assert res_ip.pii_type == PIIType.IP_ADDRESS

    # 7. Person Name
    names = ["James Smith", "Patricia Johnson", "Robert Williams"]
    res_name = detect_column_pii("patient_name", names)
    assert res_name is not None
    assert res_name.pii_type == PIIType.PERSON_NAME


def test_detect_column_pii_negatives_and_anonymized() -> None:
    """Verify that non-PII and anonymized tokens do not trigger PII findings.

    Pre-conditions:
        - Regular categorical columns and pseudonymized/anonymized token lists.
    Post-conditions:
        - detect_column_pii returns None for all negative and anonymized inputs.
    """
    # Non-PII columns
    assert detect_column_pii("state", ["CA", "NY", "TX", "FL"]) is None
    assert detect_column_pii("department", ["CARDIOLOGY", "NEUROLOGY"]) is None
    assert detect_column_pii("empty_col", [None, None, None]) is None

    # Anonymized tokens must not trigger findings
    anon_names = [f"ANON-PERSON-{i:04d}" for i in range(1, 20)]
    assert detect_column_pii("patient_name", anon_names) is None

    anon_emails = [f"anon{i:04d}@synthetic.invalid" for i in range(1, 20)]
    assert detect_column_pii("email", anon_emails) is None

    anon_ssns = [f"XXX-XX-{i:04d}" for i in range(1, 20)]
    assert detect_column_pii("ssn", anon_ssns) is None

    anon_mrns = [f"ANON-MRN-{i:06d}" for i in range(1, 20)]
    assert detect_column_pii("mrn", anon_mrns) is None

    anon_ips = ["0.0.0.0"] * 20
    assert detect_column_pii("ip_address", anon_ips) is None


def test_infer_column_type() -> None:
    """Verify schema column type inference across types.

    Pre-conditions:
        - Sample lists of booleans, datetimes, numbers, and categories.
    Post-conditions:
        - Correct ColumnDataType enum member is returned.
    """
    # When PII finding is present
    finding = detect_column_pii("ssn", ["123-45-6789"])
    assert infer_column_type("ssn", ["123-45-6789"], finding) == ColumnDataType.IDENTIFIER_PII

    # Booleans
    assert infer_column_type("flag", [True, False, True]) == ColumnDataType.BOOLEAN
    assert infer_column_type("flag_str", ["true", "false", "true"]) == ColumnDataType.BOOLEAN

    # Datetimes
    dates = ["2024-01-15", "2024-02-20", "2024-03-25"]
    assert infer_column_type("admission_date", dates) == ColumnDataType.DATETIME

    # Numerical (including binary integers)
    assert infer_column_type("age", [25, 40, 65, 80]) == ColumnDataType.NUMERICAL
    assert infer_column_type("amount", [12.5, 99.0, 450.2]) == ColumnDataType.NUMERICAL
    assert infer_column_type("is_fraud", [0, 1, 0, 0, 1]) == ColumnDataType.NUMERICAL

    # Categorical
    assert infer_column_type("state", ["CA", "NY", "TX"]) == ColumnDataType.CATEGORICAL


def test_compute_numerical_stats() -> None:
    """Verify numerical statistics, quantile calculations, and outlier detection.

    Pre-conditions:
        - List of numerical values with known summary properties and planted outliers.
    Post-conditions:
        - Accurately computes min, max, mean, std, outliers, and histogram bins.
    """
    values = [15.0 + float(i) for i in range(30)] + [1000.0]
    stats = compute_numerical_stats(values, num_bins=5)

    assert stats.min == 15.0
    assert stats.max == 1000.0
    assert stats.outlier_count_zscore >= 1
    assert stats.outlier_count_iqr >= 1
    assert len(stats.histogram) == 5

    # Total counts in histogram equals length of values
    total_hist_count = sum(b.count for b in stats.histogram)
    assert total_hist_count == len(values)

    # Empty values validation
    with pytest.raises(ValueError):
        compute_numerical_stats([])
    with pytest.raises(ValueError):
        compute_numerical_stats([1.0, 2.0], num_bins=1)


def test_compute_correlation_matrix() -> None:
    """Verify symmetric correlation matrix computation.

    Pre-conditions:
        - Tabular rows with correlated numeric columns.
    Post-conditions:
        - Returns symmetric matrix with 1.0 on diagonal and valid Pearson entries.
    """
    rows = [
        {"x": 1.0, "y": 2.0, "z": 10.0},
        {"x": 2.0, "y": 4.0, "z": 9.0},
        {"x": 3.0, "y": 6.0, "z": 8.0},
        {"x": 4.0, "y": 8.0, "z": 7.0},
        {"x": 5.0, "y": 10.0, "z": 6.0},
    ]
    cols, matrix = compute_correlation_matrix(rows, ["x", "y", "z"])
    assert cols == ["x", "y", "z"]
    assert len(matrix) == 3
    assert matrix[0][0] == 1.0
    assert matrix[1][1] == 1.0
    assert matrix[2][2] == 1.0

    # x and y are perfectly correlated
    assert pytest.approx(matrix[0][1], abs=1e-3) == 1.0
    # x and z are negatively correlated
    assert pytest.approx(matrix[0][2], abs=1e-3) == -1.0


def test_profile_dataset_benchmarks() -> None:
    """Verify profiler behavior across all 3 built-in benchmark seed datasets.

    Pre-conditions:
        - Generate raw benchmark datasets containing planted defects.
    Post-conditions:
        - Detects duplicates, missing values, extreme outliers, inconsistent states, and PII.
        - data_quality_score < 0.95 and privacy_risk_score > 0.0 on all raw benchmarks.
    """
    benchmarks = [
        "healthcare_hipaa_readmissions",
        "fintech_fraud_transactions",
        "saas_customer_churn",
    ]

    for bid in benchmarks:
        raw_data = generate_benchmark_dataset(bid, row_count=500, seed=42)
        report = profile_dataset(f"ds-{bid}", bid, raw_data)

        assert report.row_count == 500
        assert report.duplicate_row_count == 2
        assert report.data_quality_score < 0.95
        assert report.privacy_risk_score > 0.0

        issue_types = {issue.issue_type for issue in report.quality_issues}
        assert DataQualityIssueType.DUPLICATE_ROWS in issue_types
        assert DataQualityIssueType.MISSING_VALUES in issue_types
        assert DataQualityIssueType.NUMERICAL_OUTLIERS in issue_types
        assert DataQualityIssueType.INCONSISTENT_FORMATTING in issue_types
        assert DataQualityIssueType.UNMASKED_PII in issue_types

        # Verify correlation columns populated
        assert len(report.correlation_columns) > 0
        assert len(report.correlation_matrix) == len(report.correlation_columns)


def test_cleanse_dataset_and_reprofile() -> None:
    """Verify dataset cleansing pipeline on raw benchmarks.

    Pre-conditions:
        - Raw benchmark dataset with duplicates, missing values, outliers, dirty states, and PII.
    Post-conditions:
        - Cleansed dataset has 0 duplicates, 0 missing values, clamped outliers, normalized states.
        - Re-profiling yields data_quality_score >= 0.95, privacy_risk_score == 0.0, and 0 issues.
    """
    raw_data = generate_benchmark_dataset("healthcare_hipaa_readmissions", row_count=500, seed=42)
    cleansed = cleanse_dataset(raw_data, anonymize_pii=True, seed=42)

    # 1. Deduplication (500 -> 498)
    assert len(cleansed) == 498

    # 2. Missing values imputed
    null_counts = sum(
        sum(1 for v in r.values() if v is None)
        for r in cleansed
    )
    assert null_counts == 0

    # 3. Inconsistent states normalized
    states = {r["state"] for r in cleansed}
    assert " ca " not in states
    assert "ny" not in states
    assert "tx" not in states
    assert {"CA", "NY", "TX"}.issubset(states)

    # 4. Re-profiling audit
    report = profile_dataset("ds-clean", "Cleaned Healthcare", cleansed)
    assert report.duplicate_row_count == 0
    assert report.privacy_risk_score == 0.0
    assert report.data_quality_score >= 0.95
    assert len(report.quality_issues) == 0


def test_cleanse_dataset_without_anonymization() -> None:
    """Verify dataset cleansing when anonymize_pii is False.

    Pre-conditions:
        - Raw benchmark dataset passed to cleanse_dataset with anonymize_pii=False.
    Post-conditions:
        - Deduplicates and normalizes formatting, but leaves PII identifiers intact.
    """
    raw_data = generate_benchmark_dataset("healthcare_hipaa_readmissions", row_count=50, seed=42)
    cleansed = cleanse_dataset(raw_data, anonymize_pii=False, seed=42)

    # PII is still detected
    report = profile_dataset("ds-clean-no-anon", "Cleaned No Anon", cleansed)
    assert report.privacy_risk_score > 0.0
    pii_cols = {f.column_name for f in report.pii_findings}
    assert "patient_name" in pii_cols
    assert "ssn" in pii_cols
