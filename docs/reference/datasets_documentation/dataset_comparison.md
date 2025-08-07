# Dataset Comparison Gallery

View standardized biomechanical datasets side-by-side for easy comparison.

## How to Use

1. **All Datasets View**: Select a task from the dropdown to see all available datasets that include that task
2. **Pairwise Comparison**: Select two specific datasets and a task to compare them side-by-side

The plots show clean data (passing validation only) with mean patterns and standard deviation bands for each dataset.

---

## 📊 All Datasets Overview

Select a task to see all available datasets:

<div class="comparison-controls">
    <label for="taskSelect">Task: 
        <select id="taskSelect" onchange="showAllDatasets()" style="padding: 8px 12px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;">
            <option value="">Select a task...</option>
            <option value="level_walking">Level Walking</option>
            <option value="incline_walking">Incline Walking</option>
            <option value="decline_walking">Decline Walking</option>
            <option value="stair_ascent">Stair Ascent</option>
            <option value="stair_descent">Stair Descent</option>
        </select>
    </label>
</div>

<div id="allDatasetsGrid" class="comparison-grid" style="display: flex; overflow-x: auto; gap: 20px; margin: 20px 0; padding-bottom: 10px;">
    <p style="color: #666; padding: 20px;">Please select a task to view datasets.</p>
</div>

---

## 🔍 Pairwise Comparison

Compare two datasets directly:

<div class="pairwise-controls" style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px;">
    <label style="display: inline-block; margin: 5px;">Dataset 1:
        <select id="dataset1Select" style="padding: 8px 12px; margin: 5px; border: 1px solid #ddd; border-radius: 4px;">
            <option value="">Select dataset...</option>
            <option value="umich_2021">UMich 2021</option>
            <option value="gtech_2021">GTech 2021</option>
            <option value="gtech_2023">GTech 2023</option>
        </select>
    </label>
    
    <label style="display: inline-block; margin: 5px;">Dataset 2:
        <select id="dataset2Select" style="padding: 8px 12px; margin: 5px; border: 1px solid #ddd; border-radius: 4px;">
            <option value="">Select dataset...</option>
            <option value="umich_2021">UMich 2021</option>
            <option value="gtech_2021">GTech 2021</option>
            <option value="gtech_2023">GTech 2023</option>
        </select>
    </label>
    
    <label style="display: inline-block; margin: 5px;">Task:
        <select id="pairwiseTaskSelect" style="padding: 8px 12px; margin: 5px; border: 1px solid #ddd; border-radius: 4px;">
            <option value="">Select task...</option>
            <option value="level_walking">Level Walking</option>
            <option value="incline_walking">Incline Walking</option>
            <option value="decline_walking">Decline Walking</option>
            <option value="stair_ascent">Stair Ascent</option>
            <option value="stair_descent">Stair Descent</option>
        </select>
    </label>
    
    <button onclick="showPairwise()" style="padding: 8px 16px; margin: 5px; border: 1px solid #007bff; background: #007bff; color: white; border-radius: 4px; cursor: pointer;">Compare</button>
</div>

<div id="pairwiseResult" class="pairwise-result" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
    <p style="color: #666; padding: 20px; grid-column: 1 / -1;">Select two datasets and a task to compare.</p>
</div>

<style>
.comparison-grid {
    -webkit-overflow-scrolling: touch; /* Smooth scrolling on iOS */
}

.comparison-grid::-webkit-scrollbar {
    height: 8px;
}

.comparison-grid::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
}

.comparison-grid::-webkit-scrollbar-thumb {
    background: #888;
    border-radius: 4px;
}

.comparison-grid::-webkit-scrollbar-thumb:hover {
    background: #555;
}

.dataset-card {
    background: white;
    padding: 15px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    text-align: center;
    flex: 0 0 auto;
    width: 400px; /* Fixed width for horizontal scrolling */
    min-width: 400px;
}

.dataset-card h4 {
    margin: 0 0 10px 0;
    color: #333;
    font-size: 16px;
}

.dataset-card img {
    width: 100%;
    height: auto;
    border-radius: 4px;
    max-height: 600px; /* Prevent images from being too tall */
    object-fit: contain;
}

.dataset-card .error-message {
    color: #666;
    font-style: italic;
    padding: 40px 20px;
}

@media (max-width: 768px) {
    .dataset-card {
        width: 300px; /* Smaller width on mobile */
        min-width: 300px;
    }
    
    .pairwise-result {
        grid-template-columns: 1fr !important;
    }
    
    .pairwise-controls label {
        display: block !important;
        margin: 10px 0 !important;
    }
    
    .pairwise-controls select,
    .pairwise-controls button {
        width: 100%;
    }
}
</style>

