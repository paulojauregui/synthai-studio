/**
 * SynthAI Studio -- 5-State Renderers, Tabular Metrics & Circuit Breaker Fallback Views
 * Contract: docs/UX_SPEC.md Section 4 & 5 / docs/specs/M10_SPEC.md
 * Zero emojis, pure ASCII encoding.
 */

// 1. HTML Sanitization Helper (XSS Protection)
function escapeHtml(val) {
  if (val === null || val === undefined) return '';
  return String(val)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// 2. State 1: Empty State Renderer (.state-empty)
function renderEmptyState(container, title, message, ctaLabel = null, ctaAction = null) {
  if (!container) return;
  container.removeAttribute('aria-busy');
  container.classList.remove('state-loading', 'state-error', 'state-nominal');
  container.classList.add('state-empty');

  const ctaBtn = ctaLabel
    ? `<button type="button" class="btn btn-secondary empty-cta-btn" style="margin-top: 12px;">${escapeHtml(ctaLabel)}</button>`
    : '';

  container.innerHTML = `
    <div class="empty-state-content">
      <div style="font-weight: 700; margin-bottom: 6px;">${escapeHtml(title)}</div>
      <p style="color: var(--text-muted); font-size: 13px;">${escapeHtml(message)}</p>
      ${ctaBtn}
    </div>
  `;

  if (ctaLabel && ctaAction) {
    const btn = container.querySelector('.empty-cta-btn');
    if (btn) {
      if (typeof ctaAction === 'function') {
        btn.addEventListener('click', ctaAction);
      } else {
        btn.setAttribute('onclick', ctaAction);
      }
    }
  }
}

// 3. State 2: Zero-CLS Loading Skeleton Placeholder (.state-loading)
function renderLoadingSkeleton(container, variant = 'card', count = 3) {
  if (!container) return;
  container.setAttribute('aria-busy', 'true');
  container.classList.remove('state-empty', 'state-error', 'state-nominal');
  container.classList.add('state-loading');

  let skeletonClass = 'skeleton-card';
  if (variant === 'tile') skeletonClass = 'skeleton-tile';
  else if (variant === 'row') skeletonClass = 'skeleton-row';

  let html = '';
  for (let i = 0; i < count; i++) {
    html += `<div class="skeleton ${skeletonClass}" aria-hidden="true"></div>`;
  }
  container.innerHTML = html;
}

// 4. State 5: Error State Renderer (.state-error)
function renderErrorState(container, title, detail, retryLabel = 'Retry', retryAction = null) {
  if (!container) return;
  container.removeAttribute('aria-busy');
  container.classList.remove('state-loading', 'state-empty', 'state-nominal');
  container.classList.add('state-error');

  const retryBtn = retryLabel
    ? `<button type="button" class="btn btn-secondary error-retry-btn" style="margin-top: 10px;">${escapeHtml(retryLabel)}</button>`
    : '';

  container.innerHTML = `
    <div class="error-state-content">
      <div style="font-weight: 700; color: var(--status-danger-fg); margin-bottom: 4px;">${escapeHtml(title)}</div>
      <p style="color: var(--text-primary); font-size: 13px;">${escapeHtml(detail)}</p>
      ${retryBtn}
    </div>
  `;

  if (retryLabel && retryAction) {
    const btn = container.querySelector('.error-retry-btn');
    if (btn) {
      if (typeof retryAction === 'function') {
        btn.addEventListener('click', retryAction);
      } else {
        btn.setAttribute('onclick', retryAction);
      }
    }
  }
}

// 5. Step 1: Benchmark Cards Renderer
function renderBenchmarkCards(container, benchmarks, onSeedClick = null) {
  if (!container) return;
  container.removeAttribute('aria-busy');
  container.classList.remove('state-loading');

  if (!benchmarks || benchmarks.length === 0) {
    renderEmptyState(
      container,
      'No Benchmarks Available',
      'Unable to discover built-in reference datasets.',
      'Retry Discovery',
      () => window.loadBenchmarks && window.loadBenchmarks()
    );
    return;
  }

  container.innerHTML = '';
  benchmarks.forEach((b) => {
    const card = document.createElement('div');
    card.className = 'benchmark-card';
    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <strong style="color: var(--text-primary); font-size: 14px;">${escapeHtml(b.name)}</strong>
        <span class="badge badge-info">${escapeHtml(b.domain)}</span>
      </div>
      <p style="color: var(--text-muted); font-size: 12px; margin: 4px 0;">${escapeHtml(b.description)}</p>
      <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">
        Default Rows: <span class="tabular-nums">${b.default_row_count}</span> |
        Target: <code>${escapeHtml(b.target_column || 'None')}</code>
        (${escapeHtml(String(b.minority_label || '-'))})
      </div>
      <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px;">
        ${(b.pii_columns || []).map((col) => `<span class="badge badge-danger">PII: ${escapeHtml(col)}</span>`).join('')}
        ${(b.highlights || []).map((h) => `<span class="badge badge-info">${escapeHtml(h)}</span>`).join('')}
      </div>
      <button type="button" class="btn btn-secondary seed-btn" data-benchmark-id="${escapeHtml(b.benchmark_id)}">
        Seed Benchmark Dataset
      </button>
    `;

    const seedBtn = card.querySelector('.seed-btn');
    if (seedBtn) {
      seedBtn.addEventListener('click', () => {
        if (typeof onSeedClick === 'function') {
          onSeedClick(b.benchmark_id);
        } else if (window.seedBenchmark) {
          window.seedBenchmark(b.benchmark_id);
        }
      });
    }

    container.appendChild(card);
  });
}

// 6. Step 2: Quality & PII Profile View Renderer
function renderProfileView(prof) {
  const emptyState = document.getElementById('profile-empty-state');
  if (!prof) {
    if (emptyState) emptyState.hidden = false;
    return;
  }
  if (emptyState) emptyState.hidden = true;

  // 1. KPI Summary Tiles
  const profRows = document.getElementById('prof-rows');
  const profCols = document.getElementById('prof-cols');
  const profQuality = document.getElementById('prof-quality');
  const profPrivacy = document.getElementById('prof-privacy-risk');

  if (profRows) profRows.textContent = String(prof.row_count);
  if (profCols) profCols.textContent = String(prof.column_count);
  if (profQuality) profQuality.textContent = `${(prof.data_quality_score * 100).toFixed(1)}%`;
  if (profPrivacy) {
    profPrivacy.textContent = `${(prof.privacy_risk_score * 100).toFixed(1)}%`;
    profPrivacy.style.color =
      prof.privacy_risk_score === 0 ? 'var(--status-nominal-fg)' : 'var(--status-danger-fg)';
  }

  // 2. Column Profiles & PII Findings Table
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

  // 3. Quality Issues List
  const issuesContainer = document.getElementById('profile-issues-list');
  if (issuesContainer) {
    issuesContainer.innerHTML = '';
    if ((prof.quality_issues || []).length === 0) {
      issuesContainer.innerHTML =
        '<div class="state-nominal">Zero open data quality or unmasked PII defects detected.</div>';
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

  // 4. Pearson Correlation Heatmap Table
  const corrWrapper = document.getElementById('profile-corr-wrapper');
  const corrThead = document.querySelector('#profile-corr-table thead');
  const corrTbody = document.querySelector('#profile-corr-table tbody');

  if (corrThead && corrTbody) {
    corrThead.innerHTML = '';
    corrTbody.innerHTML = '';

    if (!prof.correlation_columns || prof.correlation_columns.length === 0) {
      if (corrWrapper) {
        corrTbody.innerHTML =
          '<tr><td colspan="10" class="state-degraded degraded-banner">Notice: Dataset contains zero numerical columns. Pearson rank correlation requires at least 1 numerical column.</td></tr>';
      }
    } else {
      // Header row with column labels
      const headerTr = document.createElement('tr');
      headerTr.innerHTML = '<th scope="col">Feature</th>' +
        prof.correlation_columns.map((col) => `<th scope="col" data-numeric="true">${escapeHtml(col)}</th>`).join('');
      corrThead.appendChild(headerTr);

      // Data rows
      prof.correlation_columns.forEach((rowName, i) => {
        const tr = document.createElement('tr');
        let cellsHtml = `<th scope="row"><code>${escapeHtml(rowName)}</code></th>`;
        prof.correlation_columns.forEach((_, j) => {
          const val = prof.correlation_matrix && prof.correlation_matrix[i] ? prof.correlation_matrix[i][j] : null;
          cellsHtml += `<td data-numeric="true" class="corr-cell tabular-nums">${val !== null && val !== undefined ? val.toFixed(2) : '-'}</td>`;
        });
        tr.innerHTML = cellsHtml;
        corrTbody.appendChild(tr);
      });
    }
  }
}

// 7. Compute Fallback Banner Controller (SPARK_LLM_EDGE -> CPU_WORKER local_copula)
function updateComputeFallbackBanner(job = null, report = null) {
  const isFallback =
    (job && job.config && job.config.engine === 'SPARK_LLM_EDGE' && job.compute_tier === 'CPU_WORKER') ||
    (report && report.engine === 'SPARK_LLM_EDGE' && (job?.compute_tier === 'CPU_WORKER' || !report.hipaa_gdpr_ready));

  const banner4 = document.getElementById('compute-fallback-banner');
  if (banner4) {
    banner4.hidden = !isFallback;
    if (isFallback) {
      banner4.className = 'degraded-banner state-degraded';
      banner4.innerHTML =
        '<span>Notice: DGX Spark edge endpoint unavailable under &lt; 2.0s circuit breaker. Execution cleanly fell back to local CPU Copula synthesis without data loss.</span>';
    }
  }

  const banner5 = document.getElementById('compute-fallback-banner-step5');
  if (banner5) {
    banner5.hidden = !isFallback;
    if (isFallback) {
      banner5.className = 'degraded-banner state-degraded';
      banner5.innerHTML =
        '<span>Notice: Audited synthetic dataset was generated under local CPU Copula fallback due to DGX Spark edge endpoint circuit breaker trip.</span>';
    }
  }
}

// 8. Step 4: Jobs Ledger Table & Privacy Budget Ledger
function renderJobsAndLedger(jobs, selectedJobId = null, onAuditClick = null) {
  const tbody = document.querySelector('#jobs-table tbody');
  if (!tbody) return;

  tbody.innerHTML = '';
  if (!jobs || jobs.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="state-empty">
          <div>No synthetic generation jobs executed yet.</div>
          <button type="button" class="btn btn-secondary empty-jobs-cta" style="margin-top: 8px;">
            Configure &amp; Launch Job in Step 3
          </button>
        </td>
      </tr>
    `;
    const emptyJobsBtn = tbody.querySelector('.empty-jobs-cta');
    if (emptyJobsBtn) {
      emptyJobsBtn.addEventListener('click', () => {
        if (window.switchStep) window.switchStep(3, true);
      });
    }
  } else {
    jobs.forEach((j) => {
      const isFallback = j.compute_tier === 'CPU_WORKER' && j.config && j.config.engine === 'SPARK_LLM_EDGE';
      const tierBadge = isFallback
        ? '<span class="badge badge-warn">CPU_WORKER (FALLBACK)</span>'
        : `<span class="badge badge-info">${escapeHtml(j.compute_tier)}</span>`;
      const statusBadge =
        j.status === 'COMPLETED'
          ? '<span class="badge badge-success">COMPLETED</span>'
          : `<span class="badge badge-danger">${escapeHtml(j.status)}</span>`;

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <th scope="row"><code>${escapeHtml(j.job_id)}</code></th>
        <td>${escapeHtml(j.dataset_name)}</td>
        <td><code>${escapeHtml(j.config ? j.config.engine : '-')}</code></td>
        <td>${tierBadge}</td>
        <td>${statusBadge}</td>
        <td data-numeric="true" class="tabular-nums">${j.rows_generated} (${j.throughput_rows_per_sec.toFixed(0)} r/s)</td>
        <td><button type="button" class="btn btn-secondary audit-btn" data-job-id="${escapeHtml(j.job_id)}">Audit Report</button></td>
      `;

      const btn = tr.querySelector('.audit-btn');
      if (btn) {
        btn.addEventListener('click', () => {
          if (typeof onAuditClick === 'function') {
            onAuditClick(j.job_id);
          } else if (window.viewJobReport) {
            window.viewJobReport(j.job_id);
          }
        });
      }

      tbody.appendChild(tr);
    });
  }

  // Update fallback banner for active job
  const activeJob = (jobs || []).find((j) => j.job_id === selectedJobId) || (jobs && jobs[0]) || null;
  updateComputeFallbackBanner(activeJob, null);

  // Update Privacy Budget Ledger
  if (activeJob && activeJob.privacy_ledger) {
    const pl = activeJob.privacy_ledger;
    const lStatus = document.getElementById('ledger-status');
    const lSpent = document.getElementById('ledger-spent');
    const lNoise = document.getElementById('ledger-noise-scale');
    const lRem = document.getElementById('ledger-remaining');
    const lDelta = document.getElementById('ledger-delta');
    const lInit = document.getElementById('ledger-initial');
    const lMech = document.getElementById('ledger-mechanism');
    const lPsd = document.getElementById('ledger-psd');

    if (lStatus) {
      lStatus.textContent = pl.privacy_level !== 'NONE' ? `DP ENFORCED (${pl.privacy_level})` : 'UNPERTURBED';
      lStatus.className = `badge ${pl.privacy_level !== 'NONE' ? 'badge-success' : 'badge-warn'}`;
    }
    if (lSpent) lSpent.textContent = pl.epsilon_spent !== null ? pl.epsilon_spent.toFixed(2) : 'NONE';
    if (lNoise) lNoise.textContent = pl.noise_scale.toFixed(4);
    if (lRem) lRem.textContent = pl.epsilon_spent !== null ? (Math.max(0, 10.0 - pl.epsilon_spent)).toFixed(2) : 'UNBOUNDED';
    if (lDelta) lDelta.textContent = pl.delta.toExponential(1);
    if (lInit) lInit.textContent = pl.privacy_level !== 'NONE' ? pl.privacy_level : 'NONE';
    if (lMech) lMech.textContent = pl.mechanism;
    if (lPsd) lPsd.textContent = pl.psd_projection_applied ? 'APPLIED (Cholesky PSD)' : 'NONE';
  }
}

// 9. Step 5: Statistical Quality & Compliance Report View
function renderQualityReportView(report, job = null) {
  const emptyState = document.getElementById('report-empty-state');
  if (!report) {
    if (emptyState) emptyState.hidden = false;
    return;
  }
  if (emptyState) emptyState.hidden = true;

  // 1. KPI Top Tiles
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

  // Update Step 5 fallback banner
  updateComputeFallbackBanner(job, report);

  // Column fidelity breakdown table
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

// Window Global Export
window.SynthAIViews = {
  escapeHtml,
  renderEmptyState,
  renderLoadingSkeleton,
  renderErrorState,
  renderBenchmarkCards,
  renderProfileView,
  updateComputeFallbackBanner,
  renderJobsAndLedger,
  renderQualityReportView,
};
