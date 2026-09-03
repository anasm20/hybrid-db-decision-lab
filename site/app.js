const REFRESH_MS = 5000;

async function loadJSON(path, fallback) {
  try {
    const r = await fetch(path, { cache: 'no-store' });
    if (!r.ok) throw new Error();
    return await r.json();
  } catch (e) { return null; }
}
function fmt(v, d = 1) { return v === null || v === undefined ? '—' : Number(v).toFixed(d); }
function setGate(id, state) {
  const el = document.querySelector(id);
  if (!el) return;
  el.textContent = state;
  el.className = 'kpi-gate ' + (state === 'PASS' ? 'gate-pass' : state === 'FAIL' ? 'gate-fail' : 'gate-nodata');
}
function setLiveStatus(ok) {
  const el = document.querySelector('#live-status');
  if (!el) return;
  const now = new Date().toLocaleTimeString('de-AT');
  if (ok) { el.classList.remove('stale'); el.textContent = `live · ${now}`; }
  else { el.classList.add('stale'); el.textContent = `verbindung verloren · zuletzt ${now}`; }
}

async function refresh() {
  const summaryFallback = { run_count: 0, rpo: {}, rto_seconds: {}, error_rate: {}, latency_ms: {}, replication_lag_seconds: {}, throughput_rps: {}, runs: [] };
  const [summaryLoaded, decisionLoaded, costLoaded] = await Promise.all([
    loadJSON('data/summary.json', summaryFallback),
    loadJSON('data/decision.json', { mandatory_gates: {} }),
    loadJSON('data/cost.json', { monthly: {} }),
  ]);
  setLiveStatus(summaryLoaded !== null);
  const summary = summaryLoaded || summaryFallback;
  const decision = decisionLoaded || { mandatory_gates: {} };
  const cost = costLoaded || { monthly: {} };
  const gates = decision.mandatory_gates || {};
  const hasRuns = (summary.run_count || 0) > 0;

  document.querySelectorAll('#run-count').forEach(el => el.textContent = `${summary.run_count || 0} runs`);

  // 1. RPO
  const rpo = summary.rpo || {};
  const lossMedian = rpo.acknowledged_write_loss_probes?.median;
  const lossMax = rpo.acknowledged_write_loss_probes?.max;
  document.querySelector('#rpo-value').textContent = hasRuns ? `${fmt(lossMedian, 0)} Writes` : '—';
  document.querySelector('#rpo-detail').textContent = hasRuns
    ? `Median verloren · max ${fmt(lossMax, 0)} · ≈ ${fmt(rpo.estimated_seconds?.median, 2)}s geschätzt`
    : 'bestätigte Schreibvorgänge verloren';
  setGate('#rpo-gate', !hasRuns ? 'NO DATA' : (lossMax <= (gates.acknowledged_write_loss_max ?? 0) ? 'PASS' : 'FAIL'));

  // 2. RTO
  const rto = summary.rto_seconds || {};
  const ci = rto.bootstrap_95_ci_median || [];
  document.querySelector('#rto-value').textContent = hasRuns ? `${fmt(rto.median, 2)} s` : '—';
  document.querySelector('#rto-detail').textContent = hasRuns
    ? `Median, 95%-Bootstrap-CI: ${ci[0] == null ? '—' : `${fmt(ci[0], 1)}–${fmt(ci[1], 1)}s`}`
    : 'Median, 95%-Bootstrap-CI: —';
  setGate('#rto-gate', !hasRuns ? 'NO DATA' : (rto.max <= (gates.rto_seconds_max ?? Infinity) ? 'PASS' : 'FAIL'));

  // 3. Error rate
  const err = summary.error_rate || {};
  document.querySelector('#error-value').textContent = hasRuns && err.median != null ? `${fmt(err.median * 100, 2)}%` : '—';
  document.querySelector('#error-detail').textContent = hasRuns && err.max != null
    ? `Median über Runs · max ${fmt(err.max * 100, 2)}%`
    : 'fehlgeschlagene Requests während Workload';
  setGate('#error-gate', !hasRuns || err.max == null ? 'NO DATA' : (err.max < 0.05 ? 'PASS' : 'FAIL'));

  // 4. Latency
  const lat = summary.latency_ms || {};
  const p95 = lat.p95 || {}, p99 = lat.p99 || {};
  document.querySelector('#latency-value').textContent = hasRuns && p95.median != null
    ? `${fmt(p95.median, 0)} / ${fmt(p99.median, 0)} ms`
    : '—';
  document.querySelector('#latency-detail').textContent = hasRuns && p95.median != null
    ? `p95 max ${fmt(p95.max, 0)} ms · p99 max ${fmt(p99.max, 0)} ms`
    : 'Millisekunden, Median über alle Runs';
  setGate('#latency-gate', !hasRuns || p95.max == null ? 'NO DATA' : (p95.max < 500 ? 'PASS' : 'FAIL'));

  // 5. Replication lag
  const lag = summary.replication_lag_seconds || {};
  document.querySelector('#lag-value').textContent = hasRuns && lag.max != null ? `${fmt(lag.max, 2)} s` : '—';
  document.querySelector('#lag-detail').textContent = hasRuns && lag.max != null
    ? `Median ${fmt(lag.median, 2)}s · max ${fmt(lag.max, 2)}s`
    : 'max. beobachtete Sekunden während Runs';
  setGate('#lag-gate', !hasRuns || lag.max == null ? 'NO DATA' : (lag.max < 5 ? 'PASS' : 'FAIL'));

  // 6. Throughput + cost
  const tput = summary.throughput_rps || {};
  document.querySelector('#throughput-value').textContent = hasRuns && tput.median != null ? `${fmt(tput.median, 1)} req/s` : '—';

  const labels = { onprem: 'On-Prem', cloud: 'Cloud', hybrid: 'Hybrid' };
  const costEntries = Object.entries(cost.monthly || {});
  document.querySelector('#cost-mini').innerHTML = costEntries.length
    ? costEntries.map(([k, v]) => `<div><span>${labels[k] || k}</span><b>€ ${Number(v).toLocaleString('de-AT', { maximumFractionDigits: 0 })}</b></div>`).join('')
    : '<div class="muted">Run analysis/cost_model.py</div>';
  document.querySelector('#cost-cards').innerHTML = costEntries.length
    ? costEntries.map(([k, v]) => `<div class="kpi"><small>${labels[k] || k}</small><strong>€ ${Number(v).toLocaleString('de-AT', { maximumFractionDigits: 0 })}</strong><span>/ Monat · MODELLED</span></div>`).join('')
    : '<p class="muted">Run analysis/cost_model.py</p>';

  // RTO by run chart
  const runs = (summary.runs || []).filter(x => x.rto_seconds != null);
  const maxRto = Math.max(1, ...runs.map(x => x.rto_seconds));
  document.querySelector('#chart').innerHTML = runs.length
    ? runs.map((r, i) => `<div class="bar-wrap" title="${r.experiment_id}: ${fmt(r.rto_seconds, 2)}s"><div class="bar" style="height:${Math.max(4, r.rto_seconds / maxRto * 180)}px"></div><span class="bar-label">${i + 1}</span></div>`).join('')
    : '<p class="muted">Noch keine MEASURED Runs. Führe scripts/run_failover.py aus und starte die Analyse.</p>';

  // Recent runs table — every test result, newest first.
  const tbody = document.querySelector('#runs-table-body');
  const allRuns = [...(summary.runs || [])].sort((a, b) => new Date(b.finished_at || 0) - new Date(a.finished_at || 0));
  tbody.innerHTML = allRuns.length
    ? allRuns.slice(0, 20).map(r => {
      const w = r.workload || {};
      const prov = r.provenance === 'MEASURED' ? 'prov-measured' : 'prov-simulated';
      const when = r.finished_at ? new Date(r.finished_at).toLocaleString('de-AT') : '—';
      return `<tr>
        <td>${r.experiment_id}</td>
        <td><span class="prov-tag ${prov}">${r.provenance || '—'}</span></td>
        <td>${fmt(r.rto_seconds, 2)} s</td>
        <td>${r.acknowledged_write_loss ?? '—'}</td>
        <td>${fmt(w.p95_ms, 0)} / ${fmt(w.p99_ms, 0)} ms</td>
        <td>${w.error_rate != null ? fmt(w.error_rate * 100, 2) + '%' : '—'}</td>
        <td>${when}</td>
      </tr>`;
    }).join('')
    : '<tr><td colspan="7" class="muted">Noch keine Runs.</td></tr>';
}

