---
title: Tutorials
---

# Tutorials

Do the tasks below. Pick your environment once and the page follows your choice.

Select your language:

<div class="code-mode-buttons">
  <a href="#" class="code-mode-button" data-lang="python">Python</a>
  <a href="#" class="code-mode-button" data-lang="matlab">MATLAB</a>
  
</div>

## Test Dataset

Use this small sample to try the tutorials quickly:

[Download Example CSV (1000 rows)](../../contributing/locohub_example_data.csv){ .md-button .md-button--primary download="locohub_example_data.csv" }

Or use the full parquet datasets linked on the homepage.

## 1) Load Data

=== "Raw"
    <div class="code-lang code-lang-python">
    
    ```python
    import pandas as pd
    import numpy as np
    
    # Load phase-indexed dataset (150 samples per cycle)
    df = pd.read_parquet('umich_2021_phase.parquet')
    print(df.shape)
    
    # Inspect structure
    print(df.columns.tolist()[:10])
    print(df.dtypes.head())
    
    # Filter to one subject + task
    subset = df[(df['task'] == 'level_walking') & (df['subject_id'] == 'UM21_AB01')]
    
    # Extract arrays for analysis/plotting
    phase = subset['phase_percent'].to_numpy()
    knee  = subset['knee_flexion_angle_ipsi_rad'].to_numpy()
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    % Load phase-indexed dataset (150 samples per cycle)
    T = parquetread('umich_2021_phase.parquet');
    size(T)  % rows x columns
    
    % Inspect structure
    T.Properties.VariableNames(1:10)
    varfun(@class, T(1,:), 'OutputFormat','table')
    
    % Filter to one subject + task
    subset = T(T.task == "level_walking" & T.subject_id == "UM21_AB01", :);
    
    % Extract arrays for analysis/plotting
    phase = subset.phase_percent;
    knee  = subset.knee_flexion_angle_ipsi_rad;
    ```
    
    </div>

=== "Library"
    <div class="code-lang code-lang-python">
    
    ```python
    from user_libs.python.locomotion_data import LocomotionData
    
    data = LocomotionData('umich_2021_phase.parquet')
    print(data.shape)            # rows, columns
    print(data.get_variables()[:10])
    
    # Filter and extract cycles (3D array: n_cycles x 150 x n_features)
    subset = data.filter(task='level_walking', subjects=['UM21_AB01'])
    cycles, features = subset.get_cycles('UM21_AB01', 'level_walking')
    
    # Convenience arrays for a single feature
    knee_idx = features.index('knee_flexion_angle_ipsi_rad')
    knee_cycles = cycles[:, :, knee_idx]
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    addpath('user_libs/matlab');
    loco  = LocomotionData('umich_2021_phase.parquet');
    [rows, cols] = loco.getShape()
    
    % Filter and extract cycles (n_cycles x 150 x n_features)
    level = loco.filterTask('level_walking').filterSubject('UM21_AB01');
    [cycles, features] = level.getCycles('UM21_AB01', 'level_walking');
    
    % Convenience arrays for a single feature
    kneeIdx = find(strcmp(features,'knee_flexion_angle_ipsi_rad'));
    kneeCycles = squeeze(cycles(:, :, kneeIdx));
    ```
    
    </div>

## 2) Filter / Subset

=== "Raw"
    <div class="code-lang code-lang-python">
    
    ```python
    # Filter by subject + task + columns
    cols = ['subject_id','task','phase_percent','knee_flexion_angle_ipsi_rad']
    subset = df.loc[(df.task=='level_walking') & (df.subject_id=='UM21_AB01'), cols]
    
    # Multiple tasks
    walking = df[df['task'].isin(['level_walking','incline_walking','decline_walking'])]
    
    # First N cycles per subject-task
    def first_n_cycles(x, n=5):
        return x[x['cycle_id'].isin(x['cycle_id'].unique()[:n])]
    first5 = df.groupby(['subject_id','task'], group_keys=False).apply(first_n_cycles, n=5)
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    % Filter by subject + task + columns
    cols = {'subject_id','task','phase_percent','knee_flexion_angle_ipsi_rad'};
    mask = T.task=="level_walking" & T.subject_id=="UM21_AB01";
    subset = T(mask, cols);
    
    % Multiple tasks
    maskWalk = ismember(T.task, {"level_walking","incline_walking","decline_walking"});
    walking = T(maskWalk, :);
    
    % First N cycles per subject-task
    % (Example using cycle_id if available)
    % See detailed MATLAB tutorial for grouping utilities.
    ```
    
    </div>

