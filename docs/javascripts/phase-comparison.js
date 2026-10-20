/* Static, lazy-loaded subject-balanced summaries; no Parquet parsing in the browser. */
(function () {
  'use strict';
  const app = document.getElementById('comparison-app');
  if (!app) return;
  const node = (tag, text, cls) => { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; };
  const {makeChart, displayUnit} = window.LocoHubPhaseChart;
  const task = document.getElementById('comparison-task'), signal = document.getElementById('comparison-signal');
  const band = document.getElementById('comparison-sd'), scale = document.getElementById('comparison-scale');
  const status = document.getElementById('comparison-status'), results = document.getElementById('comparison-results');
  const retry = document.getElementById('comparison-retry');
  const manifestURL = new URL(app.dataset.aggregateSource, location.href);
  const checks = new Map(); let datasets, catalog, selectedSignal, records = [], sequence = 0, controller;
  const fmt = x => Number.isFinite(x) ? String(Number(x.toPrecision(6))) : '—';
  async function json(url, abortSignal) { const r = await fetch(url, {signal: abortSignal}); if (!r.ok) throw new Error('Unavailable'); return r.json(); }
  function links(card, slug) {
    const wrap = node('div', undefined, 'comparison-links'), a = node('a', 'Study notes and subjects');
    a.href = `../${encodeURIComponent(slug)}/#phase-plots`; wrap.append(a); card.append(wrap);
  }
  function draw() {
    results.replaceChildren();
    const series = records.map(record => ({...record, stats: record.payload?.all?.signals?.[signal.value]}));
    let min = Infinity, max = -Infinity;
    const unit = displayUnit(selectedSignal?.unit);
    series.forEach(({stats}) => stats?.mean.forEach((value, i) => {
      if (!Number.isFinite(value)) return;
      const sd = band.checked && stats.n[i] >= 2 && Number.isFinite(stats.sd[i]) ? stats.sd[i] : 0;
      min = Math.min(min, (value - sd) * unit.factor); max = Math.max(max, (value + sd) * unit.factor);
    }));
    const pad = Math.max((max-min)*.1, Math.abs(max)*.01, .000001);
    const domain = scale.checked && Number.isFinite(min) ? [min-pad,max+pad] : undefined;
    let shown = 0;
    series.forEach(({slug, dataset, metadata, payload, error, stats}) => {
      const card = node('article', undefined, 'phase-comparison-card');
      card.append(node('h2', catalog.find(d => d.slug === slug)?.display_name || dataset?.label || slug.toUpperCase()));
      if (!stats || !stats.mean.some(Number.isFinite)) {
        card.append(node('p', error ? 'Summary could not be loaded. Use Retry to try again.' : !metadata ? 'No numerical summary is available for this task.' : 'This signal has no recorded values in this summary.'));
        links(card, slug); results.append(card); return;
      }
      shown++;
      const positive = stats.n.filter(n => n > 0), low = Math.min(...positive), high = Math.max(...positive);
      card.append(node('p', `${low === high ? high : `${low}–${high}`} subjects contributing per recorded point.`, 'phase-source'));
      const figure = node('figure', undefined, 'preview-chart aggregate-chart');
      figure.append(makeChart(payload.phase, stats, selectedSignal, band.checked, 540, domain));
      const hasSD = stats.sd.some((v,i) => Number.isFinite(v) && stats.n[i] >= 2);
      figure.append(node('figcaption', `Mean of subject averages (${unit.label}). ${band.checked && hasSD ? 'Band: ±1 SD between subjects.' : band.checked ? 'No band: SD needs at least two subjects.' : 'SD hidden.'} ${scale.checked ? 'Matching vertical scales.' : 'Independent vertical scales.'}`));
      card.append(figure, node('p', dataset.source.filename, 'phase-source'));
      const detail = node('details'), tableWrap = node('div', undefined, 'preview-table-wrap'); tableWrap.tabIndex = 0;
      tableWrap.setAttribute('role','region'); tableWrap.setAttribute('aria-label', 'Chart values');
      detail.append(node('summary','Chart values and CSV'));
      const table = node('table'), head = node('thead'), hr = node('tr');
      ['Movement (%)',`Mean (${unit.label})`,`SD (${unit.label})`,'Subjects (n)'].forEach(t => {const th=node('th',t);th.scope='col';hr.append(th);});head.append(hr);table.append(head);
      const body = node('tbody'), csv = [['phase_percent',`mean_${unit.label}`,`sd_${unit.label}`,'subjects_n'].join(',')];
      payload.phase.forEach((phase,i) => {
        const values = [phase,Number.isFinite(stats.mean[i]) ? stats.mean[i]*unit.factor : null,Number.isFinite(stats.sd[i]) && stats.n[i]>=2 ? stats.sd[i]*unit.factor : null,stats.n[i]];
        const tr=node('tr');values.forEach(v=>tr.append(node('td',fmt(v),'num')));body.append(tr);
        csv.push(values.map(v=>Number.isFinite(v)?v:'').join(','));
      });
      table.append(body);tableWrap.append(table);detail.append(tableWrap);
      const download = node('button','Download chart values','preview-rows-toggle'); download.type='button';
      download.addEventListener('click',()=>{
        const url=URL.createObjectURL(new Blob([csv.join('\n')+'\n'],{type:'text/csv;charset=utf-8'}));
        const a=node('a');a.href=url;a.download=`${slug}_${task.value}_${signal.value}_summary.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      });detail.append(download);card.append(detail);links(card,slug);results.append(card);
    });
    status.textContent = `${shown} of ${records.length} selected datasets have recorded values for this task and signal. Missing sections stay blank; conditions are pooled.`;
  }
  async function load() {
    const current = ++sequence;
    controller?.abort();controller = new AbortController();const abortSignal = controller.signal;
    records=[];results.replaceChildren();retry.hidden=true;app.setAttribute('aria-busy','true');
    status.textContent='Loading selected task summaries…';
    const choices = [...checks].filter(([,c])=>c.checked).map(([slug])=>slug);
    const signals = new Map();
    choices.forEach(slug => datasets[slug]?.tasks?.find(t=>t.id===task.value)?.signals.forEach(s=>signals.set(s.column,s)));
    const old = signal.value;signal.replaceChildren();
    [...signals.values()].sort((a,b)=>a.label.localeCompare(b.label)).forEach(s=>signal.add(new Option(`${s.label} (${displayUnit(s.unit).label})`,s.column)));
    signal.value=signals.has(old)?old:signals.has('knee_flexion_angle_ipsi_rad')?'knee_flexion_angle_ipsi_rad':signal.options[0]?.value||'';
    selectedSignal=signals.get(signal.value);signal.disabled=!signals.size;
    try {
      // Fetch serially: one small task summary at a time, only for selected datasets.
      for (const slug of choices) {
        const dataset=datasets[slug], metadata=dataset?.tasks?.find(t=>t.id===task.value);
        const record={slug,dataset,metadata};
        if (metadata) {
          try { record.payload=await json(new URL(metadata.url,manifestURL),abortSignal); }
          catch(error) { if(error.name==='AbortError')return;record.error=true; }
        }
        if(current!==sequence)return;
        records.push(record);
      }
      if(current!==sequence)return;
      retry.hidden=!records.some(r=>r.error);draw();
      if(!choices.length)status.textContent='Select at least one dataset.';
    } finally {if(current===sequence)app.setAttribute('aria-busy','false');}
  }
  async function initialize() {
    try {
      const manifest=await json(manifestURL);datasets=manifest.datasets;
      catalog=(await json(new URL(app.dataset.source,location.href))).datasets;
      const tasks=new Map();Object.values(datasets).forEach(d=>d.tasks?.forEach(t=>tasks.set(t.id,t.label)));
      [...tasks].sort((a,b)=>a[1].localeCompare(b[1])).forEach(([id,label])=>task.add(new Option(label,id)));
      task.value=tasks.has('level_walking')?'level_walking':task.options[0]?.value||'';
      const options=document.getElementById('comparison-options');
      catalog.forEach(d=>{
        const label=node('label',undefined,'dataset-option'),check=node('input');check.type='checkbox';check.checked=!!datasets[d.slug]?.tasks?.length;
        label.append(check,document.createTextNode(` ${d.display_name}`));options.append(label);checks.set(d.slug,check);check.addEventListener('change',load);
      });
      task.addEventListener('change',load);band.addEventListener('change',draw);scale.addEventListener('change',draw);
      signal.addEventListener('change',()=>{selectedSignal=Object.values(datasets).flatMap(d=>d.tasks||[]).flatMap(t=>t.signals).find(s=>s.column===signal.value);draw();});
      retry.onclick=load;document.getElementById('comparison-controls').hidden=false;await load();
    } catch(error) {
      status.textContent='Phase summaries could not be loaded. Retry or open the dataset catalog.';
      retry.hidden=false;document.getElementById('comparison-controls').hidden=false;retry.onclick=()=>location.reload();app.setAttribute('aria-busy','false');
    }
  }
  initialize();
})();
