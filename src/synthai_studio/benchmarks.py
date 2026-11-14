"""SynthAI Studio built-in deterministic benchmark datasets.

Pre-conditions:
    - Python >= 3.11 runtime environment with ``numpy`` installed.
Post-conditions:
    - Provides deterministic benchmark datasets with planted realistic defects,
      domain correlations, and target class imbalance for auditing.
"""

from datetime import datetime, timedelta
from typing import Any

import numpy as np

from synthai_studio.models import BenchmarkMetadata

__all__ = [
    "BENCHMARK_REGISTRY",
    "generate_benchmark_dataset",
    "get_benchmark_metadata",
    "list_benchmarks",
]

_FIRST_NAMES: list[str] = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
]

_LAST_NAMES: list[str] = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
]

_EMAIL_DOMAINS: list[str] = [
    "example.com",
    "healthcorp.org",
    "medcenter.net",
    "fintechglobal.io",
    "cloudscale.tech",
]

_VALID_STATES: list[str] = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]

BENCHMARK_REGISTRY: dict[str, BenchmarkMetadata] = {
    "healthcare_hipaa_readmissions": BenchmarkMetadata(
        benchmark_id="healthcare_hipaa_readmissions",
        name="Healthcare HIPAA Readmissions",
        domain="Healthcare",
        description=(
            "Inpatient hospital records with HIPAA identifiers, clinical comorbidity scores, "
            "and 30-day readmission outcomes."
        ),
        default_row_count=500,
        target_column="readmitted_30d",
        minority_label=1,
        pii_columns=["patient_name", "ssn", "mrn", "email"],
        highlights=[
            "HIPAA PII identifiers (SSN, MRN, Email)",
            "Planted duplicates, outliers, and dirty states",
            "Clinical risk vs readmission correlation",
            "Class imbalance (~16% readmitted)",
        ],
    ),
    "fintech_fraud_transactions": BenchmarkMetadata(
        benchmark_id="fintech_fraud_transactions",
        name="Fintech Fraud & Anomalous Transactions",
        domain="Financial Services",
        description=(
            "High-throughput payment transaction stream with merchant categories, "
            "network telemetry, and fraud labels."
        ),
        default_row_count=500,
        target_column="is_fraud",
        minority_label=1,
        pii_columns=["cardholder_name", "cardholder_email", "phone", "ip_address"],
        highlights=[
            "PCI and network telemetry PII",
            "Velocity and geolocation anomaly correlations",
            "Planted missing device trust scores and extreme amounts",
            "Class imbalance (~10% fraud)",
        ],
    ),
    "saas_customer_churn": BenchmarkMetadata(
        benchmark_id="saas_customer_churn",
        name="B2B SaaS Customer Subscription & Churn",
        domain="Enterprise Software",
        description=(
            "B2B subscription telemetry with seat licensing, usage metrics, "
            "support ticket volumes, and churn status."
        ),
        default_row_count=500,
        target_column="churned",
        minority_label=1,
        pii_columns=["contact_name", "contact_email", "phone"],
        highlights=[
            "B2B usage and revenue metrics",
            "Seat count vs MRR strong linear correlation",
            "Utilization vs NPS and support ticket correlations",
            "Class imbalance (~14% churn)",
        ],
    ),
}


def list_benchmarks() -> list[BenchmarkMetadata]:
    """Enumerate all available benchmark seed dataset specifications.

    Pre-conditions:
        - None.
    Post-conditions:
        - Returns a list containing all registered ``BenchmarkMetadata`` records.
    """
    return list(BENCHMARK_REGISTRY.values())


def get_benchmark_metadata(benchmark_id: str) -> BenchmarkMetadata:
    """Retrieve metadata descriptor for a specific benchmark dataset.

    Pre-conditions:
        - ``benchmark_id`` is a string identifier.
    Post-conditions:
        - Returns matching ``BenchmarkMetadata`` if found.
        - Raises ``KeyError`` if ``benchmark_id`` is not registered.
    """
    if benchmark_id not in BENCHMARK_REGISTRY:
        available = list(BENCHMARK_REGISTRY.keys())
        raise KeyError(
            f"Unknown benchmark dataset ID: '{benchmark_id}'. Available benchmarks: {available}"
        )
    return BENCHMARK_REGISTRY[benchmark_id]