=== "Library"
    <div class="code-lang code-lang-python">
    
    ```python
    # Filter by subject + task + features
    subset = data.filter(task='level_walking', subjects=['UM21_AB01'],
                         features=['knee_flexion_angle_ipsi_rad'])
    
    # Multiple tasks
    walking = data.filter(tasks=['level_walking','incline_walking','decline_walking'])
    
    # First N cycles per subject-task
    first5 = data.get_first_n_cycles(n=5)
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    % Filter by subject + task + features
    subset = level.selectFeatures({'knee_flexion_angle_ipsi_rad'});
    
    % Multiple tasks (re-load or filter from loco)
    walking = loco.filterTasks({"level_walking","incline_walking","decline_walking"});
    
    % First N cycles per subject-task
    first5 = loco.getFirstNCycles(5);
    ```
    
    </div>

## 3) Visualize

=== "Raw"
    <div class="code-lang code-lang-python">
    
    ```python
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    
    # Load + filter
    df = pd.read_parquet('umich_2021_phase.parquet')
    subset = df[(df['task'] == 'level_walking') & (df['subject_id'] == 'UM21_AB01')]
    
    # Mean ± SD band over phase
    mean_knee = subset.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean().to_numpy()
    std_knee  = subset.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].std().to_numpy()
    phase100  = subset['phase_percent'].unique()
    
    plt.figure(figsize=(6,4))
    plt.fill_between(phase100, mean_knee-std_knee, mean_knee+std_knee, alpha=0.2)
    plt.plot(phase100, mean_knee, label='Knee Flex (rad)')
    plt.xlabel('Gait Cycle (%)'); plt.ylabel('Knee Flexion (rad)'); plt.legend(); plt.tight_layout(); plt.show()
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    % Load + filter
    T = parquetread('umich_2021_phase.parquet');
    subset = T(T.task=="level_walking" & T.subject_id=="UM21_AB01", :);
    
    % Mean ± SD band over phase
    [g,~,idx] = unique(subset.phase_percent);
    mean_knee = splitapply(@mean, subset.knee_flexion_angle_ipsi_rad, idx);
    std_knee  = splitapply(@std,  subset.knee_flexion_angle_ipsi_rad, idx);
    
    figure('Position',[100,100,600,380]); hold on
    fill([g; flipud(g)], [mean_knee-std_knee; flipud(mean_knee+std_knee)], [0 0.45 0.9], 'FaceAlpha',0.2,'EdgeColor','none');
    plot(g, mean_knee, 'Color',[0 0.45 0.9], 'LineWidth',1.8)
    xlabel('Gait Cycle (%)'); ylabel('Knee Flexion (rad)'); grid on; box on; hold off
    ```
    
    </div>

=== "Library"
    <div class="code-lang code-lang-python">
    
    ```python
    from user_libs.python.locomotion_data import LocomotionData
    data = LocomotionData('umich_2021_phase.parquet')
    subset = data.filter(task='level_walking', subjects=['UM21_AB01'])

    # Built-in phase plotter (adds mean ± SD by default)
    subset.plot_phase_patterns('UM21_AB01','level_walking',['knee_flexion_angle_ipsi_rad'])
   
    # Task comparison helper
    subset.plot_task_comparison('UM21_AB01',['level_walking','incline_walking'],['knee_flexion_angle_ipsi_rad'])
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    addpath('user_libs/matlab');
    loco = LocomotionData('umich_2021_phase.parquet');
    level = loco.filterTask('level_walking').filterSubject('UM21_AB01');
    
    % Built-in phase plotter (adds mean ± SD)
    level.plotPhasePatterns('UM21_AB01','level_walking',{'knee_flexion_angle_ipsi_rad'});
    
    % Task comparison helper
    level.plotTaskComparison('UM21_AB01', {"level_walking","incline_walking"}, {'knee_flexion_angle_ipsi_rad'});
    ```
    
    </div>

