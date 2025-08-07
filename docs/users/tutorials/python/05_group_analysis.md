# Tutorial 5: Group Analysis

## Overview

Learn to aggregate biomechanical data across multiple subjects, compute group statistics, and perform population-level analyses.

## Learning Objectives

- Aggregate data across subjects
- Compute ensemble averages with confidence intervals
- Handle missing data appropriately
- Perform statistical comparisons between groups
- Create normative reference data

## Setup

=== "Using Library"
    ```python
    from user_libs.python.locomotion_data import LocomotionData
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy import stats
    
    # Load data
    data = LocomotionData('converted_datasets/umich_2021_phase.parquet')
    
    # Get all subjects
    all_subjects = data.get_subjects()
    print(f"Total subjects: {len(all_subjects)}")
    ```

=== "Using Raw Data"
    ```python
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy import stats
    
    # Load data
    data = pd.read_parquet('converted_datasets/umich_2021_phase.parquet')
    
    # Get all subjects
    all_subjects = data['subject'].unique()
    print(f"Total subjects: {len(all_subjects)}")
    ```

## Subject Aggregation

### Computing Group Means

=== "Using Library"
    ```python
    # Compute group mean for level walking
    group_mean = data.compute_group_mean(
        task='level_walking',
        variable='knee_flexion_angle_ipsi_rad',
        subjects=None  # Use all available subjects
    )
    
    # Get mean and confidence intervals
    mean_curve = group_mean['mean']
    ci_lower = group_mean['ci_lower']
    ci_upper = group_mean['ci_upper']
    
    # Get subject-specific curves for comparison
    subject_curves = group_mean['subject_curves']
    
    print(f"Included {group_mean['n_subjects']} subjects")
    print(f"Total cycles analyzed: {group_mean['n_cycles_total']}")
    ```

=== "Using Raw Data"
    ```python
    # Filter for level walking
    level_walking = data[data['task'] == 'level_walking']
    
    # Compute mean for each subject first
    subject_means = {}
    for subject in all_subjects:
        subject_data = level_walking[level_walking['subject'] == subject]
        if len(subject_data) > 0:
            subject_mean = subject_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
            subject_means[subject] = subject_mean
    
    # Stack subject means and compute group statistics
    all_subject_curves = pd.DataFrame(subject_means)
    
    # Group mean and confidence intervals
    mean_curve = all_subject_curves.mean(axis=1)
    std_curve = all_subject_curves.std(axis=1)
    n_subjects = all_subject_curves.shape[1]
    
    # 95% confidence interval
    sem = std_curve / np.sqrt(n_subjects)
    ci_lower = mean_curve - 1.96 * sem
    ci_upper = mean_curve + 1.96 * sem
    
    print(f"Included {n_subjects} subjects")
    ```

### Inter-Subject Variability

=== "Using Library"
    ```python
    # Analyze inter-subject variability
    variability = data.analyze_variability(
        task='level_walking',
        variable='knee_flexion_angle_ipsi_rad'
    )
    
    # Get variability metrics
    print(f"Coefficient of variation (mean): {variability['cv_mean']:.2%}")
    print(f"ICC (intraclass correlation): {variability['icc']:.3f}")
    
    # Phase-specific variability
    phase_cv = variability['phase_cv']
    max_var_phase = variability['max_variability_phase']
    print(f"Maximum variability at {max_var_phase}% gait cycle")
    
    # Plot variability across gait cycle
    variability.plot_variability_profile()
    ```

=== "Using Raw Data"
    ```python
    # Calculate coefficient of variation at each phase
    cv_by_phase = []
    
    for phase in range(0, 100):
        phase_data = level_walking[level_walking['phase_percent'] == phase]
        
        # Get values for each subject
        subject_values = []
        for subject in all_subjects:
            subject_phase = phase_data[phase_data['subject'] == subject]
            if len(subject_phase) > 0:
                mean_val = subject_phase['knee_flexion_angle_ipsi_rad'].mean()
                subject_values.append(mean_val)
        
        if len(subject_values) > 1:
            cv = np.std(subject_values) / np.mean(subject_values) * 100
            cv_by_phase.append(cv)
        else:
            cv_by_phase.append(np.nan)
    
    # Find phase with maximum variability
    max_var_phase = np.nanargmax(cv_by_phase)
    
    print(f"Mean CV: {np.nanmean(cv_by_phase):.2f}%")
    print(f"Maximum variability at {max_var_phase}% gait cycle")
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(range(100), cv_by_phase, 'b-', linewidth=2)
    ax.set_xlabel('Gait Cycle (%)')
    ax.set_ylabel('Coefficient of Variation (%)')
    ax.set_title('Inter-Subject Variability Profile')
    ax.grid(True, alpha=0.3)
    plt.show()
    ```

