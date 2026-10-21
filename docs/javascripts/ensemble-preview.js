/* Source participant-condition means only. Never aggregate legs or conditions. */
(function () {
  'use strict';
  const data = JSON.parse(document.getElementById('ensemble-data').textContent);
  const el = (tag, text) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; return node; };
  const format = value => Number.isFinite(value) ? Number(value.toPrecision(6)).toString() : '—';
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
  const features = el('fieldset'); features.append(el('legend', 'Signals — select more than one'));
  const defaults = data.signals.filter(signal => !signal.column.startsWith('source_')).slice(0,3);
  const signals = new Set((defaults.length ? defaults : data.signals.slice(0,3)).map(signal => signal.column));
  data.signals.forEach(signal => {
    const label = el('label'), input = el('input'); input.type = 'checkbox'; input.checked = signals.has(signal.column);
    input.addEventListener('change', () => { input.checked ? signals.add(signal.column) : signals.delete(signal.column); render(); });
    label.append(input, document.createTextNode(` ${signal.label}`)); features.append(label);
  });
  controls.append(features);
  function render() {
    const plots = document.getElementById('plots'); plots.replaceChildren();
    for (const signal of data.signals.filter(signal => signals.has(signal.column))) {
      const curves = data.observations.filter(o => selected.has(o.observation_id) && o.signals[signal.column]);
      const panel = el('section'); panel.className = 'plot'; panel.append(el('h2', signal.label)); plots.append(panel);
      if (!curves.length) { panel.append(el('p', 'No recorded values for the selected observations.')); continue; }
      const unit = window.LocoHubPhaseChart.displayUnit(signal.unit);
      const values = curves.flatMap(o => o.signals[signal.column].filter(Number.isFinite).map(value => value*unit.factor));
      const low = Math.min(...values), high = Math.max(...values), pad = Math.max((high-low)*.1, Math.abs(high)*.01, .000001);
      const colors = ['#334155','#2563eb','#9a3412','#6d28d9'];
      const series = curves.map((o,index) => ({slug:o.observation_id, label:`${o.subject} · ${o.task_id} · ${o.reference_side}`, phase:o.phase,
        // Renderer interface only; SD and contributor counts are deliberately absent.
        stats:{mean:o.signals[signal.column],sd:[],n:[]},color:colors[index%colors.length],dash:index>=colors.length?'5 3':'none'}));
      const chart = window.LocoHubPhaseChart.makeComparisonChart(series,signal,false,520,[low-pad,high+pad]);
      chart.setAttribute('aria-label', `${signal.label}: separate source participant-condition means. Shared axes; no standard deviation available.`);
      panel.append(chart);
      series.forEach(s => { const legend = el('p',s.label); legend.style.color=s.color; panel.append(legend); });
      const details=el('details'), summary=el('summary','Chart values — displayed units'); details.append(summary);
      const scroll=el('div'); scroll.className='scroll'; const table=el('table'), head=el('tr');
      head.append(el('th','Phase (%)')); series.forEach(s=>head.append(el('th',`${s.label} (${unit.label})`))); table.append(head);
      for(let i=0;i<150;i++) { const row=el('tr'); row.append(el('td',format(curves[0].phase[i]))); curves.forEach(o=>row.append(el('td',format(Number.isFinite(o.signals[signal.column][i])?o.signals[signal.column][i]*unit.factor:null)))); table.append(row); }
      scroll.append(table); details.append(scroll); panel.append(details);
    }
    if (!signals.size) plots.append(el('p','Select at least one signal.'));
  }
  render();
})();
