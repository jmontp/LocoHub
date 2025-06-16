# Your First Dataset Analysis

Complete walkthrough of analyzing a standardized locomotion dataset from start to finish.

!!! info "What You'll Learn"
    - Load and explore a real biomechanical dataset
    - Perform quality checks and data validation
    - Conduct a comprehensive gait analysis
    - Generate publication-ready visualizations
    - Export results for further analysis

## Dataset Overview

We'll use the **Georgia Tech 2023** dataset, which contains:

- **10 subjects** performing various locomotion tasks
- **3 tasks**: Level walking, incline walking, stair climbing
- **~500 gait cycles** with complete kinematic and kinetic data
- **Phase-indexed format**: 150 points per gait cycle (0-100%)

## Step 1: Load and Explore

=== "Python"

    ```python
    import pandas as pd
    import matplotlib.pyplot as plt
    import numpy as np
    import seaborn as sns
    
    # Set up plotting style
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
    
    # Load the dataset
    data = pd.read_parquet('gtech_2023_phase.parquet')
    
    # Initial exploration
    print("=== Dataset Overview ===")
    print(f"Shape: {data.shape}")
    print(f"Memory usage: {data.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
    print(f"Date range: {data.index.min()} to {data.index.max()}")
    
    # Check for missing data
    missing_pct = (data.isnull().sum() / len(data)) * 100
    print(f"\nMissing data:")
    print(missing_pct[missing_pct > 0])
    
    # Basic statistics
    print(f"\n=== Data Composition ===")
    print(f"Subjects: {data['subject'].nunique()}")
    print(f"Tasks: {', '.join(data['task'].unique())}")
    print(f"Total gait cycles: {data['step'].nunique()}")
    print(f"Average cycles per subject: {data.groupby('subject')['step'].nunique().mean():.1f}")
    ```

=== "MATLAB"

    ```matlab
    % Load the dataset
    data = readtable('gtech_2023_phase.parquet');
    
    % Initial exploration
    fprintf('=== Dataset Overview ===\n');
    fprintf('Shape: %d rows, %d columns\n', height(data), width(data));
    
    % Check data types and basic info
    fprintf('Variables: %s\n', strjoin(data.Properties.VariableNames, ', '));
    
    % Check for missing data
    fprintf('\n=== Missing Data Check ===\n');
    for i = 1:width(data)
        var_name = data.Properties.VariableNames{i};
        missing_count = sum(ismissing(data.(var_name)));
        if missing_count > 0
            fprintf('%s: %d missing (%.1f%%)\n', var_name, missing_count, ...
                (missing_count/height(data))*100);
        end
    end
    
    % Basic statistics
    fprintf('\n=== Data Composition ===\n');
    fprintf('Subjects: %d\n', length(unique(data.subject)));
    fprintf('Tasks: %s\n', strjoin(unique(data.task), ', '));
    fprintf('Total gait cycles: %d\n', length(unique(data.step)));
    
    % Average cycles per subject
    cycles_per_subject = groupcounts(data, 'subject', 'GroupingVariables', 'step');
    fprintf('Average cycles per subject: %.1f\n', mean(cycles_per_subject.GroupCount));
    ```

## Step 2: Quality Assessment

Before analysis, verify data quality:

=== "Python"

    ```python
    # Check phase indexing (should be exactly 150 points per cycle)
    print("=== Phase Indexing Quality Check ===")
    phase_counts = data.groupby(['subject', 'task', 'step']).size()
    
    if all(phase_counts == 150):
        print("✅ Phase indexing: PASS (all cycles have 150 points)")
    else:
        print("⚠️  Phase indexing: ISSUES FOUND")
        print(f"Cycles with ≠150 points: {sum(phase_counts != 150)}")
    
    # Check phase values (should be 0 to 100)
    phase_range = data.groupby(['subject', 'task', 'step'])['phase_percent'].agg(['min', 'max'])
    
    if all(phase_range['min'] == 0) and all(phase_range['max'] == 100):
        print("✅ Phase range: PASS (0-100% for all cycles)")
    else:
        print("⚠️  Phase range: ISSUES FOUND")
    
    # Check biomechanical plausibility
    print("\n=== Biomechanical Range Check ===")
    
    # Knee flexion should be within reasonable range
    knee_angle = data['knee_flexion_angle_ipsi_rad']
    knee_deg = np.degrees(knee_angle)
    
    print(f"Knee flexion range: {knee_deg.min():.1f}° to {knee_deg.max():.1f}°")
    
    if knee_deg.min() >= -10 and knee_deg.max() <= 120:
        print("✅ Knee angles: PASS (within expected range)")
    else:
        print("⚠️  Knee angles: CHECK NEEDED")
    
    # Check for outliers (values beyond 3 standard deviations)
    outliers = np.abs(knee_deg - knee_deg.mean()) > 3 * knee_deg.std()
    print(f"Outliers: {outliers.sum()}/{len(knee_deg)} points ({outliers.mean()*100:.1f}%)")
    ```

=== "MATLAB"

    ```matlab
    % Check phase indexing (should be exactly 150 points per cycle)
    fprintf('=== Phase Indexing Quality Check ===\n');
    
    % Count points per cycle
    phase_counts = groupcounts(data, {'subject', 'task', 'step'});
    
    if all(phase_counts.GroupCount == 150)
        fprintf('✅ Phase indexing: PASS (all cycles have 150 points)\n');
    else
        fprintf('⚠️  Phase indexing: ISSUES FOUND\n');
        fprintf('Cycles with ≠150 points: %d\n', sum(phase_counts.GroupCount ~= 150));
    end
    
    % Check phase values (should be 0 to 100)
    phase_summary = groupsummary(data, {'subject', 'task', 'step'}, {'min', 'max'}, 'phase_percent');
    
    if all(phase_summary.min_phase_percent == 0) && all(phase_summary.max_phase_percent == 100)
        fprintf('✅ Phase range: PASS (0-100%% for all cycles)\n');
    else
        fprintf('⚠️  Phase range: ISSUES FOUND\n');
    end
    
    % Check biomechanical plausibility
    fprintf('\n=== Biomechanical Range Check ===\n');
    
    % Knee flexion should be within reasonable range
    knee_angle = data.knee_flexion_angle_ipsi_rad;
    knee_deg = rad2deg(knee_angle);
    
    fprintf('Knee flexion range: %.1f° to %.1f°\n', min(knee_deg), max(knee_deg));
    
    if min(knee_deg) >= -10 && max(knee_deg) <= 120
        fprintf('✅ Knee angles: PASS (within expected range)\n');
    else
        fprintf('⚠️  Knee angles: CHECK NEEDED\n');
    end
    
    % Check for outliers (values beyond 3 standard deviations)
    outliers = abs(knee_deg - mean(knee_deg)) > 3 * std(knee_deg);
    fprintf('Outliers: %d/%d points (%.1f%%)\n', sum(outliers), length(knee_deg), mean(outliers)*100);
    ```

## Step 3: Comprehensive Gait Analysis

Analyze gait patterns across different conditions:

