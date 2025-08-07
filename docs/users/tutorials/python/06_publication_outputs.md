# Tutorial 6: Publication Outputs

## Overview

Learn to create publication-ready figures, tables, and reproducible analysis reports from your biomechanical data.

## Learning Objectives

- Create multi-panel figures with consistent formatting
- Generate publication-ready tables with statistics
- Apply journal-specific formatting requirements
- Ensure reproducibility of analyses
- Prepare data for sharing and archiving

## Setup

=== "Using Library"
    ```python
    from user_libs.python.locomotion_data import LocomotionData
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from matplotlib import rcParams
    import pandas as pd
    
    # Load data
    data = LocomotionData('converted_datasets/umich_2021_phase.parquet')
    
    # Set publication style
    data.set_publication_style('biomechanics')  # or 'nature', 'ieee', etc.
    ```

=== "Using Raw Data"
    ```python
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    from matplotlib import rcParams
    import seaborn as sns
    
    # Load data
    data = pd.read_parquet('converted_datasets/umich_2021_phase.parquet')
    
    # Set publication style
    plt.style.use('seaborn-v0_8-paper')
    rcParams['font.family'] = 'sans-serif'
    rcParams['font.sans-serif'] = ['Arial']
    rcParams['font.size'] = 10
    ```

## Multi-Panel Figures

### Creating Complex Layouts

=== "Using Library"
    ```python
    # Create multi-panel figure
    fig = data.create_publication_figure(
        layout='2x3',  # 2 rows, 3 columns
        figsize=(180, 120),  # mm for journal specs
        dpi=300
    )
    
    # Add panels
    fig.add_panel(0, 0, 'phase_pattern', 
                  subject='SUB01', task='level_walking',
                  variable='knee_flexion_angle_ipsi_rad',
                  title='A. Knee Flexion')
    
    fig.add_panel(0, 1, 'phase_pattern',
                  subject='SUB01', task='level_walking', 
                  variable='hip_flexion_angle_ipsi_rad',
                  title='B. Hip Flexion')
    
    fig.add_panel(0, 2, 'phase_pattern',
                  subject='SUB01', task='level_walking',
                  variable='ankle_flexion_angle_ipsi_rad', 
                  title='C. Ankle Flexion')
    
    fig.add_panel(1, 0, 'group_comparison',
                  task='level_walking',
                  variable='knee_flexion_angle_ipsi_rad',
                  title='D. Group Comparison')
    
    fig.add_panel(1, 1, 'correlation',
                  x_var='knee_rom', y_var='walking_speed',
                  title='E. ROM vs Speed')
    
    fig.add_panel(1, 2, 'boxplot',
                  variable='stride_time',
                  groups=['young', 'elderly'],
                  title='F. Stride Time')
    
    # Apply consistent formatting
    fig.format_for_journal('jbiomech')
    
    # Save
    fig.save('figure1.pdf', dpi=300)
    ```

