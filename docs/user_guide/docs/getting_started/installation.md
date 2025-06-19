# Installation

Get set up to work with standardized locomotion data in just a few minutes.

## Choose Your Environment

=== "Python Users"

    ### System Requirements
    - Python 3.10 or newer (tested with Python 3.12)
    - 8GB RAM recommended (4GB minimum) 
    - 2GB disk space for datasets

    ### Quick Install
    ```bash
    # Install required packages
    pip install pandas matplotlib numpy pyarrow

    # Verify installation
    python -c "import pandas, matplotlib, numpy, pyarrow; print('Ready to go!')"
    ```

    ### Conda Environment (Recommended)
    ```bash
    # Create dedicated environment
    conda create -n locomotion python=3.12 pandas matplotlib numpy pyarrow
    conda activate locomotion

    # Verify installation
    python -c "import pandas, matplotlib, numpy, pyarrow; print('Environment ready!')"
    ```

=== "MATLAB Users"

    ### System Requirements
    - MATLAB R2019b or newer
    - Statistics and Machine Learning Toolbox (recommended)
    - 8GB RAM recommended (4GB minimum)
    - 2GB disk space for datasets

    ### Required Toolboxes
    Check if you have the required toolboxes:
    ```matlab
    % Check available toolboxes
    ver
    
    % Look for these (recommended but not required):
    % - Statistics and Machine Learning Toolbox
    % - Signal Processing Toolbox
    ```

    ### Verify Installation
    ```matlab
    % Test basic functionality
    data = table([1; 2; 3], [0.1; 0.2; 0.3], 'VariableNames', {'step', 'angle'});
    disp('MATLAB ready for locomotion data analysis!')
    ```

## Get the Library Code

Clone the repository to access the locomotion analysis libraries:

=== "Git Clone"

    ```bash
    # Clone the repository (replace with actual repository URL)
    git clone https://github.com/your-org/locomotion-data-standardization.git
    cd locomotion-data-standardization

    # Verify you have the library files
    ls lib/core/locomotion_analysis.py
    ls lib/validation/
    ```

=== "Download ZIP"

    1. Go to the GitHub repository (contact maintainers for URL)
    2. Click "Code" > "Download ZIP" 
    3. Extract the ZIP file
    4. Navigate to the extracted folder

!!! note "Sample Data Included"
    The repository includes small test datasets in the `tests/` directory for immediate experimentation.

## Verify Your Setup

Test that everything works correctly:

=== "Python Test"

    ```python
    import sys
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np

    # Add library to path (assuming you're in the repo root)
    sys.path.append('.')
    from lib.core.locomotion_analysis import LocomotionData

    # Test with included sample data
    try:
        # Load the test dataset
        data = LocomotionData('test_locomotion_data.csv')
        print("✅ LocomotionData library works!")
        
        # Test basic operations
        subjects = data.get_subjects()
        tasks = data.get_tasks()
        print(f"Subjects: {subjects}")
        print(f"Tasks: {tasks}")
        
        # Test plotting with real data (keep it minimal for verification)
        plt.figure(figsize=(8, 4))
        # Create a simple synthetic plot for verification
        phase = np.linspace(0, 100, 150)
        knee_angle = np.sin(np.linspace(0, 2*np.pi, 150)) * 0.5 + 0.3
        plt.plot(phase, knee_angle)
        plt.xlabel('Gait Cycle (%)')
        plt.ylabel('Knee Flexion (rad)')
        plt.title('Installation Verification - All Systems Working!')
        plt.grid(True)
        plt.savefig('installation_test.png')
        plt.close()  # Close to avoid display issues
        
        print("✅ Python setup fully verified! Test plot saved as 'installation_test.png'")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure you're running this from the repository root directory.")
    ```

    **Expected Output:**
    ```
    Data validation passed: 2 subjects, 2 tasks
    Loaded data with 1800 rows, 2 subjects, 2 tasks, 6 features
    Variable name validation: All 6 variables are standard compliant
    ✅ LocomotionData library works!
    Subjects: ['SUB01', 'SUB02']
    Tasks: ['fast_walk', 'normal_walk']
    ✅ Python setup fully verified! Test plot saved as 'installation_test.png'
    ```

