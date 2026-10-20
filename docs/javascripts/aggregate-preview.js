/* Precomputed task summaries only: no research files or statistics are loaded in the browser. */
(function () {
  'use strict';
  let manifestPromise, manifestURL, generation = 0, request, subjectRequest, observer;
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const svgEl = (tag, attrs, text) => {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const finite = Number.isFinite;
  const fmt = (value) => finite(value) ? Number(value.toPrecision(5)).toString() : '—';
  function dispose() {
    generation += 1;
    if (request) request.abort();
    if (subjectRequest) subjectRequest.abort();
    if (observer) observer.disconnect();
    request = subjectRequest = observer = undefined;
  }
  function displayUnit(unit) {
    if (unit === 'rad') return {factor: 180 / Math.PI, label: 'degrees'};
    if (['rad/s', 'rad_s'].includes(unit)) return {factor: 180 / Math.PI, label: 'degrees/s'};
    if (['rad/s²', 'rad/s^2', 'rad_s2'].includes(unit)) return {factor: 180 / Math.PI, label: 'degrees/s²'};
    const labels = {deg: 'degrees', deg_s: 'degrees/s', deg_s2: 'degrees/s²', m_s: 'm/s', m_s2: 'm/s²', Nm_kg: 'Nm/kg', N_kg: 'N/kg', W_kg: 'W/kg', BW: 'body weights'};
    return {factor: 1, label: labels[unit] || unit || 'as stored'};
  }
  function ticks(min, max) {
    const raw = (max - min) / 4;
    if (!(raw > 0) || !finite(raw)) return [min];
    const power = 10 ** Math.floor(Math.log10(raw)), ratio = raw / power;
    const step = (ratio < 1.5 ? 1 : ratio < 3 ? 2 : ratio < 7 ? 5 : 10) * power;
    const result = [];
    for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-9 && result.length < 20; v += step) result.push(Number(v.toPrecision(12)));
    return result;
  }
  function makeChart(phase, stats, signal, band, width) {
    const unit = displayUnit(signal.unit);
    const points = phase.map((x, i) => ({x, y: finite(stats.mean[i]) ? stats.mean[i] * unit.factor : null,
      sd: finite(stats.sd[i]) && stats.n[i] >= 2 ? stats.sd[i] * unit.factor : null}));
    const valid = points.filter((p) => finite(p.x) && finite(p.y));
    if (!valid.length) return el('p', 'No recorded values for this signal and selection.', 'aggregate-empty');
    const W = Math.max(320, Math.round(width || 480)), H = 270, L = 52, R = 16, T = 28, B = 44;
    const lows = valid.map((p) => p.y - (band && finite(p.sd) ? p.sd : 0));
    const highs = valid.map((p) => p.y + (band && finite(p.sd) ? p.sd : 0));
    const lo = Math.min(...lows), hi = Math.max(...highs), pad = Math.max((hi - lo) * .1, Math.abs(hi) * .01, .000001);
    const ymin = lo - pad, ymax = hi + pad;
    const fullPhase = phase.filter(finite);
    const xmin = Math.min(...fullPhase), xmax = Math.max(...fullPhase);
    const X = (x) => L + (x - xmin) / (xmax - xmin || 1) * (W - L - R);
    const Y = (y) => H - B - (y - ymin) / (ymax - ymin) * (H - T - B);
    const svg = svgEl('svg', {viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': `${signal.label}: mean${band ? ' and one standard deviation where at least two observations contribute' : ''}. Exact values are in Chart values below.`});
    svg.append(svgEl('title', {}, `${signal.label} (${unit.label})`));
    ticks(ymin, ymax).forEach((v) => {
      svg.append(svgEl('line', {x1: L, x2: W - R, y1: Y(v), y2: Y(v), class: 'preview-grid'}));
      svg.append(svgEl('text', {x: L - 8, y: Y(v) + 4, 'text-anchor': 'end'}, fmt(v)));
    });
    ticks(xmin, xmax).forEach((v) => svg.append(svgEl('text', {x: X(v), y: H - B + 17, 'text-anchor': 'middle'}, fmt(v))));
    if (ymin < 0 && ymax > 0) svg.append(svgEl('line', {x1: L, x2: W - R, y1: Y(0), y2: Y(0), class: 'preview-zero'}));
    svg.append(svgEl('text', {x: L, y: 14, class: 'preview-axis-title'}, unit.label));
    svg.append(svgEl('text', {x: L + (W - L - R) / 2, y: H - 6, 'text-anchor': 'middle'}, 'Movement (%)'));
    if (band) {
      let segment = [];
      const flush = () => {
        if (segment.length > 1) {
          const top = segment.map((p) => `${X(p.x).toFixed(2)},${Y(p.y + p.sd).toFixed(2)}`);
          const bottom = [...segment].reverse().map((p) => `${X(p.x).toFixed(2)},${Y(p.y - p.sd).toFixed(2)}`);
          svg.append(svgEl('path', {d: `M${top.join(' L')} L${bottom.join(' L')} Z`, class: 'aggregate-band'}));
        }
        segment = [];
      };
      points.forEach((p) => { if (finite(p.x) && finite(p.y) && finite(p.sd)) segment.push(p); else flush(); });
      flush();
    }
    let path = '', connected = false;
    points.forEach((p) => {
      if (!finite(p.x) || !finite(p.y)) { connected = false; return; }
      path += `${connected ? 'L' : 'M'}${X(p.x).toFixed(2)},${Y(p.y).toFixed(2)} `; connected = true;
    });
    svg.append(svgEl('path', {d: path, class: 'preview-line aggregate-mean'}));
    return svg;
  }

  async function mount(options) {
    const {panel, slug, anchor, controls: rawControls, plot: rawPlot, meta, note, sampleRows, sample, stopRawChart} = options;
    const current = generation;
    if (!panel.dataset.aggregateSource) return;
    if (!manifestPromise) {
      manifestURL = new URL(panel.dataset.aggregateSource, window.location.href);
      manifestPromise = fetch(manifestURL).then((r) => { if (!r.ok) throw new Error(); return r.json(); })
        .catch((error) => { manifestPromise = undefined; throw error; });
    }
    let dataset;
    try { dataset = (await manifestPromise).datasets[slug]; }
    catch (_) {
      if (current === generation && anchor.isConnected) note.textContent += ' Task averages could not be loaded.';
      return;
    }
    if (current !== generation || !anchor.isConnected || !dataset?.tasks?.length) return;
    let restoreSignalFocus = rawControls.contains(document.activeElement);
    let initialSignal = rawControls.querySelector('select')?.value || '';
    stopRawChart();
    const widget = el('section', undefined, 'aggregate-preview');
    widget.setAttribute('aria-label', 'Explore task averages');
    rawControls.replaceWith(widget); rawPlot.remove();
    meta.replaceChildren(el('code', dataset.source.filename));
    note.textContent = 'Averages from a local file; its version may differ from the download.';
    const rawTask = sample?.rows?.[0]?.task || 'as stored';
    if (sampleRows) sampleRows.querySelector('summary').textContent = `Example file rows · ${String(rawTask).replaceAll('_', ' ')}`;
    const form = el('div', undefined, 'aggregate-controls');
    function selectControl(label, id) {
      const wrapper = el('label', label), select = el('select');
      select.id = id; wrapper.htmlFor = id; wrapper.append(select); form.append(wrapper); return select;
    }
    const taskSelect = selectControl('Task', 'preview-task');
    dataset.tasks.forEach((task) => taskSelect.add(new Option(`${task.label}${task.signals.length ? '' : ' — no signals'}`, task.id)));
    const defaultTask = dataset.tasks.find((t) => t.id === 'level_walking' && t.signals.length) || dataset.tasks.find((t) => t.signals.length) || dataset.tasks[0];
    taskSelect.value = defaultTask.id;
    const subjectSelect = selectControl('Subject', 'preview-subject');
    const signalSelect = selectControl('Signal', 'preview-signal');
    const bandLabel = el('label', undefined, 'aggregate-band-control'), band = el('input');
    band.type = 'checkbox'; band.checked = true; band.id = 'preview-sd';
    bandLabel.append(band, document.createTextNode('Show standard deviation'));
    const status = el('p', '', 'aggregate-status'); status.setAttribute('role', 'status');
    const retry = el('button', 'Retry averages', 'preview-rows-toggle'); retry.type = 'button'; retry.hidden = true;
    const column = el('p', '', 'preview-column');
    const figure = el('figure', undefined, 'preview-chart aggregate-chart');
    const plot = el('div'); const caption = el('figcaption'); figure.append(plot, caption);
    const values = el('details', undefined, 'aggregate-values'); values.append(el('summary', 'Chart values'));
    const valueWrap = el('div', undefined, 'preview-table-wrap'); valueWrap.tabIndex = 0;
    valueWrap.setAttribute('role', 'region'); valueWrap.setAttribute('aria-label', 'Mean, standard deviation and contributing counts'); values.append(valueWrap);
    const method = el('details', undefined, 'aggregate-method'); method.append(el('summary', 'How these averages are calculated'));
    method.append(el('p', 'All subjects: first average complete stored curves within each subject, then give each subject equal weight. The shaded band is ±1 sample standard deviation between subject averages—not a confidence interval.'));
    method.append(el('p', 'One subject: the band is ±1 sample standard deviation across that subject’s stored curves. Missing values are skipped point by point. At least two contributors are needed for a standard deviation. Different speeds and conditions within the same task are combined.'));
    method.append(el('p', 'Only complete, ordered 150-point curves on the same phase grid are included. Some older files already contain averaged curves rather than individual movements. These checks do not establish biomechanical quality or resolve reused recording identifiers in older files.'));
    method.append(el('p', dataset.source.note || 'These local files have not been verified against the linked downloads.'));
    if (dataset.excluded_counts) {
      const counts = dataset.excluded_counts;
      const rejected = Object.entries(counts).filter(([key]) => key.endsWith('_observations') && key !== 'complete_observations').reduce((sum, [, n]) => sum + n, 0);
      method.append(el('p', `File checks: ${counts.complete_observations || 0} complete curves found; ${rejected} incomplete or invalid blocks excluded.`));
    }
    widget.append(form, bandLabel, status, retry, column, figure, values, method);
    let payload, task, subjectPayload, subjectPending = false, subjectError = false, subjectNumber = 0, requestNumber = 0, drawnWidth = 0;
    function chosenStats() { return subjectSelect.value ? subjectPayload : payload.all; }
    function draw(updateValues = true) {
      if (!payload || subjectPending || subjectError) return;
      const signal = task.signals.find((s) => s.column === signalSelect.value), group = chosenStats();
      const stats = signal && group?.signals?.[signal.column];
      drawnWidth = plot.clientWidth;
      plot.replaceChildren(); valueWrap.replaceChildren();
      if (!stats) {
        status.textContent = `${task.label} · ${subjectSelect.value || 'All subjects'} · No recorded values for this signal`;
        plot.append(el('p', 'No recorded values for this signal and subject.')); caption.textContent = ''; column.textContent = '';
        panel.dispatchEvent(new Event('toggle')); return;
      }
      const unit = displayUnit(signal.unit), counts = stats.n.filter((n) => n > 0);
      const nmin = counts.length ? Math.min(...counts) : 0, nmax = counts.length ? Math.max(...counts) : 0;
      const countText = nmin === nmax ? String(nmax) : `${nmin}–${nmax}`;
      const subject = subjectSelect.value;
      status.textContent = `${task.label} · ${subject || 'All subjects'} · ${countText} ${subject ? 'curves' : 'subjects'} contributing per recorded point`;
      column.replaceChildren('Column ', el('code', signal.column));
      plot.append(makeChart(payload.phase, stats, signal, band.checked, drawnWidth));
      const sdAvailable = stats.sd.some((sd, i) => finite(sd) && stats.n[i] >= 2);
      caption.textContent = subject
        ? 'Line: mean of this subject’s stored curves. Shading: ±1 standard deviation across curves.'
        : 'Line: mean of subject averages, with equal weight per subject. Shading: ±1 standard deviation between subject averages.';
      if (!band.checked) caption.textContent = caption.textContent.split(' Shading:')[0] + ' Standard deviation hidden.';
      else if (!sdAvailable) caption.textContent = caption.textContent.split(' Shading:')[0] + ' No band: standard deviation needs at least two contributors.';
      caption.textContent += ` Displayed in ${unit.label}; missing portions stay blank.`;
      const table = el('table'), head = el('thead'), tr = el('tr');
      ['Movement (%)', `Mean (${unit.label})`, `SD (${unit.label})`, subject ? 'Curves (n)' : 'Subjects (n)'].forEach((text) => { const th = el('th', text); th.scope = 'col'; tr.append(th); });
      head.append(tr); table.append(head); const body = el('tbody');
      payload.phase.forEach((phase, i) => {
        const row = el('tr');
        [phase, finite(stats.mean[i]) ? stats.mean[i] * unit.factor : null, finite(stats.sd[i]) ? stats.sd[i] * unit.factor : null, stats.n[i]].forEach((v) => row.append(el('td', fmt(v), 'num')));
        body.append(row);
      });
      table.append(body); valueWrap.append(table);
      panel.dispatchEvent(new Event('toggle'));
    }
    function updateSignals() {
      const previous = signalSelect.value || initialSignal; initialSignal = '';
      signalSelect.replaceChildren();
      if (!task.signals.length) return false;
      task.signals.forEach((signal) => signalSelect.add(new Option(`${signal.label} (${displayUnit(signal.unit).label})`, signal.column)));
      signalSelect.value = task.signals.some((s) => s.column === previous) ? previous
        : (task.signals.find((s) => s.column === 'knee_flexion_angle_ipsi_rad') || task.signals[0]).column;
      return true;
    }
    async function loadSubject() {
      const sequence = ++subjectNumber, subject = subjectSelect.value;
      if (subjectRequest) subjectRequest.abort();
      subjectPayload = undefined; subjectPending = subjectError = false; retry.hidden = true;
      const entry = subject && payload.subjects[subject];
      if (!subject || entry?.signals) {
        subjectPayload = entry; signalSelect.disabled = !task.signals.length; widget.setAttribute('aria-busy', 'false');
        if (task.signals.length) draw(); return;
      }
      subjectPending = true; signalSelect.disabled = true;
      plot.replaceChildren(); caption.textContent = ''; valueWrap.replaceChildren(); column.textContent = '';
      status.textContent = `Loading ${subject} averages…`; widget.setAttribute('aria-busy', 'true');
      subjectRequest = new AbortController();
      try {
        const response = await fetch(new URL(entry.url, new URL(task.url, manifestURL)), {signal: subjectRequest.signal});
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (current !== generation || sequence !== subjectNumber || subjectSelect.value !== subject || !widget.isConnected) return;
        subjectPayload = data; subjectPending = false; signalSelect.disabled = !task.signals.length; draw();
      } catch (error) {
        if (error.name !== 'AbortError' && current === generation && sequence === subjectNumber) {
          subjectPending = false; subjectError = true; status.textContent = `Averages for ${subject} could not be loaded. Retry or choose another subject.`; retry.hidden = false;
        }
      } finally { if (current === generation && sequence === subjectNumber) widget.setAttribute('aria-busy', 'false'); }
    }
    async function loadTask() {
      const sequence = ++requestNumber; retry.hidden = true;
      subjectNumber += 1; subjectPending = subjectError = false; subjectPayload = undefined;
      if (subjectRequest) subjectRequest.abort();
      if (request) request.abort(); request = new AbortController();
      const previousSubject = subjectSelect.value;
      task = dataset.tasks.find((t) => t.id === taskSelect.value);
      payload = undefined; subjectSelect.disabled = signalSelect.disabled = true;
      plot.replaceChildren(); caption.textContent = ''; valueWrap.replaceChildren(); column.textContent = '';
      status.textContent = `Loading ${task.label.toLowerCase()} averages…`;
      widget.setAttribute('aria-busy', 'true');
      try {
        const response = await fetch(new URL(task.url, manifestURL), {signal: request.signal});
        if (!response.ok) throw new Error();
        const data = await response.json();
        if (current !== generation || sequence !== requestNumber || !widget.isConnected) return;
        payload = data;
        subjectSelect.replaceChildren(new Option(`All subjects (${Object.keys(data.subjects).length})`, ''));
        Object.keys(data.subjects).sort().forEach((subject) => subjectSelect.add(new Option(subject, subject)));
        subjectSelect.value = Object.hasOwn(data.subjects, previousSubject) ? previousSubject : '';
        const hasSignals = updateSignals(); subjectSelect.disabled = false; signalSelect.disabled = !hasSignals;
        if (hasSignals) await loadSubject();
        else { status.textContent = `${task.label} · No recorded signals for this task`; plot.append(el('p', 'No recorded signals for this task.')); }
        if (current !== generation || sequence !== requestNumber) return;
        if (restoreSignalFocus && document.activeElement === document.body) (hasSignals ? signalSelect : taskSelect).focus();
        restoreSignalFocus = false;
      } catch (error) {
        if (error.name !== 'AbortError' && current === generation && sequence === requestNumber) {
          status.textContent = 'These averages could not be loaded. Retry or choose another task.'; retry.hidden = false;
        }
      } finally { if (current === generation && sequence === requestNumber) widget.setAttribute('aria-busy', 'false'); }
    }
    taskSelect.addEventListener('change', loadTask);
    retry.addEventListener('click', () => { if (payload && subjectSelect.value) loadSubject(); else loadTask(); });
    subjectSelect.addEventListener('change', loadSubject);
    signalSelect.addEventListener('change', () => draw()); band.addEventListener('change', () => draw());
    if ('ResizeObserver' in window) {
      let frame;
      observer = new ResizeObserver(() => {
        if (frame) return;
        frame = requestAnimationFrame(() => { frame = 0; if (current === generation && Math.abs(plot.clientWidth - drawnWidth) >= 1) draw(false); });
      });
      observer.observe(plot);
    }
    await loadTask();
  }
  window.LocoHubAverages = {mount, dispose};
})();