def _generate_healthcare(row_count: int, seed: int) -> list[dict[str, Any]]:
    """Generate the Healthcare HIPAA Readmissions synthetic dataset.

    Pre-conditions:
        - ``row_count >= 20``.
        - ``seed`` is an integer seed for PRNG.
    Post-conditions:
        - Returns ``row_count`` rows conforming to the healthcare benchmark specification.
        - Exactly 2 duplicate rows and 4 missing values in ``lab_creatinine_mg_dl`` planted.
        - Exactly 2 extreme outliers in ``billing_amount_usd`` planted.
        - Inconsistent state codes planted at deterministic indices.
    """
    rng = np.random.default_rng(seed)
    base_date = datetime(2024, 1, 1)

    rows: list[dict[str, Any]] = []
    risks: list[float] = []

    for _ in range(row_count):
        fn = _FIRST_NAMES[int(rng.integers(0, len(_FIRST_NAMES)))]
        ln = _LAST_NAMES[int(rng.integers(0, len(_LAST_NAMES)))]
        name = f"{fn} {ln}"
        domain = _EMAIL_DOMAINS[int(rng.integers(0, len(_EMAIL_DOMAINS)))]
        email = f"{fn.lower()}.{ln.lower()}{int(rng.integers(10, 99))}@{domain}"
        ssn = (
            f"{int(rng.integers(100, 999)):03d}-{int(rng.integers(10, 99)):02d}-"
            f"{int(rng.integers(1000, 9999)):04d}"
        )
        mrn = f"MRN-{int(rng.integers(10000000, 99999999)):08d}"

        age = int(rng.integers(18, 86))
        age_norm = (age - 18.0) / 68.0

        state = _VALID_STATES[int(rng.integers(0, len(_VALID_STATES)))]
        adm_type = str(rng.choice(["EMERGENCY", "ELECTIVE", "URGENT"], p=[0.5, 0.3, 0.2]))

        charlson = int(np.clip(np.round(age_norm * 6.0 + rng.normal(0.0, 0.6)), 0, 10))
        los = int(np.clip(np.round(1.0 + age_norm * 14.0 + rng.normal(0.0, 1.2)), 1, 30))
        billing = round(
            float(
                np.clip(
                    5000.0 + age_norm * 35000.0 + los * 1200.0 + rng.normal(0.0, 1500.0),
                    3000.0,
                    120000.0,
                )
            ),
            2,
        )
        creat = round(float(np.clip(0.6 + age_norm * 1.0 + rng.normal(0.0, 0.2), 0.4, 4.5)), 2)

        adm_date = (base_date + timedelta(days=int(rng.integers(0, 365)))).strftime("%Y-%m-%d")

        risk = (
            0.35 * age_norm
            + 0.35 * (charlson / 10.0)
            + 0.30 * (los / 30.0)
            + float(rng.normal(0.0, 0.05))
        )

        rows.append(
            {
                "patient_name": name,
                "ssn": ssn,
                "mrn": mrn,
                "email": email,
                "age": age,
                "state": state,
                "admission_type": adm_type,
                "charlson_comorbidity_index": charlson,
                "length_of_stay_days": los,
                "lab_creatinine_mg_dl": creat,
                "billing_amount_usd": billing,
                "admission_date": adm_date,
                "readmitted_30d": 0,
            }
        )
        risks.append(risk)

    target_positives = max(1, int(round(row_count * 0.16)))
    reserved_zero_indices = {0, 10, 16, 18}
    candidate_indices = [idx for idx in range(row_count) if idx not in reserved_zero_indices]
    candidate_indices.sort(key=lambda idx: risks[idx], reverse=True)
    for idx in candidate_indices[:target_positives]:
        rows[idx]["readmitted_30d"] = 1

    # Planted defects
    rows[2]["state"] = " ca "
    rows[4]["state"] = "ny"
    rows[6]["state"] = "tx"

    rows[7]["billing_amount_usd"] = 450000.0
    rows[15]["billing_amount_usd"] = 485000.0

    rows[5]["lab_creatinine_mg_dl"] = None
    rows[9]["lab_creatinine_mg_dl"] = None
    rows[13]["lab_creatinine_mg_dl"] = None
    rows[17]["lab_creatinine_mg_dl"] = None

    rows[16] = dict(rows[0])
    rows[18] = dict(rows[10])

    return rows