=== "Python"

    ```python
    # Create comprehensive analysis
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Comprehensive Gait Analysis - Georgia Tech 2023 Dataset', fontsize=16)
    
    # 1. Average gait patterns by task
    ax1 = axes[0, 0]
    for task in data['task'].unique():
        task_data = data[data['task'] == task]
        avg_pattern = task_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
        ax1.plot(avg_pattern.index, np.degrees(avg_pattern.values), 
                label=task.replace('_', ' ').title(), linewidth=2)
    
    ax1.set_xlabel('Gait Cycle (%)')
    ax1.set_ylabel('Knee Flexion (degrees)')
    ax1.set_title('Average Knee Angle by Task')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Subject variability
    ax2 = axes[0, 1]
    level_walking = data[data['task'] == 'level_walking']
    
    for subject in level_walking['subject'].unique()[:5]:  # Show first 5 subjects
        subj_data = level_walking[level_walking['subject'] == subject]
        avg_pattern = subj_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
        ax2.plot(avg_pattern.index, np.degrees(avg_pattern.values), 
                alpha=0.7, label=subject)
    
    ax2.set_xlabel('Gait Cycle (%)')
    ax2.set_ylabel('Knee Flexion (degrees)')
    ax2.set_title('Inter-Subject Variability (Level Walking)')
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    # 3. Range of motion comparison
    ax3 = axes[0, 2]
    rom_data = []
    for task in data['task'].unique():
        task_data = data[data['task'] == task]
        rom_by_cycle = task_data.groupby(['subject', 'step'])['knee_flexion_angle_ipsi_rad'].apply(
            lambda x: np.degrees(x.max() - x.min())
        )
        rom_data.extend([(task, rom) for rom in rom_by_cycle])
    
    rom_df = pd.DataFrame(rom_data, columns=['Task', 'ROM'])
    sns.boxplot(data=rom_df, x='Task', y='ROM', ax=ax3)
    ax3.set_ylabel('Knee ROM (degrees)')
    ax3.set_title('Range of Motion by Task')
    ax3.tick_params(axis='x', rotation=45)
    
    # 4. Peak knee flexion timing
    ax4 = axes[1, 0]
    peak_timing = []
    for task in data['task'].unique():
        task_data = data[data['task'] == task]
        for (subject, step), group in task_data.groupby(['subject', 'step']):
            peak_idx = group['knee_flexion_angle_ipsi_rad'].idxmax()
            peak_phase = group.loc[peak_idx, 'phase_percent']
            peak_timing.append((task, peak_phase))
    
    timing_df = pd.DataFrame(peak_timing, columns=['Task', 'Peak_Phase'])
    sns.boxplot(data=timing_df, x='Task', y='Peak_Phase', ax=ax4)
    ax4.set_ylabel('Peak Knee Flexion Phase (%)')
    ax4.set_title('Peak Flexion Timing')
    ax4.tick_params(axis='x', rotation=45)
    
    # 5. Gait cycle consistency
    ax5 = axes[1, 1]
    consistency_data = []
    for subject in data['subject'].unique():
        subj_data = data[(data['subject'] == subject) & (data['task'] == 'level_walking')]
        if len(subj_data) > 0:
            # Calculate coefficient of variation across cycles
            cv_by_phase = subj_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].apply(
                lambda x: np.std(x) / np.abs(np.mean(x)) if np.mean(x) != 0 else 0
            )
            consistency_data.append(cv_by_phase.mean())
    
    ax5.hist(consistency_data, bins=10, alpha=0.7, edgecolor='black')
    ax5.set_xlabel('Coefficient of Variation')
    ax5.set_ylabel('Number of Subjects')
    ax5.set_title('Gait Consistency (Level Walking)')
    ax5.grid(True, alpha=0.3)
    
    # 6. Data quality summary
    ax6 = axes[1, 2]
    quality_metrics = {
        'Complete Cycles': sum(data.groupby(['subject', 'step']).size() == 150),
        'Valid Phase Range': sum((data.groupby(['subject', 'step'])['phase_percent'].min() == 0) & 
                                (data.groupby(['subject', 'step'])['phase_percent'].max() == 100)),
        'No Missing Data': sum(~data.groupby(['subject', 'step'])['knee_flexion_angle_ipsi_rad'].apply(
            lambda x: x.isnull().any())),
        'Plausible Range': sum(data.groupby(['subject', 'step'])['knee_flexion_angle_ipsi_rad'].apply(
            lambda x: (np.degrees(x.min()) >= -10) & (np.degrees(x.max()) <= 120)))
    }
    
    total_cycles = data['step'].nunique()
    quality_pct = {k: (v/total_cycles)*100 for k, v in quality_metrics.items()}
    
    bars = ax6.bar(range(len(quality_pct)), list(quality_pct.values()))
    ax6.set_xticks(range(len(quality_pct)))
    ax6.set_xticklabels(list(quality_pct.keys()), rotation=45, ha='right')
    ax6.set_ylabel('Percentage of Cycles (%)')
    ax6.set_title('Data Quality Metrics')
    ax6.set_ylim(0, 105)
    
    # Add percentage labels on bars
    for bar, pct in zip(bars, quality_pct.values()):
        ax6.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{pct:.1f}%', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig('comprehensive_gait_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("Comprehensive analysis saved as 'comprehensive_gait_analysis.png'")
    ```

