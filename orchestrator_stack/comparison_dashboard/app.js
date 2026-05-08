const $ = (id) => document.getElementById(id);
const historyRows = [];
const palette = {
  experimental: '#16835f', baseline: '#d48a20', blue: '#2f6f9f', red: '#b44634', ink: '#10201a', muted: '#65756e', grid: 'rgba(16,32,26,.14)', panel: 'rgba(255,255,255,.58)'
};
const PRESSURE_TIMELINE_WINDOW_MS = 5 * 60 * 1000;

function esc(value) { return String(value ?? 'n/a').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch])); }
function num(value) { const n = Number(value); return Number.isFinite(n) ? n : null; }
function fmt(value, digits = 3) { const n = num(value); return n === null ? 'n/a' : n.toFixed(digits); }
function pct(value) { const n = num(value); return n === null ? 'n/a' : `${n.toFixed(1)}%`; }
function hpaDesired(cluster) { return (cluster.hpa || []).reduce((sum, item) => sum + Number(item.desired ?? item.current ?? item.min ?? 0), 0); }
function hpaCurrent(cluster) { return (cluster.hpa || []).reduce((sum, item) => sum + Number(item.current ?? 0), 0); }
function hpaMax(cluster) { return (cluster.hpa || []).reduce((sum, item) => sum + Number(item.max ?? 0), 0); }
function hpaFirst(cluster) { return (cluster.hpa || [])[0] || {}; }
function hpaReaction(cluster) {
  const items = cluster.hpa || [];
  if (!items.length) return { label: 'HPA not installed', detail: 'No autoscaling/v2 object was returned by the baseline cluster.', state: 'unknown' };
  const current = hpaCurrent(cluster);
  const desired = hpaDesired(cluster);
  const max = hpaMax(cluster);
  const first = hpaFirst(cluster);
  const cpu = num(first.cpu_utilization);
  const target = num(first.target_cpu_utilization);
  const lastScale = first.last_scale_time ? new Date(first.last_scale_time).toLocaleTimeString() : 'not recorded';
  let state = 'steady';
  let label = `stable at ${current} replicas`;
  if (max && current >= max && desired >= max) {
    state = 'saturated';
    label = `maxed at ${current}/${max} replicas`;
  } else if (desired > current) {
    state = 'scale-up';
    label = `scaling up ${current} -> ${desired} replicas`;
  } else if (desired < current) {
    state = 'scale-down';
    label = `scaling down ${current} -> ${desired} replicas`;
  }
  const headroom = max ? `${Math.max(0, max - current)} replica headroom` : 'max unknown';
  const cpuText = cpu === null || target === null ? 'CPU metric pending' : `CPU ${cpu.toFixed(0)}% / target ${target.toFixed(0)}%`;
  return { label: `HPA ${label}`, detail: `${cpuText}; ${headroom}; last scale ${lastScale}`, state, current, desired, max, cpu, target, lastScale };
}
function agentProposal(decision, agent) {
  return (decision?.proposals || []).find(item => item.agent === agent) || {};
}
function proposalSummary(decision, agent) {
  const proposal = agentProposal(decision, agent);
  if (!proposal.kind) return 'no proposal';
  const target = proposal.target ? ` -> ${proposal.target}` : '';
  return `${proposal.kind}${target}, score ${fmt(proposal.score)}`;
}
function selectedSummary(decision, agent) {
  if (decision?.agent === agent) return `selected ${decision.kind || 'action'}`;
  if (!decision?.agent) return 'waiting';
  return `observing; ${decision.agent} selected`;
}
function stimulusSummary(payload) {
  const stimulus = payload.shared_stimulus || {};
  const mirrorCount = stimulus.mirror_count ?? (stimulus.mirrors || []).length ?? 0;
  const resource = stimulus.resources || {};
  const size = [resource.cpu_request, resource.memory_request, resource.replicas ? `${resource.replicas} replicas` : null].filter(Boolean).join(' / ');
  return {
    title: stimulus.phase || stimulus.message || 'waiting for shared stimulus',
    detail: `${stimulus.operation || 'n/a'} in ${stimulus.namespace || 'n/a'}; mirrored clusters ${mirrorCount}${size ? `; ${size}` : ''}`,
  };
}
function objectiveStatus(kind, payload) {
  const exp = payload.experimental || {};
  const base = payload.baseline || {};
  const reward = exp.reward_summary || {};
  const stimulus = payload.shared_stimulus || {};
  if (kind === 'safety') {
    const risk = num(exp.max_risk) ?? 0;
    const sla = num(exp.sla_violations) ?? 0;
    if (sla === 0 && risk < 0.7) return ['healthy', 'good'];
    if (sla === 0 && risk < 0.83) return ['mitigating', 'watch'];
    return ['high risk', 'bad'];
  }
  if (kind === 'efficiency') {
    const demand = num(exp.min_demand) ?? 1;
    if (demand < 0.45) return ['saving opportunity', 'good'];
    if (demand < 0.7) return ['balanced', 'neutral'];
    return ['high demand', 'watch'];
  }
  if (kind === 'admission') {
    const expPending = num(exp.pending_pods) ?? 0;
    const basePending = num(base.pending_pods) ?? 0;
    if (expPending < basePending) return ['better backlog', 'good'];
    if (expPending === basePending) return ['matched backlog', 'neutral'];
    return ['higher backlog', 'watch'];
  }
  if (kind === 'learning') {
    const count = num(reward.count) ?? 0;
    if ((exp.ray?.status === 'trained' || exp.optuna?.completed_trials > 0) && count > 0) return ['learning active', 'good'];
    return ['waiting', 'watch'];
  }
  if (kind === 'fidelity') {
    const mirrorCount = num(stimulus.mirror_count ?? (stimulus.mirrors || []).length) ?? 0;
    return mirrorCount > 0 ? ['mirrored', 'good'] : ['not mirrored', 'bad'];
  }
  return ['observing', 'neutral'];
}
function metricHtml(rows) { return rows.map(([k, v]) => `<div><b>${esc(v)}</b><span>${esc(k)}</span></div>`).join(''); }
function latest() { return historyRows[historyRows.length - 1] || {}; }
function compactAction(value) {
  const text = String(value || 'n/a');
  const parts = text.split(':');
  if (parts.length >= 3) return `${parts[0]}:${parts[2]}`;
  return text;
}
function displayTime(value) {
  if (!value) return 'waiting';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}
