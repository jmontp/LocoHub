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
    df = pd.read_parquet('umich_2021_phase.parquet')
    subset = df[(df['task'] == 'level_walking') & (df['subject_id'] == 'UM21_AB01')]
    phase = subset['phase_percent'].to_numpy()
    knee  = subset['knee_flexion_angle_ipsi_rad'].to_numpy()
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    T = parquetread('umich_2021_phase.parquet');
    subset = T(T.task == "level_walking" & T.subject_id == "UM21_AB01", :);
    phase = subset.phase_percent;
    knee  = subset.knee_flexion_angle_ipsi_rad;
    ```
    
    </div>

=== "Library"
    <div class="code-lang code-lang-python">
    
    ```python
    from user_libs.python.locomotion_data import LocomotionData
    data = LocomotionData('umich_2021_phase.parquet')
    subset = data.filter(task='level_walking', subjects=['UM21_AB01'])
    cycles, features = subset.get_cycles('UM21_AB01', 'level_walking')
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    addpath('user_libs/matlab');
    loco  = LocomotionData('umich_2021_phase.parquet');
    level = loco.filterTask('level_walking').filterSubject('UM21_AB01');
    [cycles, features] = level.getCycles('UM21_AB01', 'level_walking');
    ```
    
    </div>

## 2) Filter / Subset

=== "Raw"
    <div class="code-lang code-lang-python">
    
    ```python
    # by subject, task, and columns
    cols = ['subject_id','task','phase_percent','knee_flexion_angle_ipsi_rad']
    subset = df.loc[(df.task=='level_walking') & (df.subject_id=='UM21_AB01'), cols]
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    cols = {'subject_id','task','phase_percent','knee_flexion_angle_ipsi_rad'};
    mask = T.task=="level_walking" & T.subject_id=="UM21_AB01";
    subset = T(mask, cols);
    ```
    
    </div>

=== "Library"
    <div class="code-lang code-lang-python">
    
    ```python
    subset = data.filter(task='level_walking', subjects=['UM21_AB01'],
                         features=['knee_flexion_angle_ipsi_rad'])
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    subset = level.selectFeatures({'knee_flexion_angle_ipsi_rad'});
    ```
    
    </div>

## 3) Visualize

=== "Raw"
    <div class="code-lang code-lang-python">
    
    ```python
    import matplotlib.pyplot as plt
    plt.plot(phase, knee)
    plt.xlabel('Gait Cycle (%)'); plt.ylabel('Knee Flexion (rad)'); plt.show()
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    plot(phase, knee);
    xlabel('Gait Cycle (%)'); ylabel('Knee Flexion (rad)'); grid on;
    ```
    
    </div>

=== "Library"
    <div class="code-lang code-lang-python">
    
    ```python
    subset.plot_phase_patterns('UM21_AB01','level_walking',['knee_flexion_angle_ipsi_rad'])
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    level.plotPhasePatterns('UM21_AB01','level_walking',{'knee_flexion_angle_ipsi_rad'});
    ```
    
    </div>

## 4) Cycle Analysis

=== "Raw"
    <div class="code-lang code-lang-python">
    
    ```python
    # group by stride (if available) or compute peaks on subset
    rom = knee.max() - knee.min()
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    rom = max(knee) - min(knee);
    ```
    
    </div>

=== "Library"
    <div class="code-lang code-lang-python">
    
    ```python
    stats = subset.get_summary_statistics('UM21_AB01','level_walking')
    rom   = subset.calculate_rom('UM21_AB01','level_walking')
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    stats = level.getSummaryStatistics('UM21_AB01','level_walking');
    rom   = level.calculateROM('UM21_AB01','level_walking');
    ```
    
    </div>

## 5) Group Analysis

=== "Raw"
    <div class="code-lang code-lang-python">
    
    ```python
    import numpy as np
    mean_knee = subset.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean().to_numpy()
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    [g,~,idx] = unique(subset.phase_percent);
    mean_knee = splitapply(@mean, subset.knee_flexion_angle_ipsi_rad, idx);
    ```
    
    </div>

=== "Library"
    <div class="code-lang code-lang-python">
    
    ```python
    mean_patterns = subset.get_mean_patterns('UM21_AB01','level_walking')
    mean_knee = mean_patterns['knee_flexion_angle_ipsi_rad']
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    patterns = level.getMeanPatterns('UM21_AB01','level_walking');
    mean_knee = patterns('knee_flexion_angle_ipsi_rad');
    ```
    
    </div>

## 6) Publication Outputs

=== "Raw"
    <div class="code-lang code-lang-python">
    
    ```python
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4,3)); ax.plot(phase, knee); fig.savefig('figure.png', dpi=300)
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    set(gcf,'Position',[100,100,500,350]); print('-dpng','-r300','figure.png');
    ```
    
    </div>

=== "Library"
    <div class="code-lang code-lang-python">
    
    ```python
    subset.plot_phase_patterns('UM21_AB01','level_walking',['knee_flexion_angle_ipsi_rad'], save_path='figure.png')
    ```
    
    </div>
    <div class="code-lang code-lang-matlab">
    
    ```matlab
    level.plotPhasePatterns('UM21_AB01','level_walking',{'knee_flexion_angle_ipsi_rad'}, 'SavePath','figure.png');
    ```
    
    </div>

## References

- Data schema: [What the data looks like](../index.md#what-the-data-looks-like)
- Specs: [Technical Specification](../../reference/standard_spec/standard_spec.md)