=== "MATLAB"

    ```matlab
    % Create comprehensive analysis
    figure('Position', [100, 100, 1200, 800]);
    
    % 1. Average gait patterns by task
    subplot(2, 3, 1);
    tasks = unique(data.task);
    colors = lines(length(tasks));
    
    for i = 1:length(tasks)
        task = tasks{i};
        task_data = data(strcmp(data.task, task), :);
        avg_pattern = groupsummary(task_data, 'phase_percent', 'mean', 'knee_flexion_angle_ipsi_rad');
        
        plot(avg_pattern.phase_percent, rad2deg(avg_pattern.mean_knee_flexion_angle_ipsi_rad), ...
            'Color', colors(i,:), 'LineWidth', 2, 'DisplayName', strrep(task, '_', ' '));
        hold on;
    end
    
    xlabel('Gait Cycle (%)');
    ylabel('Knee Flexion (degrees)');
    title('Average Knee Angle by Task');
    legend('show');
    grid on;
    hold off;
    
    % 2. Subject variability
    subplot(2, 3, 2);
    level_walking = data(strcmp(data.task, 'level_walking'), :);
    subjects = unique(level_walking.subject);
    
    for i = 1:min(5, length(subjects))  % Show first 5 subjects
        subject = subjects{i};
        subj_data = level_walking(strcmp(level_walking.subject, subject), :);
        avg_pattern = groupsummary(subj_data, 'phase_percent', 'mean', 'knee_flexion_angle_ipsi_rad');
        
        plot(avg_pattern.phase_percent, rad2deg(avg_pattern.mean_knee_flexion_angle_ipsi_rad), ...
            'LineWidth', 1.5, 'DisplayName', subject);
        hold on;
    end
    
    xlabel('Gait Cycle (%)');
    ylabel('Knee Flexion (degrees)');
    title('Inter-Subject Variability (Level Walking)');
    legend('show');
    grid on;
    hold off;
    
    % 3. Range of motion comparison
    subplot(2, 3, 3);
    rom_by_task = cell(length(tasks), 1);
    
    for i = 1:length(tasks)
        task = tasks{i};
        task_data = data(strcmp(data.task, task), :);
        
        % Calculate ROM for each cycle
        rom_summary = groupsummary(task_data, {'subject', 'step'}, {'min', 'max'}, 'knee_flexion_angle_ipsi_rad');
        rom_values = rad2deg(rom_summary.max_knee_flexion_angle_ipsi_rad - rom_summary.min_knee_flexion_angle_ipsi_rad);
        
        rom_by_task{i} = rom_values;
    end
    
    boxplot([rom_by_task{:}], 'Labels', strrep(tasks, '_', ' '));
    ylabel('Knee ROM (degrees)');
    title('Range of Motion by Task');
    xtickangle(45);
    
    % 4. Peak knee flexion timing
    subplot(2, 3, 4);
    peak_timing_by_task = cell(length(tasks), 1);
    
    for i = 1:length(tasks)
        task = tasks{i};
        task_data = data(strcmp(data.task, task), :);
        
        % Find peak timing for each cycle
        cycle_groups = findgroups(task_data.subject, task_data.step);
        peak_phases = splitapply(@(angle, phase) phase(angle == max(angle)), ...
            task_data.knee_flexion_angle_ipsi_rad, task_data.phase_percent, cycle_groups);
        
        peak_timing_by_task{i} = peak_phases;
    end
    
    boxplot([peak_timing_by_task{:}], 'Labels', strrep(tasks, '_', ' '));
    ylabel('Peak Knee Flexion Phase (%)');
    title('Peak Flexion Timing');
    xtickangle(45);
    
    % 5. Gait cycle consistency
    subplot(2, 3, 5);
    subjects = unique(data.subject);
    consistency_values = zeros(length(subjects), 1);
    
    for i = 1:length(subjects)
        subject = subjects{i};
        subj_data = data(strcmp(data.subject, subject) & strcmp(data.task, 'level_walking'), :);
        
        if ~isempty(subj_data)
            % Calculate coefficient of variation by phase
            cv_by_phase = groupsummary(subj_data, 'phase_percent', {'mean', 'std'}, 'knee_flexion_angle_ipsi_rad');
            cv_values = cv_by_phase.std_knee_flexion_angle_ipsi_rad ./ abs(cv_by_phase.mean_knee_flexion_angle_ipsi_rad);
            consistency_values(i) = mean(cv_values(~isnan(cv_values) & ~isinf(cv_values)));
        end
    end
    
    histogram(consistency_values(consistency_values > 0), 10, 'EdgeColor', 'black');
    xlabel('Coefficient of Variation');
    ylabel('Number of Subjects');
    title('Gait Consistency (Level Walking)');
    grid on;
    
    % 6. Data quality summary
    subplot(2, 3, 6);
    
    % Calculate quality metrics
    cycle_groups = findgroups(data.subject, data.task, data.step);
    points_per_cycle = splitapply(@height, data, cycle_groups);
    complete_cycles = sum(points_per_cycle == 150);
    
    phase_ranges = splitapply(@(p) [min(p), max(p)], data.phase_percent, cycle_groups);
    valid_ranges = sum(phase_ranges(:,1) == 0 & phase_ranges(:,2) == 100);
    
    knee_ranges = splitapply(@(k) [min(k), max(k)], data.knee_flexion_angle_ipsi_rad, cycle_groups);
    plausible_ranges = sum(rad2deg(knee_ranges(:,1)) >= -10 & rad2deg(knee_ranges(:,2)) <= 120);
    
    total_cycles = length(unique(data.step));
    
    quality_metrics = [complete_cycles, valid_ranges, total_cycles, plausible_ranges];
    quality_labels = {'Complete Cycles', 'Valid Phase Range', 'No Missing Data', 'Plausible Range'};
    quality_pct = (quality_metrics / total_cycles) * 100;
    
    b = bar(quality_pct);
    set(gca, 'XTickLabel', quality_labels);
    xtickangle(45);
    ylabel('Percentage of Cycles (%)');
    title('Data Quality Metrics');
    ylim([0, 105]);
    
    % Add percentage labels
    for i = 1:length(quality_pct)
        text(i, quality_pct(i) + 2, sprintf('%.1f%%', quality_pct(i)), ...
            'HorizontalAlignment', 'center');
    end
    
    sgtitle('Comprehensive Gait Analysis - Georgia Tech 2023 Dataset');
    
    % Save the figure
    saveas(gcf, 'comprehensive_gait_analysis.png');
    
    fprintf('Comprehensive analysis saved as ''comprehensive_gait_analysis.png''\n');
    ```

