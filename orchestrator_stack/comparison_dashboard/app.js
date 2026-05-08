const $ = (id) => document.getElementById(id);
const historyRows = [];
function fmt(value) { const n = Number(value); return Number.isFinite(n) ? n.toFixed(3) : 'n/a'; }
function intFmt(value) { const n = Number(value); return Number.isFinite(n) ? String(n) : 'n/a'; }
function metricHtml(rows) { return rows.map(([k, v]) => `<div><b>${v ?? 'n/a'}</b><span>${k}</span></div>`).join(''); }
function hpaDesired(cluster) { return (cluster.hpa || []).reduce((sum, item) => sum + Number(item.desired ?? item.current ?? item.min ?? 0), 0); }
function draw() {
  const canvas = $('differenceCanvas');
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0,0,w,h);
  const pad = { left: 64, right: 28, top: 24, bottom: 44 };
  const plotW = w - pad.left - pad.right, plotH = h - pad.top - pad.bottom;
  const rows = historyRows.slice(-80);
  const series = [
    { key:'experimentalPending', color:'#16835f', label:'experimental pending pods' },
    { key:'baselinePending', color:'#d48a20', label:'baseline pending pods' },
    { key:'experimentalNodes', color:'#2f6f9f', label:'experimental schedulable nodes' },
    { key:'baselineNodes', color:'#b44634', label:'baseline schedulable nodes' },
  ];
  const values = rows.flatMap(row => series.map(s => Number(row[s.key]))).filter(Number.isFinite);
  const max = Math.max(1, ...values) * 1.12;
  const yFor = value => h - pad.bottom - (Number(value || 0) / max) * plotH;
  const xFor = index => rows.length <= 1 ? pad.left + plotW / 2 : pad.left + (index / (rows.length - 1)) * plotW;
  ctx.fillStyle = 'rgba(255,255,255,.46)'; ctx.fillRect(pad.left, pad.top, plotW, plotH);
  ctx.strokeStyle = 'rgba(16,29,24,.13)'; ctx.fillStyle = 'rgba(16,29,24,.62)'; ctx.font = '12px Avenir Next, sans-serif';
  for (let i=0; i<=4; i++) { const y = pad.top + (i/4)*plotH; ctx.beginPath(); ctx.moveTo(pad.left,y); ctx.lineTo(w-pad.right,y); ctx.stroke(); ctx.textAlign='right'; ctx.fillText((max - (i/4)*max).toFixed(1), pad.left-8, y+4); }
  series.forEach(s => { ctx.strokeStyle=s.color; ctx.lineWidth=3; ctx.beginPath(); rows.forEach((row,i)=>{ const x=xFor(i), y=yFor(row[s.key]); if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y); }); ctx.stroke(); });
  ctx.fillStyle = 'rgba(16,29,24,.76)'; ctx.textAlign='center'; ctx.fillText('comparison samples', pad.left + plotW/2, h-12);
  $('differenceLegend').innerHTML = series.map(s => `<span><b style="color:${s.color}">■</b> ${s.label}</span>`).join('');
}
function render(payload) {
  const exp = payload.experimental || {};
  const base = payload.baseline || {};
  const karp = base.karpenter || {};
  $('updatedAt').textContent = new Date().toLocaleTimeString();
  $('experimentalRole').textContent = exp.role || 'experimental';
  $('baselineRole').textContent = base.role || 'baseline';
  $('experimentalMetrics').innerHTML = metricHtml([
    ['nodes', `${exp.ready_nodes ?? 0}/${exp.nodes ?? 0}`], ['workers', `${exp.ready_workers ?? 0}/${exp.worker_nodes ?? 0}`], ['schedulable workers', exp.schedulable_nodes], ['pending', exp.pending_pods], ['reward', fmt(exp.last_reward)], ['avg reward', fmt(exp.avg_reward)], ['stage', exp.active_stage || 'n/a'], ['status', exp.orchestrator_status || 'n/a']
  ]);
  $('baselineMetrics').innerHTML = metricHtml([
    ['nodes', `${base.ready_nodes ?? 0}/${base.nodes ?? 0}`], ['workers', `${base.ready_workers ?? 0}/${base.worker_nodes ?? 0}`], ['schedulable workers', base.schedulable_nodes], ['pending', base.pending_pods], ['active nodes', karp.active_nodes], ['warm nodes', karp.warm_nodes], ['baseline pods', base.baseline_pods], ['HPA objects', (base.hpa || []).length]
  ]);
  $('experimentalRisk').textContent = fmt(exp.max_risk);
  $('experimentalDecision').textContent = exp.last_decision || 'n/a';
  $('baselineHpa').textContent = intFmt(hpaDesired(base));
  $('baselineWarm').textContent = intFmt(karp.warm_nodes);
  $('hpaTable').innerHTML = (base.hpa || []).map(item => `<div><span>${item.namespace}/${item.name}</span><b>current ${item.current ?? 'n/a'} / desired ${item.desired ?? 'n/a'} / min ${item.min ?? 'n/a'} / max ${item.max ?? 'n/a'}</b></div>`).join('') || '<div><span>hpa</span><b>not installed or not ready</b></div>';
  $('karpenterState').innerHTML = [`<div><span>mode</span><b>${karp.mode || 'n/a'}</b></div>`, `<div><span>last action</span><b>${(karp.actions || []).map(a => `${a.action}:${a.node}`).join(', ') || 'none'}</b></div>`, `<div><span>nodes</span><b>${(karp.nodes || []).map(n => `${n.name}:${n.state}`).join(', ') || 'n/a'}</b></div>`].join('');
  $('notes').textContent = (payload.notes || []).join(' ');
  historyRows.push({ experimentalPending: exp.pending_pods || 0, baselinePending: base.pending_pods || 0, experimentalNodes: exp.schedulable_nodes || 0, baselineNodes: base.schedulable_nodes || 0 });
  draw();
}
async function tick() { try { const res = await fetch('/api/comparison', { cache:'no-store' }); render(await res.json()); } catch (err) { console.error(err); } }
tick(); setInterval(tick, 2500);
