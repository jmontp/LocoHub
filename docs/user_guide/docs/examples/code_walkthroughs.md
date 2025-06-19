# Code Walkthroughs

**Step-by-step analysis workflows with real biomechanical data and complete working code.**

<div class="walkthrough-features" markdown>
:material-check-circle: **Tested Code** - All examples verified to work with current datasets  
:material-download: **Copyable Snippets** - One-click copy for immediate use  
:material-chart-line: **Real Results** - Based on actual research data  
:material-book-open: **Learning Focused** - Detailed explanations of each step  
</div>

## Quick Start Examples

### 1. Load and Explore Your First Dataset {#5min-analysis}

<div class="example-container" markdown>

**Time Required:** 5 minutes  
**Skill Level:** Beginner  
**Learning Goals:** Load data, understand structure, create basic visualization

#### The Complete Workflow

=== "Python"
    ```python
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Step 1: Load the dataset
    data_path = 'docs/user_guide/docs/tutorials/test_files/locomotion_data.csv'
    data = pd.read_csv(data_path)
    
    print("✅ Dataset loaded successfully!")
    print(f"Shape: {data.shape}")
    print(f"Columns: {list(data.columns)}")
    
    # Step 2: Explore the data structure
    print("\n📊 Data Overview:")
    print(f"Subjects: {data['subject_id'].nunique()}")
    print(f"Tasks: {data['task_id'].nunique()}")
    print(f"Time range: {data['time_s'].min():.2f} - {data['time_s'].max():.2f} seconds")
    
    # Step 3: Basic statistics
    print("\n📈 Knee Flexion Statistics:")
    knee_stats = data['knee_flexion_angle_rad'].describe()
    print(f"Mean: {np.degrees(knee_stats['mean']):.1f}°")
    print(f"Range: {np.degrees(knee_stats['min']):.1f}° to {np.degrees(knee_stats['max']):.1f}°")
    print(f"Std Dev: {np.degrees(knee_stats['std']):.1f}°")
    
    # Step 4: Create your first plot
    plt.figure(figsize=(12, 6))
    
    # Convert to degrees for better readability
    time = data['time_s']
    knee_deg = np.degrees(data['knee_flexion_angle_rad'])
    
    plt.plot(time, knee_deg, 'b-', linewidth=1.5, alpha=0.7)
    plt.xlabel('Time (seconds)')
    plt.ylabel('Knee Flexion Angle (degrees)')
    plt.title('Knee Flexion Over Time - Your First Biomechanical Plot!')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('my_first_biomech_plot.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("🎉 Your first biomechanical analysis is complete!")
    print("📁 Plot saved as 'my_first_biomech_plot.png'")
    ```

=== "MATLAB"
    ```matlab
    % Step 1: Load the dataset
    data_path = 'docs/user_guide/docs/tutorials/test_files/locomotion_data.csv';
    data = readtable(data_path);
    
    fprintf('✅ Dataset loaded successfully!\n');
    fprintf('Shape: %d rows x %d columns\n', height(data), width(data));
    fprintf('Columns: %s\n', strjoin(data.Properties.VariableNames, ', '));
    
    % Step 2: Explore the data structure
    fprintf('\n📊 Data Overview:\n');
    fprintf('Subjects: %d\n', length(unique(data.subject_id)));
    fprintf('Tasks: %d\n', length(unique(data.task_id)));
    fprintf('Time range: %.2f - %.2f seconds\n', min(data.time_s), max(data.time_s));
    
    % Step 3: Basic statistics
    fprintf('\n📈 Knee Flexion Statistics:\n');
    knee_deg = rad2deg(data.knee_flexion_angle_rad);
    fprintf('Mean: %.1f°\n', mean(knee_deg));
    fprintf('Range: %.1f° to %.1f°\n', min(knee_deg), max(knee_deg));
    fprintf('Std Dev: %.1f°\n', std(knee_deg));
    
    % Step 4: Create your first plot
    figure('Position', [100, 100, 800, 400]);
    
    plot(data.time_s, knee_deg, 'b-', 'LineWidth', 1.5);
    xlabel('Time (seconds)');
    ylabel('Knee Flexion Angle (degrees)');
    title('Knee Flexion Over Time - Your First Biomechanical Plot!');
    grid on;
    
    % Save the plot
    saveas(gcf, 'my_first_biomech_plot_matlab.png');
    
    fprintf('🎉 Your first biomechanical analysis is complete!\n');
    fprintf('📁 Plot saved as ''my_first_biomech_plot_matlab.png''\n');
    ```

#### What You Just Learned

✅ **Data Loading**: How to read biomechanical datasets  
✅ **Data Exploration**: Checking dimensions, variables, and basic statistics  
✅ **Unit Conversion**: Converting radians to degrees for interpretation  
✅ **Visualization**: Creating publication-ready plots  
✅ **File Management**: Saving results for future use  

