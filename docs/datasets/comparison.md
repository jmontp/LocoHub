---
title: Compare dataset coverage
---

# Compare dataset coverage

Choose a task to inspect the existing dataset documentation, available downloads, historical observation counts, and plots together.

!!! warning "Historical evidence, not a dataset ranking"
    These catalog records are legacy / unreviewed. Counts and plots may come from different file variants or rule versions. They are shown for investigation; they do not establish comparable pass rates or release approval. Check the exact input artifact and profile before using a historical report.

<div id="comparison-app" data-source="../comparison_data.json" aria-busy="true">
  <div class="catalog-controls" id="comparison-controls" hidden>
    <label for="comparison-task">Task <select id="comparison-task"></select></label>
    <fieldset><legend>Datasets to show</legend><div id="comparison-options"></div></fieldset>
  </div>
  <p id="comparison-status" role="status" aria-live="polite">Loading catalog records…</p>
  <div id="comparison-results" class="comparison-grid"></div>
</div>

<noscript><p>This comparison requires JavaScript. The <a href="../">dataset catalog</a> contains the same dataset documentation and download links without JavaScript.</p></noscript>

A missing task row means it is absent from the historical comparison metadata. It does not prove that the source study did not record the activity. Missing signals, unchecked rules, and excluded observations must be assessed in the release evidence.
