# MATLAB Tutorials

## Overview

Learn to analyze standardized biomechanical data using MATLAB with our comprehensive tutorial series. These tutorials progress from basic data loading to publication-ready analysis.

## Tutorial Series

### :material-numeric-1-circle: [Loading Data Efficiently](01_loading_data.md)
**Learn the fundamentals of data loading and memory management**
- Load phase and time-indexed datasets
- Select specific columns to reduce memory usage
- Understand data structure and naming conventions
- List available subjects, tasks, and variables

**Time: 20 minutes** | **Level: Beginner**

---

### :material-numeric-2-circle: [Data Filtering](02_data_filtering.md)
**Master the critical skill of data subsetting**
- Filter by task, subject, and variables
- Combine multiple filter conditions
- Create reusable filter functions
- Save filtered datasets for analysis

**Time: 25 minutes** | **Level: Beginner**

---

### :material-numeric-3-circle: [Basic Visualization](03_visualization.md)
**Create essential biomechanical plots**
- Compute and plot phase averages
- Add standard deviation shading
- Create spaghetti plots
- Compare multiple conditions

**Time: 30 minutes** | **Level: Intermediate**

---

### :material-numeric-4-circle: [Cycle Analysis](04_cycle_analysis.md)
**Analyze individual gait cycles**
- Extract individual cycles
- Calculate ROM and peak values
- Detect timing of key events
- Identify outlier cycles

**Time: 25 minutes** | **Level: Intermediate**

---

### :material-numeric-5-circle: [Group Analysis](05_group_analysis.md)
**Aggregate data across subjects**
- Compute group means and variability
- Handle missing data appropriately
- Create ensemble averages
- Statistical comparisons

**Time: 30 minutes** | **Level: Intermediate**

---

### :material-numeric-6-circle: [Publication Outputs](06_publication_outputs.md)
**Generate publication-ready figures and tables**
- Create multi-panel figures
- Export summary statistics
- Format for journal requirements
- Ensure reproducibility

**Time: 30 minutes** | **Level: Advanced**

## Advanced Guides

- [Biomechanics Visualization Guide](biomechanics_visualization_guide.md)

## Prerequisites

### Required Knowledge
- Basic MATLAB programming
- Understanding of biomechanical concepts
- Familiarity with MATLAB plotting and data structures

### Required Software
```matlab
% MATLAB R2019b or later
% Required toolboxes:
% - Statistics and Machine Learning Toolbox (recommended)
% - Signal Processing Toolbox (optional)

% LocoHub library
addpath('user_libs/matlab');
```

### Installation
```matlab
% Add library to MATLAB path (from project root)
addpath('user_libs/matlab');

% Verify installation
loco = LocomotionData();  % Should work without errors
```

## Learning Path

### For Beginners
1. Start with **Tutorial 1** to understand data structure
2. Master **Tutorial 2** on filtering - this is critical
3. Practice **Tutorial 3** visualization techniques
4. Work through exercises at your own pace

### For Experienced Users
- Jump to specific tutorials as needed
- Focus on **Tutorial 2** (filtering) and **Tutorial 3** (visualization)
- Check **Tutorial 6** for publication workflows

### For Data Scientists
- Review **Tutorial 1** for data structure
- Use **Tutorial 2** to understand subsetting patterns
- Apply your own statistical methods to filtered data

## Quick Reference

### Common Operations
```matlab
% Add library to path
addpath('user_libs/matlab');

% Load data
loco = LocomotionData('dataset.parquet');

% Filter
levelWalking = loco.filterTask('level_walking').filterSubject('SUB01');

% Get mean patterns
meanPatterns = levelWalking.getMeanPatterns('SUB01', 'level_walking');

% Plot
phase = 0:100/149:100;
plot(phase, rad2deg(meanPatterns.knee_flexion_angle_ipsi_rad));
xlabel('Gait Cycle (%)');
ylabel('Knee Flexion (deg)');
title('Mean Knee Flexion Pattern');
grid on;
```

## Getting Help

### Documentation
- [API Reference](../../api/locomotion-data-api.md)
- [Data Format Specification](../../../reference/standard_spec/standard_spec.md)
- [Variable Definitions](../../../reference/biomechanical_standard.md)

### Community Support
- GitHub Issues for bug reports
- Discussions for questions
- Example scripts in repository

## Tips for Success

1. **Always filter first** - Don't analyze the entire dataset if you only need a subset
2. **Check your units** - Data is stored in radians and SI units
3. **Validate your results** - Compare with published normal ranges
4. **Save your work** - Use scripts (.m files), not just Command Window
5. **Document your choices** - Record filtering criteria and analysis decisions

## MATLAB-Specific Tips

6. **Close figures** - Use `close all` to manage memory
7. **Preallocate arrays** - For better performance with large datasets
8. **Use cell arrays** - For feature names and subject lists
9. **Handle NaN values** - Use `'omitnan'` option in statistical functions
10. **Export figures** - Use `print()` for high-quality publication figures

## Next Steps

Ready to start? Begin with [Tutorial 1: Loading Data Efficiently](01_loading_data.md) →
