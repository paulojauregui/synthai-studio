/**
 * SynthAI Studio -- Client Application State Store, WAI-ARIA Controller & API Handlers
 * Contract: docs/UX_SPEC.md / docs/specs/M09_SPEC.md
 * Zero emojis, zero external runtime dependencies.
 */

// 1. Centralized Application State Store
const StudioState = {
  activeStep: 1,
  benchmarks: [],
  datasets: [],
  jobs: [],
  currentDatasetId: null,
  currentJobId: null,
  currentProfile: null,
  currentReport: null,
};

// 2. HTML Sanitization Helper
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// 3. WAI-ARIA Live Announcers (Polite & Assertive)
function announcePolite(message) {
  const el = document.getElementById('aria-status-polite');
  if (el) {
    el.textContent = '';
    setTimeout(() => {
      el.textContent = message;
    }, 50);
  }
}

function announceAssertive(message) {
  const el = document.getElementById('aria-status-assertive');
  if (el) {
    el.textContent = '';
    setTimeout(() => {
      el.textContent = message;
    }, 50);
  }
}

// 4. Global Error Alert & Focus Management
let currentErrorRetry = null;

function showGlobalError(title, detail, retryCallback = null) {
  const banner = document.getElementById('global-error-banner');
  const textEl = document.getElementById('global-error-text');
  currentErrorRetry = retryCallback;

  if (textEl) {
    textEl.innerHTML = `<strong>${escapeHtml(title)}:</strong> ${escapeHtml(detail || 'An unexpected error occurred.')}`;
  }
  if (banner) {
    banner.hidden = false;
    banner.focus();
  }
  announceAssertive(`Error: ${title}. ${detail || ''}`);
}

function dismissGlobalError() {
  const banner = document.getElementById('global-error-banner');
  if (banner) {
    banner.hidden = true;
  }
  currentErrorRetry = null;
  const activeTab = document.getElementById(`tab-step-${StudioState.activeStep}`);
  if (activeTab) {
    activeTab.focus();
  }
}

// 5. WAI-ARIA Tabs Controller with Roving tabindex
function switchStep(step, focusTab = false) {
  const stepNum = parseInt(step, 10);
  if (isNaN(stepNum) || stepNum < 1 || stepNum > 5) return;
  StudioState.activeStep = stepNum;

  // Update step panels visibility
  for (let i = 1; i <= 5; i++) {
    const panel = document.getElementById(`step-${i}`);
    if (panel) {
      const isTarget = i === stepNum;
      panel.classList.toggle('active', isTarget);
      panel.hidden = !isTarget;
    }
  }

  // Update tabs roving tabindex and aria-selected state
  for (let i = 1; i <= 5; i++) {
    const tab = document.getElementById(`tab-step-${i}`);
    if (tab) {
      const isTarget = i === stepNum;
      tab.classList.toggle('active', isTarget);
      tab.setAttribute('aria-selected', isTarget ? 'true' : 'false');
      tab.setAttribute('tabindex', isTarget ? '0' : '-1');
      if (isTarget && focusTab) {
        tab.focus();
      }
    }
  }

  const titles = [
    'Connect & Seed',
    'Quality & PII Audit',
    'Engine & DP Config',
    'Worker Monitor',
    'Fidelity & Export',
  ];
  announcePolite(`Activated Step ${stepNum}: ${titles[stepNum - 1]}.`);
}

function handleTabKeydown(evt) {
  const target = evt.target.closest('[role="tab"]');
  if (!target) return;

  const currentStep = parseInt(target.getAttribute('data-step') || StudioState.activeStep, 10);
  let nextStep = currentStep;

  switch (evt.key) {
    case 'ArrowRight':
    case 'ArrowDown':
      evt.preventDefault();
      nextStep = currentStep === 5 ? 1 : currentStep + 1;
      switchStep(nextStep, true);
      break;
    case 'ArrowLeft':
    case 'ArrowUp':
      evt.preventDefault();
      nextStep = currentStep === 1 ? 5 : currentStep - 1;
      switchStep(nextStep, true);
      break;
    case 'Home':
      evt.preventDefault();
      switchStep(1, true);
      break;
    case 'End':
      evt.preventDefault();
      switchStep(5, true);
      break;
    case 'Enter':
    case ' ':
      evt.preventDefault();
      switchStep(currentStep, true);
      break;
    case 'Escape':
      evt.preventDefault();
      dismissGlobalError();
      break;
    default:
      break;
  }
}

// 6. Console Activity Logger
function logConsole(message) {
  const consoleEl = document.getElementById('worker-console');
  if (!consoleEl) return;
  const now = new Date();
  const timestamp = now.toTimeString().split(' ')[0];
  const line = `[${timestamp}] ${message}`;
  const p = document.createElement('div');
  p.textContent = line;
  consoleEl.appendChild(p);
  consoleEl.scrollTop = consoleEl.scrollHeight;
}