=== "Using Raw Data"
    ```python
    # Create figure with GridSpec for complex layout
    fig = plt.figure(figsize=(7.08, 4.72))  # 180mm x 120mm at 300 dpi
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    # Panel A: Knee Flexion
    ax1 = fig.add_subplot(gs[0, 0])
    subject_data = data[(data['subject'] == 'SUB01') & (data['task'] == 'level_walking')]
    mean_knee = subject_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
    std_knee = subject_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].std()
    
    ax1.plot(mean_knee.index, np.degrees(mean_knee), 'b-', linewidth=1.5)
    ax1.fill_between(mean_knee.index, 
                     np.degrees(mean_knee - std_knee),
                     np.degrees(mean_knee + std_knee),
                     alpha=0.3, color='blue')
    ax1.set_title('A. Knee Flexion', fontsize=10, fontweight='bold', loc='left')
    ax1.set_xlabel('Gait Cycle (%)', fontsize=9)
    ax1.set_ylabel('Angle (°)', fontsize=9)
    ax1.tick_params(labelsize=8)
    ax1.grid(True, alpha=0.3, linewidth=0.5)
    
    # Panel B: Hip Flexion
    ax2 = fig.add_subplot(gs[0, 1])
    mean_hip = subject_data.groupby('phase_percent')['hip_flexion_angle_ipsi_rad'].mean()
    std_hip = subject_data.groupby('phase_percent')['hip_flexion_angle_ipsi_rad'].std()
    
    ax2.plot(mean_hip.index, np.degrees(mean_hip), 'r-', linewidth=1.5)
    ax2.fill_between(mean_hip.index,
                     np.degrees(mean_hip - std_hip),
                     np.degrees(mean_hip + std_hip),
                     alpha=0.3, color='red')
    ax2.set_title('B. Hip Flexion', fontsize=10, fontweight='bold', loc='left')
    ax2.set_xlabel('Gait Cycle (%)', fontsize=9)
    ax2.set_ylabel('Angle (°)', fontsize=9)
    ax2.tick_params(labelsize=8)
    ax2.grid(True, alpha=0.3, linewidth=0.5)
    
    # Panel C: Ankle Flexion
    ax3 = fig.add_subplot(gs[0, 2])
    mean_ankle = subject_data.groupby('phase_percent')['ankle_flexion_angle_ipsi_rad'].mean()
    std_ankle = subject_data.groupby('phase_percent')['ankle_flexion_angle_ipsi_rad'].std()
    
    ax3.plot(mean_ankle.index, np.degrees(mean_ankle), 'g-', linewidth=1.5)
    ax3.fill_between(mean_ankle.index,
                     np.degrees(mean_ankle - std_ankle),
                     np.degrees(mean_ankle + std_ankle),
                     alpha=0.3, color='green')
    ax3.set_title('C. Ankle Flexion', fontsize=10, fontweight='bold', loc='left')
    ax3.set_xlabel('Gait Cycle (%)', fontsize=9)
    ax3.set_ylabel('Angle (°)', fontsize=9)
    ax3.tick_params(labelsize=8)
    ax3.grid(True, alpha=0.3, linewidth=0.5)
    
    # Additional panels would follow similar pattern...
    
    # Remove top and right spines for all axes
    for ax in [ax1, ax2, ax3]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    # Save at high DPI
    fig.savefig('figure1.pdf', dpi=300, bbox_inches='tight')
    fig.savefig('figure1.png', dpi=300, bbox_inches='tight')
    ```

### Consistent Formatting

=== "Using Library"
    ```python
    # Define consistent style for all figures
    style_config = {
        'line_width': 1.5,
        'font_size': 10,
        'label_size': 9,
        'tick_size': 8,
        'colors': ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'],
        'alpha_fill': 0.3,
        'grid': True,
        'spines': ['left', 'bottom'],
        'legend_loc': 'best',
        'figure_dpi': 300
    }
    
    # Apply to all figures in session
    data.set_figure_style(style_config)
    
    # Create figures with consistent style
    fig1 = data.create_figure('knee_patterns', style='consistent')
    fig2 = data.create_figure('hip_patterns', style='consistent')
    
    # Batch export with same settings
    data.export_all_figures(
        format='pdf',
        dpi=300,
        path='figures/'
    )
    ```