## 4) Cycle Analysis

=== "Raw"
    <div class="code-lang code-lang-python">
    
    ```python
    import pandas as pd
    import numpy as np
    
    df = pd.read_parquet('umich_2021_phase.parquet')
    sub = df[(df['task']=='level_walking') & (df['subject_id']=='UM21_AB01')]
    phase = sub['phase_percent'].to_numpy()
    knee  = sub['knee_flexion_angle_ipsi_rad'].to_numpy()
    
    # ROM for a single stride sequence (example)
    rom = float(np.nanmax(knee) - np.nanmin(knee))
    
    # Peak timing in the cycle
    peak_idx = int(np.nanargmax(knee))
    peak_phase = float(phase[peak_idx])
    print({'rom': rom, 'peak_phase_percent': peak_phase})
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    % Load + filter
    T = parquetread('umich_2021_phase.parquet');
    sub = T(T.task=="level_walking" & T.subject_id=="UM21_AB01", :);
    phase = sub.phase_percent; knee = sub.knee_flexion_angle_ipsi_rad;
    
    % ROM and peak timing
    rom = max(knee) - min(knee);
    [~,peakIdx] = max(knee);
    peakPhase = phase(peakIdx);
    fprintf('ROM=%.3f, Peak at %.2f%%\n', rom, peakPhase);
    ```
    
    </div>

=== "Library"
    <div class="code-lang code-lang-python">
    
    ```python
    from user_libs.python.locomotion_data import LocomotionData
    data = LocomotionData('umich_2021_phase.parquet')
    subset = data.filter(task='level_walking', subjects=['UM21_AB01'])
    
    # Summary statistics and ROM
    stats = subset.get_summary_statistics('UM21_AB01','level_walking')
    rom   = subset.calculate_rom('UM21_AB01','level_walking')
    
    # Outlier cycles based on deviation
    outliers = subset.find_outlier_cycles('UM21_AB01','level_walking', ['knee_flexion_angle_ipsi_rad'])
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    addpath('user_libs/matlab');
    loco = LocomotionData('umich_2021_phase.parquet');
    level = loco.filterTask('level_walking').filterSubject('UM21_AB01');
    
    % Summary statistics and ROM
    stats = level.getSummaryStatistics('UM21_AB01','level_walking');
    rom   = level.calculateROM('UM21_AB01','level_walking');
    
    % Outlier cycles
    outliers = level.findOutlierCycles('UM21_AB01','level_walking', {'knee_flexion_angle_ipsi_rad'});
    ```
    
    </div>

## 5) Group Analysis

=== "Raw"
    <div class="code-lang code-lang-python">
    
    ```python
    import pandas as pd
    import numpy as np
    
    df = pd.read_parquet('umich_2021_phase.parquet')
    subset = df[(df['task']=='level_walking') & (df['subject_id']=='UM21_AB01')]
    
    # Group mean across all cycles of the subset
    mean_knee = subset.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean().to_numpy()
    std_knee  = subset.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].std().to_numpy()
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    T = parquetread('umich_2021_phase.parquet');
    subset = T(T.task=="level_walking" & T.subject_id=="UM21_AB01", :);
    
    % Group mean across all cycles of the subset
    [g,~,idx] = unique(subset.phase_percent);
    mean_knee = splitapply(@mean, subset.knee_flexion_angle_ipsi_rad, idx);
    std_knee  = splitapply(@std,  subset.knee_flexion_angle_ipsi_rad, idx);
    ```
    
    </div>