refresh();
setInterval(refresh, REFRESH_MS);
document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });

// --- Detect whether the local dashboard backend (upload/API/simulate) is reachable.
// On a static host like GitHub Pages this endpoint doesn't exist, so those
// features stay hidden and the static-data banner stays visible instead. ---
async function detectLocalApi() {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 1500);
    const r = await fetch('/api/status', { cache: 'no-store', signal: ctrl.signal });
    clearTimeout(t);
    if (!r.ok) throw new Error();
    document.querySelectorAll('.local-only').forEach(el => { el.hidden = false; });
    const banner = document.querySelector('#static-banner');
    if (banner) banner.hidden = true;
  } catch (e) {
    // stays static: banner visible, local-only sections hidden (default state)
  }
}
detectLocalApi();

// --- Live run panel: while scripts/run_failover.py is executing, its events are
// pushed to /api/events in real time. Poll frequently and show them as a timeline. ---
const EVENT_LABELS = {
  experiment_started: 'Test gestartet',
  failure_injected: 'Primary getötet',
  new_primary_detected: 'Neuer Primary erkannt',
  service_write_recovered: 'Schreibzugriff wiederhergestellt',
  recovery_timeout: 'Timeout — keine Wiederherstellung',
  experiment_completed: 'Test abgeschlossen',
};
let liveRunId = null;
let liveRunSinceEpoch = 0;
let liveRunStartedEpoch = null;
let liveRunHideTimer = null;