=== "Using Raw Data"
    ```python
    # Define consistent style parameters
    def set_publication_style():
        """Set consistent style for all figures."""
        plt.style.use('seaborn-v0_8-whitegrid')
        
        # Font settings
        rcParams['font.family'] = 'sans-serif'
        rcParams['font.sans-serif'] = ['Arial']
        rcParams['font.size'] = 10
        rcParams['axes.labelsize'] = 10
        rcParams['axes.titlesize'] = 11
        rcParams['xtick.labelsize'] = 9
        rcParams['ytick.labelsize'] = 9
        rcParams['legend.fontsize'] = 9
        
        # Line settings
        rcParams['lines.linewidth'] = 1.5
        rcParams['patch.linewidth'] = 0.5
        
        # Grid settings
        rcParams['grid.linewidth'] = 0.5
        rcParams['grid.alpha'] = 0.3
        
        # Figure settings
        rcParams['figure.dpi'] = 100
        rcParams['savefig.dpi'] = 300
        
        # Color palette
        colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
        return colors
    
    # Apply style
    colors = set_publication_style()
    
    # Function to format axes consistently
    def format_axis(ax, xlabel='', ylabel='', title=''):
        """Apply consistent formatting to axis."""
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title, loc='left', fontweight='bold')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(direction='out', length=4, width=0.5)
        ax.grid(True, alpha=0.3, linewidth=0.5)
        
        return ax
    ```

## Journal-Ready Tables

### Summary Statistics Table

=== "Using Library"
    ```python
    # Generate comprehensive statistics table
    stats_table = data.create_statistics_table(
        subjects='all',
        task='level_walking',
        variables=['knee_flexion_angle_ipsi_rad', 
                  'hip_flexion_angle_ipsi_rad',
                  'ankle_flexion_angle_ipsi_rad'],
        metrics=['mean_rom', 'peak_value', 'peak_timing', 'symmetry_index'],
        format='latex'  # or 'html', 'markdown', 'excel'
    )
    
    # Add significance indicators
    stats_table.add_significance_markers(
        reference_group='control',
        test='mann-whitney'
    )
    
    # Format for specific journal
    stats_table.format_for_journal('gait_posture')
    
    # Export
    stats_table.to_latex('table1.tex', caption='Kinematic parameters during level walking')
    stats_table.to_excel('table1.xlsx')
    ```

=== "Using Raw Data"
    ```python
    # Create summary statistics table
    subjects = data['subject'].unique()
    variables = ['knee_flexion_angle_ipsi_rad', 
                'hip_flexion_angle_ipsi_rad',
                'ankle_flexion_angle_ipsi_rad']
    
    # Calculate statistics
    stats_list = []
    for var in variables:
        var_stats = {}
        var_stats['Variable'] = var.replace('_', ' ').title()
        
        # Calculate for each subject
        rom_values = []
        peak_values = []
        
        for subject in subjects:
            subject_data = data[(data['subject'] == subject) & 
                               (data['task'] == 'level_walking')]
            if len(subject_data) > 0:
                cycles = subject_data['cycle_id'].unique()
                for cycle in cycles:
                    cycle_data = subject_data[subject_data['cycle_id'] == cycle]
                    values = cycle_data[var].values
                    rom = np.max(values) - np.min(values)
                    peak = np.max(values)
                    rom_values.append(np.degrees(rom))
                    peak_values.append(np.degrees(peak))
        
        # Calculate group statistics
        var_stats['ROM (°)'] = f"{np.mean(rom_values):.1f} ± {np.std(rom_values):.1f}"
        var_stats['Peak (°)'] = f"{np.mean(peak_values):.1f} ± {np.std(peak_values):.1f}"
        var_stats['N'] = len(subjects)
        
        stats_list.append(var_stats)
    
    # Create DataFrame
    stats_df = pd.DataFrame(stats_list)
    
    # Format as LaTeX
    latex_table = stats_df.to_latex(
        index=False,
        caption='Kinematic parameters during level walking (mean ± SD)',
        label='tab:kinematics',
        column_format='lccc',
        escape=False
    )
    
    # Save to file
    with open('table1.tex', 'w') as f:
        f.write(latex_table)
    
    # Also save as Excel
    stats_df.to_excel('table1.xlsx', index=False)
    
    print(stats_df)
    ```

### Demographic Table