## Step 4: Statistical Analysis

Perform statistical comparisons between conditions:

=== "Python"

    ```python
    from scipy import stats
    
    # Compare peak knee flexion between tasks
    print("=== Statistical Analysis ===")
    
    # Extract peak knee flexion for each cycle
    peak_flexion_data = []
    for task in data['task'].unique():
        task_data = data[data['task'] == task]
        for (subject, step), group in task_data.groupby(['subject', 'step']):
            peak_angle = np.degrees(group['knee_flexion_angle_ipsi_rad'].max())
            peak_flexion_data.append({
                'task': task, 
                'subject': subject, 
                'step': step, 
                'peak_knee_flexion': peak_angle
            })
    
    peak_df = pd.DataFrame(peak_flexion_data)
    
    # Descriptive statistics
    print("\nPeak Knee Flexion by Task (degrees):")
    print(peak_df.groupby('task')['peak_knee_flexion'].agg(['count', 'mean', 'std', 'min', 'max']).round(1))
    
    # Statistical comparison (ANOVA)
    if len(data['task'].unique()) > 2:
        groups = [peak_df[peak_df['task'] == task]['peak_knee_flexion'].values 
                 for task in data['task'].unique()]
        f_stat, p_value = stats.f_oneway(*groups)
        
        print(f"\nOne-way ANOVA:")
        print(f"F-statistic: {f_stat:.3f}")
        print(f"p-value: {p_value:.3e}")
        
        if p_value < 0.05:
            print("✅ Significant differences between tasks (p < 0.05)")
            
            # Post-hoc pairwise comparisons
            from itertools import combinations
            tasks = data['task'].unique()
            
            print("\nPairwise t-tests (with Bonferroni correction):")
            alpha_corrected = 0.05 / len(list(combinations(tasks, 2)))
            
            for task1, task2 in combinations(tasks, 2):
                group1 = peak_df[peak_df['task'] == task1]['peak_knee_flexion']
                group2 = peak_df[peak_df['task'] == task2]['peak_knee_flexion']
                
                t_stat, p_val = stats.ttest_ind(group1, group2)
                significant = p_val < alpha_corrected
                
                print(f"{task1} vs {task2}: t={t_stat:.3f}, p={p_val:.3e} {'*' if significant else ''}")
        else:
            print("No significant differences between tasks (p >= 0.05)")
    ```

