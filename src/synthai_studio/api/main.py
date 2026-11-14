"""SynthAI Studio FastAPI REST Service and 5-Step Interactive Web UI.

Pre-conditions:
    - Python >= 3.11 with FastAPI, Pydantic, and DuckDB installed.
Post-conditions:
    - Exposes REST endpoints for benchmarks, dataset ingestion, profiling,
      cleansing, synthetic generation, quality auditing, and file downloads.
    - Exposes interactive 5-step single-page HTML5 console at GET /.
"""

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from synthai_studio.benchmarks import BENCHMARK_REGISTRY, list_benchmarks
from synthai_studio.evaluator import render_quality_report_markdown
from synthai_studio.models import (
    BenchmarkMetadata,
    DatasetMetadata,
    DatasetProfileReport,
    ExportFormat,
    GenerationJob,
    PresignedUploadTicket,
    SynthesisConfig,
)
from synthai_studio.profiler import parse_tabular_payload
from synthai_studio.repository import StudioRepository
from synthai_studio.workflows import StudioWorkflowOrchestrator

__all__ = [
    "CleanseRequest",
    "PresignRequest",
    "SeedRequest",
    "UploadPayloadRequest",
    "app",
    "create_app",
]


class SeedRequest(BaseModel):
    """Payload for seeding a benchmark dataset with a custom row count.

    Pre-conditions:
        - row_count must be positive if supplied.
    Post-conditions:
        - Encapsulates benchmark seeding request parameters.
    """

    row_count: int | None = Field(default=None, ge=10, le=100000)


class UploadPayloadRequest(BaseModel):
    """JSON payload model for direct tabular dataset upload.

    Pre-conditions:
        - Must supply either 'rows' list or raw 'content' string.
    Post-conditions:
        - Encapsulates tabular data ingestion parameters.
    """

    name: str = "custom_dataset"
    content: str | None = None
    filename: str = "dataset.csv"
    rows: list[dict[str, Any]] | None = None


class PresignRequest(BaseModel):
    """Payload for requesting an S3/SeaweedFS presigned upload ticket.

    Pre-conditions:
        - dataset_name is a non-empty string.
    Post-conditions:
        - Encapsulates capability ticket configuration.
    """

    dataset_name: str
    expiry_seconds: int = Field(default=3600, ge=60, le=86400)


class CleanseRequest(BaseModel):
    """Payload configuring dataset cleansing and PII anonymization.

    Pre-conditions:
        - None.
    Post-conditions:
        - Encapsulates cleansing execution preferences.
    """

    anonymize_pii: bool = True


