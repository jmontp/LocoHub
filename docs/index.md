---
title: Home
hide:
  - navigation
  - toc
---

<div class="hero-section" markdown>

# :material-run: Locomotion Data Standardization

## Transform biomechanical datasets into unified, quality-assured formats that accelerate reproducible research

**Stop wrestling with inconsistent data formats.** Start analyzing standardized, validated biomechanical datasets from world-class research labs in minutes, not months.

<div class="hero-actions" markdown>

[**:material-rocket-launch: Try It Now**](users/){ .md-button .md-button--primary .hero-button }
[**:material-book-open-variant: View Tutorials**](users/tutorials/python/){ .md-button .hero-button }
[**:material-download: Get Data**](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0){ .md-button .hero-button }

</div>

</div>

<div class="trust-indicators" markdown>

:material-check-circle:{ .success-icon } **3 Research Labs** • :material-check-circle:{ .success-icon } **2,000+ Gait Cycles** • :material-check-circle:{ .success-icon } **100% Validated** • :material-check-circle:{ .success-icon } **Python & MATLAB**

</div>

<div class="main-sections-grid" markdown>

<div class="main-section" markdown>

### :material-download: **Download Datasets**

| Dataset | Tasks | Quality | Documentation | Download |
|---------|-------|---------|---------------|----------|
| **[Georgia Tech 2023](reference/datasets_documentation/dataset_gtech_2023/)** | Walking, stairs, inclines | :material-check-circle:{ .success } **Validated** | [:material-file-document: Docs](reference/datasets_documentation/dataset_gtech_2023/){ .md-button } | [:material-download: Download](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0){ .md-button } |
| **[University of Michigan 2021](reference/datasets_documentation/dataset_umich_2021/)** | Level, incline, decline walking | :material-check-circle:{ .success } **Validated** | [:material-file-document: Docs](reference/datasets_documentation/dataset_umich_2021/){ .md-button } | [:material-download: Download](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0){ .md-button } |
| **[AddBiomechanics](reference/datasets_documentation/dataset_addbiomechanics/)** | Walking, running, jumping, stairs | :material-progress-clock:{ .warning } **Coming Soon** | [:material-file-document: Docs](reference/datasets_documentation/dataset_addbiomechanics/){ .md-button } | Coming Soon |

</div>

<div class="dashboard-tile" markdown>

### :material-book: **Datasets Reference**

**Comprehensive documentation for all standardized datasets**

✓ Dataset specifications and formats  
✓ Validation reports and quality metrics  
✓ Variable definitions and conventions  
✓ Known issues and usage notes  

[**:material-arrow-right: View Datasets Reference**](reference/datasets_documentation/){ .md-button .md-button--primary }

</div>

<div class="dashboard-tile" markdown>

### :material-code-braces: **User Libraries**

**Analysis tools in Python, MATLAB, and R**

```python
from user_libs.python.locomotion_data import LocomotionData
data = LocomotionData('umich_2021_phase.parquet')
cycles, features = data.get_cycles('SUB01', 'level_walking')
```

[**:material-language-python: Python API**](users/api/locomotion-data-api/){ .md-button } [**:material-language-r: R Package**](users/tutorials/r/){ .md-button } [**MATLAB Tools**](users/tutorials/matlab/){ .md-button }

</div>

<div class="dashboard-tile" markdown>

### :material-upload: **Want to Contribute?**

**Share your lab's datasets with the research community**

✓ Convert your data to standardized format  
✓ Automated quality validation  
✓ Increase research impact and citations  
✓ Join the standardization movement  

[**:material-arrow-right: Start Contributing**](contributing/){ .md-button .md-button--primary }

</div>

</div>