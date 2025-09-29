---
title: Dataset Comparison
---

# Dataset Comparison

Compare validation outcomes across datasets. Pick a task, choose the datasets you care about, and review pass rates, download links, and validation plots side-by-side.

<div id="comparison-app" class="comparison-app">
  <div class="comparison-controls">
    <label for="task-select">Task</label>
    <select id="task-select"></select>

    <fieldset class="dataset-select">
      <legend>Datasets</legend>
      <div id="dataset-options"></div>
    </fieldset>
  </div>

  <div id="comparison-results" class="comparison-grid"></div>
</div>

<template id="dataset-option-template">
  <label class="dataset-option">
    <input type="checkbox" />
    <span class="dataset-name"></span>
  </label>
</template>

<template id="comparison-card-template">
  <div class="comparison-card">
    <div class="card-header">
      <div>
        <h3 class="dataset-title"></h3>
        <p class="dataset-slug"></p>
      </div>
      <span class="dataset-quality"></span>
    </div>
    <p class="task-status"></p>
    <div class="card-buttons"></div>
    <div class="card-plots"></div>
  </div>
</template>

<script>
(async function () {
  const resultsContainer = document.getElementById('comparison-results');
  const taskSelect = document.getElementById('task-select');
  const datasetOptionsContainer = document.getElementById('dataset-options');
  const datasetOptionTemplate = document.getElementById('dataset-option-template');
  const cardTemplate = document.getElementById('comparison-card-template');

  let comparisonData = { datasets: [] };
  try {
    const response = await fetch('./comparison_data.json');
    if (!response.ok) throw new Error('Failed to load comparison data');
    comparisonData = await response.json();
  } catch (error) {
    resultsContainer.innerHTML = `<div class="comparison-error">⚠️ ${error.message}</div>`;
    return;
  }

  const datasets = comparisonData.datasets || [];
  if (!datasets.length) {
    resultsContainer.innerHTML = '<div class="comparison-error">No datasets available yet. Run the documentation tool to generate comparison information.</div>';
    return;
  }

  const allTasks = Array.from(new Set(datasets.flatMap((dataset) => (dataset.tasks || []).map((task) => task.display_name)))).sort();
  if (!allTasks.length) {
    resultsContainer.innerHTML = '<div class="comparison-error">No validation tasks available for comparison.</div>';
    return;
  }

  for (const task of allTasks) {
    const option = document.createElement('option');
    option.value = task;
    option.textContent = task;
    taskSelect.appendChild(option);
  }

  const datasetCheckboxes = new Map();
  datasets.forEach((dataset) => {
    const optionNode = datasetOptionTemplate.content.cloneNode(true);
    const label = optionNode.querySelector('label');
    const input = optionNode.querySelector('input');
    const nameSpan = optionNode.querySelector('.dataset-name');

    input.value = dataset.slug;
    input.checked = true;
    nameSpan.textContent = dataset.display_name;
    datasetOptionsContainer.appendChild(optionNode);
    datasetCheckboxes.set(dataset.slug, input);
  });

  const getSelectedDatasets = () => {
    return datasets.filter((dataset) => {
      const checkbox = datasetCheckboxes.get(dataset.slug);
      return checkbox ? checkbox.checked : false;
    });
  };

  const renderCards = () => {
    const selectedTask = taskSelect.value;
    const selectedDatasets = getSelectedDatasets();

    resultsContainer.innerHTML = '';
    if (!selectedDatasets.length) {
      resultsContainer.innerHTML = '<div class="comparison-error">Select at least one dataset to compare.</div>';
      return;
    }

    selectedDatasets.forEach((dataset) => {
      const taskEntry = (dataset.tasks || []).find((task) => task.display_name === selectedTask);
      if (!taskEntry) {
        return;
      }

      const cardNode = cardTemplate.content.cloneNode(true);
      cardNode.querySelector('.dataset-title').textContent = dataset.display_name;
      cardNode.querySelector('.dataset-slug').textContent = dataset.short_code || dataset.slug;
      cardNode.querySelector('.dataset-quality').textContent = dataset.quality || '—';

      const statusText = taskEntry.status || '—';
      const passRate = typeof taskEntry.pass_rate === 'number' ? `${taskEntry.pass_rate.toFixed(1)}% valid` : 'Pass rate unavailable';
      cardNode.querySelector('.task-status').textContent = `${statusText} ${selectedTask}: ${passRate}`;

      const buttonsContainer = cardNode.querySelector('.card-buttons');
      const addButton = (label, url, extraClasses = '') => {
        if (url) {
          const link = document.createElement('a');
          link.href = url;
          link.target = '_blank';
          link.rel = 'noopener';
          link.className = `card-button available ${extraClasses}`;
          link.textContent = label;
          buttonsContainer.appendChild(link);
        } else {
          const span = document.createElement('span');
          span.className = `card-button unavailable ${extraClasses}`;
          span.textContent = label;
          buttonsContainer.appendChild(span);
        }
      };

      addButton('Clean Dataset', dataset.clean_url);
      addButton('Full Dataset', dataset.dirty_url);
      addButton('Validation Report', dataset.validation_report);

      const plotsContainer = cardNode.querySelector('.card-plots');
      if (taskEntry.plots && taskEntry.plots.length) {
        taskEntry.plots.forEach((plotPath) => {
          const img = document.createElement('img');
          img.src = `./${plotPath}`;
          img.alt = `${dataset.display_name} ${selectedTask} validation plot`;
          img.loading = 'lazy';
          plotsContainer.appendChild(img);
        });
      } else {
        const placeholder = document.createElement('div');
        placeholder.className = 'plots-placeholder';
        placeholder.textContent = 'Validation plots not available for this task.';
        plotsContainer.appendChild(placeholder);
      }

      resultsContainer.appendChild(cardNode);
    });

    if (!resultsContainer.childElementCount) {
      resultsContainer.innerHTML = '<div class="comparison-error">Selected datasets do not include this task yet.</div>';
    }
  };

  taskSelect.addEventListener('change', renderCards);
  datasetCheckboxes.forEach((checkbox) => checkbox.addEventListener('change', renderCards));

  taskSelect.value = allTasks[0];
  renderCards();
})();
</script>

