/* Small pre-exported research samples. No browser Parquet reader or backend. */
(function () {
  "use strict";
  const panel = document.getElementById("data-preview");
  if (!panel) return;
  const buttons = Array.from(document.querySelectorAll("[data-preview-dataset]"));
  const names = new Map(buttons.map((button) => [button, button.closest("tr").cells[0].textContent.trim()]));
  const announcer = document.getElementById("preview-status");
  // Must match the .catalog-layout breakpoint in site.css.
  const split = window.matchMedia("(min-width: 1200px)");
  let samples;
  let selected;
  let observer;
  const element = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const format = (value) => typeof value === "number"
    ? Number(value.toPrecision(6)).toString() : value === null || value === undefined ? "—" : String(value);
  const svgNode = (tag, attributes, text) => {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  };

  // Round tick spacing to 1, 2 or 5 times a power of ten.
  function ticks(min, max, count) {
    const span = max - min;
    if (!(span > 0)) return [min];
    const raw = span / count;
    const power = 10 ** Math.floor(Math.log10(raw));
    const scaled = raw / power;
    const step = (scaled < 1.5 ? 1 : scaled < 3 ? 2 : scaled < 7 ? 5 : 10) * power;
    const values = [];
    for (let value = Math.ceil(min / step) * step; value <= max + step * 1e-9; value += step) {
      values.push(Number(value.toPrecision(12)));
    }
    return values;
  }

  function chart(sample, signal, width) {
    const figure = element("figure", undefined, "preview-chart");
    const points = sample.rows.map((row) => [
      row.phase_ipsi,
      Number.isFinite(row[signal.column]) ? row[signal.column] * 180 / Math.PI : null,
    ]);
    const finite = points.filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y));
    if (!sample.chart_available || !finite.length) {
      figure.append(element("p", "No plottable values in this sample. The rows below show what is available."));
      return figure;
    }
    const xs = finite.map(([x]) => x), ys = finite.map(([, y]) => y);
    const xmin = Math.min(...xs), xmax = Math.max(...xs);
    const low = Math.min(...ys), high = Math.max(...ys);
    const padding = Math.max((high - low) * 0.12, 1);
    const ymin = low - padding, ymax = high + padding;
    // The viewBox tracks the rendered width so 12px axis text stays 12px.
    const W = Math.max(320, Math.round(width || 640)), H = 260;
    const left = 46, right = 14, top = 30, bottom = 44;
    const X = (x) => left + (x - xmin) / (xmax - xmin || 1) * (W - left - right);
    const Y = (y) => H - bottom - (y - ymin) / (ymax - ymin) * (H - top - bottom);
    const svg = svgNode("svg", {viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${signal.label} in degrees across the sample. Exact stored values are in the table below.`});
    svg.append(svgNode("title", {}, `${signal.label} — sample data`));
    ticks(ymin, ymax, 4).forEach((value) => {
      svg.append(svgNode("line", {x1: left, x2: W - right, y1: Y(value), y2: Y(value), class: "preview-grid"}));
      svg.append(svgNode("text", {x: left - 8, y: Y(value) + 4, "text-anchor": "end"}, value));
    });
    if (ymin < 0 && ymax > 0) svg.append(svgNode("line", {x1: left, x2: W - right, y1: Y(0), y2: Y(0), class: "preview-zero"}));
    svg.append(svgNode("line", {x1: left, x2: W - right, y1: H - bottom, y2: H - bottom, class: "preview-baseline"}));
    ticks(xmin, xmax, 4).forEach((value) => {
      svg.append(svgNode("text", {x: X(value), y: H - bottom + 17, "text-anchor": "middle"}, value));
    });
    svg.append(svgNode("text", {x: 0, y: 13, class: "preview-axis-title"}, `${signal.label} (degrees)`));
    svg.append(svgNode("text", {x: left + (W - left - right) / 2, y: H - 6, "text-anchor": "middle"}, sample.phase_display));
    let path = "", connected = false;
    points.forEach(([x, y]) => {
      if (!Number.isFinite(x) || !Number.isFinite(y)) { connected = false; return; }
      path += `${connected ? "L" : "M"}${X(x).toFixed(2)},${Y(y).toFixed(2)} `;
      connected = true;
    });
    svg.append(svgNode("path", {d: path, class: "preview-line"}));
    figure.append(svg, element("figcaption", "One small sample, not a dataset average. Plot angles are in degrees; file values below are in radians."));
    return figure;
  }

  function title(text) {
    const heading = element("h2", text);
    heading.id = "preview-title";
    heading.tabIndex = -1;
    return heading;
  }

  function message(text) {
    window.LocoHubAverages?.dispose();
    panel.replaceChildren(title("Data preview"), element("p", text));
    updateScrollable();
  }

  // A capped sticky panel that overflows must be reachable by keyboard.
  function updateScrollable() {
    if (panel.scrollHeight > panel.clientHeight + 1) panel.tabIndex = 0;
    else panel.removeAttribute("tabindex");
  }

  function render(slug, options = {}) {
    const button = buttons.find((item) => item.dataset.previewDataset === slug);
    if (!button) return;
    selected = slug;
    window.LocoHubAverages?.dispose();
    if (observer) { observer.disconnect(); observer = undefined; }
    buttons.forEach((item) => {
      const active = item === button;
      item.setAttribute("aria-pressed", String(active));
      item.textContent = active ? "Showing" : "Preview";
      item.setAttribute("aria-label", `${active ? "Showing" : "Preview"} ${names.get(item)}`);
      item.closest("tr").classList.toggle("selected-dataset", active);
    });
    panel.replaceChildren();
    const row = button.closest("tr");
    const name = names.get(button);
    const head = element("div", undefined, "preview-head");
    const label = element("div");
    label.append(element("p", "Data preview", "preview-kicker"), title(name));
    const back = element("button", "Back to table", "preview-back");
    back.type = "button";
    back.addEventListener("click", () => button.focus());
    head.append(label, back);
    panel.setAttribute("aria-labelledby", "preview-title");
    panel.append(head);
    if (options.announce && announcer) announcer.textContent = `Showing ${name} preview.`;
    const sample = samples.datasets[slug];
    if (!sample || !sample.available) {
      const meta = element("p", "", "preview-meta");
      const note = element("p", sample?.reason || "No small data preview is available yet.", "preview-note");
      const controls = element("div"), plot = element("div");
      panel.append(meta, note, controls, plot);
      const details = row.querySelector("[data-dataset-notes]");
      if (details) { const link = details.cloneNode(true); link.textContent = "Open dataset notes"; panel.append(link); }
      window.LocoHubAverages?.mount({panel, slug, anchor: head, controls, plot, meta, note, sampleRows: null, sample,
        stopRawChart: () => {}
      }).catch(() => { if (head.isConnected) note.textContent += " Task averages are unavailable."; });
      updateScrollable();
      return;
    }
    const meta = element("p", `${sample.rows.length} rows · ${sample.columns.length} of ${sample.source.file_columns} columns · `, "preview-meta");
    meta.append(element("code", sample.source.filename));
    panel.append(meta);
    const note = element("p", "Small sample from a local file; it may differ from the download.", "preview-note");
    panel.append(note);
    const controls = element("div", undefined, "preview-controls");
    const signalLabel = element("label", "Signal ");
    const select = element("select");
    select.id = "preview-signal";
    signalLabel.htmlFor = select.id;
    sample.signals.forEach((signal) => select.add(new Option(signal.label, signal.column)));
    const column = element("span", undefined, "preview-column");
    const plot = element("div", undefined, "preview-plot");
    let drawnWidth = 0;
    function draw() {
      const signal = sample.signals.find((item) => item.column === select.value);
      drawnWidth = plot.clientWidth;
      column.replaceChildren();
      if (signal) column.append("Column ", element("code", signal.column));
      plot.replaceChildren(signal ? chart(sample, signal, drawnWidth)
        : element("p", "No angle columns are available in this sample."));
    }
    signalLabel.append(select); controls.append(signalLabel, column); panel.append(controls, plot);
    select.addEventListener("change", draw);
    if (sample.signals.some((signal) => signal.column === "knee_flexion_angle_ipsi_rad")) select.value = "knee_flexion_angle_ipsi_rad";
    draw();
    if ("ResizeObserver" in window) {
      let frame = 0;
      observer = new ResizeObserver(() => {
        if (frame) return;
        frame = requestAnimationFrame(() => {
          frame = 0;
          if (Math.abs(plot.clientWidth - drawnWidth) >= 1) draw();
        });
      });
      observer.observe(plot);
    }

    const details = element("details");
    details.append(element("summary", "Sample rows"));
    const wrap = element("div", undefined, "preview-table-wrap");
    wrap.tabIndex = 0; wrap.setAttribute("role", "region"); wrap.setAttribute("aria-label", `${name} sample rows`);
    const numeric = new Set(sample.columns.filter((key) => sample.rows.some((values) => typeof values[key] === "number")));
    const table = element("table");
    const tableHead = element("thead"), header = element("tr");
    sample.columns.forEach((key) => {
      const cell = element("th", key, numeric.has(key) ? "num" : undefined); cell.scope = "col"; header.append(cell);
    });
    tableHead.append(header); table.append(tableHead);
    const body = element("tbody"); table.append(body);
    let showAll = false;
    const toggle = element("button", `Show all ${sample.rows.length} rows`, "preview-rows-toggle");
    toggle.type = "button";
    function rows() {
      body.replaceChildren();
      (showAll ? sample.rows : sample.rows.slice(0, 8)).forEach((values) => {
        const tr = element("tr");
        sample.columns.forEach((key) => tr.append(element("td", format(values[key]), numeric.has(key) ? "num" : undefined)));
        body.append(tr);
      });
      toggle.textContent = showAll ? "Show first 8 rows" : `Show all ${sample.rows.length} rows`;
      toggle.setAttribute("aria-expanded", String(showAll));
      updateScrollable();
    }
    toggle.addEventListener("click", () => { showAll = !showAll; rows(); });
    wrap.append(table); details.append(wrap, toggle); panel.append(details); rows();

    const load = element("details");
    load.append(element("summary", "Load a downloaded file"));
    load.append(element("p", "Use the filename of the download you saved. This local preview may be a different version."));
    [["Python", 'import pandas as pd\ndata = pd.read_parquet("your_download.parquet")\nprint(data.head())'],
      ["MATLAB", 'data = parquetread("your_download.parquet");\nhead(data)']].forEach(([language, code]) => {
      load.append(element("h3", language));
      const pre = element("pre", undefined, "preview-code"); pre.append(element("code", code)); load.append(pre);
    });
    panel.append(load);
    const source = element("details");
    source.append(element("summary", "About this preview"));
    source.append(element("p", sample.source.note));
    source.append(element("p", `${sample.source.selection} Missing and nonfinite numbers are shown as —. Some older files reuse cycle numbers across recordings; this sample does not check for that.`));
    source.append(element("p", "The full source file was not hashed or compared with the online download. This checksum identifies the exported sample rows only."));
    source.append(element("code", sample.source.sample_sha256));
    panel.append(source);
    window.LocoHubAverages?.mount({panel, slug, anchor: head, controls, plot, meta, note, sampleRows: details, sample,
      stopRawChart: () => { if (observer) { observer.disconnect(); observer = undefined; } source.querySelector("summary").textContent = "About these example rows"; }
    }).catch(() => { if (head.isConnected) note.textContent += " Task averages are unavailable."; });
    updateScrollable();
  }

  buttons.forEach((button) => button.addEventListener("click", () => {
    if (!samples) return;
    const slug = button.dataset.previewDataset;
    const stacked = !split.matches;
    history.replaceState(null, "", `#${slug}`);
    // Side by side: update in place and keep focus on the button. Stacked: move to the preview.
    if (slug !== selected) render(slug, {announce: !stacked});
    if (stacked) {
      panel.scrollIntoView({block: "start", behavior: "auto"});
      document.getElementById("preview-title")?.focus({preventScroll: true});
    }
  }));
  window.addEventListener("hashchange", () => {
    const slug = window.location.hash.slice(1);
    if (samples && buttons.some((button) => button.dataset.previewDataset === slug)) render(slug, {announce: true});
  });
  document.addEventListener("locohub:catalog-filter", (event) => {
    if (!samples) return;
    const visible = event.detail;
    if (visible.length && !visible.includes(selected)) {
      history.replaceState(null, "", `#${visible[0]}`);
      render(visible[0], {announce: true});
    } else if (!visible.length) {
      selected = null;
      message("No datasets match these filters.");
    }
  });
  panel.addEventListener("toggle", updateScrollable, true);
  let resizeFrame = 0;
  window.addEventListener("resize", () => {
    if (resizeFrame) return;
    resizeFrame = requestAnimationFrame(() => { resizeFrame = 0; updateScrollable(); });
  });
  panel.setAttribute("aria-busy", "true");
  fetch(new URL(panel.dataset.previewSource, window.location.href))
    .then((response) => { if (!response.ok) throw new Error("Preview unavailable"); return response.json(); })
    .then((payload) => {
      samples = payload;
      const requested = window.location.hash.slice(1);
      const visible = buttons.filter((button) => !button.closest("tr").hidden);
      const first = visible.find((button) => button.dataset.previewDataset === requested) || visible[0];
      if (first) render(first.dataset.previewDataset);
      else message("No datasets match these filters.");
    })
    .catch(() => {
      message("The sample could not be loaded. Dataset notes and downloads are still available in the table.");
    })
    .finally(() => panel.setAttribute("aria-busy", "false"));
})();
