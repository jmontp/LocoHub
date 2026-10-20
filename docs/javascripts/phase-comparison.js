/* Compare static summaries without loading research files. Scales are fixed per task/signal. */
(function () {
  'use strict';
  const app = document.getElementById('comparison-app'); if (!app) return;
  const $ = id => document.getElementById(id);
  const node = (tag,text,cls) => { const e=document.createElement(tag); if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e; };
  const {makeChart,makeComparisonChart,displayUnit}=window.LocoHubPhaseChart;
  const task=$('comparison-task'), band=$('comparison-sd'), status=$('comparison-status'), results=$('comparison-results');
  const checks=new Map(), selected=new Set(), signals=new Map();
  const presets={angles:['hip_flexion_angle_ipsi_rad','knee_flexion_angle_ipsi_rad','ankle_dorsiflexion_angle_ipsi_rad'],moments:['hip_flexion_moment_ipsi_Nm_kg','knee_flexion_moment_ipsi_Nm_kg','ankle_dorsiflexion_moment_ipsi_Nm_kg'],forces:['grf_vertical_ipsi_BW','grf_anterior_ipsi_BW','grf_lateral_ipsi_BW']};
  const dashes=['','7 3','2 3','10 3 2 3','12 4','5 3 1 3','1 4','9 3 1 3 1 3'];
  const manifestURL=new URL(app.dataset.aggregateSource,location.href);
  let datasets,catalog,records=[],sequence=0,controller,view='overlay',loading=false;
  const fmt=v=>Number.isFinite(v)?String(Number(v.toPrecision(6))):'—';
  async function json(url,signal) {const r=await fetch(url,{signal});if(!r.ok)throw new Error('Unavailable');return r.json();}
  function style(slug) {const i=catalog.findIndex(d=>d.slug===slug);return {color:`var(--series-${i%8})`,dash:dashes[i%8]};}
  function label(slug) {return catalog.find(d=>d.slug===slug)?.display_name||slug.toUpperCase();}
  function lineKey(slug) {
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 30 10');svg.setAttribute('aria-hidden','true');svg.classList.add('series-key');
    const line=document.createElementNS(svg.namespaceURI,'line');line.setAttribute('x1','1');line.setAttribute('x2','29');line.setAttribute('y1','5');line.setAttribute('y2','5');line.style.stroke=style(slug).color;line.style.strokeDasharray=style(slug).dash;line.style.strokeWidth='2';svg.append(line);return svg;
  }
  function seriesFor(column,visibleOnly=true) {
    return records.filter(r=>!visibleOnly||checks.get(r.slug)?.checked).map(r=>({...r,...style(r.slug),label:label(r.slug),phase:r.payload?.phase,stats:r.payload?.all?.signals?.[column]}));
  }
  function usable(s) {return s.stats?.mean.some(Number.isFinite);}
  function domainFor(column) {
    // Include all available datasets and SD even when hidden, preventing misleading rescaling on toggles.
    const unit=displayUnit(signals.get(column).unit);let lo=Infinity,hi=-Infinity;
    seriesFor(column,false).filter(usable).forEach(s=>s.stats.mean.forEach((v,i)=>{
      if(!Number.isFinite(v))return;const sd=s.stats.n[i]>=2&&Number.isFinite(s.stats.sd[i])?s.stats.sd[i]:0;
      lo=Math.min(lo,(v-sd)*unit.factor);hi=Math.max(hi,(v+sd)*unit.factor);
    }));
    const pad=Math.max((hi-lo)*.1,Math.abs(hi)*.01,.000001);return Number.isFinite(lo)?[lo-pad,hi+pad]:undefined;
  }
  function dataDetails(column,series) {
    const detail=node('details',undefined,'comparison-values');detail.append(node('summary','Chart values and CSV'));
    const render=()=>{
      if(!detail.open||detail.dataset.built)return;detail.dataset.built='true';
      const unit=displayUnit(signals.get(column).unit),rows=[];
      series.filter(usable).forEach(s=>s.phase.forEach((phase,i)=>rows.push([s.slug,phase,Number.isFinite(s.stats.mean[i])?s.stats.mean[i]*unit.factor:null,Number.isFinite(s.stats.sd[i])&&s.stats.n[i]>=2?s.stats.sd[i]*unit.factor:null,s.stats.n[i]])));
      const wrap=node('div',undefined,'preview-table-wrap');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Chart values');
      const table=node('table'),head=node('thead'),tr=node('tr'),body=node('tbody');
      ['Dataset','Movement (%)',`Mean (${unit.label})`,`SD (${unit.label})`,'Subjects (n)'].forEach(t=>{const th=node('th',t);th.scope='col';tr.append(th);});head.append(tr);table.append(head);
      rows.forEach(values=>{const row=node('tr');values.forEach((v,i)=>row.append(node('td',i===0?v:fmt(v))));body.append(row);});table.append(body);wrap.append(table);detail.append(wrap);
      const download=node('button','Download chart values','preview-rows-toggle');download.type='button';download.onclick=()=>{
        const csv=[['dataset','phase_percent',`mean_${unit.label}`,`sd_${unit.label}`,'subjects_n'],...rows].map(row=>row.map(v=>v===null?'':`"${String(v).replaceAll('"','""')}"`).join(',')).join('\n');
        const url=URL.createObjectURL(new Blob([csv+'\n'],{type:'text/csv;charset=utf-8'})),a=node('a');a.href=url;a.download=`${task.value}_${column}_summary.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      };detail.append(download);
    };detail.addEventListener('toggle',render);return detail;
  }
  function draw() {
    results.replaceChildren();if(loading)return;
    const slugs=[...checks].filter(([,c])=>c.checked).map(([slug])=>slug);
    if(!slugs.length){status.textContent='Select at least one dataset.';return;}
    if(!selected.size){status.textContent='Choose one or more signals.';return;}
    const plotted=[...selected].filter(c=>signals.has(c));
    results.className=`comparison-workspace comparison-${view}`;
    const scroll=node('div',undefined,view==='panels'?'comparison-matrix':'comparison-overlays');
    if(view==='panels'){scroll.tabIndex=0;scroll.setAttribute('role','region');scroll.setAttribute('aria-label','Aligned signal rows. Scroll horizontally to compare datasets.');results.append(node('p','Scroll sideways to see more datasets. Every signal row uses matching axes.','comparison-scale-note'));}
    plotted.forEach(column=>{
      const signal=signals.get(column),series=seriesFor(column),valid=series.filter(usable),domain=domainFor(column);
      const section=node('section',undefined,'comparison-feature');section.dataset.signal=column;
      const heading=node('h2',signal.label);section.append(heading);
      if(view==='overlay') {
        const fig=node('figure',undefined,'preview-chart aggregate-chart');
        fig.append(makeComparisonChart(valid,signal,band.checked,480,domain));
        fig.append(node('figcaption',`${displayUnit(signal.unit).label} · ${valid.length} datasets${band.checked?' · ±1 SD':''}`));section.append(fig);
      } else {
        const row=node('div',undefined,'comparison-panel-row');row.style.gridTemplateColumns=`repeat(${slugs.length}, 320px)`;
        series.forEach(s=>{
          const cell=node('div',undefined,'comparison-panel');const title=node('h3');title.append(lineKey(s.slug),document.createTextNode(s.label));cell.append(title);
          if(usable(s)) {
            const figure=node('figure',undefined,'preview-chart aggregate-chart');
            figure.append(makeComparisonChart([s],signal,band.checked,320,domain));
            const n=s.stats.n.filter(v=>v>0);figure.append(node('figcaption',`${Math.min(...n)}–${Math.max(...n)} subjects per recorded point`));cell.append(figure);
          } else cell.append(node('p',s.error?'Summary could not be loaded. Retry above.':'No recorded values for this task and signal.','comparison-missing'));
          row.append(cell);
        });section.append(row);
      }
      const absent=series.filter(s=>!usable(s));if(absent.length)section.append(node('p',`No curve: ${absent.map(s=>s.label+(s.error?' (load failed)':'')).join('; ')}.`,'comparison-missing'));
      section.append(dataDetails(column,series));scroll.append(section);
    });results.append(scroll);
    status.textContent=`${slugs.length} datasets · ${plotted.length} signals. ${view==='overlay'&&slugs.length>4?'Curves may overlap; use Aligned panels to separate them.':'Ranges remain fixed across views and dataset toggles.'}`;
  }
  function updateSignalPicker() {
    const options=$('comparison-signals');options.replaceChildren();
    [...signals.values()].sort((a,b)=>a.label.localeCompare(b.label)).forEach(s=>{
      const wrapper=node('label'),check=node('input');check.type='checkbox';check.value=s.column;check.checked=selected.has(s.column);
      check.disabled=!check.checked&&selected.size>=6;
      wrapper.append(check,document.createTextNode(`${s.label} (${displayUnit(s.unit).label})`));wrapper.dataset.search=`${s.label} ${s.column}`.toLowerCase();
      check.onchange=()=>{if(check.checked)selected.add(s.column);else selected.delete(s.column);updateSignalPicker(); options.querySelector(`input[value="${s.column}"]`)?.focus(); draw();};options.append(wrapper);
    });
    $('comparison-signal-count').textContent=`(${selected.size} selected)`;
    const chips=$('comparison-selected-signals');chips.replaceChildren();
    [...selected].forEach(c=>{const button=node('button',`${signals.get(c)?.label||c} ×`);button.type='button';button.setAttribute('aria-label',`Remove ${signals.get(c)?.label||c}`);button.onclick=()=>{selected.delete(c);updateSignalPicker();draw();};chips.append(button);});
    filterSignals();
  }
  function filterSignals() {const q=$('comparison-signal-search').value.toLowerCase();$('comparison-signals').querySelectorAll('label').forEach(e=>e.hidden=!e.dataset.search.includes(q));}
  async function load() {
    const current=++sequence;controller?.abort();controller=new AbortController();const abortSignal=controller.signal;
    loading=true;records=[];signals.clear();results.replaceChildren();app.setAttribute('aria-busy','true');status.textContent='Loading task summaries, one dataset at a time…';$('comparison-retry').hidden=true;
    Object.values(datasets).forEach(d=>d.tasks?.find(t=>t.id===task.value)?.signals.forEach(s=>signals.set(s.column,s)));
    [...selected].forEach(c=>{if(!signals.has(c))selected.delete(c);});
    if(!selected.size)presets.angles.filter(c=>signals.has(c)).forEach(c=>selected.add(c));
    if(!selected.size&&signals.size)selected.add(signals.keys().next().value);updateSignalPicker();
    try {
      for(const dataset of catalog) {
        const slug=dataset.slug,meta=datasets[slug]?.tasks?.find(t=>t.id===task.value),record={slug,meta};
        if(meta){try{record.payload=await json(new URL(meta.url,manifestURL),abortSignal);}catch(error){if(error.name==='AbortError')return;record.error=true;}}
        if(current!==sequence)return;records.push(record);
      }
      if(current!==sequence)return;loading=false;$('comparison-retry').hidden=!records.some(r=>r.error);draw();
    } finally {if(current===sequence)app.setAttribute('aria-busy','false');}
  }
  async function initialize() {
    try {
      datasets=(await json(manifestURL)).datasets;catalog=(await json(new URL(app.dataset.source,location.href))).datasets;
      const tasks=new Map();Object.values(datasets).forEach(d=>d.tasks?.forEach(t=>tasks.set(t.id,t.label)));
      [...tasks].sort((a,b)=>a[1].localeCompare(b[1])).forEach(([id,label])=>task.add(new Option(label,id)));task.value=tasks.has('level_walking')?'level_walking':task.options[0]?.value||'';
      let enabled=0;catalog.forEach(d=>{
        const wrapper=node('label',undefined,'dataset-toggle'),check=node('input');check.type='checkbox';check.checked=!!datasets[d.slug]?.tasks?.length&&enabled++<3;
        wrapper.append(check,lineKey(d.slug),document.createTextNode(d.display_name));$('comparison-options').append(wrapper);checks.set(d.slug,check);check.onchange=draw;
      });
      task.onchange=load;band.onchange=draw;$('comparison-retry').onclick=load;
      document.querySelectorAll('[name="comparison-view"]').forEach(r=>r.onchange=()=>{view=r.value;draw();});
      $('comparison-all').onclick=()=>{checks.forEach(c=>c.checked=true);draw();};$('comparison-none').onclick=()=>{checks.forEach(c=>c.checked=false);draw();};
      $('comparison-signal-search').oninput=filterSignals;
      document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>{selected.clear();presets[b.dataset.preset].filter(c=>signals.has(c)).forEach(c=>selected.add(c));updateSignalPicker();draw();});
      $('comparison-controls').hidden=false;await load();
    } catch(error) {status.textContent='Phase summaries could not be loaded. Retry or open the dataset catalog.';$('comparison-controls').hidden=false;$('comparison-retry').hidden=false;$('comparison-retry').onclick=()=>location.reload();app.setAttribute('aria-busy','false');}
  }
  initialize();
})();
