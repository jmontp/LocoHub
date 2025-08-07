# Python Tutorials

## Overview

Learn to analyze standardized biomechanical data using Python with our comprehensive tutorial series. These tutorials progress from basic data loading to publication-ready analysis.

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

## Prerequisites

### Required Knowledge
- Basic Python programming
- Familiarity with pandas DataFrames
- Understanding of biomechanical concepts

### Required Packages
```python
# Core packages
pandas >= 1.3.0
numpy >= 1.20.0
matplotlib >= 3.3.0

# LocoHub library
user_libs.python.locomotion_data

# Optional but recommended
seaborn >= 0.11.0  # Better plot styling
scipy >= 1.7.0     # Statistical functions
```

### Installation
```bash
# Install required packages
pip install pandas numpy matplotlib seaborn scipy

# Install locomotion library (from project root)
pip install -e user_libs/python
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
- Apply your own ML/statistical methods to filtered data

## Quick Reference

### Common Operations
```python
from user_libs.python.locomotion_data import LocomotionData

# Load data
data = LocomotionData('dataset.parquet')

# Filter
level_walking = data[data['task'] == 'level_walking']

# Compute mean
mean = level_walking.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()

# Plot
import matplotlib.pyplot as plt
plt.plot(mean.index, np.degrees(mean.values))
plt.xlabel('Gait Cycle (%)')
plt.ylabel('Knee Flexion (deg)')
plt.show()
```

## Getting Help

### Documentation
- [API Reference](../../api/locomotion-data-api.md)
- [Data Format Specification](../../../reference/standard_spec/standard_spec.md)
- [Variable Definitions](../../../reference/biomechanical_standard.md)

### Community Support
- GitHub Issues for bug reports
- Discussions for questions
- Example notebooks in repository

## Tips for Success

1. **Always filter first** - Don't analyze the entire dataset if you only need a subset
2. **Check your units** - Data is stored in radians and SI units
3. **Validate your results** - Compare with published normal ranges
4. **Save your work** - Use scripts, not just notebooks
5. **Document your choices** - Record filtering criteria and analysis decisions

## Next Steps

Ready to start? Begin with [Tutorial 1: Loading Data Efficiently](01_loading_data.md) →