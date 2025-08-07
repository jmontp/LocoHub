# Contributing Datasets

Convert your biomechanical data to the standardized format and contribute to the research community.

## The Standardization Challenge

Every biomechanics lab collects data differently - different marker sets, joint conventions, coordinate systems, and file formats. This fragmentation prevents:

- **Meta-analyses** across multiple studies and populations
- **Validation** of findings across different labs and cohorts  
- **Machine learning** models that generalize beyond single datasets
- **Clinical translation** of research findings into practice

Your contribution helps solve this fundamental challenge in biomechanics research.

## Join the Validated Data Ecosystem

When you standardize your dataset, you're not just converting files - you're:

- **Joining a growing collection** of validated biomechanical data that researchers worldwide can access
- **Enabling reproducibility** - other researchers can directly reproduce and extend your findings
- **Contributing to population norms** - your data helps establish reference ranges across diverse populations
- **Building clinical evidence** - standardized multi-study data accelerates translation to clinical practice
- **Future-proofing your research** - your data remains valuable and usable as analysis methods evolve

## Overview of the Process

The conversion workflow below guides you through transforming your raw biomechanical data into the standardized format. Most contributors spend their time on variable mapping (Step 2) and iterative validation (Step 3). The process is designed to preserve your data's scientific value while ensuring compatibility with the ecosystem's analysis tools. Each step provides clear feedback to help you succeed.

## What Makes a Good Dataset Contribution

**Quality Criteria**:
- Clear gait cycles or movement phases that can be identified
- Consistent data collection across subjects and trials
- Documented collection protocols and equipment specifications
- Sufficient sample size for meaningful analysis

**Documentation Requirements**:
- Data source and collection context (study purpose, year, institution)
- Subject demographics and inclusion/exclusion criteria  
- Equipment and software used for collection and processing
- Any preprocessing or filtering already applied
- Known limitations or special considerations

**Validation Philosophy**:
- Validation identifies potential issues, not pass/fail judgments
- Custom ranges can be created for special populations (elderly, pathological gait, prosthetics)
- The goal is biomechanical consistency, not forcing all data into narrow ranges
- Outliers may represent real variation, not errors

## Dataset Conversion Workflow

Follow this flowchart to convert and validate your dataset:

```mermaid
flowchart TD
    Start([Start: Have Biomechanical Data]) --> Step1[Step 1: Study Reference Dataset]
    
    Step1 --> Step1Details[/"
    • Review existing datasets (e.g., umich_2021_phase.parquet)
    • Understand required columns
    • Note: 150 points per cycle for phase data
    "/]
    
    Step1Details --> Step2[Step 2: Convert to Table Format]
    
    Step2 --> Step2Details[/"
    • Create conversion script (dataset-specific)
    • Map variables to standard names
    • Follow examples in contributor_tools/conversion_scripts/
    "/]
    
    Step2Details --> CheckPhase{Does your data<br/>have phase indexing?}
    
    CheckPhase -->|No| ConvertPhase[Convert Time to Phase]
    ConvertPhase --> ConvertDetails[/"
    Run: python conversion_generate_phase_dataset.py dataset_time.parquet
    Converts to 150 points per gait cycle
    "/]
    ConvertDetails --> CheckRanges
    
    CheckPhase -->|Yes| CheckRanges{Do validation ranges<br/>exist for your population?}
    
    CheckRanges -->|Yes, Standard Population| Step3[Step 3: Validate Dataset]
    
    CheckRanges -->|No, or Special Population| CreateRanges[Create Validation Ranges]
    CreateRanges --> RangeOptions[/"
    Choose Method:
    • Generate from your data (automated_fine_tuning.py)
    • Copy and modify existing ranges
    • Create manually for special needs
    "/]
    RangeOptions --> SaveRanges[/"
    Save to: contributor_tools/validation_ranges/
    "/]
    SaveRanges --> Step3
    
    Step3 --> ValidateCmd[/"
    Run: python contributor_tools/create_dataset_validation_report.py \
         --dataset your_dataset_phase.parquet
    "/]
    
    ValidateCmd --> CheckValid{Validation<br/>Issues to Address?}
    
    CheckValid -->|No Issues| Success([✓ Success!<br/>Dataset Ready])
    Success --> SuccessSteps[/"
    • Add to converted_datasets/
    • Update documentation
    • Share with community
    "/]
    
    CheckValid -->|Has Issues| Review[Review Validation Report]
    Review --> FixIssues[/"
    • Check error messages
    • Fix variable mapping
    • Adjust data processing
    • Consider custom ranges
    "/]
    FixIssues --> Step2
    
    style Start fill:#e1f5e1
    style Success fill:#c8e6c9
    style CheckPhase fill:#fff3e0
    style CheckRanges fill:#fff3e0
    style CheckValid fill:#fff3e0
    style CreateRanges fill:#e3f2fd
    style Review fill:#ffebee
```