=== "Using Library"
    ```python
    # Create demographic table
    demo_table = data.create_demographic_table(
        include_stats=['age', 'height', 'weight', 'bmi', 'sex'],
        group_by='condition',  # If groups exist
        show_normality=True
    )
    
    # Format values
    demo_table.format_values(
        decimal_places={'age': 1, 'height': 1, 'weight': 1, 'bmi': 1},
        units={'height': 'cm', 'weight': 'kg', 'bmi': 'kg/m²'}
    )
    
    # Add statistical comparisons
    demo_table.add_group_comparisons(test='auto')  # Automatically choose test
    
    # Export
    demo_table.to_word('demographics.docx')
    ```

=== "Using Raw Data"
    ```python
    # Create demographic table (assuming metadata exists)
    # For this example, we'll create sample demographic data
    np.random.seed(42)
    
    demographics = pd.DataFrame({
        'Subject': [f'SUB{i:02d}' for i in range(1, 21)],
        'Age (years)': np.random.normal(35, 10, 20).round(1),
        'Height (cm)': np.random.normal(170, 10, 20).round(1),
        'Weight (kg)': np.random.normal(70, 12, 20).round(1),
        'Sex': np.random.choice(['M', 'F'], 20),
        'Group': np.random.choice(['Control', 'Patient'], 20)
    })
    
    # Calculate BMI
    demographics['BMI (kg/m²)'] = (
        demographics['Weight (kg)'] / 
        (demographics['Height (cm)'] / 100) ** 2
    ).round(1)
    
    # Create summary table by group
    summary = demographics.groupby('Group').agg({
        'Age (years)': ['mean', 'std'],
        'Height (cm)': ['mean', 'std'],
        'Weight (kg)': ['mean', 'std'],
        'BMI (kg/m²)': ['mean', 'std'],
        'Sex': lambda x: f"M/F: {(x=='M').sum()}/{(x=='F').sum()}"
    }).round(1)
    
    # Format as mean ± SD
    formatted_summary = pd.DataFrame()
    for col in ['Age (years)', 'Height (cm)', 'Weight (kg)', 'BMI (kg/m²)']:
        formatted_summary[col] = summary[col].apply(
            lambda x: f"{x['mean']:.1f} ± {x['std']:.1f}", axis=1
        )
    formatted_summary['Sex (M/F)'] = summary['Sex']['<lambda_0>']
    
    print(formatted_summary)
    
    # Save to Excel
    formatted_summary.to_excel('demographics.xlsx')
    ```

## Color Schemes and Accessibility

### Colorblind-Friendly Palettes

=== "Using Library"
    ```python
    # Use colorblind-friendly palettes
    fig = data.create_comparison_figure(
        groups=['control', 'patient1', 'patient2'],
        color_scheme='colorblind_safe'  # Built-in accessible palettes
    )
    
    # Or specify custom accessible colors
    colors = data.get_accessible_colors(
        n_colors=4,
        palette='viridis'  # or 'cividis', 'wong', 'okabe_ito'
    )
    
    # Apply to figure
    fig.set_group_colors(colors)
    
    # Add patterns for additional distinction
    fig.add_patterns(['solid', 'dashed', 'dotted'])
    
    # Check accessibility
    accessibility_report = fig.check_accessibility()
    print(f"Contrast ratio: {accessibility_report['contrast_ratio']}")
    print(f"Colorblind safe: {accessibility_report['colorblind_safe']}")
    ```