=== "MATLAB"

    ```matlab
    % Statistical Analysis
    fprintf('=== Statistical Analysis ===\n');
    
    % Extract peak knee flexion for each cycle
    cycle_groups = findgroups(data.subject, data.task, data.step);
    peak_flexion = splitapply(@max, data.knee_flexion_angle_ipsi_rad, cycle_groups);
    [subjects, tasks, steps] = splitapply(@(s,t,st) {s{1}, t{1}, st(1)}, ...
        data.subject, data.task, data.step, cycle_groups);
    
    % Create summary table
    peak_data = table(subjects, tasks, steps, rad2deg(peak_flexion), ...
        'VariableNames', {'subject', 'task', 'step', 'peak_knee_flexion'});
    
    % Descriptive statistics
    fprintf('\nPeak Knee Flexion by Task (degrees):\n');
    task_stats = groupsummary(peak_data, 'task', {'count', 'mean', 'std', 'min', 'max'}, 'peak_knee_flexion');
    disp(task_stats);
    
    % Statistical comparison (ANOVA)
    unique_tasks = unique(data.task);
    if length(unique_tasks) > 2
        [p, tbl, stats] = anova1(peak_data.peak_knee_flexion, peak_data.task, 'off');
        
        fprintf('\nOne-way ANOVA:\n');
        fprintf('F-statistic: %.3f\n', tbl{2,5});
        fprintf('p-value: %.3e\n', p);
        
        if p < 0.05
            fprintf('✅ Significant differences between tasks (p < 0.05)\n');
            
            % Post-hoc multiple comparisons
            fprintf('\nPost-hoc multiple comparisons:\n');
            [c, m, h, nms] = multcompare(stats, 'Display', 'off');
            
            for i = 1:size(c, 1)
                task1 = nms{c(i,1)};
                task2 = nms{c(i,2)};
                p_val = c(i,6);
                significant = p_val < 0.05;
                
                fprintf('%s vs %s: p=%.3e %s\n', task1, task2, p_val, ...
                    char(42 * significant)); % Print * if significant
            end
        else
            fprintf('No significant differences between tasks (p >= 0.05)\n');
        end
    end
    ```

