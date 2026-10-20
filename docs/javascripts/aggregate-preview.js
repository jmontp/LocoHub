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
  const finite = Number.isFinite;
  const fmt = (value) => finite(value) ? Number(value.toPrecision(5)).toString() : '—';
  function dispose() {
    generation += 1;
    if (request) request.abort();
    if (subjectRequest) subjectRequest.abort();
    if (observer) observer.disconnect();
    request = subjectRequest = observer = undefined;
  }
  const {makeChart, displayUnit} = window.LocoHubPhaseChart;

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
    const rangeToggle = el('input'); rangeToggle.type = 'checkbox'; rangeToggle.checked = true;
    const rangeLabel = el('label', undefined, 'aggregate-band-control'); rangeLabel.append(rangeToggle, document.createTextNode('Show configured range boxes'));
    const rangeDetails = el('details', undefined, 'range-values'); rangeDetails.append(el('summary', 'Configured bounds and mean at each check'));
    const rangeBody = el('div'); rangeDetails.append(rangeBody);
    widget.append(form, bandLabel);
    if (options.rangeProfile) widget.append(rangeLabel);
    widget.append(status, retry, column, figure, values);
    if (options.rangeProfile) widget.append(rangeDetails);
    widget.append(method);
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
      const ranges = options.rangeProfile?.tasks?.[task.id]?.[signal.column] || [];
      plot.append(makeChart(payload.phase, stats, signal, band.checked, drawnWidth, undefined, rangeToggle.checked ? ranges : []));
      if (options.rangeProfile) {
        rangeBody.replaceChildren();
        rangeBody.append(el('p', ranges.length ? 'Boxes show the configured minimum and maximum at each sampled phase. Their width is visual only. Comparing an average with these limits is not an observation-level pass/fail result.' : 'No phase bounds are configured for this task and signal. This is unchecked, not a pass.'));
        if (ranges.length) {
          const wrap = el('div', undefined, 'preview-table-wrap'); wrap.tabIndex = 0;
          const table = el('table'), head = el('thead'), row = el('tr');
          ['Check (%)', 'Sample (%)', `Minimum (${unit.label})`, `Maximum (${unit.label})`, 'Displayed mean', 'Mean relative to bounds'].forEach(t => { const h = el('th', t); h.scope = 'col'; row.append(h); });
          head.append(row); table.append(head); const body = el('tbody');
          ranges.forEach(r => {
            const mean = stats.mean[r.sample_index], relation = !finite(mean) ? 'Missing' : mean < r.min ? 'Below' : mean > r.max ? 'Above' : 'Within';
            const tr = el('tr'); [fmt(r.phase), fmt(r.sample_phase), fmt(r.min * unit.factor), fmt(r.max * unit.factor), fmt(finite(mean) ? mean * unit.factor : null), relation].forEach(v => tr.append(el('td', v))); body.append(tr);
          }); table.append(body); wrap.append(table); rangeBody.append(wrap);
        }
      }
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
    signalSelect.addEventListener('change', () => draw()); band.addEventListener('change', () => draw()); rangeToggle.addEventListener('change', () => draw());
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