=== "Using Raw Data"
    ```python
    # Define colorblind-friendly palette
    # Wong palette - optimized for colorblind viewers
    wong_palette = [
        '#000000',  # Black
        '#E69F00',  # Orange
        '#56B4E9',  # Sky blue
        '#009E73',  # Bluish green
        '#F0E442',  # Yellow
        '#0072B2',  # Blue
        '#D55E00',  # Vermillion
        '#CC79A7'   # Reddish purple
    ]
    
    # Okabe-Ito palette
    okabe_ito = [
        '#E69F00',  # Orange
        '#56B4E9',  # Sky blue
        '#009E73',  # Green
        '#F0E442',  # Yellow
        '#0072B2',  # Blue
        '#D55E00',  # Vermillion
        '#CC79A7',  # Pink
        '#999999'   # Gray
    ]
    
    # Create figure with accessible colors
    fig, ax = plt.subplots(figsize=(10, 6))
    
    groups = ['Control', 'Condition A', 'Condition B']
    colors = wong_palette[:3]
    linestyles = ['-', '--', ':']  # Additional distinction
    
    for i, group in enumerate(groups):
        # Filter data for group
        group_data = data[data['group'] == group]  # Assuming group column exists
        mean_curve = group_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
        
        ax.plot(mean_curve.index, np.degrees(mean_curve),
               color=colors[i], linestyle=linestyles[i],
               linewidth=2, label=group)
    
    ax.set_xlabel('Gait Cycle (%)')
    ax.set_ylabel('Knee Flexion (°)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Add direct labels for additional clarity
    for i, group in enumerate(groups):
        ax.text(95, np.degrees(mean_curve.iloc[-1]) + i*2, group,
               color=colors[i], fontweight='bold')
    
    plt.show()
    ```

## Reproducible Workflows

### Analysis Scripts

=== "Using Library"
    ```python
    # Create reproducible analysis script
    analysis = data.create_reproducible_analysis(
        name='knee_flexion_analysis',
        author='Your Name',
        date='2024-01-01'
    )
    
    # Record all processing steps
    analysis.add_step('load_data', 
                     filepath='converted_datasets/umich_2021_phase.parquet')
    analysis.add_step('filter', 
                     task='level_walking', 
                     min_cycles=5)
    analysis.add_step('calculate_rom')
    analysis.add_step('statistical_test', 
                     method='anova', 
                     alpha=0.05)
    
    # Generate complete script
    analysis.generate_script('analysis_script.py')
    
    # Create methods section for paper
    methods_text = analysis.generate_methods_text(
        style='biomechanics_journal'
    )
    
    # Save analysis log
    analysis.save_log('analysis_log.json')
    ```

=== "Using Raw Data"
    ```python
    # Create reproducible analysis script
    import json
    from datetime import datetime
    import sys
    
    # Record analysis parameters
    analysis_log = {
        'date': datetime.now().isoformat(),
        'python_version': sys.version,
        'data_file': 'converted_datasets/umich_2021_phase.parquet',
        'parameters': {
            'task': 'level_walking',
            'min_cycles': 5,
            'statistical_test': 'anova',
            'alpha': 0.05
        },
        'packages': {
            'pandas': pd.__version__,
            'numpy': np.__version__,
            'matplotlib': plt.matplotlib.__version__
        }
    }
    
    # Function to log each step
    def log_step(step_name, **kwargs):
        if 'steps' not in analysis_log:
            analysis_log['steps'] = []
        
        step = {
            'step': step_name,
            'timestamp': datetime.now().isoformat(),
            'parameters': kwargs
        }
        analysis_log['steps'].append(step)
        print(f"Step logged: {step_name}")
    
    # Example analysis with logging
    log_step('load_data', file='umich_2021_phase.parquet')
    data = pd.read_parquet('converted_datasets/umich_2021_phase.parquet')
    
    log_step('filter_data', task='level_walking')
    filtered_data = data[data['task'] == 'level_walking']
    
    log_step('calculate_rom', variable='knee_flexion_angle_ipsi_rad')
    rom_values = []
    for subject in filtered_data['subject'].unique():
        subject_data = filtered_data[filtered_data['subject'] == subject]
        rom = subject_data['knee_flexion_angle_ipsi_rad'].max() - \
              subject_data['knee_flexion_angle_ipsi_rad'].min()
        rom_values.append(rom)
    
    log_step('statistical_analysis', test='descriptive')
    results = {
        'mean_rom': np.mean(rom_values),
        'std_rom': np.std(rom_values),
        'n_subjects': len(rom_values)
    }
    
    analysis_log['results'] = results
    
    # Save log
    with open('analysis_log.json', 'w') as f:
        json.dump(analysis_log, f, indent=2)
    
    # Generate methods text
    methods_text = f"""
    Data Processing and Analysis
    
    Biomechanical data were loaded from standardized parquet files containing 
    phase-normalized gait cycles (150 points per cycle). Data were filtered to 
    include only level walking trials with a minimum of {analysis_log['parameters']['min_cycles']} 
    cycles per subject. 
    
    Range of motion (ROM) was calculated as the difference between maximum and 
    minimum values across the gait cycle. Statistical analyses were performed 
    using Python {sys.version.split()[0]} with pandas {pd.__version__} and 
    numpy {np.__version__}.
    
    All analysis code and parameters are available in the supplementary materials.
    """
    
    print(methods_text)
    ```

