const $ = (id) => document.getElementById(id);
const historyRows = [];
const palette = {
  experimental: '#16835f', baseline: '#d48a20', blue: '#2f6f9f', red: '#b44634', ink: '#10201a', muted: '#65756e', grid: 'rgba(16,32,26,.14)', panel: 'rgba(255,255,255,.58)'
};
const phaseColors = { Running:'#16835f', Pending:'#d48a20', Succeeded:'#2f6f9f', Failed:'#b44634', Unknown:'#65756e' };

function esc(value) { return String(value ?? 'n/a').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch])); }
function num(value) { const n = Number(value); return Number.isFinite(n) ? n : null; }
function fmt(value, digits = 3) { const n = num(value); return n === null ? 'n/a' : n.toFixed(digits); }
function intFmt(value) { const n = num(value); return n === null ? 'n/a' : String(Math.round(n)); }
function pct(value) { const n = num(value); return n === null ? 'n/a' : `${n.toFixed(1)}%`; }
function pctPoints(value) { const n = num(value); return n === null ? 'n/a' : `${n >= 0 ? '+' : ''}${n.toFixed(1)} pts`; }
function hpaDesired(cluster) { return (cluster.hpa || []).reduce((sum, item) => sum + Number(item.desired ?? item.current ?? item.min ?? 0), 0); }
function hpaCurrent(cluster) { return (cluster.hpa || []).reduce((sum, item) => sum + Number(item.current ?? 0), 0); }
function metricHtml(rows) { return rows.map(([k, v]) => `<div><b>${esc(v)}</b><span>${esc(k)}</span></div>`).join(''); }
function valueClass(value) { const n = num(value); if (n === null || Math.abs(n) < 0.001) return 'delta-neutral'; return n > 0 ? 'delta-positive' : 'delta-negative'; }
function topEntries(obj, limit = 7) { return Object.entries(obj || {}).sort((a,b) => Number(b[1]) - Number(a[1]) || a[0].localeCompare(b[0])).slice(0, limit); }
function latest() { return historyRows[historyRows.length - 1] || {}; }

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
function axes(ctx, w, h, pad, max, label) {
  ctx.clearRect(0,0,w,h);
  ctx.fillStyle = 'rgba(255,255,255,.48)';
  ctx.fillRect(pad.left, pad.top, w - pad.left - pad.right, h - pad.top - pad.bottom);
  ctx.strokeStyle = palette.grid;
  ctx.fillStyle = 'rgba(16,32,26,.62)';
  ctx.font = '12px Avenir Next, sans-serif';
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (i / 4) * (h - pad.top - pad.bottom);
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
    ctx.textAlign = 'right'; ctx.fillText((max - (i / 4) * max).toFixed(1), pad.left - 8, y + 4);
  }
  ctx.textAlign = 'center'; ctx.fillText(label, pad.left + (w - pad.left - pad.right) / 2, h - 12);
}
function drawLineChart(canvasId, series, label) {
  const canvas = $(canvasId); if (!canvas) return;
  const { ctx, w, h } = setupCanvas(canvas);
  const pad = { left: 58, right: 26, top: 24, bottom: 42 };
  const rows = historyRows.slice(-120);
  const values = rows.flatMap(row => series.map(item => num(row[item.key]))).filter(v => v !== null);
  const max = Math.max(1, ...values) * 1.12;
  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;
  const yFor = value => h - pad.bottom - (Number(value || 0) / max) * plotH;
  const xFor = index => rows.length <= 1 ? pad.left + plotW / 2 : pad.left + (index / (rows.length - 1)) * plotW;
  axes(ctx, w, h, pad, max, label);
  series.forEach(item => {
    ctx.strokeStyle = item.color;
    ctx.lineWidth = item.width || 2.6;
    ctx.beginPath();
    rows.forEach((row, index) => {
      const x = xFor(index), y = yFor(row[item.key]);
      if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  });
  $('timelineLegend').innerHTML = series.map(item => `<span><b style="color:${item.color}">■</b> ${esc(item.label)}</span>`).join('');
}
function drawDonut(ctx, cx, cy, radius, values, colors, label, sublabel) {
  const total = values.reduce((sum, value) => sum + Math.max(0, Number(value) || 0), 0) || 1;
  let start = -Math.PI / 2;
  values.forEach((value, index) => {
    const angle = (Math.max(0, Number(value) || 0) / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, start, start + angle);
    ctx.lineWidth = radius * 0.28;
    ctx.strokeStyle = colors[index];
    ctx.stroke();
    start += angle;
  });
  ctx.fillStyle = palette.ink;
  ctx.font = `800 ${Math.max(13, Math.min(17, radius * 0.27))}px Avenir Next, sans-serif`;
  ctx.textAlign = 'center';
  ctx.fillText(label, cx, cy - 4, radius * 1.65);
  ctx.fillStyle = palette.muted;
  ctx.font = `700 ${Math.max(10, Math.min(12, radius * 0.19))}px Avenir Next, sans-serif`;
  ctx.fillText(sublabel, cx, cy + 18, radius * 1.85);
}
function drawResourcePie(payload) {
  const { ctx, w, h } = setupCanvas($('resourcePieCanvas'));
  ctx.clearRect(0,0,w,h);
  const exp = payload.experimental || {}, base = payload.baseline || {};
  const expRes = exp.resource_totals || {}, baseRes = base.resource_totals || {};
  const compact = w < 440;
  const radius = compact ? Math.max(38, Math.min(54, w * 0.13, h * 0.13)) : Math.max(46, Math.min(68, w * 0.14, h * 0.17));
  const centers = compact
    ? [[w * 0.50, 78], [w * 0.50, 198]]
    : [[w * 0.30, 118], [w * 0.70, 118]];
  drawDonut(ctx, centers[0][0], centers[0][1], radius, [expRes.usage_cpu_m, expRes.usage_memory_mi], [palette.experimental, palette.blue], 'Experimental', compact ? '' : 'CPU m / memory Mi');
  drawDonut(ctx, centers[1][0], centers[1][1], radius, [baseRes.usage_cpu_m, baseRes.usage_memory_mi], [palette.baseline, palette.red], 'Baseline', compact ? '' : 'CPU m / memory Mi');
  if (compact) {
    ctx.fillStyle = palette.muted;
    ctx.font = '700 11px Avenir Next, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('CPU m / memory Mi', centers[0][0], centers[0][1] + radius + 24, radius * 2.4);
    ctx.fillText('CPU m / memory Mi', centers[1][0], centers[1][1] + radius + 24, radius * 2.4);
  }
  const rows = [
    ['Experimental CPU', `${fmt(expRes.usage_cpu_m, 1)}m`, palette.experimental],
    ['Experimental Memory', `${fmt(expRes.usage_memory_mi, 1)}Mi`, palette.blue],
    ['Baseline CPU', `${fmt(baseRes.usage_cpu_m, 1)}m`, palette.baseline],
    ['Baseline Memory', `${fmt(baseRes.usage_memory_mi, 1)}Mi`, palette.red],
  ];
  const legendTop = compact ? Math.min(h - 92, 260) : Math.max(220, h - 94);
  const colW = compact ? w - 44 : (w - 62) / 2;
  ctx.textAlign = 'left';
  ctx.font = '700 12px Avenir Next, sans-serif';
  rows.forEach((row, i) => {
    const col = compact ? 0 : i % 2;
    const line = compact ? i : Math.floor(i / 2);
    const x = 22 + col * (colW + 18);
    const y = legendTop + line * 28;
    ctx.fillStyle = row[2];
    ctx.fillText('■', x, y);
    ctx.fillStyle = palette.muted;
    ctx.fillText(`${row[0]} ${row[1]}`, x + 20, y, colW - 20);
  });
}
function pressureLabel(value) {
  const n = num(value);
  if (n === null) return ['unknown', 'capacity-unknown'];
  if (n >= 85) return ['critical', 'capacity-hot'];
  if (n >= 60) return ['watch', 'capacity-watch'];
  return ['headroom', 'capacity-safe'];
}
function gaugeHtml(value, color) {
  const n = num(value);
  const width = n === null ? 0 : Math.max(0, Math.min(100, n));
  return `<div class="capacity-bar"><i style="width:${width}%;background:${esc(color)}"></i></div>`;
}
function capacityCellHtml(label, value, color) {
  const [stateLabel, stateClass] = pressureLabel(value);
  return `
    <div class="capacity-cell ${stateClass}">
      <span>${esc(label)}</span>
      <b>${pct(value)}</b>
      ${gaugeHtml(value, color)}
      <em>${esc(stateLabel)}</em>
    </div>
  `;
}
function renderCapacityPanel(payload) {
  const exp = payload.experimental || {}, base = payload.baseline || {};
  const expPod = exp.pod_summary || {}, basePod = base.pod_summary || {};
  const expRes = exp.resource_totals || {}, baseRes = base.resource_totals || {};
  const rows = [
    {
      title: 'CPU request pressure',
      explainer: 'Scheduler demand before live usage: requested CPU as a share of allocatable CPU.',
      exp: expPod.request_cpu_percent,
      base: basePod.request_cpu_percent,
      expColor: palette.experimental,
      baseColor: palette.baseline,
    },
    {
      title: 'Memory request pressure',
      explainer: 'Declared memory pressure before pods become pending or are rejected.',
      exp: expPod.request_memory_percent,
      base: basePod.request_memory_percent,
      expColor: palette.blue,
      baseColor: palette.red,
    },
    {
      title: 'Live CPU usage',
      explainer: 'Actual usage from Metrics Server, separated from scheduler requests.',
      exp: expRes.usage_cpu_percent,
      base: baseRes.usage_cpu_percent,
      expColor: '#72b79b',
      baseColor: '#e0a64d',
    },
  ];
  $('capacityPanel').innerHTML = rows.map(row => {
    const delta = num(row.exp) === null || num(row.base) === null ? null : num(row.exp) - num(row.base);
    const leader = delta === null ? 'insufficient telemetry' : delta > 0 ? 'experimental higher' : delta < 0 ? 'baseline higher' : 'matched';
    return `
      <article class="capacity-row">
        <header>
          <span>${esc(row.title)}</span>
          <b>${esc(leader)}</b>
        </header>
        <div class="capacity-pair">
          ${capacityCellHtml('Experimental', row.exp, row.expColor)}
          ${capacityCellHtml('Baseline', row.base, row.baseColor)}
        </div>
        <footer>
          <b class="${valueClass(delta)}">${pctPoints(delta)}</b>
          <small>${esc(row.explainer)}</small>
        </footer>
      </article>
    `;
  }).join('');
}
function drawPhase(payload) {
  const { ctx, w, h } = setupCanvas($('phaseCanvas'));
  ctx.clearRect(0,0,w,h);
  const clusters = [['Experimental', payload.experimental], ['Baseline', payload.baseline]];
  const phases = ['Running', 'Pending', 'Succeeded', 'Failed', 'Unknown'];
  const max = Math.max(1, ...clusters.map(([, cluster]) => phases.reduce((sum, phase) => sum + Number(cluster?.pod_summary?.phase_counts?.[phase] || 0), 0)));
  const baseY = h - 54;
  const barW = Math.min(120, w * .20);
  clusters.forEach(([label, cluster], index) => {
    const x = w * (.32 + index * .36) - barW / 2;
    let y = baseY;
    phases.forEach(phase => {
      const value = Number(cluster?.pod_summary?.phase_counts?.[phase] || 0);
      const segment = (value / max) * (h - 108);
      y -= segment;
      ctx.fillStyle = phaseColors[phase]; ctx.fillRect(x, y, barW, segment);
    });
    ctx.fillStyle = palette.ink; ctx.textAlign = 'center'; ctx.font = '700 16px Avenir Next, sans-serif'; ctx.fillText(label, x + barW / 2, h - 24);
  });
  ctx.textAlign = 'left'; ctx.font = '12px Avenir Next, sans-serif';
  phases.forEach((phase, i) => { ctx.fillStyle = phaseColors[phase]; ctx.fillText('■', 18, 26 + i * 18); ctx.fillStyle = palette.muted; ctx.fillText(phase, 36, 26 + i * 18); });
}
function drawNamespace(payload) {
  const { ctx, w, h } = setupCanvas($('namespaceCanvas'));
  ctx.clearRect(0,0,w,h);
  const expEntries = topEntries(payload.experimental?.pod_summary?.namespace_counts, 5);
  const baseEntries = topEntries(payload.baseline?.pod_summary?.namespace_counts, 5);
  const keys = Array.from(new Set([...expEntries, ...baseEntries].map(([key]) => key))).slice(0, 7);
  const max = Math.max(1, ...keys.flatMap(key => [payload.experimental?.pod_summary?.namespace_counts?.[key] || 0, payload.baseline?.pod_summary?.namespace_counts?.[key] || 0]));
  const pad = { left: 138, right: 34, top: 24, bottom: 24 };
  const rowH = (h - pad.top - pad.bottom) / Math.max(1, keys.length);
  keys.forEach((key, i) => {
    const y = pad.top + i * rowH + 5;
    const expVal = Number(payload.experimental?.pod_summary?.namespace_counts?.[key] || 0);
    const baseVal = Number(payload.baseline?.pod_summary?.namespace_counts?.[key] || 0);
    ctx.fillStyle = palette.muted; ctx.font = '12px Avenir Next, sans-serif'; ctx.textAlign = 'right'; ctx.fillText(key, pad.left - 12, y + 16);
    ctx.fillStyle = palette.experimental; ctx.fillRect(pad.left, y, (w - pad.left - pad.right) * expVal / max, 12);
    ctx.fillStyle = palette.baseline; ctx.fillRect(pad.left, y + 16, (w - pad.left - pad.right) * baseVal / max, 12);
  });
  ctx.fillStyle = palette.experimental; ctx.fillText('■ experimental', pad.left, h - 8);
  ctx.fillStyle = palette.baseline; ctx.fillText('■ baseline', pad.left + 124, h - 8);
}
function drawCharts(payload) {
  drawLineChart('timelineCanvas', [
    { key:'experimentalPending', color:palette.experimental, label:'experimental pending pods', width:3 },
    { key:'baselinePending', color:palette.baseline, label:'baseline pending pods', width:3 },
    { key:'experimentalCpu', color:palette.blue, label:'experimental CPU %' },
    { key:'baselineCpu', color:palette.red, label:'baseline CPU %' },
    { key:'experimentalMem', color:'#72b79b', label:'experimental memory %' },
    { key:'baselineMem', color:'#e0a64d', label:'baseline memory %' },
  ], 'live comparison samples');
  drawResourcePie(payload);
  renderCapacityPanel(payload);
  drawPhase(payload);
  drawNamespace(payload);
}

function renderScorecards(payload) {
  $('scorecards').innerHTML = (payload.scorecards || []).map(card => `
    <article class="score-card">
      <span>${esc(card.label)}</span>
      <div class="score-values">
        <div><span>experimental</span><b>${esc(card.experimental)}</b></div>
        <div><span>baseline</span><b>${esc(card.baseline)}</b></div>
      </div>
      <small>${esc(card.interpretation)}</small>
    </article>
  `).join('');
}
function renderLedger(payload) {
  $('differenceLedger').innerHTML = (payload.differences || []).map(row => `
    <article class="ledger-row">
      <span>${esc(row.metric)}</span>
      <b class="${valueClass(row.delta)}">${fmt(row.delta)}</b>
      <small>exp ${fmt(row.experimental)} / base ${fmt(row.baseline)}</small>
      <small>${esc(row.note)}</small>
    </article>
  `).join('');
}
function renderNodeTable(id, rows) {
  $(id).innerHTML = (rows || []).map(node => `
    <div>
      <span>${esc(node.name)}</span>
      <b>${esc(node.role)} / ready=${esc(node.ready)} / schedulable=${esc(!node.unschedulable)} / state=${esc(node.provisioning_state || 'direct')}<br>
      cpu ${fmt(node.usage_cpu_m, 1)}m used, ${fmt(node.allocatable_cpu_m, 0)}m allocatable (${pct(node.usage_cpu_percent)}) / memory ${fmt(node.usage_memory_mi, 1)}Mi used, ${fmt(node.allocatable_memory_mi, 0)}Mi allocatable (${pct(node.usage_memory_percent)})</b>
    </div>
  `).join('') || '<div><span>nodes</span><b>not visible</b></div>';
}
function renderWorkloads(exp, base) {
  const rows = [
    ...(exp.workloads || []).map(item => ({...item, cluster:'experimental'})),
    ...(base.workloads || []).map(item => ({...item, cluster:'baseline'})),
  ].slice(0, 28);
  $('workloadInventory').innerHTML = rows.map(item => `
    <div><span>${esc(item.cluster)} / ${esc(item.kind)}</span><b>${esc(item.namespace)}/${esc(item.name)} desired ${esc(item.desired)} ready ${esc(item.ready)} available ${esc(item.available)}</b></div>
  `).join('') || '<div><span>workloads</span><b>no workload objects discovered</b></div>';
}
function renderAutoscaling(base) {
  const karp = base.karpenter || {};
  $('hpaTable').innerHTML = (base.hpa || []).map(item => `
    <div><span>${esc(item.namespace)}/${esc(item.name)}</span><b>target ${esc(item.target)} / replicas ${esc(item.current)} -> ${esc(item.desired)} / min ${esc(item.min)} max ${esc(item.max)} / cpu ${esc(item.cpu_utilization ?? item.cpu_average_value ?? 'n/a')}</b></div>
  `).join('') || '<div><span>hpa</span><b>not installed or not ready</b></div>';
  $('karpenterState').innerHTML = [
    `<div><span>mode</span><b>${esc(karp.mode || 'n/a')}</b></div>`,
    `<div><span>last action</span><b>${esc((karp.actions || []).map(a => `${a.action}:${a.node}`).join(', ') || 'none')}</b></div>`,
    `<div><span>nodes</span><b>${esc((karp.nodes || []).map(n => `${n.name}:${n.state}`).join(', ') || 'n/a')}</b></div>`,
  ].join('');
}
function renderReactions(exp, base) {
  const decision = exp.decision || {};
  const stimulus = window.latestPayload?.shared_stimulus || {};
  const mirrorCount = stimulus.mirror_count ?? (stimulus.mirrors || []).length ?? 0;
  const proposals = (decision.proposals || []).map(item => `<span class="pill">${esc(item.agent)} ${esc(item.kind)} score ${fmt(item.score)}</span>`).join('');
  const reward = exp.reward_summary || {};
  const ray = exp.ray || {}, optuna = exp.optuna || {};
  $('reactionPanel').innerHTML = `
    <article class="reaction-card"><span>shared intentional stimulus</span><b>${esc(stimulus.phase || stimulus.message || 'n/a')}</b><small>${esc(stimulus.namespace || 'no namespace')} / operation ${esc(stimulus.operation || 'n/a')} / mirrored clusters ${esc(mirrorCount)}</small></article>
    <article class="reaction-card"><span>experimental decision</span><b>${esc(exp.last_decision || 'n/a')}</b><small>${esc(decision.reason || 'no reason recorded')}</small><div class="pill-row">${proposals || '<span class="pill">no proposals</span>'}</div></article>
    <article class="reaction-card"><span>experimental learning</span><b>Ray ${esc(ray.status || 'n/a')} / Optuna ${esc(optuna.status || 'n/a')}</b><small>reward avg ${fmt(reward.average_total)} / last ${fmt(reward.last_total)} / count ${esc(reward.count || 0)}</small></article>
    <article class="reaction-card"><span>baseline reaction</span><b>HPA ${hpaCurrent(base)} -> ${hpaDesired(base)} replicas</b><small>local Karpenter ${esc(base.karpenter?.active_nodes ?? 'n/a')} active workers / ${esc(base.karpenter?.warm_nodes ?? 'n/a')} warm workers</small></article>
  `;
}
function render(payload) {
  window.latestPayload = payload;
  const exp = payload.experimental || {};
  const base = payload.baseline || {};
  const karp = base.karpenter || {};
  const expRes = exp.resource_totals || {}, baseRes = base.resource_totals || {};
  $('updatedAt').textContent = new Date().toLocaleTimeString();
  $('sampleCount').textContent = `${historyRows.length + 1} samples`;
  $('experimentalRole').textContent = exp.role || 'experimental';
  $('baselineRole').textContent = base.role || 'baseline';
  $('experimentalMetrics').innerHTML = metricHtml([
    ['nodes', `${exp.ready_nodes ?? 0}/${exp.nodes ?? 0}`], ['workers', `${exp.ready_workers ?? 0}/${exp.worker_nodes ?? 0}`], ['pending', exp.pending_pods], ['CPU used', pct(expRes.usage_cpu_percent)], ['mem used', pct(expRes.usage_memory_percent)], ['reward', fmt(exp.last_reward)], ['stage', exp.active_stage || 'n/a'], ['status', exp.orchestrator_status || 'n/a']
  ]);
  $('baselineMetrics').innerHTML = metricHtml([
    ['nodes', `${base.ready_nodes ?? 0}/${base.nodes ?? 0}`], ['workers', `${base.ready_workers ?? 0}/${base.worker_nodes ?? 0}`], ['pending', base.pending_pods], ['CPU used', pct(baseRes.usage_cpu_percent)], ['mem used', pct(baseRes.usage_memory_percent)], ['HPA objects', (base.hpa || []).length], ['active nodes', karp.active_nodes], ['warm nodes', karp.warm_nodes]
  ]);
  $('experimentalRisk').textContent = fmt(exp.max_risk);
  $('experimentalDecision').textContent = exp.last_decision || 'n/a';
  $('baselineHpa').textContent = `${hpaCurrent(base)} -> ${hpaDesired(base)} replicas`;
  $('baselineWarm').textContent = `${karp.active_nodes ?? 'n/a'} active / ${karp.warm_nodes ?? 'n/a'} warm`;
  renderScorecards(payload);
  renderLedger(payload);
  renderNodeTable('experimentalNodes', exp.node_rows);
  renderNodeTable('baselineNodes', base.node_rows);
  renderWorkloads(exp, base);
  renderAutoscaling(base);
  renderReactions(exp, base);
  $('notes').textContent = (payload.notes || []).join(' ');
  const errors = [...(exp.errors || []), ...(base.errors || [])];
  $('errors').textContent = errors.length ? `API/metrics warnings: ${errors.join(' | ')}` : '';
  historyRows.push({
    experimentalPending: exp.pending_pods || 0,
    baselinePending: base.pending_pods || 0,
    experimentalNodes: exp.schedulable_nodes || 0,
    baselineNodes: base.schedulable_nodes || 0,
    experimentalCpu: expRes.usage_cpu_percent || 0,
    baselineCpu: baseRes.usage_cpu_percent || 0,
    experimentalMem: expRes.usage_memory_percent || 0,
    baselineMem: baseRes.usage_memory_percent || 0,
  });
  if (historyRows.length > 240) historyRows.shift();
  drawCharts(payload);
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
window.addEventListener('resize', () => { if (latest()) tick(); });
tick();
setInterval(tick, 2500);
