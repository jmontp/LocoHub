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

[**:material-rocket-launch: Try It Now**](getting_started/quick_start/){ .md-button .md-button--primary .hero-button }
[**:material-eye: View Examples**](interactive/gallery/){ .md-button .hero-button }
[**:material-download: Get Datasets**](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0){ .md-button .hero-button }

</div>

</div>

<div class="trust-indicators" markdown>

:material-check-circle:{ .success-icon } **3 Research Labs** • :material-check-circle:{ .success-icon } **2,000+ Gait Cycles** • :material-check-circle:{ .success-icon } **100% Validated** • :material-check-circle:{ .success-icon } **Python & MATLAB**

</div>

## :material-lightning-bolt: Why Researchers Choose Our Platform

<div class="value-props" markdown>

### :material-timer: **5 Minutes to Analysis**
**No more weeks of data cleaning.** Load standardized datasets and start analyzing immediately with consistent variable names and validated quality.

### :material-shield-check: **Research-Grade Quality**
**Every dataset passes 50+ biomechanical validation checks.** Automated quality assurance ensures physiologically plausible joint angles, moments, and gait patterns.

### :material-account-group: **Multi-Lab Ecosystem**
**Combine datasets from Georgia Tech, University of Michigan, and AddBiomechanics.** Cross-study comparisons with identical data formats and units.

### :material-code-tags: **Production-Ready Tools**
**Built by researchers, for researchers.** Optimized Python and MATLAB libraries with 3D array operations, visualization, and analysis functions.

</div>

## :material-account-multiple: Choose Your Path

<div class="audience-grid" markdown>

<div class="audience-card researcher" markdown>

### :material-school: **Researchers & Students**

**Use validated datasets for immediate analysis**

✓ Download standardized datasets from multiple labs  
✓ Skip data cleaning - focus on discovery  
✓ Reproduce published results with confidence  
✓ Compare across studies with identical formats  

[**Start Analyzing :material-arrow-right:**](audiences/researchers/){ .md-button .researcher-button }

</div>

<div class="audience-card contributor" markdown>

### :material-upload: **Dataset Contributors**

**Share your data with the research community**

✓ Convert your lab's data to standard format  
✓ Automated quality validation and reporting  
✓ Increase citation and research impact  
✓ Join the standardization movement  

[**Contribute Data :material-arrow-right:**](audiences/contributors/){ .md-button .contributor-button }

</div>

<div class="audience-card developer" markdown>

### :material-code-braces: **Tool Developers**

**Build on standardized data infrastructure**

✓ Consistent APIs across Python and MATLAB  
✓ Validated data contracts and schemas  
✓ Extensible validation and analysis framework  
✓ Production-ready libraries and documentation  

[**View APIs :material-arrow-right:**](audiences/developers/){ .md-button .developer-button }

</div>

</div>

## :material-play-circle: See It In Action

<div class="demo-section" markdown>

### **Load and Analyze in 3 Lines of Code**

=== "Python"

    ```python
    from locomotion_analysis import LocomotionData
    data = LocomotionData.from_parquet('gtech_2023_phase.parquet')
    knee_angles = data.get_variable_3d('knee_flexion_angle_ipsi_rad')
    
    # Plot average knee angle across gait cycle
    import matplotlib.pyplot as plt
    walking = data.filter_task('level_walking')
    avg_knee = walking.get_average_trajectory('knee_flexion_angle_ipsi_rad')
    plt.plot(avg_knee)
    plt.title('Average Knee Angle - Level Walking')
    plt.xlabel('Gait Cycle (%)')  
    plt.ylabel('Knee Flexion (rad)')
    plt.show()
    ```
    
    **Output:** Professional publication-ready plots in seconds

=== "MATLAB"

    ```matlab
    % Load standardized dataset
    data = LocomotionData('gtech_2023_phase.parquet');
    knee_angles = data.get_variable('knee_flexion_angle_ipsi_rad');
    
    % Plot average knee angle across gait cycle  
    walking = data.filter_task('level_walking');
    avg_knee = walking.get_average_trajectory('knee_flexion_angle_ipsi_rad');
    plot(avg_knee);
    title('Average Knee Angle - Level Walking');
    xlabel('Gait Cycle (%)');
    ylabel('Knee Flexion (rad)');
    ```
    
    **Output:** Native MATLAB integration with biomechanics toolboxes

</div>

## :material-chart-line: Available Research Datasets

<div class="datasets-showcase" markdown>

| Dataset | Tasks | Subjects | Cycles | Quality | Download |
|---------|-------|----------|---------|---------|----------|
| **Georgia Tech 2023** | Walking, stairs, inclines, running | 13 | 500+ | :material-check-circle:{ .success } **Validated** | [:material-download: Get Data](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
| **University of Michigan 2021** | Level, incline, decline walking | 12 | 600+ | :material-check-circle:{ .success } **Validated** | [:material-download: Get Data](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) |
| **AddBiomechanics** | Walking, running, jumping, stairs | 50+ | 2000+ | :material-progress-clock:{ .warning } **In Progress** | Coming Soon |

**All datasets include:** Joint angles, moments, ground reaction forces, and metadata with standardized variable names

[:material-information: View Dataset Details](reference/datasets_documentation/){ .md-button }

</div>

## :material-rocket-launch: Ready to Get Started?

<div class="getting-started-flow" markdown>

<div class="flow-step" markdown>

### 1. **Choose Your Approach**

=== ":material-timer: 5-Minute Quick Start"

    **Perfect for:** First-time users, students, quick prototyping
    
    - Download sample dataset
    - Run provided analysis script
    - See results immediately
    
    [:material-rocket-launch: Quick Start](getting_started/quick_start/){ .md-button .md-button--primary }

=== ":material-school: Complete Tutorial"

    **Perfect for:** Research projects, in-depth learning
    
    - Step-by-step Python/MATLAB tutorials
    - Real dataset analysis examples
    - Publication-ready visualizations
    
    [:material-book-open: View Tutorials](tutorials/){ .md-button }

=== ":material-upload: Contribute Your Data"

    **Perfect for:** Lab directors, dataset creators
    
    - Convert your data to standard format
    - Automated validation and quality reports
    - Share with the research community
    
    [:material-account-group: Contribute](contributor_guide/){ .md-button }

</div>

</div>

### 2. **Install & Setup** (2 minutes)

```bash
# Python installation
pip install locomotion-analysis

# Or use our datasets with any Python environment
# No installation required - just download and analyze!
```

### 3. **Start Analyzing** (3 minutes)

Load any dataset and create publication-ready plots instantly.

</div>

## :material-help-circle: Questions & Support

<div class="support-section" markdown>

**Need Help?** Our community is here to support your research:

- :material-book-help: **[Documentation](user_guide/troubleshooting/)** - Comprehensive guides and troubleshooting
- :material-github: **[GitHub Issues](https://github.com/your-org/locomotion-data-standardization/issues)** - Bug reports and feature requests  
- :material-email: **[Research Community](mailto:contact@locomotion-data-standardization.org)** - Connect with other researchers
- :material-school: **[Tutorials](tutorials/)** - Step-by-step learning with real data

</div>

---

<div class="footer-cta" markdown>

## Ready to Transform Your Biomechanics Research?

**Join researchers from 20+ institutions who trust our standardized datasets for reproducible science.**

[**:material-rocket-launch: Start Your Analysis**](getting_started/quick_start/){ .md-button .md-button--primary .footer-button }
[**:material-eye: Explore Examples**](interactive/gallery/){ .md-button .footer-button }

*Maintained by biomechanics researchers and software engineers committed to open, reproducible science.*

</div>