### Version Control

=== "Using Library"
    ```python
    # Track versions of data and analysis
    version_control = data.create_version_tracker()
    
    # Register data version
    version_control.register_data(
        file='umich_2021_phase.parquet',
        checksum=data.calculate_checksum(),
        version='1.0.0'
    )
    
    # Track analysis versions
    version_control.tag_analysis(
        tag='v1.0_initial',
        description='Initial analysis for manuscript submission'
    )
    
    # Create snapshot for reproducibility
    snapshot = version_control.create_snapshot(
        include_data=True,
        include_code=True,
        include_environment=True
    )
    
    # Export for archiving
    snapshot.export('analysis_snapshot_20240101.zip')
    ```

=== "Using Raw Data"
    ```python
    import hashlib
    import pickle
    import subprocess
    
    # Calculate data checksum
    def calculate_checksum(filepath):
        """Calculate MD5 checksum of file."""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    # Create version info
    version_info = {
        'data': {
            'file': 'converted_datasets/umich_2021_phase.parquet',
            'checksum': calculate_checksum('converted_datasets/umich_2021_phase.parquet'),
            'date_accessed': datetime.now().isoformat()
        },
        'code': {
            'git_commit': subprocess.getoutput('git rev-parse HEAD'),
            'git_branch': subprocess.getoutput('git branch --show-current'),
            'modified_files': subprocess.getoutput('git status --short')
        },
        'environment': {
            'python': sys.version,
            'packages': {
                'pandas': pd.__version__,
                'numpy': np.__version__,
                'matplotlib': plt.matplotlib.__version__,
                'scipy': stats.scipy.__version__
            }
        }
    }
    
    # Save version info
    with open('version_info.json', 'w') as f:
        json.dump(version_info, f, indent=2)
    
    # Create requirements file
    requirements = subprocess.getoutput('pip freeze')
    with open('requirements.txt', 'w') as f:
        f.write(requirements)
    
    print(f"Data checksum: {version_info['data']['checksum']}")
    print(f"Git commit: {version_info['code']['git_commit']}")
    ```

## Data Sharing

### Preparing for Repositories

=== "Using Library"
    ```python
    # Prepare data for sharing
    shared_dataset = data.prepare_for_sharing(
        remove_identifiers=True,
        add_metadata=True,
        format='bids'  # Brain Imaging Data Structure adapted for biomechanics
    )
    
    # Add documentation
    shared_dataset.add_readme(
        description='Processed gait analysis data from healthy adults',
        citation='Your et al., 2024',
        license='CC-BY-4.0'
    )
    
    # Create data dictionary
    data_dict = shared_dataset.create_data_dictionary(
        include_units=True,
        include_descriptions=True
    )
    
    # Validate before sharing
    validation = shared_dataset.validate(
        standard='fair',  # FAIR data principles
        checks=['completeness', 'consistency', 'documentation']
    )
    
    if validation['is_valid']:
        # Export for repository
        shared_dataset.export('shared_data/', 
                            format='parquet',
                            compress=True)
        
        # Generate DOI metadata
        shared_dataset.generate_doi_metadata('datacite.xml')
    ```