function downsample(rows, maxPoints = 1100) {
  if (!Array.isArray(rows) || rows.length <= maxPoints) return rows || [];
  const step = Math.ceil(rows.length / maxPoints);
  return rows.filter((_, index) => index % step === 0 || index === rows.length - 1);
}
function pressureWindowRows(rows, windowMs = PRESSURE_TIMELINE_WINDOW_MS) {
  if (!Array.isArray(rows) || rows.length <= 1) return rows || [];
  const latestMs = Math.max(...rows.map(row => new Date(row.time).getTime()).filter(Number.isFinite));
  if (!Number.isFinite(latestMs)) return rows;
  const startMs = latestMs - windowMs;
  const visible = rows.filter(row => {
    const t = new Date(row.time).getTime();
    return Number.isFinite(t) && t >= startMs;
  });
  return visible.length ? visible : rows.slice(-1);
}

function setupCanvas(canvas) {
  const ctx = canvas.getContext('2d');
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(10, Math.floor(rect.width * ratio));
  const height = Math.max(10, Math.floor(rect.height * ratio));
  if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { ctx, w: rect.width, h: rect.height };
}
function scaledMax(values, floor = 1) {
  const realValues = values.map(num).filter(v => v !== null);
  const raw = Math.max(floor, ...realValues);
  if (raw <= 5) return Math.ceil(raw + 1);
  if (raw <= 25) return Math.ceil(raw / 5) * 5;
  if (raw <= 100) return Math.ceil(raw / 10) * 10;
  return Math.ceil(raw / 25) * 25;
}
function drawAxisTicks(ctx, panel, scale, side) {
  ctx.strokeStyle = palette.grid;
  ctx.fillStyle = 'rgba(16,32,26,.62)';
  ctx.font = '11px Avenir Next, sans-serif';
  ctx.textAlign = side === 'right' ? 'left' : 'right';
  for (let i = 0; i <= 3; i++) {
    const ratio = i / 3;
    const y = panel.y + ratio * panel.h;
    const value = scale.max - ratio * (scale.max - scale.min);
    ctx.beginPath();
    ctx.moveTo(panel.x, y);
    ctx.lineTo(panel.x + panel.w, y);
    ctx.stroke();
    const labelX = side === 'right' ? panel.x + panel.w + 10 : panel.x - 10;
    ctx.fillText(value.toFixed(value >= 10 ? 0 : 1), labelX, y + 4);
  }
}
function drawPanelSeries(ctx, rows, panel, scale, series) {
  const xFor = index => rows.length <= 1 ? panel.x + panel.w / 2 : panel.x + (index / (rows.length - 1)) * panel.w;
  const yFor = value => panel.y + panel.h - ((Number(value || 0) - scale.min) / (scale.max - scale.min || 1)) * panel.h;
  series.forEach(item => {
    ctx.strokeStyle = item.color;
    ctx.lineWidth = item.width || 2.8;
    ctx.setLineDash(item.dash || []);
    ctx.beginPath();
    rows.forEach((row, index) => {
      const value = num(row[item.key]);
      const x = xFor(index), y = yFor(value ?? 0);
      if (index === 0) {
        ctx.moveTo(x, y);
      } else if (item.stepped) {
        const previous = num(rows[index - 1][item.key]) ?? 0;
        ctx.lineTo(x, yFor(previous));
        ctx.lineTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();
    ctx.setLineDash([]);
  });
}
function drawPressureTimeline(canvasId, sourceRows) {
  const canvas = $(canvasId); if (!canvas) return;
  const { ctx, w, h } = setupCanvas(canvas);
  const rows = downsample(sourceRows);
  const left = 68, right = 86, top = 24, bottom = 50, gap = 24;
  const panels = [
    {
      title: 'Safety risk',
      unit: 'risk score / SLA count',
      side: 'left',
      y: top,
      series: [
        { key:'experimentalRisk', color:palette.red, label:'Agent A risk forecast', width:3 },
        { key:'experimentalSla', color:'#6d372f', label:'experimental SLA violations', width:2.3, dash:[6, 5], stepped:true },
      ],
      maxFloor: 1,
    },
    {
      title: 'Admission backlog',
      unit: 'queue / pending pods',
      side: 'left',
      y: 0,
      series: [
        { key:'experimentalQueue', color:palette.blue, label:'Agent C queue length', width:3 },
        { key:'experimentalPending', color:palette.experimental, label:'experimental pending pods', width:2.5 },
        { key:'baselinePending', color:palette.baseline, label:'baseline pending pods', width:2.5 },
      ],
      maxFloor: 5,
    },
    {
      title: 'Efficiency signal',
      unit: 'estimated watts',
      side: 'right',
      y: 0,
      series: [
        { key:'experimentalEnergy', color:palette.experimental, label:'Agent B estimated watts', width:2.8 },
      ],
      maxFloor: 5,
    },
    {
      title: 'Reward outcome',
      unit: 'weighted total reward',
      side: 'right',
      y: 0,
      series: [
        { key:'experimentalReward', color:'#111f1a', label:'experimental weighted reward', width:3 },
      ],
      maxFloor: 5,
    },
  ];
  const plotW = w - left - right;
  const panelH = (h - top - bottom - gap * (panels.length - 1)) / panels.length;
  panels.forEach((panel, index) => { panel.y = top + index * (panelH + gap); });

  ctx.clearRect(0,0,w,h);
  ctx.fillStyle = 'rgba(255,255,255,.48)';
  ctx.fillRect(left, top, plotW, h - top - bottom);
  panels.forEach(item => {
    const panel = { x:left, y:item.y, w:plotW, h:panelH };
    const values = rows.flatMap(row => item.series.map(seriesItem => row[seriesItem.key]));
    const max = scaledMax(values, item.maxFloor);
    const scale = { min:0, max };
    ctx.fillStyle = 'rgba(255,255,255,.34)';
    ctx.fillRect(panel.x, panel.y, panel.w, panel.h);
    drawAxisTicks(ctx, panel, scale, item.side);
    ctx.fillStyle = palette.ink;
    ctx.font = '800 13px Avenir Next, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(item.title, panel.x + 8, panel.y + 17);
    ctx.fillStyle = palette.muted;
    ctx.font = '10px Avenir Next, sans-serif';
    ctx.fillText(item.unit, panel.x + 8, panel.y + 32);
    if (rows.length) drawPanelSeries(ctx, rows, panel, scale, item.series);
  });
  if (rows.length) {
    const bottomPanel = { x:left, y:top + (panelH + gap) * (panels.length - 1), w:plotW, h:panelH };
    const xFor = index => rows.length <= 1 ? bottomPanel.x + bottomPanel.w / 2 : bottomPanel.x + (index / (rows.length - 1)) * bottomPanel.w;
    const ticks = [0, Math.floor((rows.length - 1) / 2), rows.length - 1];
    ctx.fillStyle = 'rgba(16,32,26,.58)';
    ctx.font = '11px Avenir Next, sans-serif';
    ticks.forEach(index => {
      const row = rows[index];
      const x = xFor(index);
      ctx.textAlign = index === 0 ? 'left' : index === rows.length - 1 ? 'right' : 'center';
      ctx.fillText(displayTime(row.time), x, h - 27);
    });
  }
  ctx.fillStyle = 'rgba(16,32,26,.68)';
  ctx.font = '12px Avenir Next, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('last 5 minutes', left + plotW / 2, h - 9);
  const legendSeries = panels.flatMap(panel => panel.series);
  $('timelineLegend').innerHTML = legendSeries.map(item => `<span><b style="color:${item.color}">■</b> ${esc(item.label)}</span>`).join('');
}
function drawCharts(payload, chartHistory) {
  drawPressureTimeline('timelineCanvas', chartHistory);
}

function renderObjectiveEvidence(payload) {
  const target = $('objectiveEvidence');
  if (!target) return;
  const exp = payload.experimental || {};
  const base = payload.baseline || {};
  const decision = exp.decision || {};
  const reward = exp.reward_summary || {};
  const baseSummary = base.pod_summary || {};
  const basePhases = baseSummary.phase_counts || {};
  const hpa = hpaReaction(base);
  const stimulus = stimulusSummary(payload);
  const optuna = exp.optuna || {};
  const ray = exp.ray || {};
  const objectives = [
    {
      label: 'Agent A safety',
      value: `risk ${fmt(exp.max_risk)} / SLA ${esc(exp.sla_violations ?? 0)}`,
      baseline: `baseline failed ${esc(basePhases.Failed || 0)} / restarts ${esc(baseSummary.restarts || 0)}`,
      note: 'Proactive risk mitigation should lower failure exposure before Kubernetes only sees restarts or failed pods.',
      tone: 'safety',
    },
    {
      label: 'Agent B efficiency',
      value: `${fmt(exp.energy_watts, 1)}W ${exp.power_metric_kind ? `(${esc(exp.power_metric_kind)})` : ''}`,
      baseline: `${hpa.label}; ${esc(base.karpenter?.active_nodes ?? 'n/a')} active / ${esc(base.karpenter?.warm_nodes ?? 'n/a')} warm`,
      note: 'Efficiency is judged by estimated power and consolidation pressure, not just CPU percentage.',
      tone: 'efficiency',
    },
    {
      label: 'Agent C admission',
      value: `queue ${esc(exp.queue_length ?? 0)} / pending ${esc(exp.pending_pods ?? 0)}`,
      baseline: `baseline pending ${esc(base.pending_pods ?? 0)} / unscheduled ${esc(baseSummary.unscheduled || 0)}`,
      note: 'Admission control is about preventing bad queue growth while preserving useful throughput.',
      tone: 'admission',
    },
    {
      label: 'Learning loop',
      value: `reward avg ${fmt(reward.average_total)} / last ${fmt(reward.last_total)}`,
      baseline: `Ray ${esc(ray.status || 'n/a')} / Optuna ${esc(optuna.completed_trials ?? 0)} trials`,
      note: 'This shows whether policy/reward adaptation is active; HPA has no comparable learned policy state.',
      tone: 'learning',
    },
    {
      label: 'Experiment fidelity',
      value: stimulus.title,
      baseline: stimulus.detail,
      note: 'The same intentional perturbation must be mirrored to both clusters; only controller reactions should differ.',
      tone: 'fidelity',
    },
  ];
  target.innerHTML = objectives.map(item => `
    <article class="objective-card ${item.tone}">
      <span>${esc(item.label)}</span>
      <strong class="outcome-badge ${objectiveStatus(item.tone, payload)[1]}">${esc(objectiveStatus(item.tone, payload)[0])}</strong>
      <b>${esc(item.value)}</b>
      <em>${esc(item.baseline)}</em>
      <small>${esc(item.note)}</small>
    </article>
  `).join('');
}
function renderAgentGoalMatrix(payload) {
  const target = $('agentGoalMatrix');
  if (!target) return;
  const exp = payload.experimental || {};
  const base = payload.baseline || {};
  const decision = exp.decision || {};
  const rewards = exp.reward_summary?.last_by_agent || {};
  const baseSummary = base.pod_summary || {};
  const hpa = hpaReaction(base);
  const rows = [
    {
      agent: 'Agent A',
      role: 'Safety / risk mitigator',
      goal: 'Keep tasks alive under high node failure risk.',
      trigger: 'risk >= 0.5 throttle, >= 0.7 migrate, >= 0.83 replicate',
      signal: `max risk ${fmt(exp.max_risk)} on ${esc(exp.max_risk_node || 'n/a')}; SLA ${esc(exp.sla_violations ?? 0)}`,
      proposal: proposalSummary(decision, 'AgentA'),
      selected: selectedSummary(decision, 'AgentA'),
      reward: fmt(rewards.AgentA),
      baseline: `reactive evidence: failed pods ${(baseSummary.phase_counts || {}).Failed || 0}, restarts ${baseSummary.restarts || 0}`,
      tone: 'safety',
    },
    {
      agent: 'Agent B',
      role: 'Efficiency / energy optimizer',
      goal: 'Reduce waste through DVFS, memory ballooning, and power-state decisions.',
      trigger: 'low demand selects sleep, DVFS, or memory balloon before wasting active capacity',
      signal: `min demand ${fmt(exp.min_demand)} on ${esc(exp.min_demand_node || 'n/a')}; estimated power ${fmt(exp.energy_watts, 1)}W`,
      proposal: proposalSummary(decision, 'AgentB'),
      selected: selectedSummary(decision, 'AgentB'),
      reward: fmt(rewards.AgentB),
      baseline: `${hpa.label}; local Karpenter ${esc(base.karpenter?.active_nodes ?? 'n/a')} active / ${esc(base.karpenter?.warm_nodes ?? 'n/a')} warm`,
      tone: 'efficiency',
    },
    {
      agent: 'Agent C',
      role: 'Admission / queue gatekeeper',
      goal: 'Avoid saturation by admitting, queueing, deprioritizing, rejecting, or capping work.',
      trigger: 'queue >= 8 queues, >= 80 deprioritizes, >= 120 applies resource cap',
      signal: `queue ${esc(exp.queue_length ?? 0)}; pending ${esc(exp.pending_pods ?? 0)}; completed ${esc(exp.completed_tasks ?? 0)}`,
      proposal: proposalSummary(decision, 'AgentC'),
      selected: selectedSummary(decision, 'AgentC'),
      reward: fmt(rewards.AgentC),
      baseline: `pending ${esc(base.pending_pods ?? 0)} / unscheduled ${esc(baseSummary.unscheduled || 0)}; HPA handles replicas, not admission policy`,
      tone: 'admission',
    },
  ];
  target.innerHTML = rows.map(row => `
    <article class="agent-goal-row ${row.tone}">
      <div class="agent-title">
        <span>${esc(row.role)}</span>
        <b>${esc(row.agent)}</b>
      </div>
      <div><span>Goal</span><p>${esc(row.goal)}</p></div>
      <div><span>Trigger logic</span><p>${esc(row.trigger)}</p></div>
      <div><span>Live signal</span><p>${esc(row.signal)}</p></div>
      <div><span>Proposal</span><p>${esc(row.proposal)}</p></div>
      <div><span>Current control</span><p>${esc(row.selected)} / reward ${esc(row.reward)}</p></div>
      <div><span>Baseline analogue</span><p>${esc(row.baseline)}</p></div>
    </article>
  `).join('');
}
function renderReactions(exp, base) {
  const decision = exp.decision || {};
  const stimulus = window.latestPayload?.shared_stimulus || {};
  const mirrorCount = stimulus.mirror_count ?? (stimulus.mirrors || []).length ?? 0;
  const proposals = (decision.proposals || []).map(item => `<span class="pill">${esc(item.agent)} ${esc(item.kind)} score ${fmt(item.score)}</span>`).join('');
  const reward = exp.reward_summary || {};
  const ray = exp.ray || {}, optuna = exp.optuna || {};
  const hpa = hpaReaction(base);
  $('reactionPanel').innerHTML = `
    <article class="reaction-card"><span>shared intentional stimulus</span><b>${esc(stimulus.phase || stimulus.message || 'n/a')}</b><small>${esc(stimulus.namespace || 'no namespace')} / operation ${esc(stimulus.operation || 'n/a')} / mirrored clusters ${esc(mirrorCount)}</small></article>
    <article class="reaction-card"><span>experimental decision</span><b>${esc(exp.last_decision || 'n/a')}</b><small>${esc(decision.reason || 'no reason recorded')}</small><div class="pill-row">${proposals || '<span class="pill">no proposals</span>'}</div></article>
    <article class="reaction-card"><span>experimental learning</span><b>Ray ${esc(ray.status || 'n/a')} / Optuna ${esc(optuna.status || 'n/a')}</b><small>reward avg ${fmt(reward.average_total)} / last ${fmt(reward.last_total)} / count ${esc(reward.count || 0)}</small></article>
    <article class="reaction-card hpa-${esc(hpa.state)}"><span>baseline reaction</span><b>${esc(hpa.label)}</b><small>${esc(hpa.detail)} / local Karpenter ${esc(base.karpenter?.active_nodes ?? 'n/a')} active workers / ${esc(base.karpenter?.warm_nodes ?? 'n/a')} warm workers</small></article>
  `;
}
function render(payload) {
  window.latestPayload = payload;
  const exp = payload.experimental || {};
  const base = payload.baseline || {};
  const karp = base.karpenter || {};
  const hpa = hpaReaction(base);
  const expRes = exp.resource_totals || {}, baseRes = base.resource_totals || {};
  $('updatedAt').textContent = new Date().toLocaleTimeString();
  const serverHistory = Array.isArray(payload.history) ? payload.history : [];
  $('sampleCount').textContent = `${serverHistory.length || historyRows.length + 1} samples`;
  $('experimentalRole').textContent = exp.role || 'experimental';
  $('baselineRole').textContent = base.role || 'baseline';
  $('experimentalMetrics').innerHTML = metricHtml([
    ['nodes', `${exp.ready_nodes ?? 0}/${exp.nodes ?? 0}`], ['workers', `${exp.ready_workers ?? 0}/${exp.worker_nodes ?? 0}`], ['pending', exp.pending_pods], ['CPU used', pct(expRes.usage_cpu_percent)], ['mem used', pct(expRes.usage_memory_percent)], ['reward', fmt(exp.last_reward)], ['stage', exp.active_stage || 'n/a'], ['status', exp.orchestrator_status || 'n/a']
  ]);
  $('baselineMetrics').innerHTML = metricHtml([
    ['nodes', `${base.ready_nodes ?? 0}/${base.nodes ?? 0}`], ['workers', `${base.ready_workers ?? 0}/${base.worker_nodes ?? 0}`], ['pending', base.pending_pods], ['CPU used', pct(baseRes.usage_cpu_percent)], ['mem used', pct(baseRes.usage_memory_percent)], ['HPA objects', (base.hpa || []).length], ['active nodes', karp.active_nodes], ['warm nodes', karp.warm_nodes]
  ]);
  $('experimentalRisk').textContent = fmt(exp.max_risk);
  $('experimentalDecision').textContent = compactAction(exp.last_decision);
  $('experimentalDecision').title = exp.last_decision || 'n/a';
  const baselineController = $('baselineController');
  if (baselineController) {
    baselineController.textContent = 'HPA + local Karpenter';
    baselineController.title = hpa.detail;
  }
  $('baselineWarm').textContent = `${karp.active_nodes ?? 'n/a'} active / ${karp.warm_nodes ?? 'n/a'} warm`;
  renderObjectiveEvidence(payload);
  renderAgentGoalMatrix(payload);
  renderReactions(exp, base);
  $('notes').textContent = (payload.notes || []).join(' ');
  const errors = [...(exp.errors || []), ...(base.errors || [])];
  $('errors').textContent = errors.length ? `API/metrics warnings: ${errors.join(' | ')}` : '';
  if (!serverHistory.length) {
    historyRows.push({
      time: new Date().toISOString(),
      experimentalPending: exp.pending_pods || 0,
      baselinePending: base.pending_pods || 0,
      experimentalQueue: exp.queue_length || 0,
      experimentalRisk: exp.max_risk || 0,
      experimentalSla: exp.sla_violations || 0,
      experimentalEnergy: exp.energy_watts || 0,
      experimentalReward: exp.last_reward || 0,
      experimentalMinDemand: exp.min_demand || 0,
      experimentalSchedulable: exp.schedulable_nodes || 0,
      baselineSchedulable: base.schedulable_nodes || 0,
      experimentalCpu: expRes.usage_cpu_percent || 0,
      baselineCpu: baseRes.usage_cpu_percent || 0,
      experimentalMem: expRes.usage_memory_percent || 0,
      baselineMem: baseRes.usage_memory_percent || 0,
    });
    if (historyRows.length > 7200) historyRows.shift();
  }
  const chartHistory = serverHistory.length ? serverHistory : historyRows;
  const pressureHistory = pressureWindowRows(chartHistory);
  const first = pressureHistory[0], last = pressureHistory[pressureHistory.length - 1];
  $('timelineWindow').textContent = pressureHistory.length
    ? `Showing ${pressureHistory.length} samples from the past 5 minutes (${displayTime(first.time)} to ${displayTime(last.time)}); ${chartHistory.length} retained total samples remain available while the server runs.`
    : 'waiting for comparison samples';
  drawCharts(payload, pressureHistory);
}
async function tick() {
  try {
    const res = await fetch('/api/comparison', { cache:'no-store' });
    render(await res.json());
  } catch (err) {
    console.error(err);
    $('errors').textContent = `dashboard fetch failed: ${err}`;
  }
}
window.addEventListener('resize', () => { if (window.latestPayload || latest()) tick(); });
tick();
setInterval(tick, 2500);