<style>
.comparison-app {
  display: grid;
  gap: 1.5rem;
}

.comparison-controls {
  display: grid;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid #d1d5db;
  border-radius: 0.75rem;
  background: #f9fafb;
}

.comparison-controls label,
.comparison-controls legend {
  font-weight: 600;
  color: #1f2937;
}

.dataset-select {
  border: none;
  padding: 0;
  margin: 0;
}

.dataset-option {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.4rem;
}

.dataset-option input {
  transform: scale(1.1);
}

.comparison-grid {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.comparison-card {
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  padding: 1.25rem;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
}

.card-header h3 {
  margin: 0;
  font-size: 1.15rem;
}

.dataset-slug {
  margin: 0;
  color: #6b7280;
  font-size: 0.9rem;
}

.dataset-quality {
  background: #1f78d1;
  color: #fff;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  font-size: 0.85rem;
}

.task-status {
  margin: 0;
  font-weight: 500;
}

.card-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.card-button {
  display: inline-block;
  padding: 0.5rem 1.0rem;
  border-radius: 999px;
  font-weight: 600;
  font-size: 0.9rem;
  text-decoration: none;
}

.card-button.available {
  background: #1f78d1;
  color: #fff;
}

.card-button.available:hover {
  background: #1663ad;
}

.card-button.unavailable {
  background: #e5e7eb;
  color: #9ca3af;
}

.card-plots {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.card-plots img {
  width: 100%;
  max-width: 320px;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
}

.plots-placeholder {
  padding: 0.75rem;
  border: 1px dashed #d1d5db;
  border-radius: 0.5rem;
  color: #6b7280;
  font-size: 0.9rem;
}

.comparison-error {
  border: 1px solid #fee2e2;
  background: #fef2f2;
  color: #b91c1c;
  padding: 1rem;
  border-radius: 0.75rem;
}
</style>
