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
function eventNode(kind) {
  if (kind === 'cluster' || kind === 'exercise') return 'cluster';
  if (kind === 'reward') return 'scoreboard';
  if (kind === 'ray') return 'rllib';
  if (kind === 'optuna') return 'optuna';
  return 'simulator';
}
function diagramNodeMarkup(node, activeKeys) {
  const active = activeKeys.has(node.id) ? 'active' : '';
  return `
    <article class="diagram-node ${node.tone} ${active}" style="left:${node.x}%;top:${node.y}%">
      <div class="node-kicker">${safeText(node.kicker)}</div>
      <strong>${safeText(node.title)}</strong>
      <span>${safeText(node.metric)}</span>
      <p>${safeText(node.detail)}</p>
    </article>
  `;
}
function diagramCalloutMarkup(event, index) {
  const node = event.kind === 'decision' && event.agent ? event.agent : eventNode(event.kind);
  return `
    <article class="diagram-callout ${eventTone(event.kind)} node-${node}" style="--delay:${index * 75}ms">
      <span>${safeText(shortTime(event.time))} · ${safeText(event.kind)}</span>
      <strong>${safeText(event.action || event.phase || event.agent || event.name || 'runtime')}</strong>
      <p>${safeText(event.message)}</p>
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
  const recentEvents = (events || []).slice(-8).reverse();
  const activeKeys = new Set(recentEvents.map(e => e.kind === 'decision' && e.agent ? e.agent : eventNode(e.kind)));
  if (decision.agent) activeKeys.add(decision.agent);

  $('flowClock').textContent = shortTime(state.updated_at || decision.time || cluster.time);
  const agentMetric = (agent) => decision.agent === agent ? decision.kind : 'candidate';
  const agentDetail = (agent) => {
    const reward = byAgent[agent];
    if (decision.agent === agent) return `${decision.target || 'cluster'} / score ${fmt(decision.score)}`;
    return `last reward ${fmt(reward)} / observing`;
  };
  const nodes = [
    {
      id: 'cluster', tone: 'cluster', x: 5, y: 18,
      kicker: 'Layer 1',
      title: 'Kubernetes',
      metric: `risk ${fmt(cluster.max_risk)}`,
      detail: `${cluster.nodes ?? 0} node / ${cluster.tasks ?? 0} task / sla ${cluster.sla_violations ?? 0}`,
    },
    {
      id: 'exercise', tone: 'exercise', x: 5, y: 62,
      kicker: 'Perturbation',
      title: 'Workload pulse',
      metric: latestExercise ? 'active' : 'idle',
      detail: latestExercise?.phase || 'observing cluster state',
    },
    {
      id: 'simulator', tone: 'simulator', x: 25, y: 40,
      kicker: 'Layer 2',
      title: 'AIOps Twin',
      metric: `cpu ${fmt(cluster.avg_cpu)}`,
      detail: `mem ${fmt(cluster.avg_mem)} energy ${fmt(cluster.energy_watts)}W`,
    },
    {
      id: 'brain', tone: 'brain', x: 45, y: 16,
      kicker: 'Layer 3',
      title: 'XGBoost Brain',
      metric: `demand ${fmt(cluster.min_demand)}`,
      detail: `risk node ${cluster.max_risk_node || 'n/a'}`,
    },
    {
      id: 'AgentA', tone: 'AgentA', x: 42, y: 50,
      kicker: 'Layer 4 Safety',
      title: 'Agent A',
      metric: agentMetric('AgentA'),
      detail: agentDetail('AgentA'),
    },
    {
      id: 'AgentB', tone: 'AgentB', x: 42, y: 72,
      kicker: 'Layer 4 Efficiency',
      title: 'Agent B',
      metric: agentMetric('AgentB'),
      detail: agentDetail('AgentB'),
    },
    {
      id: 'AgentC', tone: 'AgentC', x: 42, y: 94,
      kicker: 'Layer 4 Admission',
      title: 'Agent C',
      metric: agentMetric('AgentC'),
      detail: agentDetail('AgentC'),
    },
    {
      id: 'referee', tone: 'referee', x: 64, y: 40,
      kicker: 'Referee',
      title: 'Decision Gate',
      metric: `score ${fmt(decision.score)}`,
      detail: decision.reason || 'waiting for recommendation',
    },
    {
      id: 'scoreboard', tone: 'scoreboard', x: 82, y: 18,
      kicker: 'Layer 6',
      title: 'Reward Feedback',
      metric: fmt(lastReward.total),
      detail: `A ${fmt(byAgent.AgentA)} / B ${fmt(byAgent.AgentB)} / C ${fmt(byAgent.AgentC)}`,
    },
    {
      id: 'rllib', tone: 'rllib', x: 82, y: 62,
      kicker: 'Ray RLlib',
      title: 'PPO Trainer',
      metric: ray.status || 'idle',
      detail: ray.reward_mean === undefined ? 'policy loop' : `reward mean ${fmt(ray.reward_mean)}`,
    },
    {
      id: 'optuna', tone: 'optuna', x: 64, y: 78,
      kicker: 'Layer 5',
      title: 'Ray + Optuna',
      metric: opt.best_score === undefined ? 'n/a' : fmt(opt.best_score),
      detail: opt.study || 'reward and policy search',
    },
  ];

  $('flowDiagram').innerHTML = `
    <svg class="diagram-arrows" viewBox="0 0 1000 520" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <marker id="arrowHead" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
          <path d="M0,0 L10,5 L0,10 z"></path>
        </marker>
      </defs>
      <path id="flow-cluster-twin" class="arrow main" d="M170 155 C245 155 250 260 315 260" />
      <path id="flow-exercise-twin" class="arrow main" d="M170 380 C250 380 250 270 315 270" />
      <path id="flow-twin-brain" class="arrow main" d="M400 250 C455 160 485 145 545 145" />
      <path id="flow-twin-agent-a" class="arrow main agent-a" d="M400 285 C430 300 455 300 500 292" />
      <path id="flow-twin-agent-b" class="arrow main agent-b" d="M400 292 C435 360 460 382 500 398" />
      <path id="flow-twin-agent-c" class="arrow main agent-c" d="M400 302 C430 455 455 495 500 505" />
      <path id="flow-brain-referee" class="arrow main" d="M625 170 C675 215 690 235 735 255" />
      <path id="flow-agent-a-referee" class="arrow main agent-a" d="M595 292 C650 280 690 268 735 260" />
      <path id="flow-agent-b-referee" class="arrow main agent-b" d="M595 398 C660 370 700 320 735 285" />
      <path id="flow-agent-c-referee" class="arrow main agent-c" d="M595 505 C680 430 705 345 735 295" />
      <path id="flow-referee-score" class="arrow main" d="M810 255 C855 215 865 170 890 150" />
      <path id="flow-feedback" class="arrow feedback" d="M890 365 C825 490 585 500 505 410" />
      <path id="flow-meta" class="arrow meta" d="M800 415 C760 450 725 450 700 420" />
      <circle class="packet packet-one" r="7">
        <animateMotion dur="6s" repeatCount="indefinite">
          <mpath href="#flow-cluster-twin" />
        </animateMotion>
      </circle>
      <circle class="packet packet-two" r="6">
        <animateMotion dur="5s" begin=".9s" repeatCount="indefinite">
          <mpath href="#flow-agent-b-referee" />
        </animateMotion>
      </circle>
      <circle class="packet packet-three" r="5">
        <animateMotion dur="4.8s" begin=".3s" repeatCount="indefinite">
          <mpath href="#flow-feedback" />
        </animateMotion>
      </circle>
    </svg>
    <div class="diagram-grid"></div>
    ${nodes.map(node => diagramNodeMarkup(node, activeKeys)).join('')}
    <div class="diagram-callouts">${recentEvents.map(diagramCalloutMarkup).join('')}</div>
  `;
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