<script>
// Available dataset-task combinations (based on what's been generated)
// This will be populated based on actual files in comparison_plots/
const AVAILABLE_PLOTS = {
    'umich_2021': ['level_walking', 'incline_walking', 'decline_walking'],
    'gtech_2021': ['level_walking', 'incline_walking', 'decline_walking', 'stair_ascent', 'stair_descent'],
    'gtech_2023': ['level_walking', 'incline_walking', 'decline_walking', 'stair_ascent', 'stair_descent']
};

function formatName(dataset) {
    const names = {
        'umich_2021': 'UMich 2021',
        'gtech_2021': 'GTech 2021',
        'gtech_2023': 'GTech 2023'
    };
    return names[dataset] || dataset.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function showAllDatasets() {
    const task = document.getElementById('taskSelect').value;
    const grid = document.getElementById('allDatasetsGrid');
    
    if (!task) {
        grid.innerHTML = '<p style="color: #666; padding: 20px;">Please select a task to view datasets.</p>';
        return;
    }
    
    // Find datasets with this task
    const datasets = Object.keys(AVAILABLE_PLOTS)
        .filter(d => AVAILABLE_PLOTS[d].includes(task));
    
    if (datasets.length === 0) {
        grid.innerHTML = '<p style="color: #666; padding: 20px;">No datasets available for this task.</p>';
        return;
    }
    
    // Display all matching datasets
    grid.innerHTML = datasets.map(dataset => `
        <div class="dataset-card">
            <h4>${formatName(dataset)}</h4>
            <img src="../comparison_plots/${dataset}_${task}.png" 
                 alt="${formatName(dataset)} - ${task.replace(/_/g, ' ')}"
                 onerror="this.onerror=null; this.style.display='none'; var err=document.createElement('div'); err.className='error-message'; err.innerHTML='Plot not yet generated.<br>Run validation to create.'; this.parentElement.appendChild(err);">
        </div>
    `).join('');
}

function showPairwise() {
    const dataset1 = document.getElementById('dataset1Select').value;
    const dataset2 = document.getElementById('dataset2Select').value;
    const task = document.getElementById('pairwiseTaskSelect').value;
    const result = document.getElementById('pairwiseResult');
    
    if (!dataset1 || !dataset2 || !task) {
        result.innerHTML = '<p style="color: #666; padding: 20px; grid-column: 1 / -1;">Please select both datasets and a task.</p>';
        return;
    }
    
    if (dataset1 === dataset2) {
        result.innerHTML = '<p style="color: #666; padding: 20px; grid-column: 1 / -1;">Please select two different datasets to compare.</p>';
        return;
    }
    
    // Check availability
    const d1HasTask = AVAILABLE_PLOTS[dataset1]?.includes(task);
    const d2HasTask = AVAILABLE_PLOTS[dataset2]?.includes(task);
    
    if (!d1HasTask && !d2HasTask) {
        result.innerHTML = '<p style="color: #666; padding: 20px; grid-column: 1 / -1;">Selected task not available for either dataset.</p>';
        return;
    }
    
    // Display side-by-side
    result.innerHTML = `
        <div class="dataset-card">
            <h4>${formatName(dataset1)}</h4>
            ${d1HasTask ? 
                `<img src="../comparison_plots/${dataset1}_${task}.png" 
                      alt="${formatName(dataset1)} - ${task.replace(/_/g, ' ')}"
                      onerror="this.onerror=null; this.style.display='none'; var err=document.createElement('div'); err.className='error-message'; err.innerHTML='Plot not yet generated.<br>Run validation to create.'; this.parentElement.appendChild(err);">` :
                '<div class="error-message">Task not available for this dataset.</div>'
            }
        </div>
        <div class="dataset-card">
            <h4>${formatName(dataset2)}</h4>
            ${d2HasTask ? 
                `<img src="../comparison_plots/${dataset2}_${task}.png" 
                      alt="${formatName(dataset2)} - ${task.replace(/_/g, ' ')}"
                      onerror="this.onerror=null; this.style.display='none'; var err=document.createElement('div'); err.className='error-message'; err.innerHTML='Plot not yet generated.<br>Run validation to create.'; this.parentElement.appendChild(err);">` :
                '<div class="error-message">Task not available for this dataset.</div>'
            }
        </div>
    `;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Could potentially auto-discover available plots here
    // For now, using hardcoded AVAILABLE_PLOTS based on known datasets
});
</script>

---

## About the Comparison Plots

These comparison plots are automatically generated when datasets are validated using:

```bash
python contributor_tools/create_dataset_validation_report.py --datasets your_dataset.parquet
```

The plots show:
- **Clean data only**: Strides that pass biomechanical validation
- **Mean patterns**: Average across all valid strides (solid line)
- **Standard deviation**: Variability shown as shaded bands
- **All sagittal features**: Hip, knee, and ankle angles and moments

To regenerate or update comparison plots, simply re-run the validation report for the dataset.