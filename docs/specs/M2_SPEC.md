# Milestone 2 Specification (`M2_SPEC.md`): Automated Data Quality Auditor, PII/PHI Scanner & Statistical Profiler

## 1. Objective

Implement the automated dataset parser, schema type inference engine, multi-signal PII/PHI scanner, data quality defect auditor, dataset cleanser/anonymizer, and statistical distribution/correlation profiler in `src/synthai_studio/profiler.py`, verified by `tests/test_profiler.py`.

---

## 2. Non-Negotiable Engineering Invariants

1. **Absolute Imports Only**: Use `from synthai_studio...` exclusively. Zero relative imports.
2. **Design by Contract (DbC)**: Every public class, method, and function MUST include a docstring with explicit `Pre-conditions:` and `Post-conditions:` sections.
3. **Zero Emojis**: Do not include any emoji characters in source code, docstrings, or tests.
4. **Strict Static Typing**: `poetry run ruff check .` and `poetry run mypy src tests` must pass cleanly.

---

## 3. Target Files & Public Contracts

### 3.1 `src/synthai_studio/profiler.py`

Expose the following public functions:

1. `parse_tabular_payload(raw_data: bytes | str, filename: str = "dataset.csv") -> list[dict[str, Any]]`
   - **Pre-conditions**: `raw_data` is non-empty UTF-8 CSV or JSON bytes/string.
   - **Post-conditions**: Parses CSV (using `csv.DictReader`, converting empty strings `""` or `"NULL"`/`"null"`/`"NaN"` to `None`, parsing ints, floats, booleans) or JSON (array of objects or `{"rows": [...]}` / `{"data": [...]}`) into a non-empty list of row dicts. Raises `ValueError` if empty or malformed.

2. `detect_column_pii(column_name: str, values: list[Any]) -> PIIFinding | None`
   - **Pre-conditions**: `column_name` is a non-empty string; `values` contains column values.
   - **Post-conditions**: Inspects column name heuristics and regex patterns across non-null stringified values for:
     - `PIIType.EMAIL`: email regex or `"email"` in column name.
     - `PIIType.SSN`: `\b\d{3}-\d{2}-\d{4}\b` or `"ssn"` in column name.
     - `PIIType.PHONE`: phone number patterns or `"phone"` / `"mobile"` in column name.
     - `PIIType.CREDIT_CARD`: 13-19 digit card patterns or `"card_number"` / `"credit_card"` in column name.
     - `PIIType.MEDICAL_RECORD_NUMBER`: `^MRN-\d+` or `"mrn"` / `"medical_record"` in column name.
     - `PIIType.IP_ADDRESS`: IPv4 pattern `\b(?:\d{1,3}\.){3}\d{1,3}\b` or `"ip_address"` in column name.
     - `PIIType.PERSON_NAME`: `"name"` in column name (excluding `"dataset_name"`, `"column_name"`, `"filename"`, `"merchant"`, `"company"`) and values matching two or more capitalized words.
   - Returns `PIIFinding` when detected, else `None`.

3. `infer_column_type(column_name: str, values: list[Any], pii_finding: PIIFinding | None = None) -> ColumnDataType`
   - **Pre-conditions**: `column_name` is non-empty.
   - **Post-conditions**:
     - If `pii_finding is not None`, returns `ColumnDataType.IDENTIFIER_PII`.
     - If non-null values are `bool` (or strings `"true"`/`"false"`), returns `ColumnDataType.BOOLEAN`.
     - If `>= 80%` of non-null values parse as ISO-8601 date/datetime strings (`YYYY-MM-DD...`) and are not plain numbers, returns `ColumnDataType.DATETIME`.
     - If `>= 80%` of non-null values are `int` or `float` (excluding `bool`), returns `ColumnDataType.NUMERICAL` (note: binary `{0, 1}` integer flags like `is_fraud`, `readmitted_30d`, `churned` are treated as `ColumnDataType.NUMERICAL` or `CATEGORICAL`—keep numeric `{0, 1}` as `ColumnDataType.NUMERICAL` so correlation matrices and numeric stats include target flags!).
     - Otherwise returns `ColumnDataType.CATEGORICAL`.

4. `compute_numerical_stats(values: list[float], num_bins: int = 10) -> NumericalStats`
   - **Pre-conditions**: `values` is a non-empty list of finite floats; `num_bins >= 2`.
   - **Post-conditions**: Computes `min`, `p25`, `median`, `p75`, `max`, `mean`, population/sample `std` (`>= 0.0`), `skewness`, `outlier_count_zscore` ($|z| > 3.0$), `outlier_count_iqr` ($x < Q_1 - 1.5 \cdot \text{IQR}$ or $x > Q_3 + 1.5 \cdot \text{IQR}$), and a `num_bins`-element list of `HistogramBin` with `frequency` summing to `1.0` (within floating-point tolerance).