## Ensemble Averaging

### Creating Ensemble Averages

=== "Using Library"
    ```python
    # Create ensemble average with different weighting schemes
    ensemble = data.create_ensemble_average(
        task='level_walking',
        variables=['knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'],
        weighting='cycles',  # 'equal', 'cycles', or 'quality'
        min_cycles_per_subject=5
    )
    
    # Access results
    knee_ensemble = ensemble['knee_flexion_angle_ipsi_rad']
    hip_ensemble = ensemble['hip_flexion_angle_ipsi_rad']
    
    # Get metadata
    print(f"Subjects included: {ensemble['subjects_included']}")
    print(f"Total weight: {ensemble['total_weight']:.1f}")
    print(f"Effective sample size: {ensemble['effective_n']:.1f}")
    ```

=== "Using Raw Data"
    ```python
    # Create weighted ensemble average
    variables = ['knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad']
    ensemble_results = {}
    
    for var in variables:
        # Collect subject data with cycle counts
        subject_data = []
        subject_weights = []
        
        for subject in all_subjects:
            subject_walking = level_walking[level_walking['subject'] == subject]
            if len(subject_walking) > 0:
                n_cycles = len(subject_walking['cycle_id'].unique())
                if n_cycles >= 5:  # Minimum cycles threshold
                    mean_pattern = subject_walking.groupby('phase_percent')[var].mean()
                    subject_data.append(mean_pattern)
                    subject_weights.append(n_cycles)
        
        # Compute weighted average
        if len(subject_data) > 0:
            weights_array = np.array(subject_weights)
            weights_norm = weights_array / weights_array.sum()
            
            # Weighted mean
            weighted_sum = sum(w * curve for w, curve in zip(weights_norm, subject_data))
            ensemble_results[var] = {
                'mean': weighted_sum,
                'n_subjects': len(subject_data),
                'total_cycles': sum(subject_weights)
            }
    
    print(f"Subjects included: {ensemble_results[variables[0]]['n_subjects']}")
    print(f"Total cycles: {ensemble_results[variables[0]]['total_cycles']}")
    ```

### Confidence Bands vs Standard Deviation

=== "Using Library"
    ```python
    # Compare different uncertainty representations
    comparison = data.compare_uncertainty_methods(
        task='level_walking',
        variable='knee_flexion_angle_ipsi_rad'
    )
    
    # Plot comparison
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # Standard deviation
    comparison.plot_with_sd(ax=axes[0])
    axes[0].set_title('Mean ± SD')
    
    # Standard error
    comparison.plot_with_sem(ax=axes[1])
    axes[1].set_title('Mean ± SEM')
    
    # 95% Confidence interval
    comparison.plot_with_ci(ax=axes[2])
    axes[2].set_title('Mean with 95% CI')
    
    plt.tight_layout()
    plt.show()
    ```

