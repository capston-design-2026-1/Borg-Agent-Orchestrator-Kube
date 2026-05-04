const $ = (id) => document.getElementById(id);
const colors = { total: '#14211b', AgentA: '#b44634', AgentB: '#16835f', AgentC: '#2f6f9f', optuna: '#d48a20' };
async function getJSON(path) { const res = await fetch(path, { cache: 'no-store' }); return res.json(); }
let reloadingForVersion = false;
async function reloadIfDashboardChanged() {
  if (reloadingForVersion) return;
  const payload = await getJSON('/api/dashboard-version');
  if (payload.version && window.DASHBOARD_VERSION && payload.version !== window.DASHBOARD_VERSION) {
    reloadingForVersion = true;
    window.location.reload();
  }
}
function fmt(x) { return x === null || x === undefined || Number.isNaN(Number(x)) ? 'n/a' : Number(x).toFixed(3); }
function drawSeries(canvas, rows, series) {
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.strokeStyle = 'rgba(20,33,27,.12)'; ctx.lineWidth = 1;
  for (let i = 1; i < 5; i++) { const y = (h / 5) * i; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
  if (!rows.length) return;
  const values = rows.flatMap(row => series.map(s => s.value(row))).filter(Number.isFinite);
  const min = Math.min(...values, 0), max = Math.max(...values, 1);
  const span = max - min || 1;
  series.forEach(s => {
    ctx.strokeStyle = s.color; ctx.lineWidth = 3; ctx.beginPath();
    rows.forEach((row, i) => {
      const x = rows.length === 1 ? 0 : (i / (rows.length - 1)) * (w - 24) + 12;
      const y = h - 18 - ((s.value(row) - min) / span) * (h - 36);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  });
}
function renderState(state, events) {
  $('statusText').textContent = state.status || 'waiting';
  $('updatedAt').textContent = `updated ${state.updated_at || 'never'}`;
  $('activeStage').textContent = state.active_stage || 'boot';
  $('archPath').textContent = state.architecture_path || '';
  $('statusDot').className = `dot ${state.status === 'complete' ? 'complete' : state.status === 'failed' ? 'failed' : ''}`;
  const rewards = state.rewards || [];
  const last = rewards[rewards.length - 1];
  const rewardSummary = state.reward_summary || {};
  $('lastReward').textContent = fmt(last?.total);
  $('rewardSteps').textContent = rewardSummary.count ?? rewards.length;
  $('optunaBest').textContent = state.optuna?.status === 'disabled' ? 'disabled' : fmt(state.optuna?.best_score);
  $('rayStatus').textContent = state.ray?.status || 'idle';
  $('maxRisk').textContent = fmt(state.cluster?.max_risk);
  $('repeatCount').textContent = state.decision?.repeat_count ?? 0;
  $('decisionTime').textContent = state.decision?.time || 'waiting';
  $('decisionAction').textContent = state.decision?.agent ? `${state.decision.agent}:${state.decision.kind}` : 'n/a';
  $('decisionTarget').textContent = state.decision?.target || 'n/a';
  $('decisionReason').textContent = state.decision?.reason || 'n/a';

  $('stages').innerHTML = (state.stages || []).map(s => `<article class="stage ${s.status}" style="--progress:${s.progress ?? (s.status === 'complete' ? 1 : .08)}"><h3>${s.name}</h3><p>${s.status}</p><p>${s.detail || ''}</p></article>`).join('');
  drawSeries($('rewardCanvas'), rewards, [
    { color: colors.total, value: r => r.total },
    { color: colors.AgentA, value: r => r.rewards?.AgentA },
    { color: colors.AgentB, value: r => r.rewards?.AgentB },
    { color: colors.AgentC, value: r => r.rewards?.AgentC },
  ]);
  const byAgent = rewardSummary.last_by_agent || {};
  $('rewardStats').innerHTML = [
    ['count', rewardSummary.count],
    ['avg total', fmt(rewardSummary.average_total)],
    ['AgentA', fmt(byAgent.AgentA)],
    ['AgentB', fmt(byAgent.AgentB)],
    ['AgentC', fmt(byAgent.AgentC)],
  ].map(([k, v]) => `<div><b>${k}</b><br>${v ?? 'n/a'}</div>`).join('');
  $('rewardLegend').innerHTML = ['total','AgentA','AgentB','AgentC'].map(k => `<span><b style="color:${colors[k]}">■</b> ${k}</span>`).join('');

  const opt = state.optuna || {};
  $('optunaStudy').textContent = opt.status === 'disabled' ? (opt.reason || 'disabled') : (opt.study || 'study waiting');
  const params = opt.best_params || {};
  $('optunaParams').innerHTML = Object.keys(params).length ? Object.entries(params).map(([k,v]) => `<div><b>${k}</b><br>${fmt(v)}</div>`).join('') : '<div>no completed trial yet</div>';
  drawSeries($('optunaCanvas'), opt.history || [], [{ color: colors.optuna, value: r => r.value }]);

  const ray = state.ray || {};
  $('rayBody').innerHTML = Object.entries(ray).map(([k,v]) => `<div><b>${k}</b><br>${v ?? 'n/a'}</div>`).join('');
  $('artifacts').innerHTML = (state.artifacts || []).slice().reverse().map(a => `<a><b>${a.label}</b><br><span class="muted">${a.path}</span></a>`).join('') || '<span class="muted">No artifacts yet</span>';
  $('events').innerHTML = (events || []).slice().reverse().map(e => `<div class="event"><b>${e.time}</b> [${e.kind}] ${e.message}</div>`).join('');
}
async function tick() {
  try {
    await reloadIfDashboardChanged();
    renderState(await getJSON('/api/state'), await getJSON('/api/events'));
  } catch (err) { console.error(err); }
}
tick(); setInterval(tick, 1200);