def _generate_fintech(row_count: int, seed: int) -> list[dict[str, Any]]:
    """Generate the Fintech Fraud & Anomalous Transactions synthetic dataset.

    Pre-conditions:
        - ``row_count >= 20``.
        - ``seed`` is an integer seed for PRNG.
    Post-conditions:
        - Returns ``row_count`` rows conforming to the fintech benchmark specification.
        - Exactly 2 duplicate rows and 4 missing values in ``device_trust_score`` planted.
        - Exactly 2 extreme outliers in ``transaction_amount_usd`` planted.
        - Inconsistent state codes planted at deterministic indices.
    """
    rng = np.random.default_rng(seed)
    base_ts = datetime(2024, 4, 1, 0, 0, 0)
    categories = ["RETAIL", "TRAVEL", "GROCERY", "ELECTRONICS", "GAMING", "ENTERTAINMENT"]

    rows: list[dict[str, Any]] = []
    risks: list[float] = []

    for _ in range(row_count):
        fn = _FIRST_NAMES[int(rng.integers(0, len(_FIRST_NAMES)))]
        ln = _LAST_NAMES[int(rng.integers(0, len(_LAST_NAMES)))]
        name = f"{fn} {ln}"
        domain = _EMAIL_DOMAINS[int(rng.integers(0, len(_EMAIL_DOMAINS)))]
        email = f"{fn.lower()}.{ln.lower()}{int(rng.integers(10, 99))}@{domain}"
        phone = (
            f"+1-555-{int(rng.integers(100, 999)):03d}-{int(rng.integers(1000, 9999)):04d}"
        )
        ip = (
            f"{int(rng.integers(11, 220))}.{int(rng.integers(1, 255))}."
            f"{int(rng.integers(1, 255))}.{int(rng.integers(1, 254))}"
        )
        state = _VALID_STATES[int(rng.integers(0, len(_VALID_STATES)))]
        cat = str(rng.choice(categories))

        latent = float(rng.uniform(0.0, 1.0))

        velocity = int(np.clip(np.round(1 + latent * 16.0 + rng.normal(0.0, 1.0)), 1, 30))
        dist = round(
            float(np.clip(2.0 + latent * 450.0 + rng.normal(0.0, 20.0), 0.5, 1000.0)),
            2,
        )
        amount = round(
            float(
                np.clip(
                    15.0 + velocity * 18.0 + dist * 0.8 + rng.normal(0.0, 25.0),
                    5.0,
                    3500.0,
                )
            ),
            2,
        )
        trust = round(
            float(np.clip(0.96 - latent * 0.72 + rng.normal(0.0, 0.04), 0.05, 0.99)),
            3,
        )

        ts = (base_ts + timedelta(seconds=int(rng.integers(0, 86400 * 90)))).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        fraud_risk = (
            0.45 * (velocity / 30.0)
            + 0.45 * (dist / 1000.0)
            + 0.10 * (1.0 - trust)
            + float(rng.normal(0.0, 0.04))
        )

        rows.append(
            {
                "cardholder_name": name,
                "cardholder_email": email,
                "phone": phone,
                "ip_address": ip,
                "state": state,
                "merchant_category": cat,
                "transaction_amount_usd": amount,
                "velocity_24h_count": velocity,
                "distance_from_home_km": dist,
                "device_trust_score": trust,
                "transaction_timestamp": ts,
                "is_fraud": 0,
            }
        )
        risks.append(fraud_risk)

    target_positives = max(1, int(round(row_count * 0.10)))
    reserved_zero_indices = {0, 10, 16, 18}
    candidate_indices = [idx for idx in range(row_count) if idx not in reserved_zero_indices]
    candidate_indices.sort(key=lambda idx: risks[idx], reverse=True)
    for idx in candidate_indices[:target_positives]:
        rows[idx]["is_fraud"] = 1

    # Planted defects
    rows[2]["state"] = " ca "
    rows[4]["state"] = "ny"
    rows[6]["state"] = "tx"

    # Extreme outliers aligned with high velocity and distance
    rows[7]["velocity_24h_count"] = 28
    rows[7]["distance_from_home_km"] = 920.0
    rows[7]["transaction_amount_usd"] = 95000.0

    rows[15]["velocity_24h_count"] = 30
    rows[15]["distance_from_home_km"] = 980.0
    rows[15]["transaction_amount_usd"] = 125000.0

    rows[5]["device_trust_score"] = None
    rows[9]["device_trust_score"] = None
    rows[13]["device_trust_score"] = None
    rows[17]["device_trust_score"] = None

    rows[16] = dict(rows[0])
    rows[18] = dict(rows[10])

    return rows