=== "Using Raw Data"
    ```python
    # Calculate different uncertainty measures
    subject_means = []
    for subject in all_subjects:
        subject_data = level_walking[level_walking['subject'] == subject]
        if len(subject_data) > 0:
            mean_pattern = subject_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
            subject_means.append(mean_pattern)
    
    # Convert to array
    subject_array = pd.DataFrame(subject_means).T
    
    # Calculate statistics
    mean = subject_array.mean(axis=1)
    std = subject_array.std(axis=1)
    n = subject_array.shape[1]
    sem = std / np.sqrt(n)
    ci_95 = 1.96 * sem
    
    # Plot comparison
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    phase = mean.index
    
    # SD
    axes[0].plot(phase, np.degrees(mean), 'b-', linewidth=2)
    axes[0].fill_between(phase, np.degrees(mean - std), np.degrees(mean + std), 
                         alpha=0.3, color='blue')
    axes[0].set_title('Mean ± SD')
    axes[0].set_ylabel('Knee Flexion (°)')
    
    # SEM
    axes[1].plot(phase, np.degrees(mean), 'b-', linewidth=2)
    axes[1].fill_between(phase, np.degrees(mean - sem), np.degrees(mean + sem),
                         alpha=0.3, color='blue')
    axes[1].set_title('Mean ± SEM')
    
    # 95% CI
    axes[2].plot(phase, np.degrees(mean), 'b-', linewidth=2)
    axes[2].fill_between(phase, np.degrees(mean - ci_95), np.degrees(mean + ci_95),
                         alpha=0.3, color='blue')
    axes[2].set_title('Mean with 95% CI')
    
    for ax in axes:
        ax.set_xlabel('Gait Cycle (%)')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    ```

## Missing Data Handling

### Identifying Missing Data

=== "Using Library"
    ```python
    # Analyze missing data patterns
    missing_analysis = data.analyze_missing_data(
        task='level_walking',
        required_variables=['knee_flexion_angle_ipsi_rad', 
                           'hip_flexion_angle_ipsi_rad',
                           'ankle_flexion_angle_ipsi_rad']
    )
    
    # Get summary
    print(f"Complete subjects: {missing_analysis['n_complete_subjects']}/{missing_analysis['n_total_subjects']}")
    print(f"Missing data pattern:")
    for pattern, count in missing_analysis['patterns'].items():
        print(f"  {pattern}: {count} subjects")
    
    # Visualize missingness
    missing_analysis.plot_missing_pattern()
    ```

=== "Using Raw Data"
    ```python
    # Check for missing data across subjects and variables
    required_vars = ['knee_flexion_angle_ipsi_rad', 
                     'hip_flexion_angle_ipsi_rad',
                     'ankle_flexion_angle_ipsi_rad']
    
    missing_summary = []
    
    for subject in all_subjects:
        subject_data = level_walking[level_walking['subject'] == subject]
        
        subject_missing = {}
        subject_missing['subject'] = subject
        subject_missing['has_data'] = len(subject_data) > 0
        
        if len(subject_data) > 0:
            for var in required_vars:
                subject_missing[var] = not subject_data[var].isna().any()
        else:
            for var in required_vars:
                subject_missing[var] = False
        
        missing_summary.append(subject_missing)
    
    missing_df = pd.DataFrame(missing_summary)
    
    # Summary statistics
    n_complete = (missing_df[required_vars].all(axis=1)).sum()
    print(f"Complete subjects: {n_complete}/{len(all_subjects)}")
    
    # Missing patterns
    for var in required_vars:
        n_missing = (~missing_df[var]).sum()
        print(f"{var}: {n_missing} subjects missing")
    ```

### Handling Strategies

=== "Using Library"
    ```python
    # Apply different missing data strategies
    
    # Strategy 1: Complete case analysis
    complete_case = data.group_analysis(
        task='level_walking',
        missing_strategy='complete_case'
    )
    
    # Strategy 2: Pairwise deletion
    pairwise = data.group_analysis(
        task='level_walking',
        missing_strategy='pairwise'
    )
    
    # Strategy 3: Imputation
    imputed = data.group_analysis(
        task='level_walking',
        missing_strategy='impute',
        imputation_method='group_mean'  # or 'linear', 'spline'
    )
    
    print(f"Complete case N: {complete_case['n_subjects']}")
    print(f"Pairwise N: {pairwise['n_subjects_by_variable']}")
    print(f"Imputed N: {imputed['n_subjects']}")
    ```

