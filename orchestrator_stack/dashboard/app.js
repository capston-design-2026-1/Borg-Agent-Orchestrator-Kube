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
function safeText(value) {
  return String(value ?? 'n/a').replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}
function shortTime(value) {
  if (!value) return 'waiting';
  const match = String(value).match(/T(\d\d:\d\d:\d\d)/);
  return match ? match[1] : String(value);
}
function niceTick(value) {
  if (!Number.isFinite(value)) return 'n/a';
  const abs = Math.abs(value);
  if (abs >= 100) return value.toFixed(0);
  if (abs >= 10) return value.toFixed(1);
  return value.toFixed(2);
}
function drawSeries(canvas, rows, series, options = {}) {
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  const pad = { left: 68, right: 20, top: 18, bottom: 48 };
  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;
  ctx.clearRect(0, 0, w, h);
  const values = rows.flatMap(row => series.map(s => s.value(row))).filter(Number.isFinite);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const span = max - min || 1;

  ctx.save();
  ctx.font = '12px "Avenir Next", "Gill Sans", sans-serif';
  ctx.textBaseline = 'middle';
  ctx.strokeStyle = 'rgba(20,33,27,.16)';
  ctx.fillStyle = 'rgba(20,33,27,.62)';
  ctx.lineWidth = 1;

  for (let i = 0; i <= 4; i++) {
    const ratio = i / 4;
    const y = pad.top + ratio * plotH;
    const value = max - ratio * span;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(w - pad.right, y);
    ctx.stroke();
    ctx.textAlign = 'right';
    ctx.fillText(niceTick(value), pad.left - 10, y);
  }

  const xTicks = rows.length > 1 ? [0, Math.floor((rows.length - 1) / 2), rows.length - 1] : [0];
  xTicks.forEach((index) => {
    const x = rows.length <= 1 ? pad.left : pad.left + (index / (rows.length - 1)) * plotW;
    ctx.beginPath();
    ctx.moveTo(x, pad.top);
    ctx.lineTo(x, h - pad.bottom);
    ctx.stroke();
    ctx.textAlign = 'center';
    ctx.fillText(String(index), x, h - 24);
  });

  ctx.strokeStyle = 'rgba(20,33,27,.58)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, h - pad.bottom);
  ctx.lineTo(w - pad.right, h - pad.bottom);
  ctx.stroke();

  ctx.fillStyle = 'rgba(20,33,27,.78)';
  ctx.textAlign = 'center';
  ctx.fillText(options.xLabel || 'step', pad.left + plotW / 2, h - 8);
  ctx.save();
  ctx.translate(18, pad.top + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(options.yLabel || 'value', 0, 0);
  ctx.restore();
  ctx.restore();

  if (!rows.length) return;
  series.forEach(s => {
    ctx.strokeStyle = s.color; ctx.lineWidth = 3; ctx.beginPath();
    rows.forEach((row, i) => {
      const x = rows.length === 1 ? pad.left : pad.left + (i / (rows.length - 1)) * plotW;
      const y = h - pad.bottom - ((s.value(row) - min) / span) * plotH;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  });
}
function eventTone(kind) {
  if (kind === 'decision') return 'agent';
  if (kind === 'reward') return 'reward';
  if (kind === 'cluster' || kind === 'exercise') return 'cluster';
  if (kind === 'ray') return 'ray';
  if (kind === 'optuna') return 'optuna';
  if (kind === 'stage') return 'stage';
  return 'neutral';
}
function flowLaneMarkup({ key, title, subtitle, metric, detail, tone }) {
  return `
    <article class="flow-lane ${tone || key}">
      <div class="lane-cap">${safeText(title)}</div>
      <strong>${safeText(metric)}</strong>
      <span>${safeText(subtitle)}</span>
      <p>${safeText(detail)}</p>
    </article>
  `;
}
function renderFlow(state, events) {
  const cluster = state.cluster || {};
  const decision = state.decision || {};
  const rewards = state.rewards || [];
  const lastReward = rewards[rewards.length - 1] || {};
  const byAgent = lastReward.rewards || {};
  const opt = state.optuna || {};
  const ray = state.ray || {};
  const latestExercise = (events || []).slice().reverse().find(e => e.kind === 'exercise');

  $('flowClock').textContent = shortTime(state.updated_at || decision.time || cluster.time);
  $('flowLanes').innerHTML = [
    flowLaneMarkup({
      key: 'cluster',
      title: 'Kubernetes',
      subtitle: `${cluster.nodes ?? 0} node / ${cluster.tasks ?? 0} active task`,
      metric: `risk ${fmt(cluster.max_risk)}`,
      detail: `cpu ${fmt(cluster.avg_cpu)} mem ${fmt(cluster.avg_mem)} sla ${cluster.sla_violations ?? 0}`,
    }),
    flowLaneMarkup({
      key: 'exercise',
      title: 'Workload pulse',
      subtitle: latestExercise?.phase || 'observing',
      metric: latestExercise ? 'active' : 'idle',
      detail: latestExercise?.message || 'waiting for cluster perturbation',
    }),
    flowLaneMarkup({
      key: 'brain',
      title: 'Brain / Referee',
      subtitle: `${decision.proposal_count ?? 0} proposals scored`,
      metric: `score ${fmt(decision.score)}`,
      detail: decision.reason || 'waiting for recommendation',
    }),
    flowLaneMarkup({
      key: 'agent',
      title: 'Agent Decision',
      subtitle: decision.target || 'no target yet',
      metric: decision.agent ? `${decision.agent}:${decision.kind}` : 'waiting',
      detail: `priority ${decision.priority ?? 'n/a'} repeat ${decision.repeat_count ?? 0}`,
      tone: decision.agent || 'agent',
    }),
    flowLaneMarkup({
      key: 'reward',
      title: 'Reward Feedback',
      subtitle: lastReward.action || 'no reward yet',
      metric: fmt(lastReward.total),
      detail: `A ${fmt(byAgent.AgentA)} / B ${fmt(byAgent.AgentB)} / C ${fmt(byAgent.AgentC)}`,
    }),
    flowLaneMarkup({
      key: 'meta',
      title: 'Ray + Optuna',
      subtitle: `Ray ${ray.status || 'idle'} / Optuna ${opt.status || 'waiting'}`,
      metric: opt.best_score === undefined ? 'n/a' : fmt(opt.best_score),
      detail: opt.study || ray.checkpoint || 'meta-loop awaiting update',
    }),
  ].join('');

  $('flowPopups').innerHTML = (events || []).slice(-9).reverse().map((event, index) => `
    <article class="flow-popup ${eventTone(event.kind)}" style="--delay:${index * 80}ms">
      <span>${safeText(shortTime(event.time))} · ${safeText(event.kind)}</span>
      <strong>${safeText(event.action || event.phase || event.agent || event.name || 'runtime')}</strong>
      <p>${safeText(event.message)}</p>
    </article>
  `).join('');
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
  renderFlow(state, events || []);
  drawSeries($('rewardCanvas'), rewards, [
    { color: colors.total, value: r => r.total },
    { color: colors.AgentA, value: r => r.rewards?.AgentA },
    { color: colors.AgentB, value: r => r.rewards?.AgentB },
    { color: colors.AgentC, value: r => r.rewards?.AgentC },
  ], { xLabel: 'orchestration step', yLabel: 'reward' });
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
  drawSeries($('optunaCanvas'), opt.history || [], [{ color: colors.optuna, value: r => r.value }], { xLabel: 'trial', yLabel: 'objective' });

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