=== "MATLAB Test"

    ```matlab
    % Add the library to MATLAB path
    addpath('source/lib/matlab');
    
    % Test basic MATLAB functionality
    try
        % Test if LocomotionData class is available
        if exist('LocomotionData.m', 'file')
            fprintf('✅ LocomotionData MATLAB class found!\n');
        else
            fprintf('⚠️ LocomotionData.m not found. Using basic functionality.\n');
        end
        
        % Test basic data operations
        phase_percent = linspace(0, 100, 150)';
        knee_angle = sin(linspace(0, 2*pi, 150))' * 0.5 + 0.3;
        
        test_data = table(...
            repmat({'SUB01'}, 150, 1), ...
            repmat({'level_walking'}, 150, 1), ...
            ones(150, 1), ...
            phase_percent, ...
            knee_angle, ...
            'VariableNames', {'subject', 'task', 'step', 'phase_percent', 'knee_flexion_angle_ipsi_rad'});

        % Test basic operations
        fprintf('Dataset size: %d rows, %d columns\n', height(test_data), width(test_data));
        fprintf('Available columns: %s\n', strjoin(test_data.Properties.VariableNames, ', '));

        % Test plotting
        figure;
        plot(test_data.phase_percent, test_data.knee_flexion_angle_ipsi_rad);
        xlabel('Gait Cycle (%)');
        ylabel('Knee Flexion (rad)');
        title('MATLAB Installation Verification');
        grid on;
        saveas(gcf, 'matlab_installation_test.png');
        close;  % Close figure
        
        fprintf('✅ MATLAB setup verified! Test plot saved as ''matlab_installation_test.png''\n');
        
    catch ME
        fprintf('❌ Error: %s\n', ME.message);
        fprintf('Make sure you''re running from the repository root directory.\n');
    end
    ```

## Common Installation Issues

### Python Issues

!!! warning "ImportError: No module named 'pandas'"
    **Solution:** Install pandas
    ```bash
    pip install pandas
    ```

!!! warning "ModuleNotFoundError: No module named 'lib'"
    **Solution:** Make sure you're running Python from the repository root directory
    ```bash
    # Navigate to the repository root
    cd locomotion-data-standardization
    python your_script.py
    ```

!!! warning "Missing required columns: ['subject', 'task', 'phase']"
    **Solution:** Your dataset uses different column names. The LocomotionData library expects standardized names.
    ```python
    # Check what columns your data has
    import pandas as pd
    df = pd.read_csv('your_data.csv')
    print(df.columns.tolist())
    
    # For non-standard datasets, rename columns first:
    df = df.rename(columns={
        'subject_id': 'subject',
        'task_id': 'task', 
        'phase_pct': 'phase'  # and so on
    })
    df.to_csv('standardized_data.csv', index=False)
    ```

!!! warning "Memory Error when loading large datasets"
    **Solution:** Use chunked loading or work with smaller subsets
    ```python
    # Load only specific subjects or tasks
    data = LocomotionData('large_dataset.parquet')
    subset = data.get_cycles('SUB01', 'normal_walk')  # Work with smaller subsets
    ```

### MATLAB Issues

!!! warning "Error using readtable: Unable to interpret file"
    **Solution:** Check MATLAB version and file format
    ```matlab
    % Check MATLAB version
    version
    
    % For older MATLAB versions, convert parquet to CSV first
    % (conversion instructions in troubleshooting guide)
    ```

!!! warning "Out of memory errors"
    **Solution:** Clear workspace and increase memory
    ```matlab
    clear all
    close all
    
    % Check available memory
    feature('memstats')
    ```

## What's Working and What's Not

After installation, here's what you can expect:

### ✅ Fully Working
- **Python LocomotionData library** - Load and analyze standardized CSV/parquet data
- **Data validation system** - Comprehensive biomechanical validation
- **Basic plotting** - matplotlib-based visualization
- **Variable name validation** - Ensures standard naming conventions
- **Memory-efficient operations** - Handles large datasets with 3D array operations

### ⚠️ Limited or Beta Status
- **MATLAB integration** - Basic MATLAB class available but less feature-complete than Python
- **Large dataset handling** - Some memory limitations with very large files
- **Advanced visualizations** - Basic plots work, advanced features may need customization

### ❌ Known Gaps
- **Column mapping** - Non-standard datasets need manual column renaming
- **Real-time analysis** - System designed for batch processing
- **GUI interface** - Command-line and script-based only

## Next Steps

Once your installation is verified:

1. **[Quick Start](quick_start/)** - Load and analyze your first dataset  
2. **[First Dataset](first_dataset/)** - Work through a complete analysis example
3. **[Python Tutorial](../tutorials/python/getting_started_python/)** - Comprehensive Python guide
4. **[MATLAB Tutorial](../tutorials/matlab/getting_started_matlab/)** - Comprehensive MATLAB guide

## Need Help?

- **Installation problems?** Check our [Troubleshooting Guide](../user_guide/troubleshooting/)
- **Environment issues?** See platform-specific guides below
- **Still stuck?** Contact the project maintainers or check project documentation

### Platform-Specific Notes

=== "Windows"

    - Use Anaconda for Python package management
    - MATLAB path issues: Add toolbox directories manually
    - Recommended: Use Windows Subsystem for Linux (WSL) for command-line tools

=== "macOS"

    - Use Homebrew for system dependencies
    - Python: Install via `brew install python` or Anaconda
    - MATLAB: Standard installation works well

=== "Linux"

    - Install Python via package manager or conda
    - Ensure you have build tools: `sudo apt-get install build-essential`
    - For MATLAB: May need to install additional libraries

---

*Ready to start analyzing locomotion data? Continue to the [Quick Start Guide](quick_start/).*