5. `compute_correlation_matrix(rows: list[dict[str, Any]], numeric_columns: list[str]) -> tuple[list[str], list[list[float]]]`
   - **Pre-conditions**: `rows` is non-empty; `numeric_columns` lists numerical column names.
   - **Post-conditions**: Returns `(numeric_columns, matrix)` where `matrix` is a symmetric $d \times d$ Pearson correlation matrix with `1.0` on the diagonal and entries clamped to `[-1.0, 1.0]`. Missing values are imputed with column means during correlation calculation.

6. `profile_dataset(dataset_id: str, dataset_name: str, rows: list[dict[str, Any]]) -> DatasetProfileReport`
   - **Pre-conditions**: `rows` is a non-empty list of dictionaries.
   - **Post-conditions**:
     - Computes `ColumnProfile` for every column in the dataset.
     - Populates `pii_findings` for all detected PII/PHI columns.
     - Detects and populates `quality_issues` (`DataQualityIssue`):
       - `DUPLICATE_ROWS` if exact duplicate rows exist (`duplicate_row_count > 0`).
       - `MISSING_VALUES` for any column with `null_count > 0`.
       - `NUMERICAL_OUTLIERS` for any numerical column with `outlier_count_zscore > 0`.
       - `INCONSISTENT_FORMATTING` for any categorical column containing leading/trailing whitespace or mixed-case duplicates (e.g., `" ca "`, `"ny"`, `"CA"`).
       - `UNMASKED_PII` for any column with `pii_finding is not None` whose values are not already anonymized/redacted tokens.
     - Computes `data_quality_score` in `[0.0, 1.0]` (penalizing missing values, duplicates, outliers, and formatting issues so raw benchmarks score `< 0.95` and cleansed datasets score `>= 0.95`).
     - Computes `privacy_risk_score` in `[0.0, 1.0]` proportional to unmasked PII column ratio.
     - Computes `correlation_columns` and `correlation_matrix`.

7. `cleanse_dataset(rows: list[dict[str, Any]], anonymize_pii: bool = True, seed: int = 42) -> list[dict[str, Any]]`
   - **Pre-conditions**: `rows` is a non-empty list of dictionaries.
   - **Post-conditions**:
     - Returns a new deep-copied list of rows with:
       1. Exact duplicate rows removed.
       2. Categorical string values stripped of leading/trailing whitespace, and 2-letter US state codes normalized to uppercase (`" ca " -> "CA"`, `"ny" -> "NY"`).
       3. Missing values (`None`) imputed: median for numerical columns, mode (most frequent value) for categorical/datetime/boolean columns.
       4. Extreme numerical outliers ($|z| > 3.0$) clamped (Winsorized) to `[Q1 - 1.5 * IQR, Q3 + 1.5 * IQR]` (preserving integer type if the column consists of integers).
       5. If `anonymize_pii=True`, replaces detected PII column values with deterministic synthetic/pseudonymized equivalents that will not trigger `UNMASKED_PII` or collide with raw PII (or sets column values to anonymized format like `ANON-USER-0001`, `anon0001@synthetic.invalid`, `XXX-XX-0001`, etc., or re-maps PII safely). Specifically, to ensure `profile_dataset` on a cleansed dataset has lower `privacy_risk_score` and higher `data_quality_score`, pseudonymize PII values cleanly and deterministically.

---

### 3.2 `tests/test_profiler.py`
Write comprehensive unit tests covering:
- `parse_tabular_payload` for both CSV and JSON inputs, plus error handling on empty input.
- `detect_column_pii` across all 7 PII types (`EMAIL`, `SSN`, `PHONE`, `CREDIT_CARD`, `MEDICAL_RECORD_NUMBER`, `PERSON_NAME`, `IP_ADDRESS`) and negative cases.
- `profile_dataset` on all 3 benchmark datasets (`healthcare_hipaa_readmissions`, `fintech_fraud_transactions`, `saas_customer_churn`), verifying that planted missing values, duplicate rows, numerical outliers, inconsistent formatting, and PII findings are all detected.
- `cleanse_dataset` verifying that duplicate rows are eliminated, missing values are reduced to zero, extreme outliers are clamped, state formatting is normalized to uppercase, and `data_quality_score` strictly increases after cleansing.