## Step 5: Export Results

Save your analysis results for further use:

=== "Python"

    ```python
    # Create summary report
    summary_results = {
        'dataset_info': {
            'name': 'Georgia Tech 2023',
            'subjects': int(data['subject'].nunique()),
            'tasks': list(data['task'].unique()),
            'total_cycles': int(data['step'].nunique()),
            'total_datapoints': len(data)
        },
        'quality_metrics': {
            'complete_cycles_pct': (sum(data.groupby(['subject', 'step']).size() == 150) / data['step'].nunique()) * 100,
            'missing_data_pct': (data.isnull().sum().sum() / data.size) * 100,
            'outlier_pct': (outliers.sum() / len(outliers)) * 100
        },
        'biomechanical_summary': {
            'knee_flexion_mean_deg': float(np.degrees(data['knee_flexion_angle_ipsi_rad'].mean())),
            'knee_flexion_std_deg': float(np.degrees(data['knee_flexion_angle_ipsi_rad'].std())),
            'knee_flexion_range_deg': [
                float(np.degrees(data['knee_flexion_angle_ipsi_rad'].min())),
                float(np.degrees(data['knee_flexion_angle_ipsi_rad'].max()))
            ]
        }
    }
    
    # Save as JSON
    import json
    with open('analysis_summary.json', 'w') as f:
        json.dump(summary_results, f, indent=2)
    
    # Save processed data for further analysis
    # Create cycle-level summary
    cycle_summary = data.groupby(['subject', 'task', 'step']).agg({
        'knee_flexion_angle_ipsi_rad': ['min', 'max', 'mean'],
        'hip_flexion_angle_ipsi_rad': ['min', 'max', 'mean'],
        'ankle_flexion_angle_ipsi_rad': ['min', 'max', 'mean']
    }).round(4)
    
    # Flatten column names
    cycle_summary.columns = ['_'.join(col).strip() for col in cycle_summary.columns]
    cycle_summary = cycle_summary.reset_index()
    
    # Add range of motion columns
    cycle_summary['knee_rom_rad'] = (cycle_summary['knee_flexion_angle_ipsi_rad_max'] - 
                                    cycle_summary['knee_flexion_angle_ipsi_rad_min'])
    cycle_summary['hip_rom_rad'] = (cycle_summary['hip_flexion_angle_ipsi_rad_max'] - 
                                   cycle_summary['hip_flexion_angle_ipsi_rad_min'])
    cycle_summary['ankle_rom_rad'] = (cycle_summary['ankle_flexion_angle_ipsi_rad_max'] - 
                                     cycle_summary['ankle_flexion_angle_ipsi_rad_min'])
    
    cycle_summary.to_csv('cycle_level_summary.csv', index=False)
    
    print("=== Analysis Complete ===")
    print("Files generated:")
    print("- comprehensive_gait_analysis.png (6-panel analysis)")
    print("- analysis_summary.json (key metrics)")
    print("- cycle_level_summary.csv (cycle-by-cycle data)")
    print(f"\nCycles analyzed: {len(cycle_summary)}")
    print(f"Average knee ROM: {np.degrees(cycle_summary['knee_rom_rad'].mean()):.1f}° ± {np.degrees(cycle_summary['knee_rom_rad'].std()):.1f}°")
    ```

