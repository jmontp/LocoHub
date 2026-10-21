/* Source participant-condition means only. Never aggregate legs or conditions. */
(function () {
  'use strict';
  const data = JSON.parse(document.getElementById('ensemble-data').textContent);
  const el = (tag, text) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; return node; };
  const format = value => Number.isFinite(value) ? Number(value.toPrecision(6)).toString() : '—';
  const displayUnit = signal => window.LocoHubPhaseChart.displayUnit(signal.unit);
  document.getElementById('scope').textContent = `${data.subject_count} participant${data.subject_count === 1 ? '' : 's'} · ${data.observation_count} separate leg-condition averages`;
  document.getElementById('note').textContent = data.note;
  const controls = document.getElementById('controls'), selected = new Set(data.observations.map(o => o.observation_id));
  const observations = el('fieldset'); observations.append(el('legend', 'Participant, condition and leg'));
  data.observations.forEach(observation => {
    const label = el('label'), input = el('input'); input.type = 'checkbox'; input.checked = true;
    input.addEventListener('change', () => { input.checked ? selected.add(observation.observation_id) : selected.delete(observation.observation_id); render(); });
    label.append(input, document.createTextNode(` ${observation.subject} · ${observation.task_id.replaceAll('_', ' ')} · ${observation.reference_side}`)); observations.append(label);
  });
  controls.append(observations);
  const standard = data.signals.filter(signal => !signal.source_component && !signal.column.startsWith('source_'));
  const raw = data.signals.filter(signal => signal.source_component || signal.column.startsWith('source_'));
  const defaults = standard.length ? standard.slice(0,3) : raw.slice(0,3);
  const signals = new Set(defaults.map(signal => signal.column)), inputs = new Map();
  const features = el('fieldset'); features.append(el('legend', 'Compare signals'));
  const hint = el('p', 'Standard angle and moment labels are supported for the right leg. Left-leg values are available below as source components; their anatomical directions have not been confirmed.'); hint.className='hint'; features.append(hint);
  function checkbox(signal, parent) {
    const label = el('label'), input = el('input'); input.type='checkbox'; input.checked=signals.has(signal.column);
    label.title=signal.column; input.dataset.column=signal.column; inputs.set(signal.column,input);
    input.addEventListener('change',()=>{input.checked?signals.add(signal.column):signals.delete(signal.column);render();});
    label.append(input,document.createTextNode(` ${signal.label} (${displayUnit(signal).label})`));parent.append(label);
    return label;
  }
  standard.forEach(signal=>checkbox(signal,features));
  const sourceDetails=el('details'), sourceSummary=el('summary',`Source components (${raw.length})`);sourceDetails.append(sourceSummary);
  sourceDetails.append(el('p','Original component axes are preserved. X, Y and Z are source axes, not independently approved anatomical directions.'));
  const search=el('input');search.type='search';search.placeholder='Find a source component, e.g. left ankle';search.setAttribute('aria-label','Find source components');search.className='source-search';sourceDetails.append(search);
  const rawOptions=el('div');rawOptions.className='source-options';sourceDetails.append(rawOptions);
  const labels=raw.map(signal=>({signal,label:checkbox(signal,rawOptions)}));
  search.addEventListener('input',()=>{const words=search.value.toLowerCase().trim().split(/\s+/);labels.forEach(({signal,label})=>{label.hidden=!words.every(word=>`${signal.label} ${signal.column}`.toLowerCase().includes(word));});});
  features.append(sourceDetails);controls.append(features);
  const selectionNote=el('p');controls.append(selectionNote);
  const leftButton=el('button','Show left source angles');leftButton.type='button';
  leftButton.addEventListener('click',()=>{
    signals.clear();raw.filter(signal=>/^source_L(Hip|Knee|Ankle)AngleZ_deg$/.test(signal.column)).forEach(signal=>signals.add(signal.column));
    inputs.forEach((input,column)=>{input.checked=signals.has(column);});sourceDetails.open=true;render();
  });
  controls.append(leftButton);
  const download=el('button','Download preview values (JSON)');download.type='button';download.style.marginLeft='10px';
  download.addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(data)],{type:'application/json'}));const a=el('a');a.href=url;a.download='fukuchi-ensemble-preview.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});controls.append(download);
  function render() {
    const active=data.observations.filter(o=>selected.has(o.observation_id));
    const leftOnly=active.length>0&&active.every(o=>o.reference_side==='left');
    selectionNote.textContent=leftOnly?'Left leg selected: standard anatomical labels are unavailable. Use source components to view its recorded values.':active.length?'Curves retain their own leg and condition; no averages are calculated between them.':'Select at least one observation.';
    leftButton.hidden=!active.some(o=>o.reference_side==='left')||!raw.some(s=>/^source_L(Hip|Knee|Ankle)AngleZ_deg$/.test(s.column));
    const plots=document.getElementById('plots');plots.replaceChildren();
    for(const signal of data.signals.filter(signal=>signals.has(signal.column))) {
      const curves=active.filter(o=>o.signals[signal.column]);
      const panel=el('section');panel.className='plot';const title=el('h2',signal.label);title.title=signal.column;panel.append(title);plots.append(panel);
      const unit=displayUnit(signal),units=el('p',unit.label);units.className='units';panel.append(units);
      if(!curves.length){panel.append(el('p',leftOnly&&!signal.column.startsWith('source_')?'This standard signal is unavailable for the left leg. Select a source component above.':'No recorded values for the selected observations.'));continue;}
      const values=curves.flatMap(o=>o.signals[signal.column].filter(Number.isFinite).map(value=>value*unit.factor));
      const low=Math.min(...values),high=Math.max(...values),pad=Math.max((high-low)*.1,Math.abs(high)*.01,.000001),colors=['#334155','#2563eb','#9a3412','#6d28d9'];
      const series=curves.map((o,index)=>({slug:o.observation_id,label:`${o.subject} · ${o.task_id.replaceAll('_',' ')} · ${o.reference_side}`,phase:o.phase,
        stats:{mean:o.signals[signal.column],sd:[],n:[]},color:colors[index%colors.length],dash:index>=colors.length?'5 3':'none'}));
      const chart=window.LocoHubPhaseChart.makeComparisonChart(series,signal,false,520,[low-pad,high+pad]);
      chart.setAttribute('aria-label',`${signal.label}: separate source participant-condition means. Shared axes; no standard deviation available.`);panel.append(chart);
      series.forEach(s=>{const legend=el('p',s.label);legend.style.color=s.color;panel.append(legend);});
      const details=el('details');details.append(el('summary','Chart values and source column'));
      const column=el('code',signal.column);column.className='signal-name';details.append(column);
      const scroll=el('div');scroll.className='scroll';const table=el('table'),head=el('tr');head.append(el('th','Phase (%)'));
      series.forEach(s=>head.append(el('th',`${s.label} (${unit.label})`)));table.append(head);
      for(let i=0;i<150;i++){const row=el('tr');row.append(el('td',format(curves[0].phase[i])));curves.forEach(o=>row.append(el('td',format(Number.isFinite(o.signals[signal.column][i])?o.signals[signal.column][i]*unit.factor:null))));table.append(row);}
      scroll.append(table);details.append(scroll);panel.append(details);
    }
    if(!signals.size)plots.append(el('p','Select at least one signal.'));
  }
  render();
})();
