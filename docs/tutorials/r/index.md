# R Tutorials for Biomechanical Analysis

Comprehensive R Markdown templates and tutorials for research-grade biomechanical analysis using the LocomotionData package.

## :material-file-document: Research Templates

### Clinical and Research Workflows

| Template | Description | Use Case | Features |
|----------|-------------|----------|----------|
| [**Gait Analysis Report**](gait_analysis_report.Rmd) | Comprehensive clinical gait analysis | Clinical assessments, patient reports | Automated interpretation, quality metrics |
| [**Intervention Study**](intervention_study_template.Rmd) | Pre/post intervention analysis | Treatment efficacy studies | Statistical comparisons, effect sizes |
| [**Population Comparison**](population_comparison_template.Rmd) | Multi-group comparative analysis | Cohort studies, demographics | ANOVA, post-hoc tests, visualizations |
| [**Longitudinal Study**](longitudinal_study_template.Rmd) | Time-series and repeated measures | Disease progression, development | Mixed-effects models, trajectories |

### Advanced Analysis Templates

| Template | Description | Features |
|----------|-------------|----------|
| [**Interactive Research Dashboard**](interactive_dashboard_template.Rmd) | Real-time data exploration | Plotly integration, dynamic filtering |
| [**Automated Quality Assessment**](quality_assessment_template.Rmd) | Data validation and outlier detection | Automated flagging, validation reports |
| [**Publication-Ready Analysis**](publication_template.Rmd) | Journal-ready research analysis | APA formatting, statistical reporting |

## :material-school: Learning Tutorials

### Beginner Level

=== "Getting Started"
    - [**R Basics for Biomechanics**](tutorials/r_basics_biomechanics.Rmd) (30 min)
    - [**Loading and Exploring Data**](tutorials/data_loading_exploration.Rmd) (25 min)
    - [**Basic Visualizations**](tutorials/basic_visualizations.Rmd) (35 min)

=== "Core Analysis"
    - [**Statistical Analysis Fundamentals**](tutorials/statistical_analysis.Rmd) (45 min)
    - [**Gait Cycle Analysis**](tutorials/gait_cycle_analysis.Rmd) (40 min)
    - [**Quality Control Methods**](tutorials/quality_control.Rmd) (30 min)

### Advanced Level

=== "Research Methods"
    - [**Mixed-Effects Modeling**](tutorials/mixed_effects_modeling.Rmd) (60 min)
    - [**Functional Data Analysis**](tutorials/functional_data_analysis.Rmd) (75 min)
    - [**Machine Learning Applications**](tutorials/ml_applications.Rmd) (90 min)

=== "Clinical Applications"
    - [**Pathological Gait Analysis**](tutorials/pathological_gait.Rmd) (50 min)
    - [**Intervention Assessment**](tutorials/intervention_assessment.Rmd) (65 min)
    - [**Pediatric Analysis Considerations**](tutorials/pediatric_analysis.Rmd) (45 min)

## :material-chart-line: Interactive Features

### Plotly Integration

All templates include interactive visualizations with:

- **Hover Information**: Biomechanical context and values
- **Zoom and Pan**: Detailed examination of patterns
- **Dynamic Filtering**: Real-time data subset exploration
- **3D Trajectories**: Joint angle patterns in 3D space
- **Comparative Views**: Side-by-side analysis tools

### Parameterized Reports

Templates support automated generation with:

```r
# Example parameterized report generation
rmarkdown::render("gait_analysis_report.Rmd", 
                  params = list(
                    dataset = "patient_data.parquet",
                    subject_id = "PATIENT_001",
                    control_group = "healthy_controls.parquet",
                    output_dir = "reports/"
                  ))
```

## :material-cog: Setup and Requirements

### Installation

```r
# Install required packages
install.packages(c(
  "rmarkdown", "knitr", "DT", "plotly", 
  "flexdashboard", "crosstalk", "htmlwidgets",
  "lme4", "emmeans", "effectsize", "report"
))

# Load LocomotionData package
devtools::load_all("path/to/locomotion-data-standardization/source/lib/r")
```

### Template Usage

1. **Choose Template**: Select appropriate research template
2. **Configure Parameters**: Set dataset paths and analysis options
3. **Knit Report**: Generate HTML or PDF output
4. **Review Results**: Automated interpretation and recommendations

### Data Requirements

- **Phase-indexed data**: 150 points per gait cycle
- **Standard naming**: Follow LocomotionData conventions
- **Required columns**: subject, task, phase
- **File formats**: Parquet (preferred) or CSV

## :material-lightbulb: Key Features

### Automated Analysis Pipeline

- **Quality Assessment**: Automatic outlier detection and validation
- **Statistical Analysis**: Appropriate tests based on data structure
- **Effect Size Calculation**: Clinical significance metrics
- **Result Interpretation**: AI-assisted biomechanical insights

### Professional Reporting

- **Publication Standards**: APA formatting and statistical reporting
- **Clinical Summaries**: Patient-friendly result interpretation
- **Executive Reports**: Research summary for stakeholders
- **Appendix Generation**: Detailed technical information

### Research Reproducibility

- **Version Control**: Template versioning and change tracking
- **Parameter Documentation**: Complete analysis configuration
- **Data Provenance**: Source data tracking and validation
- **Code Transparency**: Full analysis code inclusion

## :material-play-circle: Quick Start

### 1. Clinical Gait Analysis

```r
# Generate a clinical gait report
rmarkdown::render("gait_analysis_report.Rmd", 
                  params = list(
                    patient_data = "patient_001.parquet",
                    reference_data = "normative_database.parquet"
                  ))
```

### 2. Research Study Analysis

```r
# Analyze intervention study
rmarkdown::render("intervention_study_template.Rmd",
                  params = list(
                    pre_data = "baseline_measurements.parquet",
                    post_data = "followup_measurements.parquet",
                    intervention = "gait_training"
                  ))
```

### 3. Interactive Dashboard

```r
# Create interactive research dashboard
rmarkdown::render("interactive_dashboard_template.Rmd",
                  output_format = "flexdashboard::flex_dashboard",
                  params = list(
                    datasets = c("study1.parquet", "study2.parquet"),
                    interactive_mode = TRUE
                  ))
```

## :material-help-circle: Support Resources

### Documentation
- [LocomotionData R Package](../../../source/lib/r/README.md)
- [Statistical Analysis Guide](statistical_analysis_guide.md)
- [Visualization Best Practices](visualization_guide.md)

### Troubleshooting
- [Common Issues](troubleshooting.md)
- [Template Customization](customization_guide.md)
- [Performance Optimization](performance_tips.md)

### Examples
- [Research Case Studies](case_studies/)
- [Clinical Applications](clinical_examples/)
- [Template Gallery](template_gallery/)

---

## :material-arrow-right: Next Steps

1. **Start with**: [Gait Analysis Report Template](gait_analysis_report.Rmd)
2. **Learn more**: [R Basics for Biomechanics](tutorials/r_basics_biomechanics.Rmd)
3. **Advanced**: [Interactive Dashboard](interactive_dashboard_template.Rmd)

Ready to analyze your biomechanical data with professional R Markdown reports!