// 7. API Handlers

// Initial Data Bootstrapping
async function loadInitData() {
  try {
    const resp = await fetch('/ready');
    if (resp.ok) {
      const ready = await resp.json();
      const sService = document.getElementById('status-service');
      const sCatalog = document.getElementById('status-catalog');
      const sTemporal = document.getElementById('status-temporal');

      if (sService) sService.textContent = 'SERVICE: ONLINE';
      if (sCatalog) sCatalog.textContent = `DATASETS: ${ready.datasets_count}`;
      if (sTemporal) {
        if (ready.temporal_host) {
          sTemporal.textContent = 'TEMPORAL: READY';
          sTemporal.className = 'badge badge-success';
        } else {
          sTemporal.textContent = 'TEMPORAL: LOCAL WORKER';
          sTemporal.className = 'badge badge-warn';
        }
      }
    }
  } catch (err) {
    logConsole(`Readiness probe failed: ${err.message}`);
  }

  await loadBenchmarks();
  await loadDatasets();
  await loadProfileForSelected();
  await loadJobs();
  await loadReportForSelected();
  updateDpDefaults();
}

// Step 1: Benchmarks Discovery & Seeding
async function loadBenchmarks() {
  const container = document.getElementById('benchmark-cards');
  if (container && window.SynthAIViews && typeof window.SynthAIViews.renderLoadingSkeleton === 'function') {
    window.SynthAIViews.renderLoadingSkeleton(container, 'card', 3);
  }
  try {
    const resp = await fetch('/api/v1/benchmarks');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    StudioState.benchmarks = data;

    if (!container) return;

    if (window.SynthAIViews && typeof window.SynthAIViews.renderBenchmarkCards === 'function') {
      window.SynthAIViews.renderBenchmarkCards(container, StudioState.benchmarks);
    } else {
      // Fallback inline rendering
      container.innerHTML = '';
      StudioState.benchmarks.forEach((b) => {
        const card = document.createElement('div');
        card.className = 'benchmark-card';
        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <strong style="color: var(--text-primary); font-size: 14px;">${escapeHtml(b.name)}</strong>
            <span class="badge badge-info">${escapeHtml(b.domain)}</span>
          </div>
          <p style="color: var(--text-muted); font-size: 12px; margin: 4px 0;">${escapeHtml(b.description)}</p>
          <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">
            Rows: <span class="tabular-nums">${b.default_row_count}</span> |
            Target: <code>${escapeHtml(b.target_column || 'None')}</code>
            (${escapeHtml(String(b.minority_label || '-'))})
          </div>
          <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px;">
            ${(b.pii_columns || []).map((col) => `<span class="badge badge-danger">PII: ${escapeHtml(col)}</span>`).join('')}
            ${(b.highlights || []).map((h) => `<span class="badge badge-info">${escapeHtml(h)}</span>`).join('')}
          </div>
          <button type="button" class="btn btn-secondary" onclick="seedBenchmark('${b.benchmark_id}')">
            Seed Benchmark Dataset
          </button>
        `;
        container.appendChild(card);
      });
    }
  } catch (err) {
    if (container && window.SynthAIViews && typeof window.SynthAIViews.renderErrorState === 'function') {
      window.SynthAIViews.renderErrorState(
        container,
        'Benchmark Discovery Failed',
        err.message,
        'Retry Benchmark Discovery',
        loadBenchmarks
      );
    }
    showGlobalError('Benchmark Discovery Failed', err.message, loadBenchmarks);
  }
}

async function seedBenchmark(bmId) {
  try {
    logConsole(`Seeding benchmark dataset '${bmId}'...`);
    const resp = await fetch(`/api/v1/benchmarks/${bmId}/seed`, { method: 'POST' });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const res = await resp.json();

    StudioState.currentDatasetId = res.dataset.dataset_id;
    StudioState.currentProfile = res.profile;

    await loadDatasets();
    const select = document.getElementById('profile-dataset-select');
    if (select) select.value = res.dataset.dataset_id;
    await loadProfileForSelected();

    announcePolite(
      `Seeded benchmark ${res.dataset.name} with ${res.dataset.row_count} rows. Navigated to Step 2: Quality and PII Audit.`
    );
    logConsole(`Benchmark '${res.dataset.name}' successfully seeded (${res.dataset.row_count} rows).`);
    switchStep(2, true);
  } catch (err) {
    showGlobalError('Benchmark Seeding Failed', err.message);
  }
}

// Step 1: Custom Dataset Upload & Presigned Ticket
async function handleUpload(evt) {
  if (evt) evt.preventDefault();
  const form = document.getElementById('upload-form');
  if (!form) return;
  const formData = new FormData(form);

  try {
    logConsole('Uploading custom tabular dataset...');
    const resp = await fetch('/api/v1/datasets/upload', {
      method: 'POST',
      body: formData,
    });
    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${resp.status}`);
    }
    const res = await resp.json();

    StudioState.currentDatasetId = res.dataset.dataset_id;
    StudioState.currentProfile = res.profile;
    await loadDatasets();

    const select = document.getElementById('profile-dataset-select');
    if (select) select.value = res.dataset.dataset_id;
    await loadProfileForSelected();

    announcePolite(`Uploaded and profiled dataset ${res.dataset.name} (${res.dataset.row_count} rows).`);
    logConsole(`Uploaded dataset '${res.dataset.name}' successfully.`);
    form.reset();
    switchStep(2, true);
  } catch (err) {
    showGlobalError('Dataset Ingestion Failed', err.message);
  }
}

async function generateTicket() {
  const nameInput = document.getElementById('presign-name');
  const datasetName = (nameInput && nameInput.value.trim()) || 'custom_upload';

  try {
    const resp = await fetch('/api/v1/presign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_name: datasetName, expiry_seconds: 3600 }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const ticket = await resp.json();

    const resultBox = document.getElementById('presign-result');
    const textPre = document.getElementById('presign-text');
    if (resultBox && textPre) {
      resultBox.hidden = false;
      textPre.textContent = JSON.stringify(ticket, null, 2);
    }
    announcePolite(`Generated presigned upload ticket for ${ticket.dataset_name}.`);
    logConsole(`Presigned ticket generated: ${ticket.upload_token}`);
  } catch (err) {
    showGlobalError('Ticket Generation Failed', err.message);
  }
}

// Step 2: Datasets & Profiling Audit
async function loadDatasets() {
  try {
    const resp = await fetch('/api/v1/datasets');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const datasets = await resp.json();
    StudioState.datasets = datasets;

    const profSelect = document.getElementById('profile-dataset-select');
    const genSelect = document.getElementById('gen-dataset-id');

    [profSelect, genSelect].forEach((sel) => {
      if (!sel) return;
      const prevVal = sel.value;
      sel.innerHTML = '';
      datasets.forEach((d) => {
        const opt = document.createElement('option');
        opt.value = d.dataset_id;
        opt.textContent = `${d.name} (${d.row_count} rows)${d.is_cleansed ? ' [CLEANSED]' : ''}`;
        sel.appendChild(opt);
      });
      if (prevVal && datasets.some((d) => d.dataset_id === prevVal)) {
        sel.value = prevVal;
      }
    });

    if (StudioState.currentDatasetId && profSelect) {
      profSelect.value = StudioState.currentDatasetId;
    }
  } catch (err) {
    logConsole(`Dataset listing failed: ${err.message}`);
  }
}

async function loadProfileForSelected() {
  const select = document.getElementById('profile-dataset-select');
  const dsId = select ? select.value : StudioState.currentDatasetId;
  const emptyState = document.getElementById('profile-empty-state');

  if (!dsId) {
    if (emptyState) emptyState.hidden = false;
    return;
  }
  if (emptyState) emptyState.hidden = true;
  StudioState.currentDatasetId = dsId;

  try {
    logConsole(`Fetching quality & PII profile for dataset '${dsId}'...`);
    const resp = await fetch(`/api/v1/datasets/${dsId}/profile`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const prof = await resp.json();
    StudioState.currentProfile = prof;

    if (window.SynthAIViews && typeof window.SynthAIViews.renderProfileView === 'function') {
      window.SynthAIViews.renderProfileView(prof);
    } else {
      // Fallback inline rendering
      const profRows = document.getElementById('prof-rows');
      const profCols = document.getElementById('prof-cols');
      const profQuality = document.getElementById('prof-quality');
      const profPrivacy = document.getElementById('prof-privacy-risk');

      if (profRows) profRows.textContent = String(prof.row_count);
      if (profCols) profCols.textContent = String(prof.column_count);
      if (profQuality) profQuality.textContent = `${(prof.data_quality_score * 100).toFixed(1)}%`;
      if (profPrivacy) {
        profPrivacy.textContent = `${(prof.privacy_risk_score * 100).toFixed(1)}%`;
        profPrivacy.style.color = prof.privacy_risk_score === 0 ? 'var(--accent-secondary)' : 'var(--status-danger-fg)';
      }

      // Column profiles table
      const tbody = document.querySelector('#profile-columns-table tbody');
      if (tbody) {
        tbody.innerHTML = '';
        (prof.columns || []).forEach((c) => {
          const finding = (prof.pii_findings || []).find((f) => f.column_name === c.name);
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <th scope="row"><code>${escapeHtml(c.name)}</code></th>
            <td><span class="badge badge-info">${escapeHtml(c.inferred_type)}</span></td>
            <td>${c.pii_type !== 'NONE' ? `<span class="badge badge-danger">${escapeHtml(c.pii_type)}</span>` : '<span class="badge badge-success">CLEAN</span>'}</td>
            <td>${finding ? `${(finding.confidence * 100).toFixed(0)}% -- ${escapeHtml(finding.remediation)}` : '-'}</td>
            <td data-numeric="true" class="tabular-nums">${c.null_count} (${(c.null_ratio * 100).toFixed(1)}%)</td>
            <td data-numeric="true" class="tabular-nums">${c.numerical_stats ? c.numerical_stats.outlier_count_zscore : '-'}</td>
          `;
          tbody.appendChild(tr);
        });
      }

      // Quality issues list
      const issuesContainer = document.getElementById('profile-issues-list');
      if (issuesContainer) {
        issuesContainer.innerHTML = '';
        if ((prof.quality_issues || []).length === 0) {
          issuesContainer.innerHTML = '<div class="state-nominal">Zero open data quality or unmasked PII defects detected.</div>';
        } else {
          prof.quality_issues.forEach((issue) => {
            const item = document.createElement('div');
            item.className = 'issue-item';
            item.setAttribute('data-severity', issue.severity);
            item.innerHTML = `
              <strong>[${escapeHtml(issue.severity)}] ${escapeHtml(issue.issue_type)}</strong> (${escapeHtml(issue.column_name || 'DATASET')}):
              ${escapeHtml(issue.description)} -- <em>Action: ${escapeHtml(issue.suggested_action)}</em>
            `;
            issuesContainer.appendChild(item);
          });
        }
      }
    }
  } catch (err) {
    showGlobalError('Profile Load Failed', err.message, loadProfileForSelected);
  }
}

async function cleanseCurrentDataset() {
  const select = document.getElementById('profile-dataset-select');
  const dsId = select ? select.value : StudioState.currentDatasetId;
  if (!dsId) {
    showGlobalError('Cleanse Error', 'No dataset selected to cleanse.');
    return;
  }

  try {
    logConsole(`Executing 1-Click Cleanse & Anonymize on '${dsId}'...`);
    const resp = await fetch(`/api/v1/datasets/${dsId}/cleanse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anonymize_pii: true }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const res = await resp.json();

    StudioState.currentProfile = res.profile;
    await loadDatasets();
    if (select) select.value = res.dataset.dataset_id;
    await loadProfileForSelected();

    announcePolite(
      `Cleansed dataset ${res.dataset.name}. Privacy risk score reduced to ${(res.profile.privacy_risk_score * 100).toFixed(1)}%.`
    );
    logConsole(`Dataset '${res.dataset.name}' successfully cleansed.`);
  } catch (err) {
    showGlobalError('Cleansing Failed', err.message);
  }
}

// Step 3: Engine & DP Configuration
function updateDpDefaults() {
  const privSelect = document.getElementById('gen-privacy-level');
  const engineSelect = document.getElementById('gen-engine');
  const epsInput = document.getElementById('gen-epsilon');
  const deltaInput = document.getElementById('gen-delta');
  const preview = document.getElementById('dp-guarantee-preview');

  const level = privSelect ? privSelect.value : 'MEDIUM';
  const engine = engineSelect ? engineSelect.value : 'GAUSSIAN_COPULA';

  let eps = 1.0;
  let delta = 0.00001;
  let disabled = false;

  switch (level) {
    case 'HIGH':
      eps = 0.1;
      delta = 0.000001;
      break;
    case 'MEDIUM':
      eps = 1.0;
      delta = 0.00001;
      break;
    case 'LOW':
      eps = 10.0;
      delta = 0.00001;
      break;
    case 'NONE':
      eps = 0;
      delta = 0.00001;
      disabled = true;
      break;
    default:
      break;
  }

  if (epsInput) {
    epsInput.disabled = disabled;
    if (!disabled) epsInput.value = String(eps);
  }
  if (deltaInput) {
    deltaInput.disabled = disabled;
    deltaInput.value = String(delta);
  }

  if (preview) {
    if (level === 'NONE') {
      preview.className = 'degraded-banner state-degraded';
      preview.textContent =
        'UNPERTURBED EMPIRICAL MODE: Formal (epsilon, delta)-DP noise injection is disabled. HIPAA/GDPR certification requires LOW, MEDIUM, or HIGH.';
    } else if (engine === 'SPARK_LLM_EDGE') {
      preview.className = 'state-nominal';
      preview.innerHTML = `<strong>(epsilon, delta)-DP Active (epsilon=${eps}, delta=${delta})</strong>: Split-timeout circuit breaker (&lt; 2.0s probe to happy.tail749110.ts.net:8000 with automatic local CPU Copula fallback).`;
    } else {
      preview.className = 'state-nominal';
      preview.textContent = `Differential Privacy Guarantee Active: Epsilon = ${eps}, Delta = ${delta}. Calibrated Laplace & Analytic Gaussian perturbation.`;
    }
  }
}

async function handleGenerate(evt) {
  if (evt) evt.preventDefault();
  const dsId = document.getElementById('gen-dataset-id')?.value;
  const rows = parseInt(document.getElementById('gen-target-rows')?.value || '250', 10);
  const engine = document.getElementById('gen-engine')?.value || 'GAUSSIAN_COPULA';
  const privLevel = document.getElementById('gen-privacy-level')?.value || 'MEDIUM';
  const epsVal = parseFloat(document.getElementById('gen-epsilon')?.value || '1.0');
  const deltaVal = parseFloat(document.getElementById('gen-delta')?.value || '0.00001');
  const anonymize = document.getElementById('gen-anonymize-pii')?.checked ?? true;
  const targetCol = document.getElementById('gen-target-col')?.value.trim();
  const minorityValRaw = document.getElementById('gen-minority-val')?.value.trim();
  const minorityRatio = parseFloat(document.getElementById('gen-minority-ratio')?.value || '0.30');

  let upsampleConfig = null;
  if (targetCol) {
    let parsedVal = minorityValRaw;
    if (minorityValRaw.toLowerCase() === 'true') parsedVal = true;
    else if (minorityValRaw.toLowerCase() === 'false') parsedVal = false;
    else if (!isNaN(Number(minorityValRaw)) && minorityValRaw !== '') parsedVal = Number(minorityValRaw);
    else if (!minorityValRaw) parsedVal = 1;

    upsampleConfig = {
      column: targetCol,
      minority_value: parsedVal,
      target_ratio: minorityRatio,
    };
  }

  const payload = {
    dataset_id: dsId,
    target_rows: rows,
    engine: engine,
    privacy_level: privLevel,
    epsilon: privLevel === 'NONE' ? null : epsVal,
    delta: deltaVal,
    anonymize_pii: anonymize,
    upsample_config: upsampleConfig,
  };

  const btn = document.getElementById('btn-launch-synth');
  const originalText = btn ? btn.textContent : '';
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Executing Synthesis & Auditing...';
  }

  try {
    logConsole(`Launching synthesis job for dataset '${dsId}' using ${engine} (${privLevel})...`);
    const resp = await fetch('/api/v1/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${resp.status}`);
    }
    const res = await resp.json();

    StudioState.currentJobId = res.job.job_id;
    StudioState.currentReport = res.report;

    if (res.job.config && res.job.config.engine === 'SPARK_LLM_EDGE' && res.job.compute_tier === 'CPU_WORKER') {
      announceAssertive(
        `Notice: DGX Spark edge endpoint unavailable under 2.0 second circuit breaker. Job ${res.job.job_id} executed on local CPU worker fallback.`
      );
    } else {
      announcePolite(
        `Generation job ${res.job.job_id} completed on ${res.job.compute_tier}. Overall quality score: ${(res.report.overall_quality_score * 100).toFixed(1)}%.`
      );
    }
    logConsole(`Generation completed: Job ${res.job.job_id} (${res.job.rows_generated} rows).`);

    await loadJobs();
    const repSelect = document.getElementById('report-job-select');
    if (repSelect) repSelect.value = res.job.job_id;
    await loadReportForSelected();
    switchStep(4, true);
  } catch (err) {
    showGlobalError('Synthesis Execution Failed', err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }
}

// Step 4: Worker Monitor & Jobs Ledger
async function loadJobs() {
  try {
    const resp = await fetch('/api/v1/jobs');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const jobs = await resp.json();
    StudioState.jobs = jobs;

    const repSelect = document.getElementById('report-job-select');
    if (repSelect) {
      const prevVal = repSelect.value;
      repSelect.innerHTML = '';
      jobs.forEach((j) => {
        const opt = document.createElement('option');
        opt.value = j.job_id;
        opt.textContent = `${j.job_id} - ${j.dataset_name} (${j.config.engine})`;
        repSelect.appendChild(opt);
      });
      if (prevVal && jobs.some((j) => j.job_id === prevVal)) {
        repSelect.value = prevVal;
      }
    }

    if (window.SynthAIViews && typeof window.SynthAIViews.renderJobsAndLedger === 'function') {
      window.SynthAIViews.renderJobsAndLedger(jobs, StudioState.currentJobId);
    } else {
      // Fallback inline rendering
      const tbody = document.querySelector('#jobs-table tbody');
      if (tbody) {
        tbody.innerHTML = '';
        if (jobs.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" class="state-empty">No synthetic generation jobs executed yet.</td></tr>';
        } else {
          jobs.forEach((j) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <th scope="row"><code>${escapeHtml(j.job_id)}</code></th>
              <td>${escapeHtml(j.dataset_name)}</td>
              <td><code>${escapeHtml(j.config.engine)}</code></td>
              <td><span class="badge ${j.compute_tier === 'CPU_WORKER' && j.config.engine === 'SPARK_LLM_EDGE' ? 'badge-warn' : 'badge-info'}">${escapeHtml(j.compute_tier)}</span></td>
              <td><span class="badge ${j.status === 'COMPLETED' ? 'badge-success' : 'badge-danger'}">${escapeHtml(j.status)}</span></td>
              <td data-numeric="true" class="tabular-nums">${j.rows_generated} (${j.throughput_rows_per_sec.toFixed(0)} r/s)</td>
              <td><button type="button" class="btn btn-secondary" onclick="viewJobReport('${j.job_id}')">Audit Report</button></td>
            `;
            tbody.appendChild(tr);
          });
        }
      }

      // Compute fallback banner
      const latestJob = jobs.find((j) => j.job_id === StudioState.currentJobId) || jobs[0];
      const fallbackBanner = document.getElementById('compute-fallback-banner');
      if (fallbackBanner) {
        const isFallback = latestJob && latestJob.config.engine === 'SPARK_LLM_EDGE' && latestJob.compute_tier === 'CPU_WORKER';
        fallbackBanner.hidden = !isFallback;
      }

      // Privacy budget ledger
      if (latestJob && latestJob.privacy_ledger) {
        const pl = latestJob.privacy_ledger;
        const lStatus = document.getElementById('ledger-status');
        const lSpent = document.getElementById('ledger-spent');
        const lNoise = document.getElementById('ledger-noise-scale');
        const lRem = document.getElementById('ledger-remaining');
        const lDelta = document.getElementById('ledger-delta');
        const lInit = document.getElementById('ledger-initial');
        const lMech = document.getElementById('ledger-mechanism');
        const lPsd = document.getElementById('ledger-psd');

        if (lStatus) lStatus.textContent = pl.privacy_level !== 'NONE' ? `DP ENFORCED (${pl.privacy_level})` : 'UNPERTURBED';
        if (lSpent) lSpent.textContent = pl.epsilon_spent !== null ? pl.epsilon_spent.toFixed(2) : 'NONE';
        if (lNoise) lNoise.textContent = pl.noise_scale.toFixed(4);
        if (lRem) lRem.textContent = pl.epsilon_spent !== null ? (Math.max(0, 10.0 - pl.epsilon_spent)).toFixed(2) : 'UNBOUNDED';
        if (lDelta) lDelta.textContent = pl.delta.toExponential(1);
        if (lInit) lInit.textContent = pl.privacy_level !== 'NONE' ? pl.privacy_level : 'NONE';
        if (lMech) lMech.textContent = pl.mechanism;
        if (lPsd) lPsd.textContent = pl.psd_projection_applied ? 'APPLIED (Cholesky PSD)' : 'NONE';
      }
    }
  } catch (err) {
    logConsole(`Job list query failed: ${err.message}`);
  }
}

function viewJobReport(jobId) {
  StudioState.currentJobId = jobId;
  const select = document.getElementById('report-job-select');
  if (select) select.value = jobId;
  loadReportForSelected();
  switchStep(5, true);
}

// Step 5: Fidelity, Compliance & Exports
async function loadReportForSelected() {
  const select = document.getElementById('report-job-select');
  const jobId = select ? select.value : StudioState.currentJobId;
  const emptyState = document.getElementById('report-empty-state');

  if (!jobId) {
    if (emptyState) emptyState.hidden = false;
    return;
  }
  if (emptyState) emptyState.hidden = true;
  StudioState.currentJobId = jobId;

  try {
    logConsole(`Fetching fidelity and compliance report for job '${jobId}'...`);
    const resp = await fetch(`/api/v1/jobs/${jobId}/report`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const report = await resp.json();
    StudioState.currentReport = report;

    const job = StudioState.jobs.find((j) => j.job_id === jobId);

    if (window.SynthAIViews && typeof window.SynthAIViews.renderQualityReportView === 'function') {
      window.SynthAIViews.renderQualityReportView(report, job);
    } else {
      // Fallback inline rendering
      const rQual = document.getElementById('rep-quality');
      const rFid = document.getElementById('rep-fidelity');
      const rCorr = document.getElementById('rep-corr');
      const rPriv = document.getElementById('rep-privacy');
      const rVerdict = document.getElementById('rep-verdict');
      const rHipaa = document.getElementById('rep-hipaa');
      const rDcr = document.getElementById('rep-dcr');
      const rNndr = document.getElementById('rep-nndr');
      const rColl = document.getElementById('rep-collisions');
      const rLeaks = document.getElementById('rep-pii-leaks');

      if (rQual) rQual.textContent = `${(report.overall_quality_score * 100).toFixed(1)}%`;
      if (rFid) rFid.textContent = `${(report.marginal_fidelity_score * 100).toFixed(1)}%`;
      if (rCorr) rCorr.textContent = `${(report.correlation_stability_score * 100).toFixed(1)}%`;
      if (rPriv) rPriv.textContent = `${(report.privacy_score * 100).toFixed(1)}%`;
      if (rVerdict) rVerdict.textContent = report.executive_verdict;
      if (rHipaa) {
        rHipaa.textContent = report.hipaa_gdpr_ready ? 'CERTIFIED READY' : 'NOT READY';
        rHipaa.className = `badge ${report.hipaa_gdpr_ready ? 'badge-success' : 'badge-danger'}`;
      }

      const pm = report.privacy_metrics || {};
      if (rDcr) rDcr.textContent = `${pm.dcr_median !== undefined ? pm.dcr_median.toFixed(4) : '-'} (p05: ${pm.dcr_p05 !== undefined ? pm.dcr_p05.toFixed(4) : '-'})`;
      if (rNndr) rNndr.textContent = `${pm.nndr_median !== undefined ? pm.nndr_median.toFixed(4) : '-'} (p05: ${pm.nndr_p05 !== undefined ? pm.nndr_p05.toFixed(4) : '-'})`;
      if (rColl) rColl.textContent = `${pm.exact_match_collision_rate !== undefined ? (pm.exact_match_collision_rate * 100).toFixed(2) : '-'}%`;
      if (rLeaks) rLeaks.textContent = pm.pii_leakage_detected ? 'DETECTED (FAIL)' : 'NONE (0 LEAKS)';

      const fallbackBanner5 = document.getElementById('compute-fallback-banner-step5');
      if (fallbackBanner5) {
        const isFallback = job && job.config.engine === 'SPARK_LLM_EDGE' && job.compute_tier === 'CPU_WORKER';
        fallbackBanner5.hidden = !isFallback;
      }

      // Column fidelity table
      const tbody = document.querySelector('#fidelity-columns-table tbody');
      if (tbody) {
        tbody.innerHTML = '';
        (report.column_metrics || []).forEach((cm) => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <th scope="row"><code>${escapeHtml(cm.column_name)}</code></th>
            <td><span class="badge badge-info">${escapeHtml(cm.column_type)}</span></td>
            <td><code>${escapeHtml(cm.metric_name)}</code></td>
            <td data-numeric="true" class="tabular-nums">${(cm.score * 100).toFixed(1)}%</td>
            <td data-numeric="true" class="tabular-nums">${cm.statistic_distance.toFixed(4)}</td>
            <td data-numeric="true" class="tabular-nums">${cm.jensen_shannon_similarity !== null ? (cm.jensen_shannon_similarity * 100).toFixed(1) + '%' : '-'}</td>
          `;
          tbody.appendChild(tr);
        });
      }
    }
  } catch (err) {
    showGlobalError('Quality Report Fetch Failed', err.message);
  }
}

function downloadArtifact(fmt) {
  const jobId = StudioState.currentJobId || document.getElementById('report-job-select')?.value;
  if (!jobId) {
    showGlobalError('Download Error', 'No active generation job selected.');
    return;
  }

  if (fmt === 'markdown') {
    window.location.href = `/api/v1/jobs/${jobId}/report?format=markdown`;
  } else {
    window.location.href = `/api/v1/jobs/${jobId}/download?format=${fmt}`;
  }
}

// 8. Event Listeners & Global Attachments
document.addEventListener('DOMContentLoaded', () => {
  // Tablist keyboard navigation and clicks
  const tablist = document.getElementById('workflow-tablist');
  if (tablist) {
    tablist.addEventListener('keydown', handleTabKeydown);
    tablist.addEventListener('click', (e) => {
      const tab = e.target.closest('[role="tab"]');
      if (tab) {
        const step = tab.getAttribute('data-step');
        if (step) switchStep(step, false);
      }
    });
  }

  // Global error banner dismissal
  const dismissBtn = document.getElementById('global-error-dismiss');
  if (dismissBtn) {
    dismissBtn.addEventListener('click', dismissGlobalError);
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') dismissGlobalError();
  });

  // Step 1: Upload Form & Presign
  const uploadForm = document.getElementById('upload-form');
  if (uploadForm) {
    uploadForm.addEventListener('submit', handleUpload);
  }
  const btnPresign = document.getElementById('btn-generate-ticket');
  if (btnPresign) {
    btnPresign.addEventListener('click', generateTicket);
  }

  // Step 2: Dataset Select & Cleanse
  const dsSelect = document.getElementById('profile-dataset-select');
  if (dsSelect) {
    dsSelect.addEventListener('change', loadProfileForSelected);
  }
  const btnCleanse = document.getElementById('btn-cleanse-dataset');
  if (btnCleanse) {
    btnCleanse.addEventListener('click', cleanseCurrentDataset);
  }

  // Step 3: Synthesis Form & Parameter Sync
  const synthForm = document.getElementById('synth-config-form');
  if (synthForm) {
    synthForm.addEventListener('submit', handleGenerate);
  }
  const genDsSelect = document.getElementById('gen-dataset-id');
  if (genDsSelect) {
    genDsSelect.addEventListener('change', () => {
      const selectedId = genDsSelect.value;
      const ds = StudioState.datasets.find((d) => d.dataset_id === selectedId);
      if (ds && ds.benchmark_id) {
        const bm = StudioState.benchmarks.find((b) => b.benchmark_id === ds.benchmark_id);
        if (bm) {
          const targetCol = document.getElementById('gen-target-col');
          const minorityVal = document.getElementById('gen-minority-val');
          if (targetCol && bm.target_column) targetCol.value = bm.target_column;
          if (minorityVal && bm.minority_label !== null && bm.minority_label !== undefined) {
            minorityVal.value = String(bm.minority_label);
          }
        }
      }
    });
  }
  const privLevel = document.getElementById('gen-privacy-level');
  if (privLevel) {
    privLevel.addEventListener('change', updateDpDefaults);
  }
  const engineSelect = document.getElementById('gen-engine');
  if (engineSelect) {
    engineSelect.addEventListener('change', updateDpDefaults);
  }

  // Step 4: Refresh Jobs
  const btnRefresh = document.getElementById('btn-refresh-jobs');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', loadJobs);
  }

  // Step 5: Report Select & Downloads
  const repSelect = document.getElementById('report-job-select');
  if (repSelect) {
    repSelect.addEventListener('change', loadReportForSelected);
  }
  const btnDlCsv = document.getElementById('btn-dl-csv');
  if (btnDlCsv) btnDlCsv.addEventListener('click', () => downloadArtifact('csv'));
  const btnDlJson = document.getElementById('btn-dl-json');
  if (btnDlJson) btnDlJson.addEventListener('click', () => downloadArtifact('json'));
  const btnDlParquet = document.getElementById('btn-dl-parquet');
  if (btnDlParquet) btnDlParquet.addEventListener('click', () => downloadArtifact('parquet'));
  const btnDlMd = document.getElementById('btn-dl-markdown');
  if (btnDlMd) btnDlMd.addEventListener('click', () => downloadArtifact('markdown'));

  // Empty-state 1-click recovery CTAs
  const btnEmptySeed = document.getElementById('btn-empty-seed-hipaa');
  if (btnEmptySeed) {
    btnEmptySeed.addEventListener('click', () => seedBenchmark('healthcare_hipaa_readmissions'));
  }
  const btnEmptyStep1 = document.getElementById('btn-empty-goto-step1');
  if (btnEmptyStep1) {
    btnEmptyStep1.addEventListener('click', () => switchStep(1, true));
  }
  const btnEmptyStep3 = document.getElementById('btn-empty-goto-step3');
  if (btnEmptyStep3) {
    btnEmptyStep3.addEventListener('click', () => switchStep(3, true));
  }

  loadInitData();
});

// Window Exports for global accessibility and event handlers
window.StudioState = StudioState;
window.escapeHtml = escapeHtml;
window.announcePolite = announcePolite;
window.announceAssertive = announceAssertive;
window.showGlobalError = showGlobalError;
window.dismissGlobalError = dismissGlobalError;
window.switchStep = switchStep;
window.handleTabKeydown = handleTabKeydown;
window.logConsole = logConsole;
window.loadInitData = loadInitData;
window.loadBenchmarks = loadBenchmarks;
window.seedBenchmark = seedBenchmark;
window.handleUpload = handleUpload;
window.generateTicket = generateTicket;
window.loadDatasets = loadDatasets;
window.loadProfileForSelected = loadProfileForSelected;
window.cleanseCurrentDataset = cleanseCurrentDataset;
window.updateDpDefaults = updateDpDefaults;
window.handleGenerate = handleGenerate;
window.loadJobs = loadJobs;
window.viewJobReport = viewJobReport;
window.loadReportForSelected = loadReportForSelected;
window.downloadArtifact = downloadArtifact;
