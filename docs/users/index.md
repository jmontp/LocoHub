---
title: For Users - Analysis Libraries
hide:
  - navigation
  - toc
---

<div class="hero-section" markdown>

# :material-code-braces: For Users - Analysis Libraries

## Access standardized biomechanical data through Python, MATLAB, and R with validated, research-ready libraries

**Choose your preferred language and approach.** Work directly with raw parquet files for maximum control, or use our high-level libraries for rapid analysis with built-in validation and visualization.

<div class="hero-actions" markdown>

[**:material-language-python: Python**](#python){ .md-button .hero-button }
[**MATLAB**](#matlab){ .md-button .hero-button }
[**:material-language-r: R**](#r){ .md-button .hero-button }

</div>

</div>

<div class="main-sections-grid" markdown>

<div class="dashboard-tile" markdown>

### :material-language-python: **Python**

**Full-featured analysis with pandas, numpy, and visualization tools**

The Python library provides comprehensive data access with built-in statistical analysis, cycle extraction, and publication-ready plotting.

```python
from user_libs.python.locomotion_data import LocomotionData

data = LocomotionData('umich_2021_phase.parquet')
cycles, features = data.get_cycles('SUB01', 'level_walking')
```

✓ Numpy/Pandas integration  
✓ Statistical analysis functions  
✓ Matplotlib/Plotly visualization  
✓ Jupyter notebook compatible  

[**:material-book-open-variant: View Tutorials**](tutorials/python/){ .md-button }
[**:material-package-variant: API Reference**](api/locomotion-data-api/){ .md-button .md-button--primary }

</div>

<div class="dashboard-tile" markdown>

### **MATLAB**

**Native MATLAB analysis with biomechanics-focused tooling**

MATLAB tools designed for biomechanical researchers with familiar syntax and integrated visualization capabilities.

```matlab
% Load phase-indexed data
data = load_locomotion_data('gtech_2023_phase.parquet');

% Extract gait cycles
[cycles, features] = get_cycles(data, 'SUB01', 'level_walking');
```

✓ Matrix operations optimized  
✓ Biomechanics-specific functions  
✓ MATLAB plotting integration  
✓ Compatible with existing workflows  

[**:material-book-open-variant: View Tutorials**](tutorials/matlab/biomechanics_visualization_guide/){ .md-button }
[**:material-package-variant: API Reference**](api/matlab-api/){ .md-button .md-button--primary }

</div>

<div class="dashboard-tile" markdown>

### :material-language-r: **R**

**Statistical analysis and reporting with tidyverse integration**

R package optimized for statistical analysis, mixed-effects modeling, and reproducible research reports with RMarkdown.

```r
library(locomotion)

# Load and analyze data
data <- load_locomotion_data("umich_2021_phase.parquet")
cycles <- get_cycles(data, "SUB01", "level_walking")
```

✓ Tidyverse compatible  
✓ Statistical modeling built-in  
✓ RMarkdown report templates  
✓ ggplot2 visualization  

[**:material-book-open-variant: View Tutorials**](tutorials/r/){ .md-button }
[**:material-package-variant: API Reference**](api/r-api/){ .md-button .md-button--primary }

</div>

</div>

## :material-rocket-launch: Quick Start Examples

<div class="main-sections-grid" markdown>

<div class="dashboard-tile" markdown>

### **Load Dataset**

=== "Python"
    ```python
    from user_libs.python.locomotion_data import LocomotionData
    
    # Load a phase-indexed dataset (150 points per gait cycle)
    data = LocomotionData('converted_datasets/umich_2021_phase.parquet')
    
    # Or load time-indexed data
    data_time = LocomotionData('converted_datasets/gtech_2023_time.parquet')
    
    # List available subjects and tasks
    subjects = data.get_subjects()
    tasks = data.get_tasks()
    ```

=== "MATLAB"
    ```matlab
    % Load phase-indexed dataset
    data = load_locomotion_data('converted_datasets/gtech_2023_phase.parquet');
    
    % Or load time-indexed data
    data_time = load_locomotion_data('converted_datasets/umich_2021_time.parquet');
    
    % List available subjects and tasks
    subjects = get_subjects(data);
    tasks = get_tasks(data);
    ```

=== "R"
    ```r
    library(locomotion)
    
    # Load phase-indexed dataset
    data <- load_locomotion_data("converted_datasets/umich_2021_phase.parquet")
    
    # Or load time-indexed data
    data_time <- load_locomotion_data("converted_datasets/gtech_2023_time.parquet")
    
    # List available subjects and tasks
    subjects <- get_subjects(data)
    tasks <- get_tasks(data)
    ```

</div>

<div class="dashboard-tile" markdown>

### **Analyze and Visualize**

=== "Python"
    ```python
    # Get gait cycles for a subject and task
    cycles_3d, features = data.get_cycles('SUB01', 'level_walking')
    
    # Get mean patterns across cycles
    mean_patterns = data.get_mean_patterns('SUB01', 'level_walking')
    
    # Create publication-ready plots
    data.plot_phase_patterns('SUB01', 'level_walking', 
                             ['knee_flexion_angle_ipsi_rad',
                              'hip_flexion_angle_ipsi_rad'])
    
    # Calculate range of motion
    rom = data.calculate_rom('SUB01', 'level_walking')
    ```

=== "MATLAB"
    ```matlab
    % Get gait cycles for a subject and task
    [cycles_3d, features] = get_cycles(data, 'SUB01', 'level_walking');
    
    % Get mean patterns
    mean_patterns = get_mean_patterns(data, 'SUB01', 'level_walking');
    
    % Create plots
    plot_phase_patterns(data, 'SUB01', 'level_walking', ...
                       {'knee_flexion_angle_ipsi_rad', ...
                        'hip_flexion_angle_ipsi_rad'});
    
    % Calculate ROM
    rom = calculate_rom(data, 'SUB01', 'level_walking');
    ```

=== "R"
    ```r
    # Get gait cycles for a subject and task
    result <- get_cycles(data, "SUB01", "level_walking")
    cycles_3d <- result$cycles
    features <- result$features
    
    # Get mean patterns
    mean_patterns <- get_mean_patterns(data, "SUB01", "level_walking")
    
    # Create visualization
    plot_phase_patterns(data, "SUB01", "level_walking",
                       c("knee_flexion_angle_ipsi_rad",
                         "hip_flexion_angle_ipsi_rad"))
    
    # Calculate ROM
    rom <- calculate_rom(data, "SUB01", "level_walking")
    ```

</div>

</div>

## :material-help-circle: Need Help?

<div class="dashboard-tile" markdown>

### **Resources & Support**

**Documentation**
- [API Reference](api/api-index/) - Detailed function documentation
- [Python Tutorials](tutorials/python/) - Step-by-step learning path
- [Validation Guide](api/validation-api/) - Understanding data quality

**Datasets**
- [Download Datasets](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0)
- [Dataset Documentation](../reference/datasets_documentation/)
- [Validation Reports](../reference/datasets_documentation/validation_reports/)

**Community**
- [GitHub Issues](https://github.com/your-repo/issues) - Report bugs or request features
- [Discussions](https://github.com/your-repo/discussions) - Ask questions and share insights

</div>