def _generate_saas(row_count: int, seed: int) -> list[dict[str, Any]]:
    """Generate the B2B SaaS Customer Subscription & Churn synthetic dataset.

    Pre-conditions:
        - ``row_count >= 20``.
        - ``seed`` is an integer seed for PRNG.
    Post-conditions:
        - Returns ``row_count`` rows conforming to the SaaS benchmark specification.
        - Exactly 2 duplicate rows and 4 missing values in ``nps_score`` planted.
        - Exactly 2 extreme outliers in ``monthly_recurring_revenue_usd`` planted.
        - Inconsistent state codes planted at deterministic indices.
    """
    rng = np.random.default_rng(seed)
    base_date = datetime(2023, 1, 1)
    tiers = ["STARTER", "PROFESSIONAL", "ENTERPRISE"]

    rows: list[dict[str, Any]] = []
    risks: list[float] = []

    for _ in range(row_count):
        fn = _FIRST_NAMES[int(rng.integers(0, len(_FIRST_NAMES)))]
        ln = _LAST_NAMES[int(rng.integers(0, len(_LAST_NAMES)))]
        name = f"{fn} {ln}"
        domain = _EMAIL_DOMAINS[int(rng.integers(0, len(_EMAIL_DOMAINS)))]
        email = f"{fn.lower()}.{ln.lower()}{int(rng.integers(10, 99))}@{domain}"
        phone = (
            f"+1-555-{int(rng.integers(100, 999)):03d}-{int(rng.integers(1000, 9999)):04d}"
        )
        state = _VALID_STATES[int(rng.integers(0, len(_VALID_STATES)))]
        tier = str(rng.choice(tiers))

        seat_count = int(rng.integers(5, 501))
        mrr = round(
            float(np.clip(seat_count * 52.0 + rng.normal(0.0, 40.0), 100.0, 150000.0)),
            2,
        )

        utilization = round(float(rng.uniform(15.0, 95.0)), 2)
        util_norm = (utilization - 15.0) / 80.0

        nps_val = int(np.clip(np.round(util_norm * 8.5 + 1.0 + rng.normal(0.0, 0.7)), 0, 10))
        nps: int | None = nps_val
        tickets = int(np.clip(np.round((1.0 - util_norm) * 12.0 + rng.normal(0.0, 1.0)), 0, 20))

        start_date = (base_date + timedelta(days=int(rng.integers(0, 730)))).strftime("%Y-%m-%d")

        churn_risk = (
            0.55 * (1.0 - util_norm)
            + 0.35 * (tickets / 20.0)
            + 0.10 * ((10 - (nps if nps is not None else 5)) / 10.0)
            + float(rng.normal(0.0, 0.04))
        )

        rows.append(
            {
                "contact_name": name,
                "contact_email": email,
                "phone": phone,
                "state": state,
                "plan_tier": tier,
                "seat_count": seat_count,
                "monthly_recurring_revenue_usd": mrr,
                "active_utilization_pct": utilization,
                "support_tickets_90d": tickets,
                "nps_score": nps,
                "contract_start_date": start_date,
                "churned": 0,
            }
        )
        risks.append(churn_risk)

    target_positives = max(1, int(round(row_count * 0.14)))
    reserved_zero_indices = {0, 10, 16, 18}
    candidate_indices = [idx for idx in range(row_count) if idx not in reserved_zero_indices]
    candidate_indices.sort(key=lambda idx: risks[idx], reverse=True)
    for idx in candidate_indices[:target_positives]:
        rows[idx]["churned"] = 1

    # Planted defects
    rows[2]["state"] = " ca "
    rows[4]["state"] = "ny"
    rows[6]["state"] = "tx"

    # Outliers aligned with high seat count
    rows[7]["seat_count"] = 495
    rows[7]["monthly_recurring_revenue_usd"] = 850000.0

    rows[15]["seat_count"] = 500
    rows[15]["monthly_recurring_revenue_usd"] = 920000.0

    rows[5]["nps_score"] = None
    rows[9]["nps_score"] = None
    rows[13]["nps_score"] = None
    rows[17]["nps_score"] = None

    rows[16] = dict(rows[0])
    rows[18] = dict(rows[10])

    return rows


def generate_benchmark_dataset(
    benchmark_id: str,
    row_count: int | None = None,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Generate a deterministic synthetic benchmark dataset with planted defects.

    Pre-conditions:
        - ``benchmark_id`` exists in ``BENCHMARK_REGISTRY``.
        - If ``row_count`` is provided, ``row_count >= 20``.
        - ``seed`` is an integer for random number generator initialization.
    Post-conditions:
        - Returns a list of dictionaries with length equal to resolved ``row_count``.
        - Output is 100% deterministic for a fixed seed.
        - Planted defects (duplicates, missing values, extreme outliers, dirty state codes)
          are present.
        - Domain correlations and class imbalance constraints are satisfied.
        - Raises ``KeyError`` if ``benchmark_id`` is not in ``BENCHMARK_REGISTRY``.
        - Raises ``ValueError`` if resolved ``row_count < 20``.
    """
    if benchmark_id not in BENCHMARK_REGISTRY:
        available = list(BENCHMARK_REGISTRY.keys())
        raise KeyError(
            f"Unknown benchmark dataset ID: '{benchmark_id}'. Available benchmarks: {available}"
        )

    meta = BENCHMARK_REGISTRY[benchmark_id]
    resolved_count = meta.default_row_count if row_count is None else row_count
    if resolved_count < 20:
        raise ValueError(
            f"row_count must be at least 20, got {resolved_count}"
        )

    if benchmark_id == "healthcare_hipaa_readmissions":
        return _generate_healthcare(resolved_count, seed)
    if benchmark_id == "fintech_fraud_transactions":
        return _generate_fintech(resolved_count, seed)
    if benchmark_id == "saas_customer_churn":
        return _generate_saas(resolved_count, seed)

    raise KeyError(f"No generator implemented for benchmark ID: '{benchmark_id}'")
