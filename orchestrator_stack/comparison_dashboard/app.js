const $ = (id) => document.getElementById(id);
const historyRows = [];
const palette = {
  experimental: '#16835f', baseline: '#d48a20', blue: '#2f6f9f', red: '#b44634', ink: '#10201a', muted: '#65756e', grid: 'rgba(16,32,26,.14)', panel: 'rgba(255,255,255,.58)'
};
const phaseColors = { Running:'#16835f', Pending:'#d48a20', Succeeded:'#2f6f9f', Failed:'#b44634', Unknown:'#65756e' };
const PRESSURE_TIMELINE_WINDOW_MS = 5 * 60 * 1000;

function esc(value) { return String(value ?? 'n/a').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch])); }
function num(value) { const n = Number(value); return Number.isFinite(n) ? n : null; }
function fmt(value, digits = 3) { const n = num(value); return n === null ? 'n/a' : n.toFixed(digits); }
function intFmt(value) { const n = num(value); return n === null ? 'n/a' : String(Math.round(n)); }
function pct(value) { const n = num(value); return n === null ? 'n/a' : `${n.toFixed(1)}%`; }
function pctPoints(value) { const n = num(value); return n === null ? 'n/a' : `${n >= 0 ? '+' : ''}${n.toFixed(1)} pts`; }
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
function metricHtml(rows) { return rows.map(([k, v]) => `<div><b>${esc(v)}</b><span>${esc(k)}</span></div>`).join(''); }
function valueClass(value) { const n = num(value); if (n === null || Math.abs(n) < 0.001) return 'delta-neutral'; return n > 0 ? 'delta-positive' : 'delta-negative'; }
function topEntries(obj, limit = 7) { return Object.entries(obj || {}).sort((a,b) => Number(b[1]) - Number(a[1]) || a[0].localeCompare(b[0])).slice(0, limit); }
function latest() { return historyRows[historyRows.length - 1] || {}; }
function compactAction(value) {
  const text = String(value || 'n/a');
  const parts = text.split(':');
  if (parts.length >= 3) return `${parts[0]}:${parts[2]}`;
  return text;
}
function compactNamespace(value) {
  const text = String(value || 'unknown');
  return text
    .replace('borg-orchestrator-exercise', 'borg-exercise')
    .replace('borg-comparison-workload', 'comparison-workload')
    .replace('local-path-storage', 'local-path');
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
  const left = 68, right = 86, top = 24, bottom = 50, gap = 34;
  const plotW = w - left - right;
  const panelH = (h - top - bottom - gap * 2) / 3;
  const panels = [
    {
      title: 'Backlog pressure',
      unit: 'pending pods',
      side: 'left',
      y: top,
      series: [
        { key:'experimentalPending', color:palette.experimental, label:'experimental pending pods', width:3 },
        { key:'baselinePending', color:palette.baseline, label:'baseline pending pods', width:3 },
      ],
      maxFloor: 5,
    },
    {
      title: 'Resource utilization',
      unit: 'percent',
      side: 'right',
      y: top + panelH + gap,
      series: [
        { key:'experimentalCpu', color:palette.blue, label:'experimental CPU %' },
        { key:'baselineCpu', color:palette.red, label:'baseline CPU %' },
        { key:'experimentalMem', color:'#72b79b', label:'experimental memory %' },
        { key:'baselineMem', color:'#e0a64d', label:'baseline memory %' },
      ],
      maxFloor: 10,
    },
    {
      title: 'Baseline HPA replica state',
      unit: 'replicas',
      side: 'right',
      y: top + (panelH + gap) * 2,
      series: [
        { key:'baselineHpaCurrent', color:'#111f1a', label:'baseline HPA current replicas', width:2.8, stepped:true },
        { key:'baselineHpaDesired', color:'#8d6d2d', label:'baseline HPA desired replicas', width:2.8, dash:[8, 6], stepped:true },
        { key:'baselineHpaMax', color:'rgba(16,32,26,.28)', label:'baseline HPA max replicas', width:1.8, dash:[2, 6], stepped:true },
      ],
      maxFloor: 5,
    },
  ];

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
    const bottomPanel = { x:left, y:top + (panelH + gap) * 2, w:plotW, h:panelH };
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
function drawLineChart(canvasId, series, label, sourceRows) {
  const canvas = $(canvasId); if (!canvas) return;
  const { ctx, w, h } = setupCanvas(canvas);
  const pad = { left: 58, right: 26, top: 24, bottom: 42 };
  const allRows = Array.isArray(sourceRows) ? sourceRows : historyRows;
  const rows = downsample(allRows);
  const values = rows.flatMap(row => series.map(item => num(row[item.key]))).filter(v => v !== null);
  const max = Math.max(1, ...values) * 1.12;
  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;
  const yFor = value => h - pad.bottom - (Number(value || 0) / max) * plotH;
  const xFor = index => rows.length <= 1 ? pad.left + plotW / 2 : pad.left + (index / (rows.length - 1)) * plotW;
  axes(ctx, w, h, pad, max, label);
  if (rows.length) {
    const ticks = [0, Math.floor((rows.length - 1) / 2), rows.length - 1];
    ctx.fillStyle = 'rgba(16,32,26,.58)';
    ctx.font = '11px Avenir Next, sans-serif';
    ticks.forEach(index => {
      const row = rows[index];
      const x = xFor(index);
      ctx.textAlign = index === 0 ? 'left' : index === rows.length - 1 ? 'right' : 'center';
      ctx.fillText(displayTime(row.time), x, h - 28);
    });
  }
  series.forEach(item => {
    ctx.strokeStyle = item.color;
    ctx.lineWidth = item.width || 2.6;
    ctx.setLineDash(item.dash || []);
    ctx.beginPath();
    rows.forEach((row, index) => {
      const x = xFor(index), y = yFor(row[item.key]);
      if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  });
  $('timelineLegend').innerHTML = series.map(item => `<span><b style="color:${item.color}">■</b> ${esc(item.label)}</span>`).join('');
}
function resourcePercent(used, allocatable) {
  const u = num(used), a = num(allocatable);
  return u === null || a === null || a <= 0 ? null : (u / a) * 100;
}
function resourceMetric(label, value, unit, percent, color) {
  const width = percent === null ? 0 : Math.max(0, Math.min(100, percent));
  return `
    <div class="resource-row">
      <div>
        <span>${esc(label)}</span>
        <b>${fmt(value, 1)}${esc(unit)}</b>
      </div>
      <em>${pct(percent)}</em>
      <i><strong style="width:${width}%;background:${esc(color)}"></strong></i>
    </div>
  `;
}
function resourceClusterCard(label, cluster, tone) {
  const res = cluster.resource_totals || {};
  const pod = cluster.pod_summary || {};
  const cpuUsedPct = num(res.usage_cpu_percent) ?? resourcePercent(res.usage_cpu_m, res.allocatable_cpu_m);
  const memUsedPct = num(res.usage_memory_percent) ?? resourcePercent(res.usage_memory_mi, res.allocatable_memory_mi);
  const cpuReqPct = num(pod.request_cpu_percent) ?? resourcePercent(pod.request_cpu_m, res.allocatable_cpu_m);
  const memReqPct = num(pod.request_memory_percent) ?? resourcePercent(pod.request_memory_mi, res.allocatable_memory_mi);
  return `
    <article class="resource-card ${tone}">
      <header>
        <span>${esc(label)}</span>
        <b>${esc(cluster.running_pods ?? 0)} running pods</b>
      </header>
      ${resourceMetric('CPU used', res.usage_cpu_m, 'm', cpuUsedPct, tone === 'experimental' ? palette.experimental : palette.baseline)}
      ${resourceMetric('Memory used', res.usage_memory_mi, 'Mi', memUsedPct, tone === 'experimental' ? palette.blue : palette.red)}
      ${resourceMetric('CPU requested', pod.request_cpu_m, 'm', cpuReqPct, tone === 'experimental' ? '#72b79b' : '#e0a64d')}
      ${resourceMetric('Memory requested', pod.request_memory_mi, 'Mi', memReqPct, tone === 'experimental' ? '#6298bd' : '#c96957')}
    </article>
  `;
}
function renderResourceMix(payload) {
  $('resourceMixPanel').innerHTML = `
    ${resourceClusterCard('Experimental', payload.experimental || {}, 'experimental')}
    ${resourceClusterCard('Baseline', payload.baseline || {}, 'baseline')}
  `;
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
  const pad = { left: Math.min(210, Math.max(148, w * 0.34)), right: 34, top: 24, bottom: 24 };
  const rowH = (h - pad.top - pad.bottom) / Math.max(1, keys.length);
  keys.forEach((key, i) => {
    const y = pad.top + i * rowH + 5;
    const expVal = Number(payload.experimental?.pod_summary?.namespace_counts?.[key] || 0);
    const baseVal = Number(payload.baseline?.pod_summary?.namespace_counts?.[key] || 0);
    ctx.fillStyle = palette.muted; ctx.font = '12px Avenir Next, sans-serif'; ctx.textAlign = 'right'; ctx.fillText(compactNamespace(key), pad.left - 12, y + 16, pad.left - 24);
    ctx.fillStyle = palette.experimental; ctx.fillRect(pad.left, y, (w - pad.left - pad.right) * expVal / max, 12);
    ctx.fillStyle = palette.baseline; ctx.fillRect(pad.left, y + 16, (w - pad.left - pad.right) * baseVal / max, 12);
  });
  ctx.fillStyle = palette.experimental; ctx.fillText('■ experimental', pad.left, h - 8);
  ctx.fillStyle = palette.baseline; ctx.fillText('■ baseline', pad.left + 124, h - 8);
}
function drawCharts(payload, chartHistory) {
  drawPressureTimeline('timelineCanvas', chartHistory);
  renderResourceMix(payload);
  renderCapacityPanel(payload);
  drawPhase(payload);
  drawNamespace(payload);
}

function renderScorecards(payload) {
  $('scorecards').innerHTML = (payload.scorecards || []).map(card => `
    <article class="score-card">
      <span>${esc(card.label)}</span>
      <div class="score-values">
        <div><span>experimental</span><b title="${esc(card.experimental)}">${esc(card.label === 'Replica reaction' ? compactAction(card.experimental) : card.experimental)}</b></div>
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
  const reaction = hpaReaction(base);
  $('hpaTable').innerHTML = (base.hpa || []).map(item => `
    <div><span>${esc(item.namespace)}/${esc(item.name)}</span><b>target ${esc(item.target)} / replicas ${esc(item.current)} -> ${esc(item.desired)} / min ${esc(item.min)} max ${esc(item.max)} / cpu ${esc(item.cpu_utilization ?? 'n/a')}% target ${esc(item.target_cpu_utilization ?? 'n/a')}% / last scale ${esc(item.last_scale_time || 'n/a')}</b></div>
  `).join('') || '<div><span>hpa</span><b>not installed or not ready</b></div>';
  $('karpenterState').innerHTML = [
    `<div><span>hpa mode</span><b>${esc(reaction.label)} / ${esc(reaction.detail)}</b></div>`,
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
  $('baselineHpa').textContent = hpa.label;
  $('baselineHpa').title = hpa.detail;
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
  if (!serverHistory.length) {
    historyRows.push({
      time: new Date().toISOString(),
      experimentalPending: exp.pending_pods || 0,
      baselinePending: base.pending_pods || 0,
      experimentalSchedulable: exp.schedulable_nodes || 0,
      baselineSchedulable: base.schedulable_nodes || 0,
      experimentalCpu: expRes.usage_cpu_percent || 0,
      baselineCpu: baseRes.usage_cpu_percent || 0,
      experimentalMem: expRes.usage_memory_percent || 0,
      baselineMem: baseRes.usage_memory_percent || 0,
      baselineHpaCurrent: hpa.current || 0,
      baselineHpaDesired: hpa.desired || 0,
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