=== "Using Raw Data"
    ```python
    # Implement different strategies
    
    # Strategy 1: Complete case analysis
    complete_subjects = []
    for subject in all_subjects:
        subject_data = level_walking[level_walking['subject'] == subject]
        if len(subject_data) > 0:
            has_all = all(not subject_data[var].isna().any() 
                         for var in required_vars)
            if has_all:
                complete_subjects.append(subject)
    
    print(f"Complete case N: {len(complete_subjects)}")
    
    # Strategy 2: Pairwise deletion (handle each variable separately)
    pairwise_n = {}
    for var in required_vars:
        valid_subjects = []
        for subject in all_subjects:
            subject_data = level_walking[level_walking['subject'] == subject]
            if len(subject_data) > 0 and not subject_data[var].isna().any():
                valid_subjects.append(subject)
        pairwise_n[var] = len(valid_subjects)
    
    print(f"Pairwise N by variable: {pairwise_n}")
    
    # Strategy 3: Simple mean imputation
    group_mean_pattern = level_walking.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
    
    # Apply imputation
    imputed_data = level_walking.copy()
    for subject in all_subjects:
        subject_mask = imputed_data['subject'] == subject
        if imputed_data[subject_mask]['knee_flexion_angle_ipsi_rad'].isna().any():
            # Fill with group mean
            for phase in range(100):
                phase_mask = (imputed_data['phase_percent'] == phase) & subject_mask
                imputed_data.loc[phase_mask, 'knee_flexion_angle_ipsi_rad'] = group_mean_pattern.iloc[phase]
    ```

## Statistical Comparisons

### Between-Group Comparisons

=== "Using Library"
    ```python
    # Define groups (e.g., by age, condition, etc.)
    # For this example, split subjects arbitrarily
    group1_subjects = all_subjects[:len(all_subjects)//2]
    group2_subjects = all_subjects[len(all_subjects)//2:]
    
    # Perform statistical comparison
    comparison = data.compare_groups(
        group1_subjects=group1_subjects,
        group2_subjects=group2_subjects,
        task='level_walking',
        variable='knee_flexion_angle_ipsi_rad',
        method='spm'  # Statistical Parametric Mapping
    )
    
    # Get results
    print(f"Significant differences at phases: {comparison['significant_phases']}")
    print(f"Maximum t-statistic: {comparison['max_t']:.2f}")
    print(f"Effect size (Cohen's d): {comparison['effect_size']:.2f}")
    
    # Visualize comparison
    comparison.plot_comparison()
    ```

=== "Using Raw Data"
    ```python
    # Split into two groups
    group1_subjects = all_subjects[:len(all_subjects)//2]
    group2_subjects = all_subjects[len(all_subjects)//2:]
    
    # Get group means
    group1_means = []
    group2_means = []
    
    for subject in group1_subjects:
        subject_data = level_walking[level_walking['subject'] == subject]
        if len(subject_data) > 0:
            mean_pattern = subject_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
            group1_means.append(mean_pattern)
    
    for subject in group2_subjects:
        subject_data = level_walking[level_walking['subject'] == subject]
        if len(subject_data) > 0:
            mean_pattern = subject_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
            group2_means.append(mean_pattern)
    
    # Convert to arrays
    group1_array = pd.DataFrame(group1_means).T
    group2_array = pd.DataFrame(group2_means).T
    
    # Perform t-tests at each phase
    t_stats = []
    p_values = []
    
    for phase in range(100):
        if phase in group1_array.index and phase in group2_array.index:
            g1_values = group1_array.loc[phase].dropna()
            g2_values = group2_array.loc[phase].dropna()
            
            if len(g1_values) > 1 and len(g2_values) > 1:
                t_stat, p_val = stats.ttest_ind(g1_values, g2_values)
                t_stats.append(t_stat)
                p_values.append(p_val)
            else:
                t_stats.append(np.nan)
                p_values.append(np.nan)
    
    # Find significant phases (p < 0.05)
    significant_phases = [i for i, p in enumerate(p_values) if p < 0.05]
    
    print(f"Significant differences at phases: {significant_phases}")
    print(f"Maximum t-statistic: {np.nanmax(np.abs(t_stats)):.2f}")
    
    # Plot comparison
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    # Mean curves
    group1_mean = group1_array.mean(axis=1)
    group2_mean = group2_array.mean(axis=1)
    
    axes[0].plot(group1_mean.index, np.degrees(group1_mean), 'b-', label='Group 1', linewidth=2)
    axes[0].plot(group2_mean.index, np.degrees(group2_mean), 'r-', label='Group 2', linewidth=2)
    axes[0].set_ylabel('Knee Flexion (°)')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Statistical significance
    axes[1].plot(range(100), t_stats, 'k-', linewidth=1)
    axes[1].axhline(y=0, color='gray', linestyle='-', alpha=0.5)
    axes[1].axhline(y=1.96, color='red', linestyle='--', alpha=0.5)
    axes[1].axhline(y=-1.96, color='red', linestyle='--', alpha=0.5)
    axes[1].fill_between(significant_phases, -5, 5, alpha=0.2, color='yellow')
    axes[1].set_xlabel('Gait Cycle (%)')
    axes[1].set_ylabel('t-statistic')
    axes[1].set_ylim([-5, 5])
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    ```

