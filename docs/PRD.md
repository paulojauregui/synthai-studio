# Product Requirements Document: SynthAI Studio (`synthai-studio`)

## 1. Executive Summary & Vision

**SynthAI Studio** is a developer-first, privacy-preserving **Synthetic Data Generation, Differential Privacy, and Statistical Quality Auditing SaaS & API** running on the `mainframe` bare-metal Kubernetes platform. It empowers engineering, healthcare analytics, and machine learning teams to inspect raw tabular datasets for data quality defects and sensitive PII/PHI, train mathematically rigorous statistical or latent neural synthesizers with formal $(\epsilon, \delta)$-Differential Privacy guarantees, upscale rare minority classes, and verify statistical fidelity and zero-memorization privacy proofs before exporting production-ready CSV, JSON, or Parquet datasets.

---

## 2. Target Personas & Use Cases

| Persona | Primary Domain | Core Pain Point | SynthAI Studio Value Proposition |
| :--- | :--- | :--- | :--- |
| **Healthcare ML Engineer** | HIPAA Clinical Analytics | Cannot share or train models on raw Electronic Health Records (EHR) containing Patient Health Information (MRNs, SSNs, patient names). | 1-click PII/PHI detection, cleansing, and $(\epsilon, \delta)$-differentially private Gaussian Copula / CTGAN synthesis with Distance to Closest Record ($DCR$) zero-memorization verification. |
| **FinTech Fraud Data Scientist** | Payment & Wire Fraud | Extreme class imbalance ($< 2\%$ positive fraud labels) starves gradient-boosted and deep tabular classifiers. | Conditional minority-class upsampling (`is_fraud == 1`) paired with DGX Spark LLM semantic edge-case synthesis (`SPARK_LLM_EDGE`). |
| **Platform & QA Lead** | B2B SaaS & Load Testing | Production database dumps violate GDPR/CCPA when copied to staging or ephemeral PR preview environments. | Pre-signed upload/export flows, deterministic Faker-Hybrid + Copula synthesis, and automated CI/CD quality verification reports. |

---

## 3. Five-Step User Journey

1. **Step 1: Connect & Seed Data**
   - Upload a raw CSV or JSON dataset directly via multipart/JSON payload, initiate a pre-signed object storage upload flow (SeaweedFS/S3 compatible), or seed instantly from three curated domain benchmark datasets:
     - `healthcare_hipaa_readmissions`: 30-day hospital readmission records containing PHI (`patient_name`, `ssn`, `mrn`, `email`), physiological vitals, length of stay, and intentional formatting/outlier defects.
     - `fintech_fraud_transactions`: High-velocity card/wire transaction records with severe class imbalance (`is_fraud`), correlated velocity/amount features, and PII (`cardholder_email`, `phone`, `ip_address`).
     - `saas_customer_churn`: B2B subscription telemetry with ARR, seat utilization, support tickets, contract dates, and customer contact PII.

2. **Step 2: Profile, Data Quality & PII Audit ("The Magic Moment")**
   - Automated column type inference (`NUMERICAL`, `CATEGORICAL`, `DATETIME`, `BOOLEAN`, `IDENTIFIER_PII`).
   - Multi-signal PII/PHI Scanner combining column naming heuristics, regular expressions, and Shannon entropy (`EMAIL`, `SSN`, `PHONE`, `CREDIT_CARD`, `MEDICAL_RECORD_NUMBER`, `PERSON_NAME`, `IP_ADDRESS`).
   - Automated Data Quality Audit detecting missing values, exact duplicate rows, $z$-score ($|z| > 3.0$) and IQR numerical outliers, and inconsistent categorical casing/state codes.
   - Pairwise correlation matrix computation (Pearson/Spearman) and 10-bin empirical histograms.
   - 1-click **Cleanse & Anonymize Dataset** action that deduplicates rows, imputes missing values (median for numerical, mode for categorical), clamps extreme outliers, normalizes strings, and masks raw PII identifiers.

