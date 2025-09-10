# Getting Started

Welcome! This guide will help you understand the conversion process and get your data standardized.

---

## Before You Begin

### What You'll Need

!!! info "Requirements"
    - **Your biomechanical data** in any structured format (CSV, MAT, C3D, etc.)
    - **Python or MATLAB** environment for running conversion scripts
    - **1-2 weeks** of time for the conversion process
    - **Basic programming knowledge** to adapt our examples

### Is Your Data Suitable?

Your data is a good fit if you have:
- Locomotion tasks (walking, running, stairs, etc.)
- Kinematic and/or kinetic measurements
- Multiple gait cycles per condition
- Clear subject identifiers

Don't worry if you're missing some variables - partial datasets are welcome!

---

## Understanding the Process

The standardization process has three main phases:

```mermaid
graph LR
    A[Your Data] --> B[Standardized Format]
    B --> C[Validated Dataset]
    C --> D[Community Resource]
    
    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#e8f5e9
    style D fill:#c8e6c9
```

1. **Convert** - Transform your data to match our structure
2. **Validate** - Check biomechanical reasonableness
3. **Share** - Contribute to the community repository

---

## Your First Steps

### Step 1: Explore a Reference Dataset

Start by downloading and exploring an existing dataset to understand the structure:

!!! example "Download and Explore"
    === "Python"
        ```python
        import pandas as pd
        
        # Download umich_2021_phase.parquet from the link
        data = pd.read_parquet('umich_2021_phase.parquet')
        
        # Explore the structure
        print(f"Shape: {data.shape}")
        print(f"Columns: {data.columns.tolist()}")
        print(f"Tasks: {data['task'].unique()}")
        print(f"Subjects: {data['subject_id'].unique()}")
        
        # Look at some data
        print(data.head())
        ```
    
    === "MATLAB"
        ```matlab
        % Download umich_2021_phase.parquet from the link
        data = parquetread('umich_2021_phase.parquet');
        
        % Explore the structure
        fprintf('Shape: %d rows, %d columns\n', height(data), width(data));
        fprintf('Columns: %s\n', strjoin(data.Properties.VariableNames, ', '));
        fprintf('Tasks: %s\n', strjoin(unique(data.task), ', '));
        fprintf('Subjects: %s\n', strjoin(unique(data.subject_id), ', '));
        
        % Look at some data
        head(data)
        ```
    
    === "R"
        ```r
        library(arrow)
        
        # Download umich_2021_phase.parquet from the link
        data <- read_parquet('umich_2021_phase.parquet')
        
        # Explore the structure
        cat(sprintf("Shape: %d rows, %d columns\n", nrow(data), ncol(data)))
        cat("Columns:", paste(names(data), collapse=", "), "\n")
        cat("Tasks:", paste(unique(data$task), collapse=", "), "\n")
        cat("Subjects:", paste(unique(data$subject_id), collapse=", "), "\n")
        
        # Look at some data
        head(data)
        ```
    
    [Download umich_2021_phase.parquet](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0)

### Step 2: Install and Test Tools

First, get the tools and then try them on a known-good dataset:

!!! example "Install the Tools"
    ```bash
    # Clone the repository
    git clone https://github.com/your-repo/locomotion-data-standardization.git
    cd locomotion-data-standardization
    
    # Install Python dependencies
    pip install pandas numpy pyarrow tqdm matplotlib pyyaml
    
    # Or use requirements.txt if available
    pip install -r requirements.txt
    
    # Verify tools are accessible
    cd contributor_tools
    ls *.py  # Should see validation and filtering tools
    ```

!!! example "Try Different Tools"
    === "Quick Validation"
        ```bash
        # Fast pass/fail statistics
        python quick_validation_check.py umich_2021_phase.parquet
        
        # Expected output:
        # ✓ level_walking: 95% pass (380/400 strides)
        # ✓ incline_walking: 92% pass (368/400 strides)
        
        # With visual plots
        python quick_validation_check.py umich_2021_phase.parquet --plot
        ```
    
    === "Visual Tuner"
        ```bash
        # Launch interactive GUI
        python interactive_validation_tuner.py
        
        # In the GUI:
        # 1. Load dataset: umich_2021_phase.parquet
        # 2. Load ranges: default_ranges.yaml
        # 3. Select task and variable to visualize
        # 4. See passing (green) vs failing (red) strides
        # 5. Drag boxes to adjust ranges if needed
        ```
    
    === "Dataset Filter"
        ```bash
        # Create a filtered dataset with only valid strides
        python create_filtered_dataset.py umich_2021_phase.parquet
        
        # Expected output:
        # Loading dataset...
        # Processing 4 tasks...
        #   level_walking: 380/400 strides passed (95.0%)
        #   incline_walking: 368/400 strides passed (92.0%)
        # Saving filtered dataset...
        # Output: umich_2021_phase_filtered.parquet
        ```
    
    === "Phase Converter"
        ```bash
        # Time-to-phase conversion tool (Coming Soon)
        # This tool will automatically detect gait cycles and 
        # normalize to 150 points per cycle
        
        # Planned usage:
        # python conversion_generate_phase_dataset.py dataset_time.parquet
        
        # For now, phase conversion must be done in your 
        # conversion script. See examples for implementation.
        ```

