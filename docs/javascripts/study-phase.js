/* A study page uses the same task/subject explorer as the catalog preview. */
(function () {
  'use strict';
  const panel = document.querySelector('[data-study-phase]');
  if (!panel) return;
  async function load() {
    window.LocoHubAverages.dispose();
    const note = panel.querySelector('.phase-note');
    panel.querySelector('.phase-retry')?.remove();
    note.textContent = 'Loading task averages…';
    await window.LocoHubAverages.mount({panel, slug: panel.dataset.studyPhase, anchor: panel,
      controls: panel.querySelector('.phase-controls'), plot: panel.querySelector('.phase-plot'),
      meta: panel.querySelector('.phase-source'), note, stopRawChart() {}});
    if (!panel.querySelector('.aggregate-preview')) {
      if (note.textContent.includes('could not be loaded')) {
        note.textContent = 'Task averages could not be loaded.';
        const retry = document.createElement('button'); retry.type = 'button'; retry.className = 'phase-retry button'; retry.textContent = 'Retry averages';
        retry.addEventListener('click', load); panel.append(retry);
      } else note.textContent = 'Interactive averages are not available for this study. Its earlier reports and downloads are listed on this page.';
    }
  }
  load();
})();