### Effect Size Calculations

=== "Using Library"
    ```python
    # Calculate various effect sizes
    effect_sizes = data.calculate_effect_sizes(
        group1_subjects=group1_subjects,
        group2_subjects=group2_subjects,
        task='level_walking',
        variables=['knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad']
    )
    
    # Display results
    for var, metrics in effect_sizes.items():
        print(f"\n{var}:")
        print(f"  Cohen's d: {metrics['cohens_d']:.2f}")
        print(f"  Hedge's g: {metrics['hedges_g']:.2f}")
        print(f"  Peak phase d: {metrics['peak_phase_d']:.2f}")
        print(f"  AUC difference: {metrics['auc_diff']:.2f}")
    ```

=== "Using Raw Data"
    ```python
    # Calculate Cohen's d at each phase
    def cohens_d(group1, group2):
        n1, n2 = len(group1), len(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
        pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
        return (np.mean(group1) - np.mean(group2)) / pooled_std
    
    # Calculate effect sizes
    effect_sizes = []
    
    for phase in range(100):
        if phase in group1_array.index and phase in group2_array.index:
            g1_values = group1_array.loc[phase].dropna()
            g2_values = group2_array.loc[phase].dropna()
            
            if len(g1_values) > 1 and len(g2_values) > 1:
                d = cohens_d(g1_values, g2_values)
                effect_sizes.append(d)
            else:
                effect_sizes.append(np.nan)
    
    # Summary statistics
    max_effect = np.nanmax(np.abs(effect_sizes))
    mean_effect = np.nanmean(np.abs(effect_sizes))
    
    print(f"Maximum effect size: {max_effect:.2f}")
    print(f"Mean effect size: {mean_effect:.2f}")
    
    # Interpret effect sizes
    large_effects = [i for i, d in enumerate(effect_sizes) if abs(d) > 0.8]
    print(f"Large effects (|d| > 0.8) at phases: {large_effects}")
    ```

## Creating Normative Data

### Building Reference Datasets

=== "Using Library"
    ```python
    # Create normative dataset
    normative = data.create_normative_data(
        task='level_walking',
        variables=['knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'],
        stratify_by=['age_group', 'sex'],  # If available in metadata
        percentiles=[5, 25, 50, 75, 95]
    )
    
    # Access normative curves
    knee_norms = normative['knee_flexion_angle_ipsi_rad']
    
    # Get specific percentiles
    median = knee_norms['p50']
    lower_bound = knee_norms['p5']
    upper_bound = knee_norms['p95']
    
    # Save normative data
    normative.save('normative_data.pkl')
    
    # Generate report
    normative.generate_report('normative_reference.pdf')
    ```

=== "Using Raw Data"
    ```python
    # Create normative reference data
    percentiles = [5, 25, 50, 75, 95]
    
    # Collect all subject curves
    all_curves = []
    for subject in all_subjects:
        subject_data = level_walking[level_walking['subject'] == subject]
        if len(subject_data) > 0:
            mean_pattern = subject_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
            all_curves.append(mean_pattern)
    
    # Convert to DataFrame
    curves_df = pd.DataFrame(all_curves).T
    
    # Calculate percentiles at each phase
    normative_data = {}
    for p in percentiles:
        normative_data[f'p{p}'] = curves_df.quantile(p/100, axis=1)
    
    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))
    phase = normative_data['p50'].index
    
    # Plot percentile bands
    ax.fill_between(phase, np.degrees(normative_data['p5']), 
                    np.degrees(normative_data['p95']),
                    alpha=0.2, color='blue', label='5th-95th percentile')
    ax.fill_between(phase, np.degrees(normative_data['p25']), 
                    np.degrees(normative_data['p75']),
                    alpha=0.3, color='blue', label='25th-75th percentile')
    ax.plot(phase, np.degrees(normative_data['p50']), 
           'b-', linewidth=2, label='Median')
    
    ax.set_xlabel('Gait Cycle (%)')
    ax.set_ylabel('Knee Flexion (°)')
    ax.set_title('Normative Reference Data')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.show()
    
    # Save normative data
    normative_df = pd.DataFrame(normative_data)
    normative_df.to_csv('normative_knee_flexion.csv')
    ```