=== "Library"
    <div class="code-lang code-lang-python">
    
    ```python
    from user_libs.python.locomotion_data import LocomotionData
    data = LocomotionData('umich_2021_phase.parquet')
    subset = data.filter(task='level_walking', subjects=['UM21_AB01'])
    
    mean_patterns = subset.get_mean_patterns('UM21_AB01','level_walking')
    mean_knee = mean_patterns['knee_flexion_angle_ipsi_rad']['mean']
    std_knee  = mean_patterns['knee_flexion_angle_ipsi_rad']['std']
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    addpath('user_libs/matlab');
    loco = LocomotionData('umich_2021_phase.parquet');
    level = loco.filterTask('level_walking').filterSubject('UM21_AB01');
    patterns = level.getMeanPatterns('UM21_AB01','level_walking');
    mean_knee = patterns('knee_flexion_angle_ipsi_rad').mean;
    std_knee  = patterns('knee_flexion_angle_ipsi_rad').std;
    ```
    
    </div>

## 6) Export Figures and Tables

=== "Raw"
    <div class="code-lang code-lang-python">
    
    ```python
    import pandas as pd
    import matplotlib.pyplot as plt
    
    df = pd.read_parquet('umich_2021_phase.parquet')
    sub = df[(df['task']=='level_walking') & (df['subject_id']=='UM21_AB01')]
    phase = sub['phase_percent']; knee = sub['knee_flexion_angle_ipsi_rad']
    
    fig, ax = plt.subplots(figsize=(5,3.5))
    ax.plot(phase, knee, lw=1.8)
    ax.set(xlabel='Gait Cycle (%)', ylabel='Knee Flexion (rad)')
    fig.tight_layout(); fig.savefig('figure.png', dpi=300)
    
    # Export summary table
    summary = sub.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].agg(['mean','std']).reset_index()
    summary.to_csv('summary_knee.csv', index=False)
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    T = parquetread('umich_2021_phase.parquet');
    sub = T(T.task=="level_walking" & T.subject_id=="UM21_AB01", :);
    phase = sub.phase_percent; knee = sub.knee_flexion_angle_ipsi_rad;
    set(gcf,'Position',[100,100,520,360]);
    plot(phase, knee, 'LineWidth',1.8);
    xlabel('Gait Cycle (%)'); ylabel('Knee Flexion (rad)'); grid on;
    print('-dpng','-r300','figure.png');
    
    % Export summary table
    [g,~,idx] = unique(sub.phase_percent);
    mean_knee = splitapply(@mean, sub.knee_flexion_angle_ipsi_rad, idx);
    std_knee  = splitapply(@std,  sub.knee_flexion_angle_ipsi_rad, idx);
    summary = table(g, mean_knee, std_knee, 'VariableNames',{'phase_percent','mean','std'});
    writetable(summary, 'summary_knee.csv');
    ```
    
    </div>

=== "Library"
    <div class="code-lang code-lang-python">
    
    ```python
    # Library plotting exists, but fine-grained figure control is often easier with raw plotting.
    from user_libs.python.locomotion_data import LocomotionData
    data = LocomotionData('umich_2021_phase.parquet')
    subset = data.filter(task='level_walking', subjects=['UM21_AB01'])
    stats = subset.get_summary_statistics('UM21_AB01','level_walking')
    
    # Export stats
    import pandas as pd
    pd.DataFrame(stats).to_csv('summary_stats.csv', index=False)
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    % Use library for quick stats export
    addpath('user_libs/matlab');
    loco = LocomotionData('umich_2021_phase.parquet');
    level = loco.filterTask('level_walking').filterSubject('UM21_AB01');
    stats = level.getSummaryStatistics('UM21_AB01','level_walking');
    % Convert to table and save as needed
    ```
    
    </div>

## References

- Data schema: [What the data looks like](../index.md#what-the-data-looks-like)
- Specs: [Technical Specification](../../reference/standard_spec/standard_spec.md)
