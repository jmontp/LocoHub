---
title: Contributing Your Data
hide:
  - navigation
  - toc
---

<div class="hero-banner" markdown>

# :material-database-plus: Contributing Your Data

## Make your biomechanics data work with data from other labs

The standardization process takes 1-2 weeks and gives you access to validated analysis tools, 
compatibility with existing datasets, and a growing research community.

<div class="hero-stats" markdown>
:material-database: **2 datasets** &nbsp; | &nbsp; :material-account-group: **25 subjects** &nbsp; | &nbsp; :material-walk: **5 tasks** &nbsp; | &nbsp; :material-timer: **1-2 weeks to convert**
</div>

[Get Started](getting_started.md){ .md-button .md-button--primary }
[View Examples](examples/umich_2021_example.md){ .md-button }

</div>

---

## Why This Matters

!!! example "Combining Datasets"

    === "Python"
        ```python
        # Combine studies from different labs
        all_data = pd.concat([umich_2021, gtech_2021, your_data])
        # 25+ subjects, 5 locomotion tasks
        ```

    === "MATLAB"
        ```matlab
        % Merge datasets from multiple sources
        all_data = [umich_2021; gtech_2021; your_data];
        % 25+ subjects, 5 locomotion tasks
        ```


    Once standardized, datasets combine without format conversion or variable mapping.

## :material-database: Current Datasets

!!! info
    | Datasets | Subjects | Tasks |
    |----------|----------|-------|
    | 2        | 25       | 5     |
    
    **University of Michigan** (10 subjects, 2021)  
    Level walking, incline, decline, stairs
    
    **Georgia Tech** (15 subjects, 2021)  
    Level walking, incline, decline, stair ascent/descent
    
    Typical conversion timeline: 1-2 weeks

---

## What You Get

=== "Benefits"
    - Compatibility with all community datasets
    - Validation tools for quality assurance
    - Analysis libraries in Python and MATLAB
    - Citations when others use your data

=== "Support"
    - Working examples from similar datasets
    - Help via GitHub discussions
    - Quick validation feedback
    - Potential collaborations on multi-dataset studies

---

## :material-tools: Validation Tools

=== "Quick Validation"
    **[`quick_validation_check.py`](tools_reference.md#quick-validation-check)**  
    Check if your data meets biomechanical expectations.
    
    === "Python"
        ```python
        import subprocess
        result = subprocess.run(
            ['python', 'quick_validation_check.py', 'your_data.parquet'],
            capture_output=True, text=True
        )
        print(result.stdout)
        ```
    
    === "Command Line"
        ```bash
        python quick_validation_check.py your_data.parquet
        # ✓ level_walking: 95% pass (380/400 strides)
        # ✗ stair_ascent: 73% pass (292/400 strides)
        
        # With plots
        python quick_validation_check.py your_data.parquet --plot
        ```

=== "Visual Tuner"
    **[`interactive_validation_tuner.py`](tools_reference.md#interactive-validation-tuner)**  
    GUI for debugging validation issues.
    
    === "Python"
        ```python
        import subprocess
        # Launch interactive GUI
        subprocess.run(['python', 'interactive_validation_tuner.py'])
        ```
    
    === "Command Line"
        ```bash
        # Launch the GUI
        python interactive_validation_tuner.py
        
        # Features:
        # - Compare passing vs failing strides
        # - Drag to adjust ranges
        # - Export custom validation YAML
        ```

=== "Dataset Filter"
    **[`create_filtered_dataset.py`](tools_reference.md#dataset-filter)**  
    Remove invalid strides from your dataset.
    
    === "Python"
        ```python
        import subprocess
        # Filter dataset
        subprocess.run([
            'python', 'create_filtered_dataset.py',
            'raw_data.parquet'
        ])
        # Creates: filtered_data.parquet
        ```
    
    === "Command Line"
        ```bash
        # Basic filtering
        python create_filtered_dataset.py raw_data.parquet
        # Creates: filtered_data.parquet
        
        # With custom ranges
        python create_filtered_dataset.py raw_data.parquet \
            --ranges custom_ranges.yaml
        
        # Exclude specific columns
        python create_filtered_dataset.py raw_data.parquet \
            --exclude-columns "emg_signal_1,emg_signal_2"
        ```

---

## :material-book-open: Documentation & Examples

!!! note "Resources"
    **Conversion Examples**  
    [MATLAB (UMich)](examples/umich_2021_example.md) | [Python (GTech)](examples/gtech_2023_example.md)
    
    **Reference Datasets**  
    [`umich_2021_phase.parquet`](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) - 10 subjects  
    [`gtech_2021_phase.parquet`](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0) - 15 subjects
    
    **Standards**  
    [Variable Naming](../reference/biomechanical_standard/) | [Task Definitions](../reference/standard_spec/task_definitions/)
    
    **Support**  
    [GitHub Discussions](https://github.com/your-repo/discussions)

---

## Additional Resources

- [Data Table Schema](contributing_skeleton.md)
- [Community](community.md)
- [Project CONTRIBUTING](CONTRIBUTING.md)

---

## Ready to Start?

The conversion process is straightforward once you understand the basics. We've built tools to handle the tedious parts and a community to help when you get stuck.

<div class="next-steps" markdown>
[**:material-rocket-launch: Get Started**](getting_started.md){ .md-button .md-button--primary .md-button--large }

Or explore:
- [**View Examples**](examples/umich_2021_example.md) - See how others converted their data
- [**Join Discussions**](https://github.com/your-repo/discussions) - Ask questions, share experiences
- [**Tools Documentation**](tools_reference.md) - Reference for all available tools
</div>