3. **Step 3: Configure & Tune Generation**
   - **Target Row Count**: Configurable from `10` to `100,000+` rows.
   - **Synthesizer Engine Selection**:
     - `GAUSSIAN_COPULA`: Multivariate Gaussian Copula using rank correlation, positive semi-definite (PSD) eigenvalue projection, Cholesky factorization, normal-to-uniform $\Phi$ mapping, and empirical inverse-CDF quantile interpolation.
     - `CTGAN_LATENT`: Conditional Tabular Latent Autoencoder/GAN synthesizer using mode-specific Gaussian mixture normalization for multimodal continuous distributions and conditional categorical latent sampling.
     - `FAKER_HYBRID`: Deterministic semantic PII generator paired with statistical copula sampling for non-PII features.
     - `SPARK_LLM_EDGE`: Local DGX Spark (`happy.tail749110.ts.net:8000`, `nvidia/Qwen3.8-Flash-Next-FP4-Local`) semantic edge-case synthesizer with a strict `< 2.0s` circuit-breaker fallback.
   - **Differential Privacy Slider ($\epsilon, \delta$-DP)**:
     - `NONE` ($\epsilon = \infty$), `LOW` ($\epsilon = 10.0, \delta = 10^{-5}$), `MEDIUM` ($\epsilon = 1.0, \delta = 10^{-5}$), `HIGH` ($\epsilon = 0.1, \delta = 10^{-6}$).
     - Injects calibrated Laplace/Gaussian noise into empirical moments, quantile knots, and categorical contingency histograms prior to sampling.
   - **Minority Class Upsampling & Declarative Constraints**: Boost target minority class labels (e.g., `is_fraud == 1` to `0.25`) and apply declarative `ConditionRule` filters (`EQ`, `NEQ`, `GT`, `GTE`, `LT`, `LTE`, `IN`).

4. **Step 4: Generate & Monitor (Durable Execution)**
   - Dispatches profiling and generation workflows to **Temporal** (`DatasetProfileWorkflow`, `SyntheticGenerationWorkflow`) with a transparent in-process execution fallback when Temporal is unreachable.
   - Tracks real-time job status, rows-per-second throughput, compute tier (`CPU_WORKER` vs `GPU_SPARK_WORKER`), and cumulative Differential Privacy budget expenditure (`epsilon_spent`, `delta`, `noise_scale`).

5. **Step 5: Evaluate Quality Report & Download ("Trust & Validation")**
   - **Marginal Fidelity Score ($0.0..1.0$)**: Mean Two-Sample Kolmogorov-Smirnov complement ($1 - D_{KS}$) for numerical columns and Total Variation Distance complement ($1 - \text{TVD}$) plus Jensen-Shannon similarity for categorical columns.
   - **Correlation Stability Score ($0.0..1.0$)**: Frobenius norm similarity $1 - \frac{\|R_{\text{real}} - R_{\text{synth}}\|_F}{\text{norm}}$.
   - **Privacy & Memorization Proof ($0.0..1.0$)**: Exact row collision rate (target $0.0\%$), Euclidean $z$-normalized Distance to Closest Record ($DCR$) 5th-percentile and median, and Nearest-Neighbor Distance Ratio ($NNDR$).
   - **Executive AI Quality Verdict**: Detailed readiness assessment for HIPAA/GDPR compliance and ML training utility.
   - **Multi-Format Export**: Download synthetic datasets as **CSV**, **JSON**, or **Parquet**, and export the Quality Validation Report as **JSON** or **Markdown**.

---

## 4. Non-Functional Requirements & Production SLAs

- **Deterministic Unit & Integration Testing**: 100% offline test execution (`pytest`) with zero external network dependencies.
- **Latency & Throughput**: Profiling and synthesizing 1,000 rows in `< 250ms` on CPU; `< 2.0s` circuit breaker for optional DGX Spark LLM calls.
- **Container Security**: Multi-stage Docker build running as non-privileged `USER 10001:10001` with `/healthz` and `/ready` probes.
- **Storage Persistence**: DuckDB embedded OLAP catalog paired with PyArrow Parquet/CSV storage and pre-signed upload/download token validation.