function renderLiveEvent(row) {
  const label = EVENT_LABELS[row.event] || row.event;
  const el = document.createElement('div');
  el.className = 'ev';
  el.innerHTML = `<b>${new Date(row.epoch * 1000).toLocaleTimeString('de-AT')}</b><span>${label}</span>`;
  document.querySelector('#live-run-timeline').appendChild(el);
  document.querySelector('#live-run-timeline').scrollLeft = 1e9;
}

async function pollLiveEvents() {
  try {
    const url = liveRunId ? `/api/events?run_id=${encodeURIComponent(liveRunId)}&since_epoch=${liveRunSinceEpoch}` : '/api/events';
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) throw new Error();
    const data = await r.json();
    const panel = document.querySelector('#live-run-panel');

    if (!liveRunId && data.active_run_ids && data.active_run_ids.length) {
      liveRunId = data.active_run_ids[0];
      liveRunSinceEpoch = 0;
      liveRunStartedEpoch = null;
      document.querySelector('#live-run-timeline').innerHTML = '';
      document.querySelector('#live-run-id').textContent = liveRunId;
      panel.hidden = false;
      if (liveRunHideTimer) { clearTimeout(liveRunHideTimer); liveRunHideTimer = null; }
      return pollLiveEvents();
    }

    if (liveRunId) {
      (data.events || []).forEach(row => {
        if (row.run_id !== liveRunId) return;
        if (liveRunStartedEpoch == null) liveRunStartedEpoch = row.epoch;
        renderLiveEvent(row);
        liveRunSinceEpoch = Math.max(liveRunSinceEpoch, row.epoch);
        if (row.event === 'experiment_completed' || row.event === 'recovery_timeout') {
          refresh();
          liveRunHideTimer = setTimeout(() => { panel.hidden = true; liveRunId = null; }, 6000);
        }
      });
      if (liveRunStartedEpoch != null) {
        document.querySelector('#live-run-elapsed').textContent = `${Math.max(0, Math.round(Date.now() / 1000 - liveRunStartedEpoch))}s seit Start`;
      }
    }
  } catch (e) {
    // dashboard-api not reachable (e.g. static hosting) — live panel simply stays hidden
  }
}
pollLiveEvents();
setInterval(pollLiveEvents, 2000);

// --- Upload real evidence ---
const tokenInput = document.querySelector('#api-token');
const fileInput = document.querySelector('#upload-file');
const uploadBtn = document.querySelector('#upload-btn');
const uploadStatus = document.querySelector('#upload-status');

if (tokenInput) {
  try { tokenInput.value = localStorage.getItem('dashboard_api_token') || ''; } catch (e) {}
  tokenInput.addEventListener('change', () => {
    try { localStorage.setItem('dashboard_api_token', tokenInput.value); } catch (e) {}
  });
}

if (uploadBtn) {
  uploadBtn.addEventListener('click', async () => {
    const token = tokenInput.value.trim();
    const file = fileInput.files[0];
    if (!token) { uploadStatus.textContent = 'Bitte API-Token eingeben.'; return; }
    if (!file) { uploadStatus.textContent = 'Bitte eine JSON-Datei auswählen.'; return; }
    uploadBtn.disabled = true;
    uploadStatus.textContent = 'Lade hoch…';
    try {
      const body = new FormData();
      body.append('file', file);
      const r = await fetch('/api/upload', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      uploadStatus.textContent = `Übernommen: ${data.experiment_id}`;
      fileInput.value = '';
      refresh();
    } catch (e) {
      uploadStatus.textContent = `Fehler: ${e.message}`;
    } finally {
      uploadBtn.disabled = false;
    }
  });
}

// --- Clearly labelled demo simulation (never stored as MEASURED evidence) ---
const simulateBtn = document.querySelector('#simulate-btn');
const simulateStatus = document.querySelector('#simulate-status');
const simulationResult = document.querySelector('#simulation-result');

if (simulateBtn) {
  simulateBtn.addEventListener('click', async () => {
    const token = tokenInput.value.trim();
    if (!token) {
      simulateStatus.textContent = 'Bitte oben zuerst den API-Token eingeben.';
      return;
    }
    simulateBtn.disabled = true;
    simulationResult.hidden = true;
    simulateStatus.textContent = 'Ausfall wird simuliert…';
    try {
      const r = await fetch('/api/simulate', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
      const workload = data.workload || {};
      simulationResult.innerHTML = `
        <div><small>Provenienz</small><strong>${data.provenance}</strong></div>
        <div><small>RTO</small><strong>${fmt(data.rto_seconds, 1)} s</strong></div>
        <div><small>Verlorene Writes</small><strong>${data.acknowledged_write_loss}</strong></div>
        <div><small>Replication Lag</small><strong>${fmt(data.replication_lag_seconds_max, 1)} s</strong></div>
        <div><small>p95</small><strong>${fmt(workload.p95_ms, 0)} ms</strong></div>
        <div><small>Fehlerrate</small><strong>${fmt(workload.error_rate * 100, 1)}%</strong></div>`;
      simulationResult.hidden = false;
      simulateStatus.textContent = `Simulation abgeschlossen: ${data.experiment_id}`;
    } catch (e) {
      simulateStatus.textContent = `Fehler: ${e.message}`;
    } finally {
      simulateBtn.disabled = false;
    }
  });
}
