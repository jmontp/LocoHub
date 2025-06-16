# Installation

Get set up to work with standardized locomotion data in just a few minutes.

## Choose Your Environment

=== "Python Users"

    ### System Requirements
    - Python 3.8 or newer
    - 8GB RAM recommended (4GB minimum)
    - 2GB disk space for datasets

    ### Quick Install
    ```bash
    # Install required packages
    pip install pandas matplotlib numpy pyarrow

    # Verify installation
    python -c "import pandas, matplotlib, numpy; print('Ready to go!')"
    ```

    ### Conda Environment (Recommended)
    ```bash
    # Create dedicated environment
    conda create -n locomotion python=3.10 pandas matplotlib numpy pyarrow
    conda activate locomotion

    # Verify installation
    python -c "import pandas, matplotlib, numpy; print('Environment ready!')"
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

## Download Sample Data

Get started with a small sample dataset:

=== "Command Line"

    ```bash
    # Create workspace directory
    mkdir locomotion_analysis
    cd locomotion_analysis

    # Download sample dataset (placeholder - will be updated with actual URLs)
    curl -O https://example.com/sample_gtech_2023_phase.parquet
    
    # Verify download
    ls -la *.parquet
    ```

=== "Python Script"

    ```python
    import os
    import urllib.request

    # Create workspace
    os.makedirs('locomotion_analysis', exist_ok=True)
    os.chdir('locomotion_analysis')

    # Download sample dataset
    url = 'https://example.com/sample_gtech_2023_phase.parquet'
    urllib.request.urlretrieve(url, 'sample_data.parquet')
    
    print("Sample data downloaded successfully!")
    ```

## Verify Your Setup

Test that everything works correctly:

=== "Python Test"

    ```python
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np

    # Test data loading (using built-in sample data)
    # This creates a minimal test dataset
    test_data = pd.DataFrame({
        'subject': ['SUB01'] * 150,
        'task': ['level_walking'] * 150,
        'step': [1] * 150,
        'phase_percent': np.linspace(0, 100, 150),
        'knee_flexion_angle_ipsi_rad': np.sin(np.linspace(0, 2*np.pi, 150)) * 0.5 + 0.3
    })

    # Test basic operations
    print(f"Dataset shape: {test_data.shape}")
    print(f"Available columns: {list(test_data.columns)}")
    
    # Test plotting
    plt.figure(figsize=(8, 4))
    plt.plot(test_data['phase_percent'], test_data['knee_flexion_angle_ipsi_rad'])
    plt.xlabel('Gait Cycle (%)')
    plt.ylabel('Knee Flexion (rad)')
    plt.title('Test Plot - Installation Successful!')
    plt.grid(True)
    plt.savefig('installation_test.png')
    print("✅ Python setup verified! Test plot saved as 'installation_test.png'")
    ```

=== "MATLAB Test"

    ```matlab
    % Test data loading and basic operations
    % Create test dataset
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
    title('Test Plot - Installation Successful!');
    grid on;
    saveas(gcf, 'installation_test.png');
    
    fprintf('✅ MATLAB setup verified! Test plot saved as ''installation_test.png''\n');
    ```

## Common Installation Issues

### Python Issues

!!! warning "ImportError: No module named 'pandas'"
    **Solution:** Install pandas
    ```bash
    pip install pandas
    ```

!!! warning "Memory Error when loading large datasets"
    **Solution:** Use chunked loading
    ```python
    # For large datasets, load in chunks
    chunk_size = 10000
    data_chunks = pd.read_parquet('large_dataset.parquet', chunksize=chunk_size)
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

## Next Steps

Once your installation is verified:

1. **[Quick Start](quick_start/)** - Load and analyze your first dataset
2. **[First Dataset](first_dataset/)** - Work through a complete analysis example
3. **[Python Tutorial](../tutorials/python/getting_started_python/)** - Comprehensive Python guide
4. **[MATLAB Tutorial](../tutorials/matlab/getting_started_matlab/)** - Comprehensive MATLAB guide

## Need Help?

- **Installation problems?** Check our [Troubleshooting Guide](../user_guide/troubleshooting/)
- **Environment issues?** See platform-specific guides below
- **Still stuck?** Open an issue on [GitHub](https://github.com/your-org/locomotion-data-standardization/issues)

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