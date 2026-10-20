/* Small pre-exported research samples. No browser Parquet reader or backend. */
(function () {
  "use strict";
  const panel = document.getElementById("data-preview");
  if (!panel) return;
  const buttons = Array.from(document.querySelectorAll("[data-preview-dataset]"));
  let samples;
  let selected;
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

  function chart(sample, signal) {
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
    const X = (x) => 60 + (x - xmin) / (xmax - xmin || 1) * 600;
    const Y = (y) => 210 - (y - ymin) / (ymax - ymin) * 175;
    const svg = svgNode("svg", {viewBox: "0 0 700 260", role: "img", "aria-label": `${signal.label} in degrees across the sample. Exact stored values are in the table below.`});
    svg.append(svgNode("title", {}, `${signal.label} — sample data`));
    for (let i = 0; i < 4; i += 1) {
      const value = ymin + (ymax - ymin) * i / 3;
      svg.append(svgNode("line", {x1: 60, x2: 660, y1: Y(value), y2: Y(value), class: "preview-grid"}));
      svg.append(svgNode("text", {x: 50, y: Y(value) + 4, "text-anchor": "end"}, Number(value.toPrecision(3))));
    }
    for (let i = 0; i < 5; i += 1) {
      const value = xmin + (xmax - xmin) * i / 4;
      svg.append(svgNode("text", {x: X(value), y: 231, "text-anchor": "middle"}, Number(value.toPrecision(3))));
    }
    svg.append(svgNode("text", {x: 60, y: 18}, `${signal.label} (degrees)`));
    svg.append(svgNode("text", {x: 360, y: 254, "text-anchor": "middle"}, sample.phase_display));
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

  function render(slug) {
    const button = buttons.find((item) => item.dataset.previewDataset === slug);
    if (!button) return;
    selected = slug;
    buttons.forEach((item) => {
      const active = item === button;
      item.setAttribute("aria-pressed", String(active));
      item.closest("tr").classList.toggle("selected-dataset", active);
    });
    panel.replaceChildren();
    const row = button.closest("tr");
    const name = row.cells[0].textContent.trim();
    const heading = element("h2", `${name} — data preview`);
    heading.id = "preview-title";
    panel.setAttribute("aria-labelledby", heading.id);
    panel.append(heading);
    const sample = samples.datasets[slug];
    if (!sample || !sample.available) {
      panel.append(element("p", sample?.reason || "No small data preview is available yet."));
      const details = row.querySelector("[data-dataset-notes]");
      if (details) { const link = details.cloneNode(true); link.textContent = "Open dataset notes"; panel.append(link); }
      return;
    }
    panel.append(element("p", "Small sample from a local file; it may differ from the download.", "preview-note"));
    panel.append(element("p", `${sample.rows.length} rows · ${sample.columns.length} of ${sample.source.file_columns} columns · ${sample.source.filename}`, "preview-meta"));
    const controls = element("div", undefined, "preview-controls");
    const label = element("label", "Signal ");
    const select = element("select");
    select.id = "preview-signal";
    label.htmlFor = select.id;
    sample.signals.forEach((signal) => select.add(new Option(signal.label, signal.column)));
    const plot = element("div");
    function draw() {
      const signal = sample.signals.find((item) => item.column === select.value);
      plot.replaceChildren();
      if (signal) plot.append(chart(sample, signal));
      else plot.append(element("p", "No angle columns are available in this sample."));
    }
    label.append(select); controls.append(label); panel.append(controls, plot);
    select.addEventListener("change", draw);
    if (sample.signals.some((signal) => signal.column === "knee_flexion_angle_ipsi_rad")) select.value = "knee_flexion_angle_ipsi_rad";
    draw();

    const details = element("details");
    details.append(element("summary", "Sample rows"));
    details.open = true;
    const wrap = element("div", undefined, "preview-table-wrap");
    wrap.tabIndex = 0; wrap.setAttribute("role", "region"); wrap.setAttribute("aria-label", `${name} sample rows`);
    const table = element("table");
    const head = element("thead"), header = element("tr");
    sample.columns.forEach((column) => {
      const cell = element("th", column); cell.scope = "col"; header.append(cell);
    });
    head.append(header); table.append(head);
    const body = element("tbody"); table.append(body);
    let showAll = false;
    const toggle = element("button", `Show all ${sample.rows.length} rows`);
    toggle.type = "button";
    function rows() {
      body.replaceChildren();
      (showAll ? sample.rows : sample.rows.slice(0, 8)).forEach((values) => {
        const tr = element("tr");
        sample.columns.forEach((column) => tr.append(element("td", format(values[column]))));
        body.append(tr);
      });
      toggle.textContent = showAll ? "Show first 8 rows" : `Show all ${sample.rows.length} rows`;
      toggle.setAttribute("aria-expanded", String(showAll));
    }
    toggle.addEventListener("click", () => { showAll = !showAll; rows(); });
    rows(); wrap.append(table); details.append(wrap, toggle); panel.append(details);

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
  }

  buttons.forEach((button) => button.addEventListener("click", () => {
    if (!samples) return;
    history.replaceState(null, "", `#${button.dataset.previewDataset}`);
    render(button.dataset.previewDataset);
    panel.scrollIntoView({block: "start", behavior: "auto"});
  }));
  window.addEventListener("hashchange", () => {
    const slug = window.location.hash.slice(1);
    if (samples && buttons.some((button) => button.dataset.previewDataset === slug)) render(slug);
  });
  document.addEventListener("locohub:catalog-filter", (event) => {
    if (!samples) return;
    const visible = event.detail;
    if (visible.length && !visible.includes(selected)) {
      history.replaceState(null, "", `#${visible[0]}`);
      render(visible[0]);
    } else if (!visible.length) {
      selected = null;
      panel.replaceChildren(element("h2", "Data preview"), element("p", "No datasets match these filters."));
    }
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
      else panel.replaceChildren(element("h2", "Data preview"), element("p", "No datasets match these filters."));
    })
    .catch(() => {
      panel.replaceChildren(element("h2", "Data preview"), element("p", "The sample could not be loaded. Dataset notes and downloads are still available in the table."));
    })
    .finally(() => panel.setAttribute("aria-busy", "false"));
})();