## Quick Start Guide

### 1. Study Reference Dataset

First, examine an existing converted dataset to understand the expected structure:

```python
import pandas as pd

# Load a reference dataset
reference = pd.read_parquet('converted_datasets/umich_2021_phase.parquet')

# Check structure
print(f"Shape: {reference.shape}")
print(f"Columns: {reference.columns.tolist()}")
print(f"Required columns: subject_id, task, phase_percent")
print(f"Points per cycle: {reference[reference['subject_id'] == reference['subject_id'].iloc[0]].groupby('phase_percent').size().iloc[0]}")
```

### 2. Convert Your Data

Create a conversion script for your dataset. See working examples:
- **MATLAB data**: [`contributor_tools/conversion_scripts/Umich_2021/`](../../contributor_tools/conversion_scripts/Umich_2021/)
- **Python data**: [`contributor_tools/conversion_scripts/Gtech_2023/`](../../contributor_tools/conversion_scripts/Gtech_2023/)

Key requirements:
- **Standard variable names**: e.g., `knee_flexion_angle_ipsi_rad`, `hip_moment_contra_Nm`
- **Required columns**: `subject_id`, `task`, `phase_percent` (0-100)
- **Units**: Angles in radians, forces in Newtons, distances in meters

### 3. Handle Phase Indexing

#### If your data is time-indexed:
```bash
# Convert time-indexed to phase-indexed (150 points per cycle)
python conversion_generate_phase_dataset.py converted_datasets/your_dataset_time.parquet

# This creates: your_dataset_phase.parquet
```

#### If your data is already phase-indexed:
- Ensure exactly 150 points per gait cycle
- Phase values from 0 to 100 (percent of gait cycle)

### 4. Validate Your Dataset

```bash
# Run validation
python contributor_tools/create_dataset_validation_report.py \
    --dataset converted_datasets/your_dataset_phase.parquet

# Check the generated report for:
# - Biomechanical consistency across variables
# - Identification of potential outliers
# - Suggestions for improvement
```

## Common Issues and Solutions

### Issue: Variable names don't match standard
**Solution**: Map your variables to standard names in your conversion script:
```python
# Example mapping
variable_mapping = {
    'KneeAngle_L': 'knee_flexion_angle_ipsi_rad',
    'HipMoment_R': 'hip_moment_contra_Nm',
    # Add all your mappings
}
```

### Issue: Wrong number of points per cycle
**Solution**: Use the phase conversion tool:
```bash
python conversion_generate_phase_dataset.py your_dataset_time.parquet
```

### Issue: Validation failures
**Solution**: Check the validation report for specific issues:
- Out-of-range values at certain phases
- Missing required variables
- Incorrect units (degrees vs radians)

## Working Examples

### Example 1: MATLAB Dataset (Umich_2021)

See the complete conversion workflow in [`examples/umich_2021_example.md`](examples/umich_2021_example.md)

Key files:
- Input: MATLAB `.mat` files
- Converter: `convert_umich_phase_to_parquet.m`
- Output: `umich_2021_phase.parquet`

### Example 2: Python Dataset (Gtech_2023)

See the complete conversion workflow in [`examples/gtech_2023_example.md`](examples/gtech_2023_example.md)

Key files:
- Input: Multiple subject files
- Converter: `convert_gtech_all_to_parquet.py`
- Output: `gtech_2023_phase.parquet`

## Resources

- **[Conversion Guide](conversion_guide.md)** - Detailed step-by-step instructions
- **[Validation Reference](validation_reference.md)** - Understanding validation checks
- **[Standard Specification](../reference/standard_spec/standard_spec.md)** - Complete data format specification
- **[Variable Naming](../reference/standard_spec/units_and_conventions.md)** - Standard variable names and units

## Getting Help

1. **Check existing examples** in `contributor_tools/conversion_scripts/`
2. **Review validation errors** carefully - they usually indicate the exact issue
3. **Open an issue** on GitHub if you encounter problems
4. **Contact maintainers** for dataset-specific questions

## Next Steps

Once your dataset passes validation:

1. **Document your dataset** - Add README describing the data source
2. **Test with analysis tools** - Verify it works with `LocomotionData` class
3. **Share with community** - Submit pull request with your converted dataset

---

**Ready to start?** Follow the flowchart above and use the working examples as templates for your conversion.