def _build_studio_ui_html() -> str:
    """Generate self-contained HTML5 single-page application for SynthAI Studio.

    Pre-conditions:
        - None.
    Post-conditions:
        - Returns high-density, terminal-inspired HTML string with zero emojis.
    """
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SynthAI Studio // Privacy-Preserving Synthetic Data & Quality Auditing</title>
<style>
  :root {
    --bg-dark: #090d16;
    --bg-panel: #111726;
    --bg-card: #182234;
    --bg-hover: #223049;
    --border-color: #27364d;
    --text-main: #f1f5f9;
    --text-muted: #94a3b8;
    --accent-cyan: #06b6d4;
    --accent-emerald: #10b981;
    --accent-blue: #3b82f6;
    --accent-amber: #f59e0b;
    --accent-rose: #f43f5e;
    --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background-color: var(--bg-dark);
    color: var(--text-main);
    font-family: var(--font-sans);
    font-size: 14px;
    line-height: 1.5;
  }
  header {
    background: var(--bg-panel);
    border-bottom: 1px solid var(--border-color);
    padding: 14px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .brand-title {
    font-family: var(--font-mono);
    font-size: 16px;
    font-weight: 700;
    color: var(--accent-cyan);
    letter-spacing: 0.5px;
  }
  .brand-subtitle {
    font-size: 12px;
    color: var(--text-muted);
  }
  .cluster-status {
    font-family: var(--font-mono);
    font-size: 11px;
    display: flex;
    gap: 8px;
  }
  .badge {
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
    text-transform: uppercase;
    font-family: var(--font-mono);
    font-size: 11px;
    display: inline-block;
  }
  .badge-success { background: #064e3b; color: #34d399; border: 1px solid #059669; }
  .badge-info { background: #0c4a6e; color: #38bdf8; border: 1px solid #0284c7; }
  .badge-warn { background: #78350f; color: #fbbf24; border: 1px solid #d97706; }
  .badge-danger { background: #881337; color: #fb7185; border: 1px solid #e11d48; }

  nav {
    background: #0d131f;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    overflow-x: auto;
    padding: 0 24px;
  }
  .nav-tab {
    padding: 12px 18px;
    color: var(--text-muted);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
    transition: all 0.2s;
  }
  .nav-tab:hover { color: var(--text-main); }
  .nav-tab.active {
    color: var(--accent-cyan);
    border-bottom-color: var(--accent-cyan);
    background: rgba(6, 182, 212, 0.05);
  }

  main { padding: 24px; max-width: 1400px; margin: 0 auto; }
  .step-panel { display: none; }
  .step-panel.active { display: block; }

  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
  .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }

  .card {
    background: var(--bg-panel);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 20px;
    margin-bottom: 20px;
  }
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border-color);
  }
  .card-title {
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 700;
    color: var(--text-main);
    text-transform: uppercase;
  }

  .stat-tile {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 16px;
    text-align: center;
  }
  .stat-val {
    font-family: var(--font-mono);
    font-size: 22px;
    font-weight: 700;
    color: var(--accent-cyan);
    margin: 4px 0;
  }
  .stat-label {
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    font-family: var(--font-mono);
  }

  label {
    display: block;
    font-size: 12px;
    font-family: var(--font-mono);
    color: var(--text-muted);
    margin-bottom: 6px;
    text-transform: uppercase;
  }
  input, select, textarea {
    width: 100%;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 8px 12px;
    color: var(--text-main);
    font-family: var(--font-mono);
    font-size: 13px;
    margin-bottom: 14px;
  }
  input:focus, select:focus, textarea:focus {
    outline: none;
    border-color: var(--accent-cyan);
  }

  button.btn {
    background: var(--accent-cyan);
    color: #000;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    text-transform: uppercase;
    transition: opacity 0.2s;
  }
  button.btn:hover { opacity: 0.85; }
  button.btn-emerald { background: var(--accent-emerald); color: #000; }
  button.btn-secondary {
    background: var(--bg-card);
    color: var(--text-main);
    border: 1px solid var(--border-color);
  }
  button.btn-secondary:hover { background: var(--bg-hover); }

  table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--font-mono);
    font-size: 12px;
    margin-top: 10px;
  }
  th, td {
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
  }
  th {
    background: var(--bg-card);
    color: var(--text-muted);
    text-transform: uppercase;
    font-weight: 600;
  }
  tr:hover { background: rgba(255, 255, 255, 0.02); }

  pre {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    padding: 12px;
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 12px;
    color: #38bdf8;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
  }
  .log-console {
    background: #050811;
    border: 1px solid var(--border-color);
    padding: 12px;
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: #a7f3d0;
    max-height: 220px;
    overflow-y: auto;
  }
</style>
</head>
<body>

<header>
  <div>
    <div class="brand-title">SYNTHAI STUDIO // AUTONOMOUS PRIVACY &amp; FIDELITY ENGINE</div>
    <div class="brand-subtitle">
      Differential Privacy (&epsilon;,&delta;) &bull; Generative Models &bull; HIPAA/GDPR
    </div>
  </div>
  <div class="cluster-status">
    <span class="badge badge-success" id="status-service">SERVICE: ONLINE</span>
    <span class="badge badge-info" id="status-catalog">CATALOG: DUCKDB</span>
    <span class="badge badge-info" id="status-temporal">TEMPORAL: ACTIVE</span>
  </div>
</header>

<nav>
  <div class="nav-tab active" onclick="switchStep(1)">[1. CONNECT &amp; SEED]</div>
  <div class="nav-tab" onclick="switchStep(2)">[2. QUALITY &amp; PII AUDIT]</div>
  <div class="nav-tab" onclick="switchStep(3)">[3. ENGINE &amp; DP CONFIG]</div>
  <div class="nav-tab" onclick="switchStep(4)">[4. WORKER MONITOR]</div>
  <div class="nav-tab" onclick="switchStep(5)">[5. FIDELITY &amp; EXPORT]</div>
</nav>

<main>
  <!-- STEP 1: CONNECT & SEED -->
  <section id="step-1" class="step-panel active">
    <div class="grid-2">
      <div class="card">
        <div class="card-header">
          <div class="card-title">Pre-Engineered Domain Benchmarks</div>
          <span class="badge badge-info">3 REFERENCE DATASETS</span>
        </div>
        <p style="color: var(--text-muted); font-size: 12px; margin-bottom: 14px;">
          Seed synthetic testing environments with realistic real-world datasets featuring
          planted PII identifiers, class imbalances, and domain statistical distributions.
        </p>
        <div id="benchmark-cards">Loading benchmarks...</div>
      </div>

      <div>
        <div class="card">
          <div class="card-header">
            <div class="card-title">Custom Tabular Data Ingestion</div>
            <span class="badge badge-info">CSV / JSON</span>
          </div>
          <form id="upload-form" onsubmit="handleUpload(event)">
            <label>Dataset Name</label>
            <input type="text" id="upload-name" placeholder="my_enterprise_dataset" required>
            <label>Upload CSV or JSON File</label>
            <input type="file" id="upload-file" accept=".csv,.json" required>
            <button type="submit" class="btn">Upload &amp; Profile Dataset</button>
          </form>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">Pre-Signed S3 / SeaweedFS Capability</div>
            <span class="badge badge-warn">CAPABILITY TICKET</span>
          </div>
          <p style="color: var(--text-muted); font-size: 12px; margin-bottom: 12px;">
            Issue short-lived single-use upload capability tokens for SeaweedFS/S3 streaming.
          </p>
          <div style="display: flex; gap: 8px;">
            <input type="text" id="presign-name" placeholder="seaweedfs_target_dataset">
            <button class="btn btn-secondary" onclick="generateTicket()"
              style="white-space: nowrap;">Generate Ticket</button>
          </div>
          <div id="presign-result" style="display: none; margin-top: 10px;">
            <label>Issued Upload URL &amp; Token</label>
            <pre id="presign-text"></pre>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- STEP 2: QUALITY & PII AUDIT -->
  <section id="step-2" class="step-panel">
    <div class="card">
      <div class="card-header">
        <div class="card-title">Automated Data Quality &amp; PII/PHI Audit Scanner</div>
        <div style="display: flex; gap: 10px; align-items: center;">
          <select id="profile-dataset-select" onchange="loadProfileForSelected()"
            style="margin: 0; min-width: 250px;"></select>
          <button class="btn btn-emerald" onclick="cleanseCurrentDataset()">
            [1-Click Cleanse &amp; Anonymize]
          </button>
        </div>
      </div>

      <div class="grid-4" style="margin-bottom: 20px;">
        <div class="stat-tile">
          <div class="stat-label">Total Records</div>
          <div class="stat-val" id="prof-rows">-</div>
        </div>
        <div class="stat-tile">
          <div class="stat-label">Total Columns</div>
          <div class="stat-val" id="prof-cols">-</div>
        </div>
        <div class="stat-tile">
          <div class="stat-label">Data Quality Score</div>
          <div class="stat-val" id="prof-quality">-</div>
        </div>
        <div class="stat-tile">
          <div class="stat-label">Privacy Risk Score</div>
          <div class="stat-val" id="prof-privacy-risk" style="color: var(--accent-rose);">-</div>
        </div>
      </div>

      <div class="card-title" style="margin-bottom: 10px;">Column Profiles &amp; PII Scan</div>
      <table id="profile-columns-table">
        <thead>
          <tr>
            <th>Column Name</th>
            <th>Inferred Type</th>
            <th>PII Finding</th>
            <th>Confidence</th>
            <th>Null Count</th>
            <th>Outliers (|z|>3)</th>
          </tr>
        </thead>
        <tbody>
          <tr><td colspan="6" style="text-align: center;">Select a dataset to view audit.</td></tr>
        </tbody>
      </table>

      <div class="card-title" style="margin-top: 24px; margin-bottom: 10px;">
        Correlation Stability Heatmap (Pearson)
      </div>
      <div id="profile-corr-wrapper" style="overflow-x: auto;">
        <table id="profile-corr-table">
          <tbody><tr><td>No correlation matrix computed.</td></tr></tbody>
        </table>
      </div>
    </div>
  </section>

  <!-- STEP 3: ENGINE & DP CONFIG -->
  <section id="step-3" class="step-panel">
    <div class="card">
      <div class="card-header">
        <div class="card-title">Multi-Engine Generative Synthesis &amp; DP Configuration</div>
        <span class="badge badge-info">DIFFERENTIAL PRIVACY SLIDERS</span>
      </div>

      <form id="synth-config-form" onsubmit="handleGenerate(event)">
        <div class="grid-2">
          <div>
            <label>Target Dataset</label>
            <select id="gen-dataset-id" required></select>

            <label>Target Row Count</label>
            <input type="number" id="gen-target-rows" value="250" min="10" max="100000" required>

            <label>Synthesizer Engine</label>
            <select id="gen-engine">
              <option value="GAUSSIAN_COPULA">GAUSSIAN_COPULA (Parametric Rank Coupling)</option>
              <option value="CTGAN_LATENT">CTGAN_LATENT (Multi-modal GMM Latent)</option>
              <option value="FAKER_HYBRID">FAKER_HYBRID (Deterministic Masking)</option>
              <option value="SPARK_LLM_EDGE">SPARK_LLM_EDGE (Local DGX Spark GB10 vLLM)</option>
            </select>

            <label>Differential Privacy Tier</label>
            <select id="gen-privacy-level" onchange="updateDpDefaults()">
              <option value="MEDIUM">MEDIUM (&epsilon;=1.0, &delta;=1e-5) [HIPAA/GDPR]</option>
              <option value="LOW">LOW (&epsilon;=5.0, &delta;=1e-5) [High Fidelity]</option>
              <option value="HIGH">HIGH (&epsilon;=0.1, &delta;=1e-6) [Max Privacy]</option>
              <option value="NONE">NONE (Zero DP Mechanism)</option>
            </select>
          </div>

          <div>
            <label>Epsilon (&epsilon;) Budget</label>
            <input type="number" id="gen-epsilon" value="1.0" step="0.1" min="0.01" max="100.0">

            <label>Delta (&delta;) Failure Probability</label>
            <input type="number" id="gen-delta" value="0.00001" step="0.000001" min="0.0000001">

            <label>Minority Class Upsampling (Target Column)</label>
            <input type="text" id="gen-target-col" placeholder="readmitted_30d / is_fraud">

            <label>Target Minority Ratio (0.05 - 0.50)</label>
            <input type="number" id="gen-minority-ratio"
              value="0.30" step="0.05" min="0.05" max="0.50">

            <div style="margin-top: 8px; margin-bottom: 14px;">
              <input type="checkbox" id="gen-anonymize-pii" checked style="width: auto;">
              <label for="gen-anonymize-pii" style="display: inline; margin-left: 6px;">
                Anonymize PII identifiers with synthetic format-preserving tokens
              </label>
            </div>

            <button type="submit" class="btn btn-emerald" style="width: 100%; padding: 12px;">
              [Launch Synthetic Generation Workflow]
            </button>
          </div>
        </div>
      </form>
    </div>
  </section>

  <!-- STEP 4: WORKER MONITOR -->
  <section id="step-4" class="step-panel">
    <div class="grid-2">
      <div class="card">
        <div class="card-header">
          <div class="card-title">Generation Jobs Ledger</div>
          <button class="btn btn-secondary" onclick="loadJobs()">Refresh Jobs</button>
        </div>
        <table id="jobs-table">
          <thead>
            <tr>
              <th>Job ID</th>
              <th>Dataset</th>
              <th>Engine</th>
              <th>Status</th>
              <th>Rows</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            <tr><td colspan="6" style="text-align: center;">Loading jobs...</td></tr>
          </tbody>
        </table>
      </div>

      <div>
        <div class="card">
          <div class="card-header">
            <div class="card-title">Privacy Budget Ledger</div>
            <span class="badge badge-info" id="ledger-status">ACTIVE</span>
          </div>
          <div class="grid-2" style="margin-bottom: 14px;">
            <div class="stat-tile">
              <div class="stat-label">Spent &epsilon;</div>
              <div class="stat-val" id="ledger-spent">-</div>
            </div>
            <div class="stat-tile">
              <div class="stat-label">Remaining &epsilon;</div>
              <div class="stat-val" id="ledger-remaining">-</div>
            </div>
          </div>
          <div style="font-family: var(--font-mono); font-size: 12px; color: var(--text-muted);">
            <div>Delta (&delta;):
              <span id="ledger-delta" style="color: var(--text-main);">-</span>
            </div>
            <div>Allocation:
              <span id="ledger-initial" style="color: var(--text-main);">-</span>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div class="card-title">Active Worker Activity Logs</div>
            <span class="badge badge-success">IN-PROCESS / TEMPORAL</span>
          </div>
          <div class="log-console" id="worker-console">
            [READY] Worker activity loop armed.<br>
            [READY] Zero-Retry Circuit Breaker initialized.<br>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- STEP 5: FIDELITY & EXPORT -->
  <section id="step-5" class="step-panel">
    <div class="card">
      <div class="card-header">
        <div class="card-title">Statistical Fidelity &amp; Privacy Verification Proof</div>
        <div style="display: flex; gap: 8px;">
          <select id="report-job-select" onchange="loadReportForSelected()"
            style="margin: 0; min-width: 200px;"></select>
        </div>
      </div>

      <div class="grid-4" style="margin-bottom: 20px;">
        <div class="stat-tile">
          <div class="stat-label">Overall Quality</div>
          <div class="stat-val" id="rep-quality">-</div>
        </div>
        <div class="stat-tile">
          <div class="stat-label">Marginal Fidelity</div>
          <div class="stat-val" id="rep-fidelity">-</div>
        </div>
        <div class="stat-tile">
          <div class="stat-label">Correlation Stability</div>
          <div class="stat-val" id="rep-corr">-</div>
        </div>
        <div class="stat-tile">
          <div class="stat-label">Privacy Protection</div>
          <div class="stat-val" id="rep-privacy" style="color: var(--accent-emerald);">-</div>
        </div>
      </div>

      <div class="grid-2">
        <div class="card" style="margin-bottom: 0;">
          <div class="card-title" style="margin-bottom: 10px;">Executive Compliance Verdict</div>
          <div id="rep-verdict" style="font-family: var(--font-mono); font-size: 13px;
            color: #38bdf8; background: var(--bg-card); padding: 12px; border-radius: 4px;">
            Awaiting job execution...
          </div>
          <div style="margin-top: 14px; font-family: var(--font-mono); font-size: 12px;">
            <div>HIPAA/GDPR Readiness:
              <span id="rep-hipaa" class="badge badge-success">YES</span>
            </div>
            <div>Distance to Closest Record (DCR): <span id="rep-dcr">-</span></div>
            <div>Nearest Neighbor Ratio (NNDR): <span id="rep-nndr">-</span></div>
            <div>Exact Collisions:
              <span id="rep-collisions" style="color: var(--accent-emerald);">0</span>
            </div>
            <div>Identifiable PII Leakage:
              <span id="rep-pii-leaks" style="color: var(--accent-emerald);">0</span>
            </div>
          </div>
        </div>

        <div class="card" style="margin-bottom: 0;">
          <div class="card-title" style="margin-bottom: 10px;">1-Click Artifact Downloads</div>
          <p style="color: var(--text-muted); font-size: 12px; margin-bottom: 14px;">
            Export privacy-certified synthetic datasets and compliance validation reports.
          </p>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            <button class="btn btn-secondary" onclick="downloadArtifact('csv')">
              Download Synthetic CSV (.csv)
            </button>
            <button class="btn btn-secondary" onclick="downloadArtifact('json')">
              Download Synthetic JSON (.json)
            </button>
            <button class="btn btn-secondary" onclick="downloadArtifact('parquet')">
              Download Synthetic Parquet (.parquet)
            </button>
            <button class="btn btn-emerald" onclick="downloadArtifact('markdown')">
              Download Compliance Audit Report (.md)
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</main>

<script>
  let activeStep = 1;
  let currentJobId = null;

  function logWorker(msg) {
    const el = document.getElementById('worker-console');
    const ts = new Date().toISOString().substring(11, 19);
    el.innerHTML += `[${ts}] ${msg}<br>`;
    el.scrollTop = el.scrollHeight;
  }

  function switchStep(step) {
    activeStep = step;
    document.querySelectorAll('.step-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.getElementById(`step-${step}`).classList.add('active');
    document.querySelectorAll('.nav-tab')[step - 1].classList.add('active');
  }

  async function loadInitData() {
    try {
      const readyRes = await fetch('/ready');
      const ready = await readyRes.json();
      document.getElementById('status-catalog').innerText = `DATASETS: ${ready.datasets_count}`;
      const thost = ready.temporal_host ? 'TEMPORAL: READY' : 'LOCAL';
      document.getElementById('status-temporal').innerText = thost;

      await loadBenchmarks();
      await loadDatasets();
      await loadJobs();
    } catch (err) {
      console.error(err);
    }
  }

  async function loadBenchmarks() {
    const res = await fetch('/api/v1/benchmarks');
    const bms = await res.json();
    const container = document.getElementById('benchmark-cards');
    container.innerHTML = '';
    bms.forEach(b => {
      const card = document.createElement('div');
      card.style.background = 'var(--bg-card)';
      card.style.border = '1px solid var(--border-color)';
      card.style.borderRadius = '4px';
      card.style.padding = '12px';
      card.style.marginBottom = '10px';
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div style="font-weight:700; font-family:var(--font-mono);">${b.name}</div>
          <span class="badge badge-info">${b.default_row_count} ROWS</span>
        </div>
        <div style="color:var(--text-muted); font-size:12px; margin:6px 0;">${b.description}</div>
        <div style="font-size:11px; font-family:var(--font-mono);
          color:#38bdf8; margin-bottom:8px;">
          Planted Defects: ${b.planted_defects.join(', ')}
        </div>
        <button class="btn btn-secondary" onclick="seedBenchmark('${b.benchmark_id}')">
          Seed Benchmark Dataset
        </button>
      `;
      container.appendChild(card);
    });
  }

  async function seedBenchmark(bmId) {
    logWorker(`Seeding benchmark dataset '${bmId}'...`);
    try {
      const res = await fetch(`/api/v1/datasets/seed/${bmId}`, { method: 'POST' });
      const data = await res.json();
      logWorker(`Seeded dataset: ${data.dataset.name} (${data.dataset.row_count} rows)`);
      await loadDatasets();
      document.getElementById('profile-dataset-select').value = data.dataset.dataset_id;
      await loadProfileForSelected();
      switchStep(2);
    } catch (err) {
      logWorker(`Error seeding benchmark: ${err}`);
    }
  }

  async function handleUpload(evt) {
    evt.preventDefault();
    const name = document.getElementById('upload-name').value;
    const file = document.getElementById('upload-file').files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);

    logWorker(`Uploading custom dataset '${name}'...`);
    try {
      const res = await fetch('/api/v1/datasets/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      logWorker(`Upload complete: ${data.dataset.name} (${data.dataset.row_count} rows)`);
      await loadDatasets();
      document.getElementById('profile-dataset-select').value = data.dataset.dataset_id;
      await loadProfileForSelected();
      switchStep(2);
    } catch (err) {
      logWorker(`Upload failed: ${err}`);
    }
  }

  async function generateTicket() {
    const dsName = document.getElementById('presign-name').value || 'custom_upload';
    const res = await fetch('/api/v1/datasets/presign-upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_name: dsName })
    });
    const ticket = await res.json();
    document.getElementById('presign-result').style.display = 'block';
    document.getElementById('presign-text').innerText = JSON.stringify(ticket, null, 2);
  }

  async function loadDatasets() {
    const res = await fetch('/api/v1/datasets');
    const datasets = await res.json();
    const profSelect = document.getElementById('profile-dataset-select');
    const genSelect = document.getElementById('gen-dataset-id');
    profSelect.innerHTML = '';
    genSelect.innerHTML = '';
    datasets.forEach(d => {
      const opt = `<option value="${d.dataset_id}">${d.name} (${d.row_count} rows)</option>`;
      profSelect.innerHTML += opt;
      genSelect.innerHTML += opt;
    });
    if (datasets.length > 0 && !profSelect.value) {
      profSelect.value = datasets[0].dataset_id;
      loadProfileForSelected();
    }
  }

  async function loadProfileForSelected() {
    const dsId = document.getElementById('profile-dataset-select').value;
    if (!dsId) return;
    try {
      const res = await fetch(`/api/v1/datasets/${dsId}/profile`);
      if (!res.ok) return;
      const prof = await res.json();

      document.getElementById('prof-rows').innerText = prof.row_count;
      document.getElementById('prof-cols').innerText = prof.column_count;
      const qPct = (prof.data_quality_score * 100).toFixed(1);
      document.getElementById('prof-quality').innerText = `${qPct}%`;
      const rPct = (prof.privacy_risk_score * 100).toFixed(1);
      document.getElementById('prof-privacy-risk').innerText = `${rPct}%`;

      const tbody = document.querySelector('#profile-columns-table tbody');
      tbody.innerHTML = '';
      prof.columns.forEach(c => {
        const tr = document.createElement('tr');
        const cConf = c.pii_confidence ? `${(c.pii_confidence * 100).toFixed(0)}%` : '-';
        const piiBadge = c.pii_type === 'NONE' ? 'badge-success' : 'badge-danger';
        const outVal = c.numerical_stats ? c.numerical_stats.outlier_count_zscore : '-';
        tr.innerHTML = `
          <td style="font-weight:600;">${c.column_name}</td>
          <td><span class="badge badge-info">${c.data_type}</span></td>
          <td><span class="badge ${piiBadge}">${c.pii_type}</span></td>
          <td style="color:var(--text-muted);">${cConf}</td>
          <td>${c.null_count}</td>
          <td>${outVal}</td>
        `;
        tbody.appendChild(tr);
      });

      const corrTbody = document.querySelector('#profile-corr-table tbody');
      corrTbody.innerHTML = '';
      if (prof.correlation_columns && prof.correlation_columns.length > 0) {
        let headerHtml = '<tr><th></th>';
        prof.correlation_columns.forEach(col => { headerHtml += `<th>${col}</th>`; });
        headerHtml += '</tr>';
        corrTbody.innerHTML += headerHtml;

        prof.correlation_matrix.forEach((row, i) => {
          let rowHtml = `<tr><th style="white-space:nowrap;">${prof.correlation_columns[i]}</th>`;
          row.forEach(val => {
            const color = val > 0.5 ? '#34d399' : (val < -0.3 ? '#fb7185' : '#94a3b8');
            rowHtml += `<td style="color:${color}; font-weight:600;">${val.toFixed(2)}</td>`;
          });
          rowHtml += '</tr>';
          corrTbody.innerHTML += rowHtml;
        });
      } else {
        corrTbody.innerHTML = '<tr><td>No numeric correlation data available.</td></tr>';
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function cleanseCurrentDataset() {
    const dsId = document.getElementById('profile-dataset-select').value;
    if (!dsId) return;
    logWorker(`Executing 1-Click Cleanse & Anonymize on '${dsId}'...`);
    try {
      const res = await fetch(`/api/v1/datasets/${dsId}/cleanse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ anonymize_pii: true })
      });
      const data = await res.json();
      logWorker(`Cleanse complete. New dataset: ${data.dataset.name}`);
      await loadDatasets();
      document.getElementById('profile-dataset-select').value = data.dataset.dataset_id;
      await loadProfileForSelected();
    } catch (err) {
      logWorker(`Cleanse failed: ${err}`);
    }
  }

  function updateDpDefaults() {
    const level = document.getElementById('gen-privacy-level').value;
    const eps = document.getElementById('gen-epsilon');
    const dlt = document.getElementById('gen-delta');
    if (level === 'NONE') { eps.value = 100.0; dlt.value = 0.001; }
    else if (level === 'LOW') { eps.value = 5.0; dlt.value = 0.00001; }
    else if (level === 'MEDIUM') { eps.value = 1.0; dlt.value = 0.00001; }
    else if (level === 'HIGH') { eps.value = 0.1; dlt.value = 0.000001; }
  }

  async function handleGenerate(evt) {
    evt.preventDefault();
    const datasetId = document.getElementById('gen-dataset-id').value;
    const targetRows = parseInt(document.getElementById('gen-target-rows').value, 10);
    const engine = document.getElementById('gen-engine').value;
    const privacyLevel = document.getElementById('gen-privacy-level').value;
    const epsilon = parseFloat(document.getElementById('gen-epsilon').value);
    const delta = parseFloat(document.getElementById('gen-delta').value);
    const targetCol = document.getElementById('gen-target-col').value.trim();
    const minorityRatio = parseFloat(document.getElementById('gen-minority-ratio').value);
    const anonymizePii = document.getElementById('gen-anonymize-pii').checked;

    const payload = {
      dataset_id: datasetId,
      target_rows: targetRows,
      engine: engine,
      privacy_level: privacyLevel,
      epsilon: epsilon,
      delta: delta,
      anonymize_pii: anonymizePii,
      target_column: targetCol || null,
      target_minority_ratio: targetCol ? minorityRatio : null
    };

    logWorker(`Submitting synthetic generation job (${engine}, ${privacyLevel})...`);
    switchStep(4);

    try {
      const res = await fetch('/api/v1/jobs/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      currentJobId = data.job.job_id;
      const qScore = (data.report.overall_quality_score * 100).toFixed(1);
      logWorker(`Job ${currentJobId} completed. Quality: ${qScore}%`);
      await loadJobs();
      renderReport(data.report);
      switchStep(5);
    } catch (err) {
      logWorker(`Generation failed: ${err}`);
    }
  }

  async function loadJobs() {
    try {
      const res = await fetch('/api/v1/jobs');
      const jobs = await res.json();
      const tbody = document.querySelector('#jobs-table tbody');
      const reportSelect = document.getElementById('report-job-select');
      tbody.innerHTML = '';
      reportSelect.innerHTML = '';

      if (jobs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No jobs yet.</td></tr>';
        return;
      }

      jobs.forEach(j => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td style="font-weight:600;">${j.job_id}</td>
          <td>${j.dataset_name}</td>
          <td><span class="badge badge-info">${j.config.engine}</span></td>
          <td><span class="badge badge-success">${j.status}</span></td>
          <td>${j.rows_generated}</td>
          <td>
            <button class="btn btn-secondary" onclick="viewJobReport('${j.job_id}')"
              style="padding:4px 8px; font-size:10px;">Audit Report</button>
          </td>
        `;
        tbody.appendChild(tr);
        const optTitle = `${j.job_id} (${j.dataset_name})`;
        reportSelect.innerHTML += `<option value="${j.job_id}">${optTitle}</option>`;
      });

      if (!currentJobId && jobs.length > 0) {
        currentJobId = jobs[0].job_id;
        reportSelect.value = currentJobId;
        loadReportForSelected();
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function viewJobReport(jobId) {
    currentJobId = jobId;
    document.getElementById('report-job-select').value = jobId;
    await loadReportForSelected();
    switchStep(5);
  }

  async function loadReportForSelected() {
    const jobId = document.getElementById('report-job-select').value;
    if (!jobId) return;
    currentJobId = jobId;
    try {
      const res = await fetch(`/api/v1/jobs/${jobId}/report?format=json`);
      if (!res.ok) return;
      const report = await res.json();
      renderReport(report);
    } catch (err) {
      console.error(err);
    }
  }

  function renderReport(report) {
    const qStr = `${(report.overall_quality_score * 100).toFixed(1)}%`;
    const fStr = `${(report.marginal_fidelity_score * 100).toFixed(1)}%`;
    const cStr = `${(report.correlation_stability_score * 100).toFixed(1)}%`;
    const pStr = `${(report.privacy_score * 100).toFixed(1)}%`;

    document.getElementById('rep-quality').innerText = qStr;
    document.getElementById('rep-fidelity').innerText = fStr;
    document.getElementById('rep-corr').innerText = cStr;
    document.getElementById('rep-privacy').innerText = pStr;
    document.getElementById('rep-verdict').innerText = report.executive_verdict;
    document.getElementById('rep-hipaa').innerText = report.hipaa_gdpr_ready ? 'YES' : 'NO';
    const hBadge = report.hipaa_gdpr_ready ? 'badge-success' : 'badge-danger';
    document.getElementById('rep-hipaa').className = `badge ${hBadge}`;

    if (report.privacy_metrics) {
      const pm = report.privacy_metrics;
      document.getElementById('rep-dcr').innerText = pm.dcr_mean.toFixed(4);
      document.getElementById('rep-nndr').innerText = pm.nndr_mean.toFixed(4);
      document.getElementById('rep-collisions').innerText = pm.exact_record_collisions;
      document.getElementById('rep-pii-leaks').innerText = pm.pii_leakage_count;
    }

    if (report.privacy_ledger) {
      const pl = report.privacy_ledger;
      document.getElementById('ledger-spent').innerText = pl.spent_epsilon.toFixed(2);
      document.getElementById('ledger-remaining').innerText = pl.remaining_epsilon.toFixed(2);
      document.getElementById('ledger-initial').innerText = pl.initial_epsilon.toFixed(2);
      document.getElementById('ledger-delta').innerText = pl.delta;
      document.getElementById('ledger-status').innerText = pl.is_exhausted ? 'EXHAUSTED' : 'ACTIVE';
      const lBadge = pl.is_exhausted ? 'badge-danger' : 'badge-success';
      document.getElementById('ledger-status').className = `badge ${lBadge}`;
    }
  }

  function downloadArtifact(fmt) {
    if (!currentJobId) return;
    if (fmt === 'markdown') {
      window.open(`/api/v1/jobs/${currentJobId}/report?format=markdown`, '_blank');
    } else {
      window.location.href = `/api/v1/jobs/${currentJobId}/download?format=${fmt}`;
    }
  }

  window.addEventListener('DOMContentLoaded', loadInitData);
</script>
</body>
</html>"""


def create_app(
    repository: StudioRepository | None = None,
    bootstrap: bool = True,
) -> FastAPI:
    """Create and configure the SynthAI Studio FastAPI application.

    Pre-conditions:
        - Python >= 3.11 with FastAPI.
    Post-conditions:
        - Returns a configured FastAPI application with all routes, health checks,
          and interactive web console mounted.
    """
    repo = repository if repository is not None else StudioRepository()
    orchestrator = StudioWorkflowOrchestrator(repo)

    if bootstrap:
        orchestrator.bootstrap_defaults()

    application = FastAPI(
        title="SynthAI Studio",
        description="Privacy-Preserving Synthetic Data & Differential Privacy Quality Auditing",
        version="0.1.0",
    )

    # Attach instances to application state for test and inspection access
    application.state.repository = repo
    application.state.orchestrator = orchestrator

    @application.get("/healthz")
    async def healthz() -> dict[str, str]:
        """Health check liveness probe.

        Pre-conditions:
            - Service process is responsive.
        Post-conditions:
            - Returns healthy status indicator.
        """
        return {"status": "healthy", "service": "synthai-studio", "version": "0.1.0"}

    @application.get("/ready")
    async def ready() -> dict[str, Any]:
        """Readiness check probe validating DuckDB catalog and orchestrator.

        Pre-conditions:
            - Repository and Orchestrator are initialized.
        Post-conditions:
            - Returns ready status with dataset and job counts.
        """
        datasets = repo.list_datasets()
        jobs = repo.list_jobs()
        return {
            "status": "ready",
            "datasets_count": len(datasets),
            "jobs_count": len(jobs),
            "temporal_host": orchestrator.temporal_host,
        }

    @application.get("/api/v1/benchmarks", response_model=list[BenchmarkMetadata])
    async def list_benchmarks_endpoint() -> list[BenchmarkMetadata]:
        """Enumerate built-in reference benchmark dataset descriptors.

        Pre-conditions:
            - None.
        Post-conditions:
            - Returns list of available BenchmarkMetadata items.
        """
        return list_benchmarks()

    @application.post("/api/v1/datasets/seed/{benchmark_id}")
    async def seed_benchmark_endpoint(
        benchmark_id: str,
        row_count: int | None = None,
        payload: SeedRequest | None = None,
    ) -> dict[str, Any]:
        """Seed a built-in benchmark dataset into the catalog.

        Pre-conditions:
            - benchmark_id exists in BENCHMARK_REGISTRY.
        Post-conditions:
            - Returns dictionary with 'dataset' and 'profile'.
        """
        if benchmark_id not in BENCHMARK_REGISTRY:
            raise HTTPException(
                status_code=404,
                detail=f"Benchmark '{benchmark_id}' not found",
            )

        resolved_count = row_count
        if resolved_count is None and payload is not None:
            resolved_count = payload.row_count

        meta, profile = orchestrator.seed_benchmark(
            benchmark_id=benchmark_id,
            row_count=resolved_count,
        )
        return {"dataset": meta, "profile": profile}

    @application.post("/api/v1/datasets/presign-upload", response_model=PresignedUploadTicket)
    async def presign_upload_endpoint(req: PresignRequest) -> PresignedUploadTicket:
        """Create a presigned upload capability ticket for SeaweedFS/S3 streaming.

        Pre-conditions:
            - req.dataset_name is non-empty.
        Post-conditions:
            - Generates and persists a PresignedUploadTicket.
        """
        return repo.create_presigned_upload_ticket(
            dataset_name=req.dataset_name,
            expiry_seconds=req.expiry_seconds,
        )

    @application.post("/api/v1/datasets/upload")
    async def upload_dataset_endpoint(
        request: Request,
        token: str | None = None,
    ) -> dict[str, Any]:
        """Ingest and profile a custom tabular dataset via multipart file or JSON.

        Pre-conditions:
            - Valid multipart form file or JSON payload containing tabular rows.
        Post-conditions:
            - Ingests, persists, and profiles dataset into DuckDB catalog.
        """
        ticket: PresignedUploadTicket | None = None
        if token:
            try:
                ticket = repo.consume_presigned_upload_ticket(token)
            except KeyError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        content_type = request.headers.get("content-type", "")
        name = ticket.dataset_name if ticket else "uploaded_dataset"
        rows: list[dict[str, Any]] = []

        if "multipart/form-data" in content_type:
            form = await request.form()
            file_item = form.get("file")
            if file_item is None or not hasattr(file_item, "read"):
                raise HTTPException(
                    status_code=400,
                    detail="Missing 'file' field in multipart form upload",
                )
            form_name = form.get("name")
            if form_name and isinstance(form_name, str) and not ticket:
                name = form_name
            filename = getattr(file_item, "filename", "upload.csv") or "upload.csv"
            raw_bytes = await file_item.read()
            rows = parse_tabular_payload(raw_bytes, filename=filename)
        elif "application/json" in content_type:
            body = await request.json()
            if not isinstance(body, dict):
                raise HTTPException(
                    status_code=400,
                    detail="JSON payload must be a JSON object",
                )
            if "name" in body and body["name"] and not ticket:
                name = str(body["name"])
            if "rows" in body and isinstance(body["rows"], list):
                rows = [dict(r) for r in body["rows"]]
            elif "content" in body:
                fname = str(body.get("filename", "upload.csv"))
                rows = parse_tabular_payload(str(body["content"]), filename=fname)
            else:
                raise HTTPException(
                    status_code=400,
                    detail="JSON payload must contain 'rows' list or 'content' string",
                )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported Content-Type '{content_type}'",
            )

        if not rows:
            raise HTTPException(
                status_code=400,
                detail="Tabular dataset contains zero parseable rows",
            )

        meta, profile = orchestrator.ingest_dataset(
            name=name,
            rows=rows,
            description=f"User ingested dataset '{name}' ({len(rows)} records)",
            source_type="upload",
        )
        return {"dataset": meta, "profile": profile}

    @application.get("/api/v1/datasets", response_model=list[DatasetMetadata])
    async def list_datasets_endpoint() -> list[DatasetMetadata]:
        """List all datasets in the DuckDB catalog.

        Pre-conditions:
            - None.
        Post-conditions:
            - Returns list of DatasetMetadata records.
        """
        return repo.list_datasets()

    @application.get("/api/v1/datasets/{dataset_id}/profile", response_model=DatasetProfileReport)
    async def get_dataset_profile_endpoint(dataset_id: str) -> DatasetProfileReport:
        """Retrieve the statistical profiling and PII report for a dataset.

        Pre-conditions:
            - dataset_id exists.
        Post-conditions:
            - Returns DatasetProfileReport; raises 404 if not found.
        """
        profile = repo.get_profile(dataset_id)
        if profile is None:
            raise HTTPException(
                status_code=404,
                detail=f"Profile for dataset '{dataset_id}' not found",
            )
        return profile

    @application.post("/api/v1/datasets/{dataset_id}/cleanse")
    async def cleanse_dataset_endpoint(
        dataset_id: str,
        payload: CleanseRequest | None = None,
    ) -> dict[str, Any]:
        """Cleanse, deduplicate, normalize, and anonymize an existing dataset.

        Pre-conditions:
            - dataset_id exists in catalog.
        Post-conditions:
            - Persists and returns cleansed dataset and newly profiled report.
        """
        anonymize = True if payload is None else payload.anonymize_pii
        try:
            clean_meta, clean_profile = orchestrator.cleanse_existing_dataset(
                dataset_id=dataset_id,
                anonymize_pii=anonymize,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"dataset": clean_meta, "profile": clean_profile}

    @application.post("/api/v1/jobs/generate")
    async def generate_synthetic_job_endpoint(config: SynthesisConfig) -> dict[str, Any]:
        """Execute a synthetic generation job and emit a quality audit report.

        Pre-conditions:
            - config.dataset_id exists in catalog.
            - config.target_rows >= 10.
        Post-conditions:
            - Returns dictionary with 'job' (GenerationJob) and 'report' (QualityValidationReport).
        """
        try:
            repo.get_dataset_metadata(config.dataset_id)
        except KeyError as exc:
            raise HTTPException(
                status_code=404,
                detail=f"Dataset '{config.dataset_id}' not found in catalog",
            ) from exc

        job, report = orchestrator.run_generation_job(config)
        return {"job": job, "report": report}

    @application.get("/api/v1/jobs", response_model=list[GenerationJob])
    async def list_jobs_endpoint() -> list[GenerationJob]:
        """Enumerate all historical synthetic generation jobs.

        Pre-conditions:
            - None.
        Post-conditions:
            - Returns list of GenerationJob records.
        """
        return repo.list_jobs()

    @application.get("/api/v1/jobs/{job_id}", response_model=GenerationJob)
    async def get_job_endpoint(job_id: str) -> GenerationJob:
        """Retrieve details of a single generation job.

        Pre-conditions:
            - job_id exists.
        Post-conditions:
            - Returns GenerationJob; raises 404 if not found.
        """
        try:
            return repo.get_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @application.get("/api/v1/jobs/{job_id}/report")
    async def get_job_report_endpoint(
        job_id: str,
        format: str = "json",
    ) -> Response:
        """Retrieve synthetic quality validation report in JSON or Markdown format.

        Pre-conditions:
            - job_id exists and has a validated report.
            - format is 'json' or 'markdown'.
        Post-conditions:
            - Returns JSON or Markdown content.
        """
        try:
            report = repo.get_quality_report(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        if format.lower() == "markdown":
            md_text = render_quality_report_markdown(report)
            return Response(content=md_text, media_type="text/markdown")

        return Response(
            content=report.model_dump_json(),
            media_type="application/json",
        )

    @application.get("/api/v1/jobs/{job_id}/download")
    async def download_synthetic_dataset_endpoint(
        job_id: str,
        format: str = "csv",
    ) -> Response:
        """Download generated synthetic rows in CSV, JSON, or Parquet format.

        Pre-conditions:
            - job_id exists.
            - format is 'csv', 'json', or 'parquet'.
        Post-conditions:
            - Returns binary payload with Content-Disposition attachment header.
        """
        try:
            repo.get_job(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        rows = repo.get_job_rows(job_id)
        try:
            export_fmt = ExportFormat(format.lower())
        except ValueError as exc:
            allowed = [f.value for f in ExportFormat]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format '{format}'. Allowed: {allowed}",
            ) from exc

        payload, media_type, ext = repo.export_rows(rows, export_fmt)
        filename = f"synthai-{job_id}.{ext}"
        return Response(
            content=payload,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @application.get("/", response_class=HTMLResponse)
    async def index_ui() -> HTMLResponse:
        """Render the 5-Step Interactive SynthAI Studio Web UI console.

        Pre-conditions:
            - None.
        Post-conditions:
            - Returns complete single-page application HTML5 interface.
        """
        return HTMLResponse(content=_build_studio_ui_html(), status_code=200)

    return application


# Global application instance for uvicorn runtime
app: FastAPI = create_app(
    bootstrap=os.getenv("SYNTHAI_BOOTSTRAP", "true").lower() in ("true", "1", "yes")
)
