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
function actionLabel(value) {
  if (!value) return 'candidate';
  return String(value).replaceAll('_', ' ');
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
  if (kind === 'ray') return 'policy';
  if (kind === 'optuna') return 'optuna';
  return 'simulator';
}
function diagramNodeMarkup(node, activeKeys) {
  const active = activeKeys.has(node.id) ? 'active' : '';
  return `
    <article class="diagram-node ${node.tone} ${active}" data-node="${safeText(node.id)}">
      <div class="node-kicker">${safeText(node.kicker)}</div>
      <strong>${safeText(node.title)}</strong>
      <span>${safeText(node.metric)}</span>
      <p>${safeText(node.detail)}</p>
    </article>
  `;
}
function actionSemantics(kind) {
  const normalized = String(kind || 'noop');
  const table = {
    migrate: {
      tone: 'movement',
      title: 'Node Movement',
      verb: 'move workload away from risky node',
      path: 'source node -> safer placement',
    },
    replicate: {
      tone: 'movement',
      title: 'Replica Placement',
      verb: 'create redundant task copy',
      path: 'target node -> replica slot',
    },
    throttle: {
      tone: 'safety',
      title: 'Safety Throttle',
      verb: 'reduce pressure on risky node',
      path: 'referee -> node throttle',
    },
    memory_balloon: {
      tone: 'efficiency',
      title: 'Memory Balloon',
      verb: 'compress memory footprint',
      path: 'referee -> memory control',
    },
    dvfs: {
      tone: 'efficiency',
      title: 'DVFS Clock Scaling',
      verb: 'lower CPU frequency for idle capacity',
      path: 'referee -> node clock',
    },
    power_state: {
      tone: 'efficiency',
      title: 'Power State Change',
      verb: 'change node power mode',
      path: 'referee -> power controller',
    },
    admission: {
      tone: 'admission',
      title: 'Admission Decision',
      verb: 'admit, queue, reject, or deprioritize work',
      path: 'referee -> workload queue',
    },
    resource_cap: {
      tone: 'admission',
      title: 'Resource Cap',
      verb: 'cap CPU and memory on overloaded node',
      path: 'referee -> resource limits',
    },
    noop: {
      tone: 'neutral',
      title: 'No-Op',
      verb: 'observe without changing the cluster',
      path: 'policy -> observation',
    },
  };
  return table[normalized] || { tone: 'neutral', title: actionLabel(normalized), verb: 'execute selected orchestration action', path: 'referee -> cluster' };
}
function proposalMarkup(proposal, selected) {
  const active = proposal.agent === selected.agent && proposal.kind === selected.kind ? 'selected' : '';
  return `
    <span class="proposal-chip ${safeText(proposal.agent)} ${active}">
      <b>${safeText(proposal.agent)}</b>
      ${safeText(actionLabel(proposal.kind))}
      <em>${fmt(proposal.score)}</em>
    </span>
  `;
}
function actionTraceMarkup(decision, cluster) {
  const semantics = actionSemantics(decision.kind);
  const proposals = Array.isArray(decision.proposals) ? decision.proposals : [];
  const selected = { agent: decision.agent, kind: decision.kind };
  const target = decision.target || cluster.max_risk_node || cluster.min_demand_node || 'cluster';
  const payload = decision.payload && Object.keys(decision.payload).length
    ? Object.entries(decision.payload).map(([key, value]) => `${key}=${value}`).join(', ')
    : 'no payload';
  return `
    <aside class="diagram-action-trace ${semantics.tone}" data-action="${safeText(decision.kind || 'noop')}">
      <div class="action-main">
        <span class="action-kicker">performed action</span>
        <strong>${safeText(decision.agent ? `${decision.agent}:${actionLabel(decision.kind)}` : 'waiting')}</strong>
        <p>${safeText(semantics.verb)}</p>
      </div>
      <div class="action-route">
        <span>referee</span>
        <b>${safeText(semantics.title)}</b>
        <span>${safeText(target)}</span>
      </div>
      <div class="action-meta">
        <span><b>path</b>${safeText(semantics.path)}</span>
        <span><b>payload</b>${safeText(payload)}</span>
      </div>
      <div class="proposal-strip">
        ${proposals.length ? proposals.map(proposal => proposalMarkup(proposal, selected)).join('') : '<span class="proposal-chip">proposals unavailable in this run</span>'}
      </div>
    </aside>
  `;
}
const diagramConnectors = [
  ['cluster', 'simulator', 'telemetry', 'flow-cluster-simulator'],
  ['exercise', 'simulator', 'telemetry', 'flow-exercise-simulator'],
  ['simulator', 'brain', 'inference', 'flow-simulator-brain'],
  ['simulator', 'observation', 'observation', 'flow-simulator-observation'],
  ['brain', 'policy', 'inference', 'flow-brain-policy'],
  ['observation', 'policy', 'policy', 'flow-observation-policy'],
  ['policy', 'AgentA', 'policy agent-a', 'flow-policy-agent-a'],
  ['policy', 'AgentB', 'policy agent-b', 'flow-policy-agent-b'],
  ['policy', 'AgentC', 'policy agent-c', 'flow-policy-agent-c'],
  ['AgentA', 'referee', 'proposal agent-a', 'flow-agent-a-referee'],
  ['AgentB', 'referee', 'proposal agent-b', 'flow-agent-b-referee'],
  ['AgentC', 'referee', 'proposal agent-c', 'flow-agent-c-referee'],
  ['referee', 'cluster', 'control', 'flow-referee-cluster'],
  ['referee', 'scoreboard', 'reward', 'flow-referee-scoreboard'],
  ['scoreboard', 'optuna', 'feedback', 'flow-scoreboard-optuna'],
  ['scoreboard', 'policy', 'feedback', 'flow-scoreboard-policy'],
  ['optuna', 'policy', 'meta', 'flow-optuna-policy'],
];
const animatedConnectorIds = [
  'flow-cluster-simulator',
  'flow-agent-b-referee',
  'flow-scoreboard-optuna',
  'flow-policy-agent-a',
  'flow-referee-scoreboard',
  'flow-optuna-policy',
];
function connectorAnchor(rect, side, rootRect) {
  const x = side === 'left' ? rect.left : side === 'right' ? rect.right : rect.left + rect.width / 2;
  const y = side === 'top' ? rect.top : side === 'bottom' ? rect.bottom : rect.top + rect.height / 2;
  return { x: x - rootRect.left, y: y - rootRect.top };
}
function connectorPath(source, target, mode) {
  const dx = Math.max(48, Math.abs(target.x - source.x) * 0.45);
  if (mode === 'return') {
    const lift = Math.min(source.y, target.y) - 72;
    return `M${source.x},${source.y} C${source.x - dx},${lift} ${target.x + dx},${lift} ${target.x},${target.y}`;
  }
  return `M${source.x},${source.y} C${source.x + dx},${source.y} ${target.x - dx},${target.y} ${target.x},${target.y}`;
}
function drawDiagramConnectors() {
  const diagram = $('flowDiagram');
  const svg = $('diagramArrows');
  if (!diagram || !svg) return;
  const rootRect = diagram.getBoundingClientRect();
  svg.setAttribute('viewBox', `0 0 ${Math.round(rootRect.width)} ${Math.round(rootRect.height)}`);
  const nodes = Object.fromEntries(
    [...diagram.querySelectorAll('[data-node]')].map(el => [el.dataset.node, el.getBoundingClientRect()])
  );
  const paths = diagramConnectors.map(([from, to, classes, id]) => {
    const sourceRect = nodes[from];
    const targetRect = nodes[to];
    if (!sourceRect || !targetRect) return '';
    const returnsToLeft = to === 'cluster' || to === 'policy' && (from === 'scoreboard' || from === 'optuna');
    const source = connectorAnchor(sourceRect, returnsToLeft ? 'left' : 'right', rootRect);
    const target = connectorAnchor(targetRect, returnsToLeft ? 'right' : 'left', rootRect);
    return `<path id="${id}" class="arrow ${classes}" d="${connectorPath(source, target, returnsToLeft ? 'return' : 'forward')}" />`;
  }).join('');
  const packets = animatedConnectorIds.map((id, index) => `
    <circle class="packet packet-${index + 1}" r="${index === 0 ? 7 : 5}">
      <animateMotion dur="${5 + index * 0.25}s" begin="${index * 0.45}s" repeatCount="indefinite">
        <mpath href="#${id}" />
      </animateMotion>
    </circle>
  `).join('');
  svg.innerHTML = `
    <defs>
      <marker id="arrowHead" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
        <path d="M0,0 L10,5 L0,10 z"></path>
      </marker>
    </defs>
    ${paths}
    ${packets}
  `;
}
function diagramEventMarkup(event, index) {
  return `
    <article class="diagram-event ${eventTone(event.kind)}" style="--delay:${index * 75}ms">
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
  const recentEvents = (events || []).slice(-5).reverse();
  const activeKeys = new Set(recentEvents.map(e => e.kind === 'decision' && e.agent ? e.agent : eventNode(e.kind)));
  if (decision.agent) activeKeys.add(decision.agent);
  if (ray.status) activeKeys.add('policy');
  if (opt.status) activeKeys.add('optuna');

  $('flowClock').textContent = shortTime(state.updated_at || decision.time || cluster.time);
  const agentMetric = (agent) => decision.agent === agent ? actionLabel(decision.kind) : 'candidate';
  const agentDetail = (agent) => {
    const reward = byAgent[agent];
    if (decision.agent === agent) return `${decision.target || 'cluster'} / score ${fmt(decision.score)}`;
    return `last reward ${fmt(reward)} / observing`;
  };
  const nodes = [
    {
      id: 'cluster', tone: 'cluster',
      kicker: 'Layer 1 source',
      title: 'Kubernetes Cluster',
      metric: `risk ${fmt(cluster.max_risk)}`,
      detail: `${cluster.nodes ?? 0} node / ${cluster.tasks ?? 0} task / sla ${cluster.sla_violations ?? 0}`,
    },
    {
      id: 'exercise', tone: 'exercise',
      kicker: 'Live perturbation',
      title: 'Workload Exerciser',
      metric: latestExercise ? 'active' : 'idle',
      detail: latestExercise?.phase || 'observing cluster state',
    },
    {
      id: 'simulator', tone: 'simulator',
      kicker: 'Layer 2 digital twin',
      title: 'AIOpsLab Twin',
      metric: `cpu ${fmt(cluster.avg_cpu)}`,
      detail: `mem ${fmt(cluster.avg_mem)} energy ${fmt(cluster.energy_watts)}W`,
    },
    {
      id: 'brain', tone: 'brain',
      kicker: 'Layer 3 predictors',
      title: 'XGBoost Brains',
      metric: `risk ${fmt(cluster.max_risk)} / demand ${fmt(cluster.min_demand)}`,
      detail: `safety forecast + resource demand projection`,
    },
    {
      id: 'observation', tone: 'observation',
      kicker: 'Observation space',
      title: 'State Vector',
      metric: `${decision.proposal_count ?? 0} proposals`,
      detail: `node map + tasks + forecasts`,
    },
    {
      id: 'policy', tone: 'policy',
      kicker: 'Layer 4 MARL',
      title: 'Ray RLlib PPO Policy',
      metric: ray.status || 'idle',
      detail: ray.reward_mean === undefined ? 'policy network for A/B/C' : `reward mean ${fmt(ray.reward_mean)}`,
    },
    {
      id: 'AgentA', tone: 'AgentA',
      kicker: 'Agent A safety',
      title: 'Agent A',
      metric: agentMetric('AgentA'),
      detail: agentDetail('AgentA'),
    },
    {
      id: 'AgentB', tone: 'AgentB',
      kicker: 'Agent B efficiency',
      title: 'Agent B',
      metric: agentMetric('AgentB'),
      detail: agentDetail('AgentB'),
    },
    {
      id: 'AgentC', tone: 'AgentC',
      kicker: 'Agent C admission',
      title: 'Agent C',
      metric: agentMetric('AgentC'),
      detail: agentDetail('AgentC'),
    },
    {
      id: 'referee', tone: 'referee',
      kicker: 'Safety-first referee',
      title: 'Decision Gate',
      metric: `score ${fmt(decision.score)}`,
      detail: decision.reason || 'waiting for recommendation',
    },
    {
      id: 'scoreboard', tone: 'scoreboard',
      kicker: 'Layer 6 feedback',
      title: 'Global Scoreboard',
      metric: fmt(lastReward.total),
      detail: `A ${fmt(byAgent.AgentA)} / B ${fmt(byAgent.AgentB)} / C ${fmt(byAgent.AgentC)}`,
    },
    {
      id: 'optuna', tone: 'optuna',
      kicker: 'Layer 5 meta optimizer',
      title: 'Optuna Trial Manager',
      metric: opt.best_score === undefined ? 'n/a' : fmt(opt.best_score),
      detail: opt.study || 'tunes reward weights + PPO params',
    },
  ];
  const nodeById = Object.fromEntries(nodes.map(node => [node.id, node]));
  const lanes = [
    { className: 'lane-source', title: 'Layer 1', detail: 'cluster source', ids: ['cluster', 'exercise'] },
    { className: 'lane-twin', title: 'Layer 2', detail: 'live digital twin', ids: ['simulator'] },
    { className: 'lane-brain', title: 'Layer 3', detail: 'prediction + state', ids: ['brain', 'observation'] },
    { className: 'lane-marl', title: 'Layer 4', detail: 'policy and agents', ids: ['policy', 'AgentA', 'AgentB', 'AgentC'] },
    { className: 'lane-referee', title: 'Referee', detail: 'safety gate', ids: ['referee'] },
    { className: 'lane-feedback', title: 'Layers 5-6', detail: 'meta + reward', ids: ['scoreboard', 'optuna'] },
  ];

  $('flowDiagram').innerHTML = `
    <svg id="diagramArrows" class="diagram-arrows" preserveAspectRatio="none" aria-hidden="true"></svg>
    <div class="diagram-grid"></div>
    <div class="diagram-legend">
      <span><b class="legend-telemetry"></b>telemetry</span>
      <span><b class="legend-inference"></b>inference</span>
      <span><b class="legend-policy"></b>policy</span>
      <span><b class="legend-reward"></b>reward/meta loop</span>
    </div>
    <div class="diagram-lanes">
      ${lanes.map(lane => `
        <section class="diagram-lane ${lane.className}">
          <header>
            <strong>${safeText(lane.title)}</strong>
            <span>${safeText(lane.detail)}</span>
          </header>
          ${lane.ids.map(id => diagramNodeMarkup(nodeById[id], activeKeys)).join('')}
        </section>
      `).join('')}
    </div>
    ${actionTraceMarkup(decision, cluster)}
  `;
  $('flowEvents').innerHTML = recentEvents.map(diagramEventMarkup).join('');
  requestAnimationFrame(drawDiagramConnectors);
}
window.addEventListener('resize', () => requestAnimationFrame(drawDiagramConnectors));
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
    ['steps', rewardSummary.count],
    ['avg total', fmt(rewardSummary.average_total)],
    ['last AgentA', fmt(byAgent.AgentA)],
    ['last AgentB', fmt(byAgent.AgentB)],
    ['last AgentC', fmt(byAgent.AgentC)],
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
