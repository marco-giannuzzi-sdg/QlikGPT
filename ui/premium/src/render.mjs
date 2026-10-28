import { filters, matrix, rows } from './data.mjs';
export const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = n => new Intl.NumberFormat('it-IT', {style:'currency',currency:'EUR',maximumFractionDigits:0}).format(n);
const compact = n => new Intl.NumberFormat('it-IT',{notation:'compact',maximumFractionDigits:1}).format(n);
const paths = [
  '<path d="M16 5a7 7 0 1 0 0 14M4 10h10M4 14h9"/>',
  '<rect x="5" y="6" width="14" height="15" rx="2"/><path d="M9 6V3h6v3M9 11h6M9 15h6"/>',
  '<path d="M4 19V5M4 19h17M8 15l4-5 4 2 5-7"/>',
  '<path d="M6 19L18 5"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/>'
];
const icon = p => '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">'+p+'</svg>';
export function trendSvg(values, id) {
  if (!values.length) return '<div class="empty">Nessun dato per le selezioni attive</div>';
  const data = [...values].sort((a,b) => Number.isFinite(a.sort) && Number.isFinite(b.sort) ? a.sort-b.sort : a.name.localeCompare(b.name));
  const lo = Math.min(0,...data.map(d=>d.value)), hi = Math.max(1,...data.map(d=>d.value));
  const step = Math.pow(10,Math.floor(Math.log10((hi-lo)/4)));
  const max = Math.ceil(hi/step)*step, min = Math.floor(lo/step)*step;
  const y = v => 252-(v-min)/(max-min)*227, x = i => 62+i*686/Math.max(1,data.length-1);
  const points = data.map((d,i)=>x(i)+','+y(d.value)).join(' ');
  let result = '<svg class="plot" role="img" aria-label="Andamento mensile del fatturato" viewBox="0 0 800 300"><defs><linearGradient id="'+id+'" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#5b87ec" stop-opacity=".3"/><stop offset="1" stop-color="#5b87ec" stop-opacity=".02"/></linearGradient></defs>';
  for(let i=0;i<=4;i++){ const v=min+(max-min)*i/4, yy=y(v); result+='<line class="gridline" x1="62" x2="748" y1="'+yy+'" y2="'+yy+'"/><text class="axis" x="48" y="'+(yy+4)+'" text-anchor="end">€ '+esc(compact(v))+'</text>'; }
  result+='<polygon points="62,'+y(min)+' '+points+' '+x(data.length-1)+','+y(min)+'" fill="url(#'+id+')"/><polyline points="'+points+'" fill="none" stroke="#3365d5" stroke-width="3" stroke-linejoin="round"/>';
  const every=Math.max(1,Math.ceil(data.length/12));
  data.forEach((d,i)=>{
    result+='<circle cx="'+x(i)+'" cy="'+y(d.value)+'" r="3.5" fill="#fff" stroke="#3365d5" stroke-width="2"/>';
    if(i%every===0)result+='<text class="axis" x="'+x(i)+'" y="282" text-anchor="middle">'+esc(d.name)+'</text>';
    if(d.elem>=0)result+='<rect class="trend-hit" tabindex="0" role="button" aria-label="'+esc(d.name+': '+d.text)+'" data-trend="'+d.elem+'" x="'+(x(i)-13)+'" y="15" width="26" height="245"><title>'+esc(d.name+': '+d.text)+'</title></rect>';
  });
  return result+'</svg>';
}
function filterHtml(f, layout) {
  const obj = layout?.qListObject;
  const values = obj?.qDataPages?.flatMap(p=>p.qMatrix.map(r=>r[0])) || [];
  const chosen = values.filter(c=>['S','L','XS','XL'].includes(c.qState));
  let options = '<option value="">'+(chosen.length>1 ? esc(chosen.length+' selezionati') : 'Tutti')+'</option>';
  values.filter(c=>c.qElemNumber>=0).forEach(c => {
    options+='<option value="'+c.qElemNumber+'" '+(chosen.length===1&&chosen[0].qElemNumber===c.qElemNumber?'selected ':'')+(c.qState==='X'?'disabled':'')+'>'+esc(c.qText)+'</option>';
  });
  return '<div class="filter"><label for="qgp-'+f.key+'">'+f.label+'</label><select id="qgp-'+f.key+'" aria-label="'+f.label+'" data-filter="'+f.key+'" '+(!obj?'disabled':'')+'>'+options+'</select></div>';
}
export function renderDashboard(layout, state, id='qgp-trend') {
  const totals=matrix(layout)[0] || [];
  const labels=['Fatturato','Ordini','Margine lordo','Margine %'];
  const notes=['Valore commerciale','Volume delle vendite','Redditività delle vendite','Margine sul fatturato'];
  const kpis=labels.map((label,i)=>'<article class="card kpi"><div class="kpi-label">'+label+'</div><div class="kpi-icon">'+icon(paths[i])+'</div><div class="kpi-value" title="'+esc(totals[i]?.qText)+'">'+esc(totals[i]?.qText || '—')+'</div><div class="kpi-note">'+notes[i]+'</div></article>').join('');
  const markets=rows(state.markets).sort((a,b)=>b.value-a.value);
  const max=Math.max(1,...markets.map(d=>Math.abs(d.value)));
  const bars=markets.map(d=>'<button class="market" data-market="'+d.elem+'" aria-label="'+esc('Seleziona '+d.name)+'"><span class="market-heading"><span>'+esc(d.name)+'</span><strong>'+esc(money(d.value))+'</strong></span><span class="bar-track"><span class="bar" style="width:'+Math.max(0,Math.abs(d.value)/max*100)+'%"></span></span></button>').join('');
  const error=state.error?'<div role="alert" class="error">'+esc(state.error)+'</div>':'';
  return '<div class="shell"><header class="masthead"><div><div class="brand"><span class="brandmark">'+icon('<path d="M4 18V9M10 18V5M16 18v-7M22 18V3"/>')+'</span>Sales Intelligence</div><small>QLIKGPT / EXECUTIVE ANALYTICS</small></div><span class="header-tag">Connesso a Qlik Cloud</span></header>'+
    '<section class="intro"><div><h1>Executive Overview</h1><p>Una visione chiara delle performance di vendita.</p></div><div class="filterbar">'+filters.map(f=>filterHtml(f,state[f.key])).join('')+'<button class="reset" data-reset title="Cancella tutte le selezioni">Reimposta</button></div></section>'+
    error+'<div class="section-label">BUSINESS PULSE</div><section class="kpis" aria-label="Indicatori principali">'+kpis+'</section>'+
    '<div class="section-label">PERFORMANCE EXPLORER</div><section class="charts"><article class="card chart"><div class="chart-head"><div><h2>Andamento del fatturato</h2><p>Evoluzione mensile dei ricavi</p></div><span class="legend">Fatturato</span></div>'+trendSvg(rows(state.trend),id)+'</article>'+
    '<article class="card chart"><div class="chart-head"><div><h2>Performance per mercato</h2><p>Confronto dei ricavi per area</p></div></div><div class="market-list">'+(bars||'<div class="empty">Nessun dato per le selezioni attive</div>')+'</div></article></section>'+
    '<footer class="footnote"><span>Sales Intelligence · Executive Overview</span><span>Selezioni condivise · Metriche dal catalogo Qlik</span></footer></div>';
}
