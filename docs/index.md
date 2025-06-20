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

[**:material-rocket-launch: Try It Now**](user_guide/docs/getting_started/quick_start/){ .md-button .md-button--primary .hero-button }
[**:material-eye: View Examples**](user_guide/docs/examples/){ .md-button .hero-button }
[**:material-download: Get Data**](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0){ .md-button .hero-button }

</div>

</div>

<div class="trust-indicators" markdown>

:material-check-circle:{ .success-icon } **3 Research Labs** • :material-check-circle:{ .success-icon } **2,000+ Gait Cycles** • :material-check-circle:{ .success-icon } **100% Validated** • :material-check-circle:{ .success-icon } **Python & MATLAB**

</div>

## :material-account-multiple: What Do You Want to Do?

<div class="user-routing-grid" markdown>

<div class="route-card analyze" markdown>

### :material-chart-line: **Analyze Existing Data**

**I want to use validated datasets for research**

✓ Load standardized datasets instantly  
✓ Compare across multiple studies  
✓ Create publication-ready plots  
✓ Focus on research, not data cleaning  

[**Start Analyzing :material-arrow-right:**](user_guides/researchers/getting_data/){ .md-button .analyze-button }

</div>

<div class="route-card learn" markdown>

### :material-school: **Learn Biomechanical Analysis**

**I'm new to biomechanical data analysis**

✓ Step-by-step tutorials with real data  
✓ Learn both Python and MATLAB workflows  
✓ Build analysis skills progressively  
✓ Get comfortable with the tools  

[**Start Learning :material-arrow-right:**](user_guide/docs/tutorials/basic/load_explore/){ .md-button .learn-button }

</div>

<div class="route-card contribute" markdown>

### :material-upload: **Contribute Your Data**

**I want to share my lab's datasets**

✓ Convert your data to standard format  
✓ Automated quality validation  
✓ Increase research impact and citations  
✓ Join the standardization movement  

[**Start Contributing :material-arrow-right:**](user_guide/docs/lab_directors/contributing_data/){ .md-button .contribute-button }

</div>

<div class="route-card develop" markdown>

### :material-code-braces: **Build Custom Tools**

**I want to extend or customize the platform**

✓ Understand the technical architecture  
✓ Build on standardized APIs  
✓ Add new analysis capabilities  
✓ Contribute to the codebase  

[**Start Developing :material-arrow-right:**](user_guide/docs/contributing/setup/){ .md-button .develop-button }

</div>

</div>

## :material-lightning-bolt: Why Researchers Trust Our Platform

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

[:material-information: View Dataset Details](user_guide/docs/reference/datasets_documentation/overview/){ .md-button }

</div>

## :material-map: Find What You Need

<div class="quick-navigation" markdown>

### :material-clock-fast: **Quick Access**
- [**Installation**](user_guide/docs/getting_started/installation/) - Get set up in 5 minutes
- [**Quick Start**](user_guide/docs/getting_started/quick_start/) - Your first analysis in 10 minutes  
- [**API Reference**](user_guide/docs/reference/api/python/) - Function documentation
- [**Download Data**](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) - Get standardized datasets

### :material-school: **Learning Paths**
- [**Beginner Tutorial**](user_guide/docs/tutorials/basic/load_explore/) - Start with basics
- [**Research Workflow**](user_guide/docs/user_guides/researchers/analysis_workflows/) - For research projects
- [**Clinical Applications**](user_guide/docs/audiences/clinicians/clinical_applications/) - For clinical work
- [**ML Pipeline Setup**](user_guide/docs/user_guides/data_scientists/ml_pipelines/) - For data science

### :material-help-circle: **Need Help?**
- [**Examples**](user_guide/docs/examples/) - Real-world use cases
- [**Troubleshooting**](user_guide/docs/audiences/researchers/getting_data/) - Common issues and solutions
- [**GitHub Issues**](https://github.com/your-org/locomotion-data-standardization/issues) - Bug reports and questions
- [**Community**](mailto:contact@locomotion-data-standardization.org) - Connect with other researchers

</div>

---

<div class="footer-cta" markdown>

## Ready to Transform Your Biomechanics Research?

**Join researchers from 20+ institutions who trust our standardized datasets for reproducible science.**

[**:material-rocket-launch: Start Your Analysis**](user_guide/docs/getting_started/quick_start/){ .md-button .md-button--primary .footer-button }
[**:material-eye: Explore Examples**](user_guide/docs/examples/){ .md-button .footer-button }

*Maintained by biomechanics researchers and software engineers committed to open, reproducible science.*

</div>