### Step 3: Understand Key Concepts

!!! note "Important Concepts"
    **Phase Normalization**: Each gait cycle is normalized to exactly 150 points (0-100% of cycle)
    
    **Variable Naming**: Standard names like `knee_flexion_angle_ipsi_rad` ensure compatibility
    
    **Task Labels**: Use standard task names (`level_walking`, `stair_ascent`, etc.)
    
    **Validation Ranges**: Biomechanical expectations at key phases of the gait cycle

#### Understanding Validation Ranges

The validation system checks if your data falls within expected biomechanical ranges at specific phases of the gait cycle:

!!! info "How Validation Works"
    ```
    Phase Points:     0%        25%        50%        75%       100%
                      ↓          ↓          ↓          ↓          ↓
    Gait Events:  Heel Strike  Loading   Mid-Stance  Swing    Heel Strike
    
    Knee Angle:   [0°-17°]   [11°-34°]   [0°-17°]  [46°-80°]  [0°-17°]
                  (typical)   (typical)   (typical)  (typical)  (typical)
    ```
    
    At each phase point (0%, 25%, 50%, 75%), the validator checks if your variables fall within expected ranges. These ranges come from healthy adult populations but can be customized for special populations.
    
    Note: Data is stored in radians for computation, but the tools can display in degrees for easier interpretation.

!!! example "Visual Example"
    When you run the interactive tuner, you'll see plots like this:
    
    ```
    Knee Flexion at 50% Phase
    ┌────────────────────────────────────┐
    │                                    │
    │    ┌──────────┐  <- Max: 17°      │
    │    │ Valid    │                    │
    │    │ Range    │                    │
    │    └──────────┘  <- Min: 0°       │
    │                                    │
    │  Green dots = Passing strides      │
    │  Red dots = Failing strides        │
    └────────────────────────────────────┘
    ```
    
    The validation ranges ensure your data is biomechanically reasonable while allowing for natural variability.

---

## Next Steps

Once you understand the basics:

1. **[Review the Technical Guide](conversion_guide.md)** - Detailed conversion workflow
2. **[Explore Tools](tools_reference.md)** - Documentation for all helper scripts
3. **[Understand Validation](validation_reference.md)** - How quality checks work

!!! tip "Getting Help"
    - **Quick questions**: [GitHub Discussions](https://github.com/your-repo/discussions)
    - **Bug reports**: [GitHub Issues](https://github.com/your-repo/issues)
    - **Examples**: Browse `contributor_tools/conversion_scripts/`
    
    Response time is typically within 24 hours.

---

## Common Questions

??? question "How long does conversion really take?"
    Most labs complete their first dataset in 1-2 weeks:
    - Days 1-3: Understanding the format and requirements
    - Days 4-7: Writing the conversion script
    - Week 2: Validation, debugging, and refinement

??? question "What if I'm missing some variables?"
    That's fine! Include what you have. Common minimal datasets include:
    - Just kinematics (joint angles)
    - Just kinetics (moments/forces)
    - Single leg data
    
    The validator will only check variables that are present.

??? question "Can I convert multiple datasets?"
    Yes! Once you have a working conversion script for one dataset, similar datasets usually take just hours to add.

??? question "What about special populations?"
    You'll need custom validation ranges for:
    - Pediatric populations
    - Clinical populations
    - Elderly subjects
    
    The interactive tuner makes this straightforward.

---

<div class="next-steps" markdown>
**Ready to dive deeper?**

[**View Technical Guide**](conversion_guide.md){ .md-button .md-button--primary }
[**Browse Examples**](examples/umich_2021_example.md){ .md-button }
</div>