/* Optional visual styles for the data browser. No data or preview state changes. */
(function () {
  "use strict";
  const names = {slate: "Slate", paper: "Paper", blueprint: "Blueprint", sage: "Sage", ink: "Ink"};
  const storageKey = "locohub.visualStyle";
  const root = document.documentElement;
  const valid = (value) => Object.prototype.hasOwnProperty.call(names, value);
  let current = "slate";
  try {
    const saved = window.localStorage.getItem(storageKey);
    if (valid(saved)) current = saved;
  } catch (_) {
    // The selector also works when browser storage is unavailable.
  }
  root.dataset.style = current;

  function initialize() {
    const picker = document.querySelector(".visual-style-picker");
    if (!picker) return;
    const summary = picker.querySelector("summary");
    const label = picker.querySelector("[data-style-label]");
    const choices = Array.from(picker.querySelectorAll('input[name="visual-style"]'));
    const status = document.getElementById("visual-style-status");

    function apply(value, persist, announce) {
      current = valid(value) ? value : "slate";
      root.dataset.style = current;
      label.textContent = names[current];
      choices.forEach((choice) => { choice.checked = choice.value === current; });
      if (persist) {
        try { window.localStorage.setItem(storageKey, current); } catch (_) {}
      }
      if (announce && status) status.textContent = `${names[current]} style selected.`;
    }

    choices.forEach((choice) => {
      choice.addEventListener("change", () => {
        if (choice.checked) apply(choice.value, true, true);
      });
    });
    picker.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && picker.open) {
        picker.open = false;
        summary.focus();
        event.preventDefault();
      }
    });
    document.addEventListener("click", (event) => {
      if (picker.open && !picker.contains(event.target)) picker.open = false;
    });
    window.addEventListener("storage", (event) => {
      if (event.key === storageKey || event.key === null) apply(event.newValue, false, false);
    });
    apply(current, false, false);
    picker.hidden = false;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, {once: true});
  } else {
    initialize();
  }
})();
