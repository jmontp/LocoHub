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
        const variant = link.hasAttribute("data-dataset-notes") ? "Dataset notes"
          : {filtered: "Filtered download", full: "Full download", time: "Time data"}[link.dataset.download];
        if (variant) link.setAttribute("aria-label", `${name}: ${variant}`);
      });
      return { row, text: row.textContent.toLowerCase(),
        tasks: (cells[1].querySelector("[data-task-list]") || cells[1]).textContent.split(",").map((value) => value.trim()),
        filtered: Boolean(row.querySelector('[data-download="filtered"]')),
        full: Boolean(row.querySelector('[data-download="full"]')),
        time: Boolean(row.querySelector('[data-download="time"]')) };
    });
    Array.from(new Set(rows.flatMap((entry) => entry.tasks))).sort().forEach((name) => {
      task.add(new Option(name, name));
    });
    const empty = textElement("p", "No datasets match these filters. Use Reset to show all datasets.", "catalog-empty");
    empty.hidden = true;
    table.closest("[data-dataset-catalog]").appendChild(empty);
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
      status.textContent = `${visible} of ${rows.length} datasets shown.`;
      empty.hidden = visible > 0;
      document.dispatchEvent(new CustomEvent("locohub:catalog-filter", {
        detail: rows.filter((entry) => !entry.row.hidden).map((entry) => entry.row.dataset.dataset).filter(Boolean),
      }));
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
      initializeSearch();
  });
})();
