/* Progressive enhancement: the native catalog table remains usable without JS. */
(function () {
  "use strict";

  function initializeCatalog() {
    const table = document.querySelector("[data-dataset-catalog] table");
    if (!table) return;
    const controls = document.getElementById("catalog-controls");
    const search = document.getElementById("catalog-search");
    const task = document.getElementById("catalog-task");
    const availability = document.getElementById("catalog-download");
    const status = document.getElementById("catalog-status");
    const rows = Array.from(table.tBodies[0].rows).map((row) => {
      const cells = row.cells;
      const name = cells[0].textContent.trim();
      row.querySelectorAll("a").forEach((link) => {
        const column = link.closest("td").cellIndex;
        const variant = {3: "Documentation", 4: "Profile-filtered phase", 5: "Full converted phase", 6: "Time data"}[column];
        link.setAttribute("aria-label", `${name}: ${variant}`);
      });
      return { row, text: row.textContent.toLowerCase(),
        tasks: cells[1].textContent.split(",").map((value) => value.trim()),
        filtered: Boolean(cells[4].querySelector("a")),
        full: Boolean(cells[5].querySelector("a")),
        time: Boolean(cells[6].querySelector("a")) };
    });
    Array.from(new Set(rows.flatMap((entry) => entry.tasks))).sort().forEach((name) => {
      task.add(new Option(name, name));
    });
    function update() {
      const query = search.value.trim().toLowerCase();
      let visible = 0;
      rows.forEach((entry) => {
        const matchesAvailability = !availability.value || (availability.value === "none"
          ? !entry.full && !entry.filtered && !entry.time : entry[availability.value]);
        const matches = entry.text.includes(query) && (!task.value || entry.tasks.includes(task.value)) && matchesAvailability;
        entry.row.hidden = !matches;
        if (matches) visible += 1;
      });
      status.textContent = `${visible} of ${rows.length} datasets shown. All current listings are legacy / unreviewed.`;
    }
    search.addEventListener("input", update);
    task.addEventListener("change", update);
    availability.addEventListener("change", update);
    document.getElementById("catalog-reset").addEventListener("click", () => {
      search.value = ""; task.value = ""; availability.value = ""; update(); search.focus();
    });
    controls.hidden = false;
    update();
  }

  function textElement(tag, text, className) {
    const element = document.createElement(tag);
    element.textContent = text;
    if (className) element.className = className;
    return element;
  }

  function addLink(parent, text, href) {
    const url = new URL(href, window.location.href);
    if (!["https:", "http:"].includes(url.protocol)) return;
    const link = textElement("a", text);
    link.href = url.href;
    parent.appendChild(link);
  }

  async function initializeComparison() {
    const app = document.getElementById("comparison-app");
    if (!app) return;
    const status = document.getElementById("comparison-status");
    const results = document.getElementById("comparison-results");
    try {
      const source = new URL(app.dataset.source, window.location.href);
      const response = await fetch(source);
      if (!response.ok) throw new Error("Catalog unavailable");
      const payload = await response.json();
      if (!Array.isArray(payload.datasets) || !payload.datasets.length) throw new Error("Catalog empty");
      const datasets = payload.datasets;
      const datasetRoot = new URL("./", source);
      const taskSelect = document.getElementById("comparison-task");
      const options = document.getElementById("comparison-options");
      const tasks = new Map();
      datasets.forEach((dataset) => (dataset.tasks || []).forEach((task) => {
        tasks.set(task.task, task.display_name || task.task);
      }));
      if (!tasks.size) throw new Error("No task records");
      Array.from(tasks).sort((a, b) => a[1].localeCompare(b[1])).forEach(([key, label]) => {
        taskSelect.add(new Option(label, key));
      });
      const checks = new Map();
      datasets.forEach((dataset) => {
        const label = textElement("label", "", "dataset-option");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox"; checkbox.checked = true;
        label.append(checkbox, document.createTextNode(` ${dataset.display_name}`));
        options.appendChild(label); checks.set(dataset.slug, checkbox);
      });
      function render() {
        results.replaceChildren();
        let shown = 0;
        datasets.forEach((dataset) => {
          if (!checks.get(dataset.slug).checked) return;
          const task = (dataset.tasks || []).find((entry) => entry.task === taskSelect.value);
          if (!task) return;
          shown += 1;
          const card = textElement("article", "", "comparison-card");
          card.append(textElement("h2", dataset.display_name), textElement("p", "Legacy / unreviewed", "release-status"));
          const count = Number.isFinite(task.total_strides) ? task.total_strides.toLocaleString() : "not recorded";
          card.appendChild(textElement("p", `Historical observations for this task: ${count}. This count is not the number of independent participants.`));
          const links = textElement("div", "", "comparison-links");
          addLink(links, "Study documentation and limitations", new URL(`${dataset.slug}/`, datasetRoot));
          if (dataset.dirty_url) addLink(links, "Full converted phase download", dataset.dirty_url);
          if (dataset.clean_url) addLink(links, "Profile-filtered phase download", dataset.clean_url);
          card.appendChild(links);
          if (!dataset.dirty_url && !dataset.clean_url) card.appendChild(textElement("p", "No phase download is registered."));
          const plots = task.plots || [];
          if (!plots.length) card.appendChild(textElement("p", "No historical plot is registered for this task."));
          plots.forEach((path) => {
            const figure = document.createElement("figure");
            const image = document.createElement("img");
            image.src = new URL(path, datasetRoot).href;
            image.alt = `${dataset.display_name}: historical ${tasks.get(taskSelect.value)} validation plot; consult the study report for checked features and exclusions.`;
            image.loading = "lazy";
            image.addEventListener("error", () => {
              image.replaceWith(textElement("p", "Historical plot unavailable. Open the study documentation for the recorded evidence."));
            }, { once: true });
            figure.append(image, textElement("figcaption", "Historical plot — input file and profile require verification."));
            card.appendChild(figure);
          });
          results.appendChild(card);
        });
        status.textContent = shown ? `${shown} dataset records include ${tasks.get(taskSelect.value)}. Historical evidence is not a quality ranking.`
          : "No selected dataset has this task in its historical metadata. Choose another task or dataset.";
      }
      taskSelect.value = tasks.has("level_walking") ? "level_walking" : taskSelect.options[0].value;
      taskSelect.addEventListener("change", render);
      checks.forEach((checkbox) => checkbox.addEventListener("change", render));
      document.getElementById("comparison-controls").hidden = false;
      render();
    } catch (error) {
      status.textContent = "Comparison records could not be loaded. Use the dataset catalog to open documentation and downloads.";
      addLink(results, "Open dataset catalog", "../");
    } finally {
      app.setAttribute("aria-busy", "false");
    }
  }

  async function initializeSearch() {
    const results = document.getElementById("search-results");
    if (!results) return;
    const input = document.getElementById("site-search-query");
    const form = document.getElementById("site-search-form");
    const status = document.getElementById("search-status");
    let records;
    async function search() {
      const query = input.value.trim().slice(0, 120);
      const tokens = query.toLocaleLowerCase().split(/\s+/).filter(Boolean);
      results.replaceChildren();
      if (!tokens.length) {
        status.textContent = "Enter words to search the documentation.";
        return;
      }
      status.textContent = "Searching documentation…";
      const current = new URL(window.location.href);
      current.searchParams.set("q", query);
      window.history.replaceState(null, "", current);
      try {
        if (!records) {
          const response = await fetch(new URL(results.dataset.searchSource, window.location.href));
          if (!response.ok) throw new Error("Search index unavailable");
          records = await response.json();
        }
        const matches = records.map((record) => {
          const title = record.title.toLocaleLowerCase();
          const text = record.text.toLocaleLowerCase();
          return { record, score: tokens.reduce((score, token) => score + (title.includes(token) ? 5 : 0), 0),
            matches: tokens.every((token) => title.includes(token) || text.includes(token)) };
        }).filter((entry) => entry.matches).sort((a, b) => b.score - a.score).slice(0, 20);
        for (const { record } of matches) {
          const item = document.createElement("li");
          const heading = document.createElement("h2");
          const root = new URL("../", window.location.href);
          addLink(heading, record.title, new URL(record.url, root));
          const first = record.text.toLocaleLowerCase().indexOf(tokens[0]);
          const start = Math.max(0, first - 65);
          const snippet = `${start ? "…" : ""}${record.text.slice(start, start + 240)}${record.text.length > start + 240 ? "…" : ""}`;
          item.append(heading, textElement("p", snippet));
          results.appendChild(item);
        }
        status.textContent = matches.length ? `${matches.length} matching pages shown.` : "No matching pages. Try a task, signal name, or a shorter phrase.";
      } catch (error) {
        status.textContent = "The search index could not be loaded. Use the navigation or dataset catalog to browse.";
      }
    }
    form.addEventListener("submit", (event) => { event.preventDefault(); search(); });
    input.value = new URL(window.location.href).searchParams.get("q") || "";
    if (input.value) await search();
  }

  document.addEventListener("DOMContentLoaded", () => {
    initializeCatalog();
    initializeComparison();
    initializeSearch();
  });
})();
