const $ = (id) => document.getElementById(id);
const palette = ['#18563c', '#367bb1', '#ac6dc0', '#cf8138', '#488b87', '#a95865', '#849389'];
let result = null;
let chartView = 'normalized';
let today = new Date().toLocaleDateString('en-CA');
let busy = false;
const pct = (v, sign = false) => `${sign && v > 0 ? '+' : ''}${(v * 100).toFixed(2)}%`;
const pp = (v) => `${v > 0 ? '+' : ''}${(v * 100).toFixed(2)} pp`;
const friendly = (d) => new Date(d + 'T12:00:00').toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'});

function textNode(tag, text, className = '') {
  const node = document.createElement(tag); node.textContent = text; node.className = className; return node;
}
function setPeriod(years) {
  $('end').value = today;
  const d = new Date(today + 'T12:00:00');
  d.setFullYear(d.getFullYear() - years);
  $('start').value = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  document.querySelectorAll('[data-years]').forEach(b => {
    const active = Number(b.dataset.years) === years; b.classList.toggle('active', active); b.setAttribute('aria-pressed', active);
  });
}
function invalidate() {
  // Never leave results visible under controls that describe another request.
  $('results').hidden = true;
  $('error').hidden = true;
  if (!busy) { $('loading').hidden = false; $('loading').textContent = 'Choose Compare stocks to apply your changes.'; }
}
function metric(label, value, symbol, note, featured = false) {
  const card = textNode('article', '', `metric-card${featured ? ' featured' : ''}`);
  card.append(textNode('p', label, 'card-label'));
  const v = textNode('p', value, 'card-value'); v.append(textNode('span', symbol, 'card-symbol')); card.append(v, textNode('p', note, 'card-note')); return card;
}
function render() {
  const rows = result.rows;
  const bench = rows.find(r => r.symbol === result.benchmark);
  const stocks = rows.filter(r => r.symbol !== result.benchmark);
  const best = (stocks.length ? stocks : rows).reduce((a,b) => a.total_return > b.total_return ? a : b);
  const worst = (stocks.length ? stocks : rows).reduce((a,b) => a.max_drawdown < b.max_drawdown ? a : b);
  const n = result.dates.length;
  $('range-label').textContent = `${friendly(result.dates[0])} – ${friendly(result.dates[n-1])} · ${n.toLocaleString()} common observations`;
  $('metric-cards').replaceChildren(
    metric('Highest return in this comparison', pct(best.total_return, true), best.symbol, `${pp(best.excess_return)} versus ${result.benchmark}`, true),
    metric('Benchmark total return', pct(bench.total_return, true), bench.symbol, 'Adjusted for splits and dividends'),
    metric(stocks.length ? 'Deepest drawdown among selected stocks' : 'Benchmark maximum drawdown', pct(worst.max_drawdown), worst.symbol, 'Largest peak-to-trough decline in this window')
  );
  $('performance-rows').replaceChildren(...rows.map((r) => {
    const row = document.createElement('tr');
    const name = textNode('td', r.symbol, 'ticker');
    if (r.symbol === result.benchmark) name.append(textNode('span', 'BENCHMARK', 'benchmark-tag'));
    row.append(name,
      textNode('td', pct(r.total_return, true), r.total_return >= 0 ? 'positive' : 'negative'),
      textNode('td', r.symbol === result.benchmark ? '—' : pp(r.excess_return), r.excess_return === 0 ? 'neutral' : r.excess_return > 0 ? 'positive' : 'negative'),
      textNode('td', pct(r.annualized_volatility)), textNode('td', pct(r.max_drawdown), 'negative'), textNode('td', r.observations.toLocaleString()));
    return row;
  }));
  $('warnings').replaceChildren(...result.warnings.map(w => textNode('li', w)));
  $('warnings-panel').hidden = result.warnings.length === 0;
  $('retrieved').textContent = `Read locally ${new Date(result.retrieved_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})} · No trading costs or taxes`;
  $('results').hidden = false;
  drawChart();
}
function svgNode(tag, attrs, text) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key,value] of Object.entries(attrs)) el.setAttribute(key, String(value));
  if (text !== undefined) el.textContent = text;
  return el;
}
function drawChart() {
  if (!result) return;
  const chart = $('chart'); chart.replaceChildren();
  const dd = chartView === 'drawdown';
  $('chart-title').textContent = dd ? 'Drawdown from the rolling peak' : 'Growth of 100';
  $('chart-description').textContent = dd ? 'Declines from each series’ highest value within this window.' : 'Same starting value. Same observed dates.';
  $('legend').replaceChildren(...result.rows.map((r,i) => {
    const legend = textNode('span', '', 'legend-item');
    const icon = svgNode('svg', {width:18,height:6,'aria-hidden':'true'});
    icon.append(svgNode('line', {x1:0,y1:3,x2:18,y2:3,stroke:palette[i], 'stroke-width':3}));
    legend.append(icon, document.createTextNode(r.symbol + (r.symbol === result.benchmark ? ' · benchmark' : ''))); return legend;
  }));
  const values = result.rows.flatMap(r => r[chartView]);
  let lo = Math.min(...values), hi = Math.max(...values);
  const pad = (hi-lo || 1) * .12;
  lo -= pad; hi = dd ? 0 : hi + pad;
  const width = Math.max(300, Math.round(chart.parentElement.clientWidth));
  const narrow = width < 600, height = narrow ? 260 : 300;
  chart.setAttribute('viewBox', `0 0 ${width} ${height}`);
  const left=50,right=width-16,top=17,bottom=height-42;
  const x = i => left + (right-left) * i / (result.dates.length-1);
  const y = v => bottom - (v-lo)/(hi-lo)*(bottom-top);
  for (let i=0;i<=4;i++) {
    const value = lo+(hi-lo)*i/4, cy=y(value);
    chart.append(svgNode('line', {x1:left,y1:cy,x2:right,y2:cy,stroke:'#e8ede9','stroke-width':1}),
      svgNode('text',{x:left-14,y:cy+4,'text-anchor':'end',fill:'#6c7e71','font-size':12}, dd ? `${(value*100).toFixed(0)}%` : value.toFixed(0)));
  }
  const ticks = narrow ? 3 : 5;
  for (let i=0;i<ticks;i++) {
    const idx=Math.round(i*(result.dates.length-1)/(ticks-1));
    const label = narrow ? new Date(result.dates[idx]+'T12:00:00').toLocaleDateString('en-US',{month:'short',year:'2-digit'}) : friendly(result.dates[idx]);
    chart.append(svgNode('text',{x:x(idx),y:height-12,'text-anchor':i===0?'start':i===ticks-1?'end':'middle',fill:'#6c7e71','font-size':12},label));
  }
  if(dd) chart.append(svgNode('line',{x1:left,y1:y(0),x2:right,y2:y(0),stroke:'#bac8bf','stroke-dasharray':'4 4'}));
  result.rows.forEach((r,i) => {
    chart.append(svgNode('path', {d:r[chartView].map((v,j)=>`${j?'L':'M'}${x(j).toFixed(2)},${y(v).toFixed(2)}`).join(' '),fill:'none',stroke:palette[i], 'stroke-width':r.symbol===result.benchmark?2:2.7,'stroke-linejoin':'round','stroke-dasharray':r.symbol===result.benchmark?'6 5':'none'}));
  });
  const cursor=svgNode('line',{x1:left,x2:left,y1:top,y2:bottom,stroke:'#82958a','stroke-dasharray':'3 3',visibility:'hidden'});chart.append(cursor);
  chart.onpointermove = (event) => {
    const p=chart.createSVGPoint();p.x=event.clientX;p.y=event.clientY;
    const local=p.matrixTransform(chart.getScreenCTM().inverse());
    const idx=Math.max(0,Math.min(result.dates.length-1,Math.round((local.x-left)/(right-left)*(result.dates.length-1))));
    cursor.setAttribute('x1',x(idx));cursor.setAttribute('x2',x(idx));cursor.setAttribute('visibility','visible');
    $('chart-detail').textContent = friendly(result.dates[idx]) + '  ·  ' + result.rows.map(r=>`${r.symbol} ${dd?pct(r.drawdown[idx]):r.normalized[idx].toFixed(2)}`).join('  /  ');
  };
  chart.onpointerleave=()=>cursor.setAttribute('visibility','hidden');
  $('chart-detail').textContent = 'Move over the chart to inspect an observation. The table below summarizes every series.';
}
async function compare(event) {
  if(event) event.preventDefault();
  if(busy || !$('research-form').reportValidity()) return;
  busy=true;
  const params = new URLSearchParams(new FormData($('research-form')));
  document.querySelectorAll('#research-form input, #research-form button, [data-years]').forEach(e=>e.disabled=true);
  $('run').textContent='Reading data…';$('error').hidden=true;$('results').hidden=true;$('loading').hidden=false;
  $('loading').textContent='Reading your local Norgate database…';
  try {
    const response=await fetch('/api/analyze?'+params, {signal:AbortSignal.timeout(90000)});
    const data=await response.json();
    if(!response.ok) throw new Error(data.error || 'The comparison could not be completed.');
    result=data;render();
    $('connection').textContent='Norgate connected';$('connection').classList.remove('offline');
  } catch(error) {
    $('error').textContent=error.name==='TimeoutError'?'The data request timed out. Check Norgate Data Updater, then try again.':error.message;
    $('error').hidden=false;
  } finally {
    busy=false;$('loading').hidden=true;
    document.querySelectorAll('#research-form input, #research-form button, [data-years]').forEach(e=>e.disabled=false);
    $('run').replaceChildren(document.createTextNode('Compare stocks '),textNode('span','↗'));
  }
}
$('research-form').addEventListener('submit',compare);
document.querySelectorAll('#research-form input').forEach(e=>e.addEventListener('input',()=>{
  invalidate();
  if(e.type==='date') document.querySelectorAll('[data-years]').forEach(b=>{b.classList.remove('active');b.setAttribute('aria-pressed',false);});
}));
document.querySelectorAll('[data-years]').forEach(b=>b.addEventListener('click',()=>{setPeriod(Number(b.dataset.years));invalidate();}));
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{
  chartView=b.dataset.view;
  document.querySelectorAll('[data-view]').forEach(btn=>{const active=btn===b;btn.classList.toggle('active',active);btn.setAttribute('aria-pressed',active);});
  drawChart();
}));
window.addEventListener('resize',()=>{if(result && !$('results').hidden) drawChart();});
async function init() {
  try {
    const response=await fetch('/api/status',{signal:AbortSignal.timeout(20000)});
    const status=await response.json();today=status.today;
    $('connection').textContent=status.connected?'Norgate connected':'Norgate needs attention';
    $('connection').classList.toggle('offline',!status.connected);
    if(!status.connected) {$('error').textContent=status.message;$('error').hidden=false;$('loading').hidden=true;}
    setPeriod(1);$('end').max=today;$('start').max=today;
    if(status.connected) await compare();
  } catch(error) {
    setPeriod(1);$('loading').hidden=true;$('connection').textContent='Connection unavailable';$('connection').classList.add('offline');
    $('error').textContent='Cannot reach the local data service. Start the app and Norgate Data Updater, then reload.';$('error').hidden=false;
  }
}
init();