### Z-Score Calculations

=== "Using Library"
    ```python
    # Compare individual to normative data
    test_subject = 'SUB01'
    
    z_scores = data.calculate_z_scores(
        subject=test_subject,
        task='level_walking',
        normative_data=normative,
        variables=['knee_flexion_angle_ipsi_rad']
    )
    
    # Identify abnormal phases
    abnormal = z_scores.identify_abnormal_phases(threshold=2.0)
    
    print(f"Subject {test_subject} deviations:")
    print(f"  Phases > 2 SD: {abnormal['high_phases']}")
    print(f"  Phases < -2 SD: {abnormal['low_phases']}")
    print(f"  Maximum |z-score|: {z_scores['max_abs_z']:.2f}")
    
    # Visualize
    z_scores.plot_with_normative()
    ```

=== "Using Raw Data"
    ```python
    # Calculate z-scores for a test subject
    test_subject = 'SUB01'
    test_data = level_walking[level_walking['subject'] == test_subject]
    
    if len(test_data) > 0:
        test_mean = test_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
        
        # Calculate population mean and std
        pop_mean = curves_df.mean(axis=1)
        pop_std = curves_df.std(axis=1)
        
        # Calculate z-scores
        z_scores = (test_mean - pop_mean) / pop_std
        
        # Identify abnormal phases
        abnormal_high = [i for i, z in enumerate(z_scores) if z > 2]
        abnormal_low = [i for i, z in enumerate(z_scores) if z < -2]
        
        print(f"Subject {test_subject} deviations:")
        print(f"  Phases > 2 SD: {abnormal_high}")
        print(f"  Phases < -2 SD: {abnormal_low}")
        print(f"  Maximum |z-score|: {np.max(np.abs(z_scores)):.2f}")
        
        # Plot
        fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        
        # Top: Subject vs normative
        axes[0].fill_between(phase, np.degrees(normative_data['p5']), 
                            np.degrees(normative_data['p95']),
                            alpha=0.2, color='gray', label='Normative range')
        axes[0].plot(phase, np.degrees(test_mean), 'r-', linewidth=2, 
                    label=f'Subject {test_subject}')
        axes[0].set_ylabel('Knee Flexion (°)')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Bottom: Z-scores
        axes[1].plot(phase, z_scores, 'b-', linewidth=2)
        axes[1].axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        axes[1].axhline(y=2, color='red', linestyle='--', alpha=0.5)
        axes[1].axhline(y=-2, color='red', linestyle='--', alpha=0.5)
        axes[1].fill_between(phase, -2, 2, alpha=0.1, color='green')
        axes[1].set_xlabel('Gait Cycle (%)')
        axes[1].set_ylabel('Z-score')
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    ```

## Practice Exercises

### Exercise 1: Subgroup Analysis
Divide subjects by walking speed (if available) and compare fast vs slow walkers. Do patterns differ significantly?

### Exercise 2: Bootstrap Confidence Intervals
Implement bootstrap resampling to create more robust confidence intervals for group means.

### Exercise 3: Mixed Effects Modeling
If multiple conditions are available, use mixed-effects models to account for within-subject correlations.

### Exercise 4: Outlier Impact
Analyze how removing outlier subjects affects group means and variability. What's the sensitivity of your results?

## Key Takeaways

1. **Group analysis** requires careful consideration of sample size and variability
2. **Multiple aggregation methods** exist - choose based on your research question
3. **Missing data** handling can significantly impact results
4. **Statistical comparisons** should account for multiple testing across the gait cycle
5. **Normative data** provides context for individual assessments

## Next Steps

[Continue to Tutorial 6: Publication Outputs →](06_publication_outputs.md)

Learn to create publication-ready figures, tables, and reproducible analysis reports.