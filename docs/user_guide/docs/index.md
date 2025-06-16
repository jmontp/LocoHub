# Locomotion Data Standardization

**Transform biomechanical datasets into a unified, quality-assured format for reproducible research.**

<div class="grid cards" markdown>

-   :material-rocket-launch: **Quick Start**
    
    ---
    
    Get up and running in minutes with our step-by-step guide
    
    [:octicons-arrow-right-24: Start Here](getting_started/quick_start/)

-   :material-book-open-variant: **Tutorials**
    
    ---
    
    Learn with hands-on examples in Python and MATLAB
    
    [:octicons-arrow-right-24: View Tutorials](tutorials/)

-   :material-account-group: **Contributor Guide**
    
    ---
    
    Add your dataset to the standardized collection
    
    [:octicons-arrow-right-24: Contribute Data](contributor_guide/)

-   :material-file-document: **Reference**
    
    ---
    
    Complete documentation of data formats and validation
    
    [:octicons-arrow-right-24: View Reference](reference/standard_spec/standard_spec/)

</div>

## What is Locomotion Data Standardization?

This project provides a unified framework for biomechanical datasets, addressing the challenge of inconsistent data formats across research labs. By standardizing variable names, units, and data structures, we enable:

- **Reproducible Research**: Consistent data formats across studies
- **Quality Assurance**: Automated validation of biomechanical plausibility
- **Easy Analysis**: Standardized tools for common biomechanics tasks
- **Cross-Study Comparison**: Compatible datasets from multiple sources

## Key Features

### :material-check-circle: Standardized Data Format
- **Consistent naming**: `knee_flexion_angle_ipsi_rad`, `hip_moment_contra_Nm`
- **Two formats**: Time-indexed (original frequency) and phase-indexed (150 points per cycle)
- **Quality validation**: Automated biomechanical plausibility checks

### :material-tools: Analysis Tools
- **Python library**: Load, analyze, and visualize standardized datasets
- **MATLAB support**: Native MATLAB functions for biomechanics workflows
- **Validation reports**: Comprehensive quality assessment with visualizations

### :material-database: Quality Datasets
- **Multi-lab sources**: Georgia Tech, University of Michigan, AddBiomechanics
- **Diverse tasks**: Level walking, stairs, inclines, running, jumping
- **Validated quality**: All datasets pass biomechanical plausibility checks

## Who Should Use This?

=== "Researchers & Students"

    **Use quality-assured datasets for your research**
    
    - Download standardized datasets from multiple labs
    - Focus on analysis rather than data cleaning
    - Reproduce published results with confidence
    
    **Start with:** [Quick Start Guide](getting_started/quick_start/)

=== "Dataset Contributors"

    **Add your datasets to the standardized collection**
    
    - Convert your lab's data to standard format
    - Validate quality with automated checks
    - Share data with the research community
    
    **Start with:** [Contributor Guide](contributor_guide/)

=== "Tool Developers"

    **Build on standardized data infrastructure**
    
    - Access consistent data formats across studies
    - Integrate with validation and analysis tools
    - Extend functionality for specific use cases
    
    **Start with:** [API Reference](reference/api_reference/)

## Quick Example

Here's how easy it is to work with standardized data:

=== "Python"

    ```python
    import pandas as pd
    import matplotlib.pyplot as plt
    
    # Load standardized dataset
    data = pd.read_parquet('gtech_2023_phase.parquet')
    
    # Filter for level walking
    walking = data[data['task'] == 'level_walking']
    
    # Plot average knee angle across gait cycle
    avg_knee = walking.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
    plt.plot(avg_knee.index, avg_knee.values)
    plt.xlabel('Gait Cycle (%)')
    plt.ylabel('Knee Flexion (rad)')
    plt.title('Average Knee Angle - Level Walking')
    plt.show()
    ```

=== "MATLAB"

    ```matlab
    % Load standardized dataset
    data = readtable('gtech_2023_phase.parquet');
    
    % Filter for level walking
    walking = data(strcmp(data.task, 'level_walking'), :);
    
    % Plot average knee angle across gait cycle
    avg_knee = groupsummary(walking, 'phase_percent', 'mean', 'knee_flexion_angle_ipsi_rad');
    plot(avg_knee.phase_percent, avg_knee.mean_knee_flexion_angle_ipsi_rad);
    xlabel('Gait Cycle (%)');
    ylabel('Knee Flexion (rad)');
    title('Average Knee Angle - Level Walking');
    ```

## Available Datasets

| Dataset | Tasks | Subjects | Gait Cycles | Status |
|---------|-------|----------|-------------|---------|
| **Georgia Tech 2023** | Level walking, stairs, inclines | 10 | ~500 | ✅ Available |
| **University of Michigan 2021** | Level walking, inclines, declines | 12 | ~600 | ✅ Available |
| **AddBiomechanics** | Walking, running, jumping | 50+ | ~2000 | 🚧 In Progress |

## Getting Started

1. **[Install](getting_started/installation/)** Python or MATLAB support
2. **[Quick Start](getting_started/quick_start/)** with a sample dataset
3. **[Follow Tutorials](tutorials/)** for hands-on learning
4. **[Contribute](contributor_guide/)** your own datasets

## Support & Community

- **Questions?** Check our [Troubleshooting Guide](user_guide/troubleshooting/)
- **Bug reports?** Open an issue on [GitHub](https://github.com/your-org/locomotion-data-standardization/issues)
- **Want to contribute?** See our [Contributor Guide](contributor_guide/)

---

*This project is maintained by a community of biomechanics researchers and software developers committed to reproducible science.*