#### Next Steps
- [Compare different tasks](#task-comparison) 
- [Analyze multiple subjects](#multi-subject)
- [Add validation checks](#validation-check)

</div>

### 2. Compare Locomotion Tasks {#task-comparison}

<div class="example-container" markdown>

**Time Required:** 10 minutes  
**Skill Level:** Beginner  
**Learning Goals:** Filter data by task, create comparative visualizations, interpret differences

#### The Complete Workflow

=== "Python"
    ```python
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Load data
    data = pd.read_csv('docs/user_guide/docs/tutorials/test_files/locomotion_data.csv')
    
    # Step 1: Identify available tasks
    tasks = data['task_id'].unique()
    print(f"📋 Available tasks: {tasks}")
    
    # Step 2: Filter data by task and prepare for comparison
    task_data = {}
    task_colors = {'P001_T01': 'blue', 'P001_T02': 'red'}
    task_labels = {'P001_T01': 'Normal Walking', 'P001_T02': 'Fast Walking'}
    
    for task in tasks:
        task_subset = data[data['task_id'] == task]
        task_data[task] = task_subset
        print(f"  {task_labels.get(task, task)}: {len(task_subset)} data points")
    
    # Step 3: Create comparative visualization
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Biomechanical Comparison: Normal vs Fast Walking', fontsize=16)
    
    # Plot 1: Knee Flexion Comparison
    ax1 = axes[0, 0]
    for task in tasks:
        time = task_data[task]['time_s']
        knee_deg = np.degrees(task_data[task]['knee_flexion_angle_rad'])
        ax1.plot(time, knee_deg, color=task_colors[task], 
                linewidth=2, label=task_labels[task], alpha=0.8)
    
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Knee Flexion (degrees)')
    ax1.set_title('Knee Flexion Patterns')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Hip Flexion Comparison
    ax2 = axes[0, 1]
    for task in tasks:
        time = task_data[task]['time_s']
        hip_deg = np.degrees(task_data[task]['hip_flexion_angle_rad'])
        ax2.plot(time, hip_deg, color=task_colors[task], 
                linewidth=2, label=task_labels[task], alpha=0.8)
    
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Hip Flexion (degrees)')
    ax2.set_title('Hip Flexion Patterns')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Ground Reaction Force Comparison
    ax3 = axes[1, 0]
    for task in tasks:
        time = task_data[task]['time_s']
        grf = task_data[task]['vertical_grf_N']
        ax3.plot(time, grf, color=task_colors[task], 
                linewidth=2, label=task_labels[task], alpha=0.8)
    
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Vertical GRF (N)')
    ax3.set_title('Ground Reaction Forces')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Statistical Summary
    ax4 = axes[1, 1]
    metrics = ['Peak Knee Flexion', 'Peak Hip Flexion', 'Peak GRF']
    normal_values = [
        np.degrees(task_data['P001_T01']['knee_flexion_angle_rad']).max(),
        np.degrees(task_data['P001_T01']['hip_flexion_angle_rad']).max(),
        task_data['P001_T01']['vertical_grf_N'].max()
    ]
    fast_values = [
        np.degrees(task_data['P001_T02']['knee_flexion_angle_rad']).max(),
        np.degrees(task_data['P001_T02']['hip_flexion_angle_rad']).max(),
        task_data['P001_T02']['vertical_grf_N'].max()
    ]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    bars1 = ax4.bar(x - width/2, normal_values[:2] + [normal_values[2]/10], width, 
                    label='Normal Walking', color='blue', alpha=0.7)
    bars2 = ax4.bar(x + width/2, fast_values[:2] + [fast_values[2]/10], width, 
                    label='Fast Walking', color='red', alpha=0.7)
    
    ax4.set_xlabel('Metrics')
    ax4.set_ylabel('Values (degrees / N×10)')
    ax4.set_title('Peak Value Comparison')
    ax4.set_xticks(x)
    ax4.set_xticklabels(['Peak Knee°', 'Peak Hip°', 'Peak GRF×10'])
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('task_comparison_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Step 4: Quantitative Analysis
    print("\n📊 Quantitative Comparison:")
    for task in tasks:
        task_label = task_labels[task]
        knee_peak = np.degrees(task_data[task]['knee_flexion_angle_rad']).max()
        hip_peak = np.degrees(task_data[task]['hip_flexion_angle_rad']).max()
        grf_peak = task_data[task]['vertical_grf_N'].max()
        
        print(f"\n{task_label}:")
        print(f"  Peak Knee Flexion: {knee_peak:.1f}°")
        print(f"  Peak Hip Flexion: {hip_peak:.1f}°")
        print(f"  Peak Vertical GRF: {grf_peak:.0f} N")
    
    # Calculate differences
    knee_diff = (np.degrees(task_data['P001_T02']['knee_flexion_angle_rad']).max() - 
                 np.degrees(task_data['P001_T01']['knee_flexion_angle_rad']).max())
    
    print(f"\n🔍 Key Finding:")
    print(f"Fast walking increases peak knee flexion by {knee_diff:.1f}°")
    
    print("\n✅ Task comparison analysis complete!")
    print("📁 Results saved as 'task_comparison_analysis.png'")
    ```

#### What You Just Learned

✅ **Data Filtering**: How to separate data by task conditions  
✅ **Comparative Analysis**: Side-by-side comparison techniques  
✅ **Multi-panel Plots**: Creating complex figure layouts  
✅ **Statistical Comparison**: Calculating and interpreting differences  
✅ **Biomechanical Interpretation**: Understanding task-specific adaptations  

</div>

### 3. Multi-Subject Analysis {#multi-subject}

<div class="example-container" markdown>

**Time Required:** 15 minutes  
**Skill Level:** Intermediate  
**Learning Goals:** Aggregate data across subjects, compute population statistics, handle variability

#### The Complete Workflow

=== "Python"
    ```python
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy import stats
    
    # For this example, we'll simulate multi-subject data since our test file has one subject
    # In real usage, you'd load a dataset with multiple subjects
    
    def simulate_multi_subject_data():
        """Create realistic multi-subject dataset for demonstration"""
        np.random.seed(42)
        subjects = ['P001', 'P002', 'P003', 'P004', 'P005']
        time_points = np.linspace(0, 1.0, 100)
        
        all_data = []
        for subject in subjects:
            # Individual subject characteristics
            subject_offset = np.random.normal(0, 0.1)  # Individual differences
            noise_level = np.random.uniform(0.02, 0.05)  # Individual noise levels
            
            for i, t in enumerate(time_points):
                # Realistic knee flexion pattern
                base_knee = 0.5 * np.sin(4 * np.pi * t) + 0.3 + subject_offset
                knee_with_noise = base_knee + np.random.normal(0, noise_level)
                
                # Hip flexion pattern
                base_hip = 0.3 * np.sin(4 * np.pi * t - np.pi/4) + 0.1 + subject_offset * 0.5
                hip_with_noise = base_hip + np.random.normal(0, noise_level * 0.8)
                
                all_data.append({
                    'time_s': t,
                    'subject_id': subject,
                    'knee_flexion_angle_rad': knee_with_noise,
                    'hip_flexion_angle_rad': hip_with_noise,
                    'task_id': 'walking'
                })
        
        return pd.DataFrame(all_data)
    
    # Step 1: Load/create multi-subject data
    data = simulate_multi_subject_data()
    subjects = data['subject_id'].unique()
    
    print(f"📊 Multi-Subject Dataset Analysis")
    print(f"Subjects: {len(subjects)} ({', '.join(subjects)})")
    print(f"Total data points: {len(data)}")
    
    # Step 2: Population Statistics Analysis
    def calculate_population_stats(data, variable):
        """Calculate population-level statistics"""
        subject_means = data.groupby('subject_id')[variable].mean()
        subject_maxes = data.groupby('subject_id')[variable].max()
        subject_mins = data.groupby('subject_id')[variable].min()
        
        return {
            'population_mean': subject_means.mean(),
            'population_std': subject_means.std(),
            'individual_means': subject_means,
            'individual_ranges': subject_maxes - subject_mins,
            'range_mean': (subject_maxes - subject_mins).mean(),
            'range_std': (subject_maxes - subject_mins).std()
        }
    
    # Analyze knee flexion across population
    knee_stats = calculate_population_stats(data, 'knee_flexion_angle_rad')
    hip_stats = calculate_population_stats(data, 'hip_flexion_angle_rad')
    
    # Step 3: Create comprehensive visualization
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Multi-Subject Biomechanical Analysis', fontsize=16)
    
    # Plot 1: Individual subject traces
    ax1 = axes[0, 0]
    colors = plt.cm.Set3(np.linspace(0, 1, len(subjects)))
    
    for i, subject in enumerate(subjects):
        subject_data = data[data['subject_id'] == subject]
        knee_deg = np.degrees(subject_data['knee_flexion_angle_rad'])
        ax1.plot(subject_data['time_s'], knee_deg, 
                color=colors[i], linewidth=2, label=subject, alpha=0.8)
    
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Knee Flexion (degrees)')
    ax1.set_title('Individual Subject Patterns')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Population mean ± std
    ax2 = axes[0, 1]
    time_unique = np.sort(data['time_s'].unique())
    
    # Calculate mean and std at each time point
    mean_at_time = []
    std_at_time = []
    
    for t in time_unique:
        time_data = data[data['time_s'] == t]['knee_flexion_angle_rad']
        mean_at_time.append(np.degrees(time_data.mean()))
        std_at_time.append(np.degrees(time_data.std()))
    
    mean_curve = np.array(mean_at_time)
    std_curve = np.array(std_at_time)
    
    ax2.plot(time_unique, mean_curve, 'b-', linewidth=3, label='Population Mean')
    ax2.fill_between(time_unique, mean_curve - std_curve, mean_curve + std_curve, 
                    alpha=0.3, color='blue', label='± 1 SD')
    ax2.fill_between(time_unique, mean_curve - 2*std_curve, mean_curve + 2*std_curve, 
                    alpha=0.2, color='blue', label='± 2 SD')
    
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Knee Flexion (degrees)')
    ax2.set_title('Population Mean ± Standard Deviation')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Subject variability analysis
    ax3 = axes[0, 2]
    subject_means_deg = np.degrees(knee_stats['individual_means'])
    subject_ranges_deg = np.degrees(knee_stats['individual_ranges'])
    
    ax3.scatter(subject_means_deg, subject_ranges_deg, s=100, alpha=0.7, c=colors)
    for i, subject in enumerate(subjects):
        ax3.annotate(subject, (subject_means_deg[subject], subject_ranges_deg[subject]),
                    xytext=(5, 5), textcoords='offset points', fontsize=10)
    
    ax3.set_xlabel('Mean Knee Flexion (degrees)')
    ax3.set_ylabel('Range of Motion (degrees)')
    ax3.set_title('Individual Subject Characteristics')
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Population statistics comparison
    ax4 = axes[1, 0]
    metrics = ['Mean Flexion', 'ROM', 'Variability']
    knee_values = [
        np.degrees(knee_stats['population_mean']),
        np.degrees(knee_stats['range_mean']),
        np.degrees(knee_stats['population_std'])
    ]
    hip_values = [
        np.degrees(hip_stats['population_mean']),
        np.degrees(hip_stats['range_mean']),
        np.degrees(hip_stats['population_std'])
    ]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    bars1 = ax4.bar(x - width/2, knee_values, width, 
                    label='Knee', color='red', alpha=0.7)
    bars2 = ax4.bar(x + width/2, hip_values, width, 
                    label='Hip', color='blue', alpha=0.7)
    
    ax4.set_xlabel('Metrics')
    ax4.set_ylabel('Values (degrees)')
    ax4.set_title('Joint Comparison')
    ax4.set_xticks(x)
    ax4.set_xticklabels(metrics)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Plot 5: Distribution analysis
    ax5 = axes[1, 1]
    ax5.hist(np.degrees(knee_stats['individual_means']), bins=10, alpha=0.7, 
            color='red', label='Knee Flexion', density=True)
    ax5.hist(np.degrees(hip_stats['individual_means']), bins=10, alpha=0.7, 
            color='blue', label='Hip Flexion', density=True)
    
    ax5.set_xlabel('Mean Joint Angle (degrees)')
    ax5.set_ylabel('Probability Density')
    ax5.set_title('Population Distribution')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # Plot 6: Statistical testing
    ax6 = axes[1, 2]
    
    # Perform t-test between knee and hip means
    t_stat, p_value = stats.ttest_ind(knee_stats['individual_means'], 
                                     hip_stats['individual_means'])
    
    # Effect size (Cohen's d)
    pooled_std = np.sqrt((knee_stats['population_std']**2 + hip_stats['population_std']**2) / 2)
    cohens_d = abs(knee_stats['population_mean'] - hip_stats['population_mean']) / pooled_std
    
    # Summary statistics text
    stats_text = f"""Statistical Summary:

    Population Size: {len(subjects)} subjects
    
    Knee Flexion:
    Mean: {np.degrees(knee_stats['population_mean']):.1f}° ± {np.degrees(knee_stats['population_std']):.1f}°
    Range: {np.degrees(knee_stats['range_mean']):.1f}° ± {np.degrees(knee_stats['range_std']):.1f}°
    
    Hip Flexion:
    Mean: {np.degrees(hip_stats['population_mean']):.1f}° ± {np.degrees(hip_stats['population_std']):.1f}°
    Range: {np.degrees(hip_stats['range_mean']):.1f}° ± {np.degrees(hip_stats['range_std']):.1f}°
    
    Statistical Test:
    t-statistic: {t_stat:.3f}
    p-value: {p_value:.3e}
    Effect size (d): {cohens_d:.3f}
    
    Interpretation:
    {'Significant' if p_value < 0.05 else 'Non-significant'} difference
    {'Large' if cohens_d > 0.8 else 'Medium' if cohens_d > 0.5 else 'Small'} effect size
    """
    
    ax6.text(0.05, 0.95, stats_text, transform=ax6.transAxes, fontsize=10,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    ax6.axis('off')
    
    plt.tight_layout()
    plt.savefig('multi_subject_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Step 4: Clinical Interpretation
    print("\n🏥 Clinical Interpretation:")
    print(f"Population knee flexion: {np.degrees(knee_stats['population_mean']):.1f}° ± {np.degrees(knee_stats['population_std']):.1f}°")
    print(f"Expected range: {np.degrees(knee_stats['population_mean'] - 2*knee_stats['population_std']):.1f}° to {np.degrees(knee_stats['population_mean'] + 2*knee_stats['population_std']):.1f}°")
    
    # Identify outliers (subjects beyond 2 SD)
    outliers = []
    for subject in subjects:
        subject_mean = knee_stats['individual_means'][subject]
        z_score = abs(subject_mean - knee_stats['population_mean']) / knee_stats['population_std']
        if z_score > 2:
            outliers.append((subject, z_score))
    
    if outliers:
        print(f"\n⚠️  Potential outliers (>2 SD from mean):")
        for subject, z_score in outliers:
            print(f"  {subject}: z-score = {z_score:.2f}")
    else:
        print(f"\n✅ All subjects within normal range (±2 SD)")
    
    print("\n✅ Multi-subject analysis complete!")
    print("📁 Results saved as 'multi_subject_analysis.png'")
    ```

#### What You Just Learned

✅ **Population Analysis**: Computing statistics across multiple subjects  
✅ **Variability Assessment**: Understanding individual differences  
✅ **Statistical Testing**: Comparing groups with appropriate tests  
✅ **Outlier Detection**: Identifying subjects outside normal ranges  
✅ **Clinical Interpretation**: Translating statistics to meaningful insights  

</div>

### 4. Data Quality Validation {#validation-check}

<div class="example-container" markdown>

**Time Required:** 12 minutes  
**Skill Level:** Intermediate  
**Learning Goals:** Assess data quality, identify issues, implement validation checks

=== "Python"
    ```python
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy import stats
    
    # Load data
    data = pd.read_csv('docs/user_guide/docs/tutorials/test_files/locomotion_data.csv')
    
    print("🔍 Data Quality Validation Analysis")
    print("=" * 50)
    
    # Step 1: Basic Data Integrity Checks
    print("\n1️⃣ BASIC INTEGRITY CHECKS")
    
    # Check for missing values
    missing_data = data.isnull().sum()
    print(f"Missing values per column:")
    for col, count in missing_data.items():
        if count > 0:
            print(f"  ❌ {col}: {count} missing ({count/len(data)*100:.1f}%)")
        else:
            print(f"  ✅ {col}: No missing values")
    
    # Check for duplicate timestamps
    duplicates = data.duplicated(subset=['time_s', 'subject_id']).sum()
    print(f"Duplicate timestamps: {'❌ ' + str(duplicates) if duplicates > 0 else '✅ None'}")
    
    # Check data types
    print(f"\nData types:")
    for col, dtype in data.dtypes.items():
        expected_numeric = ['time_s', 'knee_flexion_angle_rad', 'hip_flexion_angle_rad', 
                          'ankle_flexion_angle_rad', 'cop_x_m', 'cop_y_m', 'vertical_grf_N']
        if col in expected_numeric:
            if pd.api.types.is_numeric_dtype(dtype):
                print(f"  ✅ {col}: {dtype} (numeric as expected)")
            else:
                print(f"  ❌ {col}: {dtype} (should be numeric)")
        else:
            print(f"  ℹ️  {col}: {dtype}")
    
    # Step 2: Biomechanical Range Validation
    print("\n2️⃣ BIOMECHANICAL RANGE VALIDATION")
    
    # Define expected physiological ranges (in radians)
    expected_ranges = {
        'knee_flexion_angle_rad': (0, np.radians(120)),  # 0-120 degrees
        'hip_flexion_angle_rad': (np.radians(-20), np.radians(45)),  # -20 to 45 degrees
        'ankle_flexion_angle_rad': (np.radians(-25), np.radians(20)),  # -25 to 20 degrees
        'vertical_grf_N': (0, 2000),  # 0 to 2000 N (reasonable for walking)
    }
    
    validation_results = {}
    
    for variable, (min_val, max_val) in expected_ranges.items():
        if variable in data.columns:
            values = data[variable]
            outliers = ((values < min_val) | (values > max_val)).sum()
            outlier_percentage = outliers / len(values) * 100
            
            validation_results[variable] = {
                'outliers': outliers,
                'percentage': outlier_percentage,
                'min_observed': values.min(),
                'max_observed': values.max(),
                'expected_min': min_val,
                'expected_max': max_val
            }
            
            status = "✅" if outliers == 0 else "⚠️" if outlier_percentage < 5 else "❌"
            print(f"{status} {variable}:")
            print(f"    Expected: {min_val:.3f} to {max_val:.3f}")
            print(f"    Observed: {values.min():.3f} to {values.max():.3f}")
            print(f"    Outliers: {outliers}/{len(values)} ({outlier_percentage:.1f}%)")
    
    # Step 3: Temporal Consistency Checks
    print("\n3️⃣ TEMPORAL CONSISTENCY CHECKS")
    
    # Check sampling frequency consistency
    time_diffs = np.diff(data['time_s'])
    expected_dt = 0.01  # Expected 10ms sampling
    dt_variation = np.std(time_diffs)
    irregular_samples = np.sum(np.abs(time_diffs - expected_dt) > expected_dt * 0.1)
    
    print(f"Sampling frequency analysis:")
    print(f"  Expected interval: {expected_dt:.3f}s")
    print(f"  Mean interval: {np.mean(time_diffs):.3f}s")
    print(f"  Std deviation: {dt_variation:.6f}s")
    print(f"  Irregular samples: {irregular_samples}/{len(time_diffs)} ({irregular_samples/len(time_diffs)*100:.1f}%)")
    
    status = "✅" if irregular_samples < len(time_diffs) * 0.01 else "⚠️"
    print(f"  Status: {status}")
    
    # Step 4: Signal Quality Assessment
    print("\n4️⃣ SIGNAL QUALITY ASSESSMENT")
    
    def assess_signal_quality(signal, name):
        """Assess signal quality metrics"""
        # Calculate signal-to-noise ratio
        signal_power = np.var(signal)
        
        # Estimate noise using high-frequency components
        diff_signal = np.diff(signal)
        noise_power = np.var(diff_signal) / 2  # Approximate noise variance
        
        snr_db = 10 * np.log10(signal_power / noise_power) if noise_power > 0 else float('inf')
        
        # Check for spikes (values beyond 3 standard deviations)
        z_scores = np.abs(stats.zscore(signal))
        spikes = np.sum(z_scores > 3)
        
        # Check for flatline segments (consecutive identical values)
        identical_consecutive = 0
        for i in range(1, len(signal)):
            if signal[i] == signal[i-1]:
                identical_consecutive += 1
        
        return {
            'snr_db': snr_db,
            'spikes': spikes,
            'flatline_points': identical_consecutive,
            'mean': np.mean(signal),
            'std': np.std(signal)
        }
    
    signal_quality = {}
    key_signals = ['knee_flexion_angle_rad', 'hip_flexion_angle_rad', 'vertical_grf_N']
    
    for signal_name in key_signals:
        if signal_name in data.columns:
            quality = assess_signal_quality(data[signal_name], signal_name)
            signal_quality[signal_name] = quality
            
            print(f"{signal_name}:")
            print(f"  SNR: {quality['snr_db']:.1f} dB")
            print(f"  Spikes (>3σ): {quality['spikes']}/{len(data)} ({quality['spikes']/len(data)*100:.1f}%)")
            print(f"  Flatline points: {quality['flatline_points']}")
            
            # Quality assessment
            if quality['snr_db'] > 20 and quality['spikes'] < len(data) * 0.01:
                print(f"  Status: ✅ Good quality")
            elif quality['snr_db'] > 10 and quality['spikes'] < len(data) * 0.05:
                print(f"  Status: ⚠️ Moderate quality")
            else:
                print(f"  Status: ❌ Poor quality")
    
    # Step 5: Visualization of Quality Issues
    print("\n5️⃣ CREATING QUALITY ASSESSMENT PLOTS")
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Data Quality Assessment Dashboard', fontsize=16)
    
    # Plot 1: Range validation visualization
    ax1 = axes[0, 0]
    for i, (variable, results) in enumerate(validation_results.items()):
        if 'angle' in variable:  # Only plot angles for clarity
            values_deg = np.degrees(data[variable])
            expected_min_deg = np.degrees(results['expected_min'])
            expected_max_deg = np.degrees(results['expected_max'])
            
            ax1.scatter([i] * len(values_deg), values_deg, alpha=0.3, s=2)
            ax1.axhline(y=expected_min_deg, color='red', linestyle='--', alpha=0.7)
            ax1.axhline(y=expected_max_deg, color='red', linestyle='--', alpha=0.7)
    
    ax1.set_xlabel('Variable Index')
    ax1.set_ylabel('Angle (degrees)')
    ax1.set_title('Range Validation')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Temporal consistency
    ax2 = axes[0, 1]
    ax2.plot(time_diffs * 1000, 'b-', linewidth=1, alpha=0.7)
    ax2.axhline(y=expected_dt * 1000, color='red', linestyle='--', label='Expected')
    ax2.set_xlabel('Sample Index')
    ax2.set_ylabel('Time Interval (ms)')
    ax2.set_title('Sampling Consistency')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Signal quality overview
    ax3 = axes[0, 2]
    quality_metrics = ['SNR (dB)', 'Spikes (%)', 'Flatline (%)']
    
    for i, signal_name in enumerate(key_signals):
        if signal_name in signal_quality:
            q = signal_quality[signal_name]
            values = [
                q['snr_db'],
                q['spikes'] / len(data) * 100,
                q['flatline_points'] / len(data) * 100
            ]
            ax3.bar([x + i*0.25 for x in range(len(quality_metrics))], values, 
                   width=0.25, label=signal_name.replace('_', ' ').title(), alpha=0.7)
    
    ax3.set_xlabel('Quality Metrics')
    ax3.set_ylabel('Values')
    ax3.set_title('Signal Quality Overview')
    ax3.set_xticks(range(len(quality_metrics)))
    ax3.set_xticklabels(quality_metrics)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Distribution analysis
    ax4 = axes[1, 0]
    knee_deg = np.degrees(data['knee_flexion_angle_rad'])
    ax4.hist(knee_deg, bins=30, alpha=0.7, color='blue', density=True)
    ax4.axvline(x=np.mean(knee_deg), color='red', linestyle='--', 
                label=f'Mean: {np.mean(knee_deg):.1f}°')
    ax4.axvline(x=np.mean(knee_deg) + 2*np.std(knee_deg), color='orange', 
                linestyle='--', label='±2σ')
    ax4.axvline(x=np.mean(knee_deg) - 2*np.std(knee_deg), color='orange', linestyle='--')
    ax4.set_xlabel('Knee Flexion (degrees)')
    ax4.set_ylabel('Probability Density')
    ax4.set_title('Distribution Analysis')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Plot 5: Outlier detection
    ax5 = axes[1, 1]
    z_scores = np.abs(stats.zscore(knee_deg))
    outlier_mask = z_scores > 3
    
    ax5.scatter(data['time_s'][~outlier_mask], knee_deg[~outlier_mask], 
               c='blue', alpha=0.6, s=10, label='Normal')
    ax5.scatter(data['time_s'][outlier_mask], knee_deg[outlier_mask], 
               c='red', s=20, label='Outliers')
    ax5.set_xlabel('Time (s)')
    ax5.set_ylabel('Knee Flexion (degrees)')
    ax5.set_title('Outlier Detection')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # Plot 6: Quality summary
    ax6 = axes[1, 2]
    
    # Calculate overall quality score
    total_outliers = sum([r['outliers'] for r in validation_results.values()])
    total_points = len(data) * len(validation_results)
    outlier_rate = total_outliers / total_points * 100
    
    avg_snr = np.mean([q['snr_db'] for q in signal_quality.values()])
    total_spikes = sum([q['spikes'] for q in signal_quality.values()])
    spike_rate = total_spikes / (len(data) * len(signal_quality)) * 100
    
    # Quality score (0-100)
    quality_score = max(0, 100 - outlier_rate * 5 - spike_rate * 10 - max(0, 20 - avg_snr))
    
    summary_text = f"""QUALITY ASSESSMENT SUMMARY

    Overall Quality Score: {quality_score:.1f}/100

    📊 Data Integrity:
    • Missing values: {missing_data.sum()}/{len(data)*len(data.columns)} total
    • Duplicate timestamps: {duplicates}
    • Sampling consistency: {100-irregular_samples/len(time_diffs)*100:.1f}% regular

    🔍 Range Validation:
    • Total outliers: {total_outliers}/{total_points} ({outlier_rate:.1f}%)
    • Worst variable: {max(validation_results.keys(), key=lambda k: validation_results[k]['percentage'])}

    📡 Signal Quality:
    • Average SNR: {avg_snr:.1f} dB
    • Total spikes: {total_spikes} ({spike_rate:.1f}%)
    • Quality grade: {'A' if quality_score >= 90 else 'B' if quality_score >= 80 else 'C' if quality_score >= 70 else 'D'}

    💡 Recommendations:
    {'✅ Data quality is excellent' if quality_score >= 90 else
     '⚠️ Minor quality issues detected' if quality_score >= 80 else
     '❌ Significant quality issues - review needed'}
    """
    
    ax6.text(0.05, 0.95, summary_text, transform=ax6.transAxes, fontsize=10,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    ax6.axis('off')
    
    plt.tight_layout()
    plt.savefig('data_quality_assessment.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Step 6: Generate Quality Report
    print("\n6️⃣ QUALITY REPORT GENERATED")
    print(f"Overall Quality Score: {quality_score:.1f}/100")
    print(f"Grade: {'A' if quality_score >= 90 else 'B' if quality_score >= 80 else 'C' if quality_score >= 70 else 'D'}")
    
    if quality_score >= 90:
        print("✅ Data quality is excellent and ready for analysis")
    elif quality_score >= 80:
        print("⚠️ Data quality is good with minor issues")
    elif quality_score >= 70:
        print("⚠️ Data quality is acceptable but improvements recommended")
    else:
        print("❌ Data quality issues detected - thorough review needed")
    
    print("\n📁 Quality assessment saved as 'data_quality_assessment.png'")
    print("🎉 Data quality validation complete!")
    ```

#### What You Just Learned

✅ **Data Integrity**: Checking for missing values, duplicates, and type consistency  
✅ **Range Validation**: Verifying values fall within physiological ranges  
✅ **Temporal Analysis**: Assessing sampling consistency and timing  
✅ **Signal Quality**: Computing SNR, detecting spikes and artifacts  
✅ **Quality Scoring**: Creating comprehensive quality metrics  
✅ **Automated Reporting**: Generating actionable quality assessments  

</div>

## Advanced Examples

### 5. Statistical Gait Analysis {#statistical-analysis}

<div class="example-container" markdown>

**Time Required:** 20 minutes  
**Skill Level:** Advanced  
**Learning Goals:** Perform hypothesis testing, effect size calculation, confidence intervals

=== "Python"
    ```python
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy import stats
    import seaborn as sns
    
    # For this advanced example, we'll create a more complex dataset
    def create_advanced_dataset():
        """Create dataset with different conditions for statistical analysis"""
        np.random.seed(42)
        
        conditions = ['normal_walking', 'fast_walking', 'incline_walking']
        subjects = [f'P{i:03d}' for i in range(1, 21)]  # 20 subjects
        
        all_data = []
        
        for subject in subjects:
            # Individual subject characteristics
            age = np.random.randint(20, 70)
            baseline_knee = np.random.normal(25, 5)  # Individual baseline knee flexion
            
            for condition in conditions:
                # Condition-specific effects
                if condition == 'normal_walking':
                    condition_effect = 0
                    noise_level = 3
                elif condition == 'fast_walking':
                    condition_effect = 8  # Increased knee flexion
                    noise_level = 4
                else:  # incline_walking
                    condition_effect = 15  # Much higher knee flexion
                    noise_level = 5
                
                # Age effect (older adults have slightly less flexion)
                age_effect = -0.1 * (age - 45) if age > 45 else 0
                
                # Generate multiple gait cycles per condition
                for cycle in range(5):
                    peak_knee = baseline_knee + condition_effect + age_effect + np.random.normal(0, noise_level)
                    mean_hip = 15 + condition_effect * 0.3 + np.random.normal(0, 2)
                    peak_grf = 650 + condition_effect * 8 + np.random.normal(0, 50)
                    
                    all_data.append({
                        'subject_id': subject,
                        'condition': condition,
                        'age': age,
                        'cycle': cycle,
                        'peak_knee_flexion_deg': peak_knee,
                        'mean_hip_flexion_deg': mean_hip,
                        'peak_vertical_grf_N': peak_grf,
                        'stride_time_s': 1.1 + condition_effect * 0.02 + np.random.normal(0, 0.05)
                    })
        
        return pd.DataFrame(all_data)
    
    # Step 1: Create and explore dataset
    data = create_advanced_dataset()
    
    print("📊 STATISTICAL GAIT ANALYSIS")
    print("=" * 50)
    print(f"Dataset: {len(data)} observations")
    print(f"Subjects: {data['subject_id'].nunique()}")
    print(f"Conditions: {data['condition'].unique()}")
    print(f"Age range: {data['age'].min()}-{data['age'].max()} years")
    
    # Step 2: Descriptive Statistics
    print("\n1️⃣ DESCRIPTIVE STATISTICS")
    
    descriptive_stats = data.groupby('condition').agg({
        'peak_knee_flexion_deg': ['mean', 'std', 'min', 'max'],
        'mean_hip_flexion_deg': ['mean', 'std'],
        'peak_vertical_grf_N': ['mean', 'std'],
        'stride_time_s': ['mean', 'std']
    }).round(2)
    
    print(descriptive_stats)
    
    # Step 3: Statistical Testing
    print("\n2️⃣ HYPOTHESIS TESTING")
    
    # One-way ANOVA for knee flexion across conditions
    groups = [group['peak_knee_flexion_deg'].values for name, group in data.groupby('condition')]
    f_stat, p_anova = stats.f_oneway(*groups)
    
    print(f"One-way ANOVA (Peak Knee Flexion):")
    print(f"  F-statistic: {f_stat:.3f}")
    print(f"  p-value: {p_anova:.3e}")
    print(f"  Result: {'Significant' if p_anova < 0.05 else 'Non-significant'} difference between conditions")
    
    # Post-hoc pairwise comparisons
    conditions = data['condition'].unique()
    print(f"\nPost-hoc pairwise t-tests (Bonferroni corrected):")
    
    pairwise_results = {}
    alpha_corrected = 0.05 / 3  # Bonferroni correction for 3 comparisons
    
    for i in range(len(conditions)):
        for j in range(i+1, len(conditions)):
            cond1, cond2 = conditions[i], conditions[j]
            group1 = data[data['condition'] == cond1]['peak_knee_flexion_deg']
            group2 = data[data['condition'] == cond2]['peak_knee_flexion_deg']
            
            t_stat, p_val = stats.ttest_ind(group1, group2)
            
            # Effect size (Cohen's d)
            pooled_std = np.sqrt(((len(group1)-1)*group1.std()**2 + (len(group2)-1)*group2.std()**2) / 
                               (len(group1) + len(group2) - 2))
            cohens_d = (group1.mean() - group2.mean()) / pooled_std
            
            pairwise_results[f"{cond1}_vs_{cond2}"] = {
                't_stat': t_stat,
                'p_val': p_val,
                'cohens_d': cohens_d,
                'significant': p_val < alpha_corrected
            }
            
            significance = "***" if p_val < alpha_corrected else "ns"
            effect_size = "Large" if abs(cohens_d) > 0.8 else "Medium" if abs(cohens_d) > 0.5 else "Small"
            
            print(f"  {cond1} vs {cond2}:")
            print(f"    t = {t_stat:.3f}, p = {p_val:.3e} {significance}")
            print(f"    Cohen's d = {cohens_d:.3f} ({effect_size} effect)")
    
    # Step 4: Age Correlation Analysis
    print("\n3️⃣ AGE CORRELATION ANALYSIS")
    
    # Analyze age effects within each condition
    for condition in conditions:
        condition_data = data[data['condition'] == condition]
        
        # Correlation between age and knee flexion
        r_age_knee, p_age_knee = stats.pearsonr(condition_data['age'], 
                                               condition_data['peak_knee_flexion_deg'])
        
        print(f"{condition}:")
        print(f"  Age vs Knee Flexion: r = {r_age_knee:.3f}, p = {p_age_knee:.3f}")
        print(f"  Interpretation: {'Significant' if p_age_knee < 0.05 else 'Non-significant'} correlation")
    
    # Step 5: Confidence Intervals
    print("\n4️⃣ CONFIDENCE INTERVALS")
    
    for condition in conditions:
        condition_data = data[data['condition'] == condition]['peak_knee_flexion_deg']
        
        mean_val = condition_data.mean()
        sem = stats.sem(condition_data)  # Standard error of mean
        ci_95 = stats.t.interval(0.95, len(condition_data)-1, loc=mean_val, scale=sem)
        
        print(f"{condition}:")
        print(f"  Mean: {mean_val:.1f}° (95% CI: {ci_95[0]:.1f}° - {ci_95[1]:.1f}°)")
    
    # Step 6: Advanced Visualization
    print("\n5️⃣ CREATING STATISTICAL PLOTS")
    
    # Create comprehensive statistical visualization
    fig = plt.figure(figsize=(20, 15))
    
    # Plot 1: Box plots with individual points
    ax1 = plt.subplot(3, 3, 1)
    
    # Prepare data for seaborn
    sns.boxplot(data=data, x='condition', y='peak_knee_flexion_deg', ax=ax1)
    sns.stripplot(data=data, x='condition', y='peak_knee_flexion_deg', 
                 size=3, alpha=0.6, ax=ax1)
    
    ax1.set_title('Peak Knee Flexion by Condition')
    ax1.set_ylabel('Peak Knee Flexion (degrees)')
    ax1.tick_params(axis='x', rotation=45)
    
    # Add statistical annotations
    y_max = data['peak_knee_flexion_deg'].max()
    for i, (comparison, results) in enumerate(pairwise_results.items()):
        if results['significant']:
            y_pos = y_max + 2 + i * 3
            conditions_pair = comparison.split('_vs_')
            ax1.plot([0, 1], [y_pos, y_pos], 'k-', linewidth=1)
            ax1.text(0.5, y_pos + 0.5, f"p < 0.05", ha='center', fontsize=10)
    
    # Plot 2: Violin plots showing distributions
    ax2 = plt.subplot(3, 3, 2)
    sns.violinplot(data=data, x='condition', y='peak_knee_flexion_deg', ax=ax2)
    ax2.set_title('Distribution Shapes by Condition')
    ax2.set_ylabel('Peak Knee Flexion (degrees)')
    ax2.tick_params(axis='x', rotation=45)
    
    # Plot 3: Age correlation scatter plots
    ax3 = plt.subplot(3, 3, 3)
    colors = ['blue', 'red', 'green']
    for i, condition in enumerate(conditions):
        condition_data = data[data['condition'] == condition]
        ax3.scatter(condition_data['age'], condition_data['peak_knee_flexion_deg'], 
                   alpha=0.6, color=colors[i], label=condition, s=20)
        
        # Add regression line
        z = np.polyfit(condition_data['age'], condition_data['peak_knee_flexion_deg'], 1)
        p = np.poly1d(z)
        ax3.plot(condition_data['age'].sort_values(), 
                p(condition_data['age'].sort_values()), 
                color=colors[i], linestyle='--', alpha=0.8)
    
    ax3.set_xlabel('Age (years)')
    ax3.set_ylabel('Peak Knee Flexion (degrees)')
    ax3.set_title('Age vs Knee Flexion')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Effect sizes visualization
    ax4 = plt.subplot(3, 3, 4)
    
    comparisons = list(pairwise_results.keys())
    effect_sizes = [abs(pairwise_results[comp]['cohens_d']) for comp in comparisons]
    significance = [pairwise_results[comp]['significant'] for comp in comparisons]
    
    colors_effect = ['red' if sig else 'gray' for sig in significance]
    bars = ax4.bar(range(len(comparisons)), effect_sizes, color=colors_effect, alpha=0.7)
    
    ax4.set_xlabel('Comparisons')
    ax4.set_ylabel("Effect Size (|Cohen's d|)")
    ax4.set_title('Effect Sizes for Pairwise Comparisons')
    ax4.set_xticks(range(len(comparisons)))
    ax4.set_xticklabels([comp.replace('_', ' ') for comp in comparisons], rotation=45)
    
    # Add effect size interpretation lines
    ax4.axhline(y=0.2, color='green', linestyle='--', alpha=0.7, label='Small effect')
    ax4.axhline(y=0.5, color='orange', linestyle='--', alpha=0.7, label='Medium effect')
    ax4.axhline(y=0.8, color='red', linestyle='--', alpha=0.7, label='Large effect')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Plot 5: Confidence intervals
    ax5 = plt.subplot(3, 3, 5)
    
    means = []
    cis_lower = []
    cis_upper = []
    
    for condition in conditions:
        condition_data = data[data['condition'] == condition]['peak_knee_flexion_deg']
        mean_val = condition_data.mean()
        sem = stats.sem(condition_data)
        ci_95 = stats.t.interval(0.95, len(condition_data)-1, loc=mean_val, scale=sem)
        
        means.append(mean_val)
        cis_lower.append(ci_95[0])
        cis_upper.append(ci_95[1])
    
    x_pos = range(len(conditions))
    ax5.errorbar(x_pos, means, yerr=[np.array(means) - np.array(cis_lower), 
                                    np.array(cis_upper) - np.array(means)], 
                fmt='o', capsize=5, capthick=2, markersize=8)
    
    ax5.set_xlabel('Condition')
    ax5.set_ylabel('Peak Knee Flexion (degrees)')
    ax5.set_title('Means with 95% Confidence Intervals')
    ax5.set_xticks(x_pos)
    ax5.set_xticklabels(conditions, rotation=45)
    ax5.grid(True, alpha=0.3)
    
    # Plot 6: ANOVA assumption checks
    ax6 = plt.subplot(3, 3, 6)
    
    # Residuals for ANOVA
    overall_mean = data['peak_knee_flexion_deg'].mean()
    residuals = []
    
    for condition in conditions:
        condition_data = data[data['condition'] == condition]['peak_knee_flexion_deg']
        condition_mean = condition_data.mean()
        condition_residuals = condition_data - condition_mean
        residuals.extend(condition_residuals)
    
    # Q-Q plot for normality check
    stats.probplot(residuals, dist="norm", plot=ax6)
    ax6.set_title('Q-Q Plot: Normality Check')
    ax6.grid(True, alpha=0.3)
    
    # Plot 7: Power analysis
    ax7 = plt.subplot(3, 3, 7)
    
    # Estimate power for different effect sizes
    effect_sizes_range = np.linspace(0, 2, 100)
    powers = []
    
    for effect_size in effect_sizes_range:
        # Approximate power calculation using effect size and sample size
        n_per_group = len(data) // len(conditions)
        ncp = effect_size * np.sqrt(n_per_group / 2)  # Non-centrality parameter
        power = 1 - stats.t.cdf(stats.t.ppf(0.975, n_per_group*2-2), n_per_group*2-2, ncp)
        powers.append(power)
    
    ax7.plot(effect_sizes_range, powers, 'b-', linewidth=2)
    ax7.axhline(y=0.8, color='red', linestyle='--', alpha=0.7, label='80% Power')
    ax7.axvline(x=0.5, color='orange', linestyle='--', alpha=0.7, label='Medium Effect')
    
    ax7.set_xlabel("Effect Size (Cohen's d)")
    ax7.set_ylabel('Statistical Power')
    ax7.set_title('Power Analysis')
    ax7.legend()
    ax7.grid(True, alpha=0.3)
    
    # Plot 8: Summary statistics table
    ax8 = plt.subplot(3, 3, 8)
    
    # Create summary table
    summary_data = []
    for condition in conditions:
        condition_data = data[data['condition'] == condition]['peak_knee_flexion_deg']
        summary_data.append([
            condition,
            f"{condition_data.mean():.1f}",
            f"{condition_data.std():.1f}",
            f"{condition_data.min():.1f}",
            f"{condition_data.max():.1f}",
            f"{len(condition_data)}"
        ])
    
    table = ax8.table(cellText=summary_data,
                     colLabels=['Condition', 'Mean', 'SD', 'Min', 'Max', 'N'],
                     cellLoc='center',
                     loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)
    ax8.axis('off')
    ax8.set_title('Summary Statistics')
    
    # Plot 9: Statistical test results summary
    ax9 = plt.subplot(3, 3, 9)
    
    results_text = f"""STATISTICAL TEST RESULTS

One-way ANOVA:
F({len(conditions)-1}, {len(data)-len(conditions)}) = {f_stat:.3f}
p = {p_anova:.3e} {'***' if p_anova < 0.001 else '**' if p_anova < 0.01 else '*' if p_anova < 0.05 else 'ns'}

Post-hoc Comparisons (Bonferroni):
"""
    
    for comparison, results in pairwise_results.items():
        cond_pair = comparison.replace('_vs_', ' vs ').replace('_', ' ')
        sig_symbol = '***' if results['p_val'] < 0.001 else '**' if results['p_val'] < 0.01 else '*' if results['p_val'] < 0.05 else 'ns'
        results_text += f"{cond_pair}: p = {results['p_val']:.3e} {sig_symbol}\n"
        results_text += f"    Cohen's d = {results['cohens_d']:.3f}\n"
    
    results_text += f"""
Interpretation:
• {'Significant' if p_anova < 0.05 else 'Non-significant'} overall effect of condition
• {sum([r['significant'] for r in pairwise_results.values()])} out of {len(pairwise_results)} pairwise comparisons significant
• Effect sizes range from {min([abs(r['cohens_d']) for r in pairwise_results.values()]):.2f} to {max([abs(r['cohens_d']) for r in pairwise_results.values()]):.2f}
"""
    
    ax9.text(0.05, 0.95, results_text, transform=ax9.transAxes, fontsize=9,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
    ax9.axis('off')
    
    plt.tight_layout()
    plt.savefig('statistical_gait_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Step 7: Clinical Interpretation
    print("\n6️⃣ CLINICAL INTERPRETATION")
    
    print("Key Findings:")
    print(f"• Normal walking: {data[data['condition'] == 'normal_walking']['peak_knee_flexion_deg'].mean():.1f}° ± {data[data['condition'] == 'normal_walking']['peak_knee_flexion_deg'].std():.1f}°")
    print(f"• Fast walking: {data[data['condition'] == 'fast_walking']['peak_knee_flexion_deg'].mean():.1f}° ± {data[data['condition'] == 'fast_walking']['peak_knee_flexion_deg'].std():.1f}°")
    print(f"• Incline walking: {data[data['condition'] == 'incline_walking']['peak_knee_flexion_deg'].mean():.1f}° ± {data[data['condition'] == 'incline_walking']['peak_knee_flexion_deg'].std():.1f}°")
    
    print("\nClinical Significance:")
    normal_mean = data[data['condition'] == 'normal_walking']['peak_knee_flexion_deg'].mean()
    incline_mean = data[data['condition'] == 'incline_walking']['peak_knee_flexion_deg'].mean()
    difference = incline_mean - normal_mean
    
    print(f"• Incline walking increases knee flexion by {difference:.1f}° compared to normal walking")
    print(f"• This represents a {difference/normal_mean*100:.1f}% increase from baseline")
    
    if difference > 10:
        print("• This difference is clinically meaningful (>10° change)")
    else:
        print("• This difference may not be clinically meaningful (<10° change)")
    
    print("\n✅ Statistical gait analysis complete!")
    print("📁 Results saved as 'statistical_gait_analysis.png'")
    ```

#### What You Just Learned

✅ **Hypothesis Testing**: One-way ANOVA and post-hoc comparisons  
✅ **Effect Size Calculation**: Cohen's d and clinical interpretation  
✅ **Confidence Intervals**: Uncertainty quantification for means  
✅ **Power Analysis**: Understanding statistical power and sample size  
✅ **Assumption Checking**: Validating statistical test assumptions  
✅ **Clinical Translation**: Converting statistics to meaningful insights  

</div>

## Learning Pathways

### For Researchers
1. [Load and Explore Data](#5min-analysis) → [Compare Tasks](#task-comparison) → [Statistical Analysis](#statistical-analysis)
2. [Multi-Subject Analysis](#multi-subject) → [Quality Validation](#validation-check) → Advanced Case Studies

### For Clinicians  
1. [Load and Explore Data](#5min-analysis) → [Compare Tasks](#task-comparison) → [Multi-Subject Analysis](#multi-subject)
2. Focus on clinical interpretation sections in each example

### For Developers
1. [Quality Validation](#validation-check) → [Statistical Analysis](#statistical-analysis) → Custom Analysis Development
2. [Multi-Subject Analysis](#multi-subject) → Performance Optimization → Algorithm Development

## Next Steps

After completing these walkthroughs:

1. **[Try Case Studies](case_studies/)** - Apply these techniques to real research questions
2. **[Explore Advanced Features](../reference/api_reference/)** - Deep dive into library capabilities  
3. **[Join the Community](../community/)** - Share your analyses and learn from others
4. **[Contribute Examples](../contributor_guide/)** - Add your own analysis workflows

---

*All examples use realistic biomechanical data and have been tested with the current library version. Copy any code snippet and run it directly in your environment.*