=== "Using Raw Data"
    ```python
    # Prepare data for sharing
    
    # Remove identifiers
    shared_data = data.copy()
    
    # Anonymize subject IDs
    subject_mapping = {sub: f'P{i:03d}' 
                      for i, sub in enumerate(shared_data['subject'].unique(), 1)}
    shared_data['subject'] = shared_data['subject'].map(subject_mapping)
    
    # Create data dictionary
    data_dictionary = pd.DataFrame({
        'variable': shared_data.columns,
        'description': [
            'Anonymized participant identifier',
            'Walking task performed',
            'Gait cycle number',
            'Normalized phase of gait cycle (0-100%)',
            'Ipsilateral knee flexion angle',
            'Ipsilateral hip flexion angle',
            # ... add all variables
        ][:len(shared_data.columns)],
        'units': [
            'ID',
            'category',
            'count',
            'percentage',
            'radians',
            'radians',
            # ... add all units
        ][:len(shared_data.columns)],
        'type': shared_data.dtypes.astype(str).values
    })
    
    # Create README
    readme_content = """
    # Gait Analysis Dataset
    
    ## Description
    Processed biomechanical data from level ground walking trials.
    
    ## Data Structure
    - Phase-normalized to 150 points per gait cycle
    - Angles in radians, moments in Nm, forces in N
    - See data_dictionary.csv for variable descriptions
    
    ## Citation
    If you use this data, please cite:
    Your et al. (2024). Title. Journal. DOI: xxx
    
    ## License
    This data is shared under CC-BY-4.0 license.
    
    ## Contact
    For questions: your.email@institution.edu
    """
    
    # Save everything
    import os
    os.makedirs('shared_data', exist_ok=True)
    
    shared_data.to_parquet('shared_data/gait_data.parquet', compression='gzip')
    data_dictionary.to_csv('shared_data/data_dictionary.csv', index=False)
    
    with open('shared_data/README.md', 'w') as f:
        f.write(readme_content)
    
    # Save subject mapping (keep secure, not shared)
    with open('subject_mapping_CONFIDENTIAL.json', 'w') as f:
        json.dump(subject_mapping, f, indent=2)
    
    print("Data prepared for sharing in 'shared_data/' directory")
    ```

## Practice Exercises

### Exercise 1: Journal-Specific Formatting
Create a figure that meets the exact specifications for Journal of Biomechanics (column width, font sizes, etc.).

### Exercise 2: Automated Report
Build a function that generates a complete PDF report with figures, tables, and statistics from raw data.

### Exercise 3: Interactive Figures
Create interactive HTML figures using Plotly that readers can explore in supplementary materials.

### Exercise 4: Meta-Analysis Table
Generate a table comparing your results to published normative data from multiple studies.

## Key Takeaways

1. **Consistency is key** - Use the same formatting across all figures and tables
2. **Follow journal guidelines** precisely for acceptance
3. **Ensure reproducibility** through proper documentation and version control
4. **Make data FAIR** - Findable, Accessible, Interoperable, Reusable
5. **Consider accessibility** in color choices and figure design

## Congratulations!

You've completed the Python tutorial series for biomechanical data analysis! You now have the skills to:

- Load and filter large biomechanical datasets efficiently
- Create publication-quality visualizations
- Perform individual and group-level analyses
- Generate reproducible research outputs
- Share your data following best practices

## Additional Resources

- [API Reference](../../api/locomotion-data-api/) - Detailed function documentation
- [Dataset Documentation](../../../reference/datasets_documentation/) - Available datasets
- [Contributing Guide](../../../contributing/) - Add your own datasets
- [GitHub Repository](https://github.com/your-repo) - Source code and examples

Happy analyzing! 🎉