=== "MATLAB"

    ```matlab
    % Create cycle-level summary
    cycle_summary = groupsummary(data, {'subject', 'task', 'step'}, ...
        {'min', 'max', 'mean'}, {'knee_flexion_angle_ipsi_rad', ...
        'hip_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad'});
    
    % Add range of motion columns
    cycle_summary.knee_rom_rad = cycle_summary.max_knee_flexion_angle_ipsi_rad - ...
        cycle_summary.min_knee_flexion_angle_ipsi_rad;
    cycle_summary.hip_rom_rad = cycle_summary.max_hip_flexion_angle_ipsi_rad - ...
        cycle_summary.min_hip_flexion_angle_ipsi_rad;
    cycle_summary.ankle_rom_rad = cycle_summary.max_ankle_flexion_angle_ipsi_rad - ...
        cycle_summary.min_ankle_flexion_angle_ipsi_rad;
    
    % Save results
    writetable(cycle_summary, 'cycle_level_summary.csv');
    
    % Create summary structure
    summary_results = struct();
    summary_results.dataset_info.name = 'Georgia Tech 2023';
    summary_results.dataset_info.subjects = length(unique(data.subject));
    summary_results.dataset_info.tasks = unique(data.task);
    summary_results.dataset_info.total_cycles = length(unique(data.step));
    summary_results.dataset_info.total_datapoints = height(data);
    
    summary_results.biomechanical_summary.knee_flexion_mean_deg = ...
        rad2deg(mean(data.knee_flexion_angle_ipsi_rad));
    summary_results.biomechanical_summary.knee_flexion_std_deg = ...
        rad2deg(std(data.knee_flexion_angle_ipsi_rad));
    summary_results.biomechanical_summary.knee_rom_mean_deg = ...
        rad2deg(mean(cycle_summary.knee_rom_rad));
    
    % Save as MAT file
    save('analysis_summary.mat', 'summary_results');
    
    fprintf('=== Analysis Complete ===\n');
    fprintf('Files generated:\n');
    fprintf('- comprehensive_gait_analysis.png (6-panel analysis)\n');
    fprintf('- analysis_summary.mat (key metrics)\n');
    fprintf('- cycle_level_summary.csv (cycle-by-cycle data)\n');
    fprintf('\nCycles analyzed: %d\n', height(cycle_summary));
    fprintf('Average knee ROM: %.1f° ± %.1f°\n', ...
        rad2deg(mean(cycle_summary.knee_rom_rad)), ...
        rad2deg(std(cycle_summary.knee_rom_rad)));
    ```

## What You've Accomplished

Congratulations! You've completed a comprehensive analysis including:

- ✅ **Data loading and exploration** - Understanding dataset structure
- ✅ **Quality assessment** - Validating data integrity
- ✅ **Comprehensive visualization** - 6-panel analysis figure
- ✅ **Statistical analysis** - Comparing conditions with ANOVA
- ✅ **Results export** - Saving analysis for future use

## Key Findings Template

Use this template to summarize your results:

!!! example "Analysis Summary"
    **Dataset**: Georgia Tech 2023 (N=10 subjects, 3 tasks, ~500 cycles)
    
    **Data Quality**: 
    - ✅ Phase indexing: 100% cycles have 150 points
    - ✅ Biomechanical range: All values within expected limits
    - ✅ Missing data: <1% of total datapoints
    
    **Key Findings**:
    - Average knee ROM: XX° ± XX° (level walking)
    - Peak knee flexion: Level walking < Incline walking < Stair climbing
    - Inter-subject variability: CV = XX%
    
    **Statistical Results**:
    - ANOVA: F(2,XXX) = XX.XX, p < 0.001
    - Post-hoc: All pairwise comparisons significant (p < 0.05)

## Next Steps

### Advanced Analysis
- **[Working with Data](../user_guide/working_with_data/)** - Advanced analysis techniques
- **[API Reference](../reference/api_reference/)** - Complete function documentation

### Multiple Datasets
- Combine datasets from different sources
- Cross-lab validation and comparison
- Meta-analysis across studies

### Contribute Back
- **[Contributor Guide](../contributor_guide/)** - Share your datasets
- **[Validation Tuning](../contributor_guide/validation_tuning/)** - Improve quality standards

---

*This analysis template can be adapted for any standardized dataset. Questions? Check our [Troubleshooting Guide](../user_guide/troubleshooting/).*