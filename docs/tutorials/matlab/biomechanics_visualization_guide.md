# Biomechanics Visualization Guide - MATLAB

**Publication-ready ggplot2-style visualization system for locomotion data**

Created: 2025-06-19  
Purpose: Comprehensive guide to the enhanced MATLAB visualization system

## Overview

The biomechanics visualization system provides publication-quality plots with ggplot2-inspired design principles, specifically tailored for locomotion research. It includes biomechanics-specific themes, colorblind-friendly palettes, advanced statistical visualization, and export capabilities optimized for scientific publication.

## Key Features

- **Publication-ready themes**: Publication, presentation, and manuscript styles
- **Colorblind-friendly palettes**: Optimized for joint, task, and subject data
- **Advanced plot types**: Mean patterns, confidence bands, spaghetti plots, ribbon plots
- **Statistical annotations**: Confidence intervals, phase markers, outlier detection
- **Multi-format export**: PNG, PDF, EPS, SVG with proper DPI settings
- **Population analysis**: Group comparisons with statistical overlays

## Quick Start

```matlab
% Load data
loco = LocomotionData('your_data.parquet');

% Basic phase pattern plot
fig = loco.plotPhasePatterns_v2('SUB01', 'normal_walk', {'knee_flexion_angle_ipsi_rad'});

% Task comparison
fig = loco.plotTaskComparison_v2('SUB01', {'normal_walk', 'fast_walk'}, ...
                                 {'knee_flexion_angle_ipsi_rad'});

% Population analysis
fig = loco.plotSubjectComparison_v2({'SUB01', 'SUB02', 'SUB03'}, 'normal_walk', ...
                                    {'knee_flexion_angle_ipsi_rad'});
```

## Detailed Usage

### 1. Theme System

The visualization system provides three publication-ready themes:

#### Publication Theme (Default)
```matlab
theme = getBiomechTheme('Style', 'publication');
% Features: Arial font, moderate sizing, clean appearance
```

#### Presentation Theme
```matlab
theme = getBiomechTheme('Style', 'presentation');
% Features: Larger fonts, bold labels, high contrast
```

#### Manuscript Theme
```matlab
theme = getBiomechTheme('Style', 'manuscript');
% Features: Times New Roman, compact sizing, journal-ready
```

### 2. Color Palettes

#### Joint-Specific Colors
```matlab
colors = getBiomechColors('Palette', 'joints');
% Optimized for hip-knee-ankle visualization
% Hip: Orange, Knee: Blue, Ankle: Green
```

#### Task-Specific Colors
```matlab
colors = getBiomechColors('Palette', 'tasks');
% Different colors for locomotor tasks
% Normal walk: Blue, Fast walk: Green, Incline: Orange, etc.
```

#### Subject/Population Colors
```matlab
colors = getBiomechColors('Palette', 'subjects');
% Qualitative palette for multiple subjects
% 8 distinct, colorblind-friendly colors
```

### 3. Phase Pattern Visualization

#### Basic Phase Patterns
```matlab
fig = loco.plotPhasePatterns_v2(subject, task, features, ...
    'PlotType', 'both', ...           % 'mean', 'spaghetti', 'both', 'ribbon'
    'Theme', 'publication', ...       % Theme style
    'Colors', 'joints');              % Color palette
```

#### Advanced Options
```matlab
fig = loco.plotPhasePatterns_v2(subject, task, features, ...
    'PlotType', 'ribbon', ...         % Confidence ribbon plot
    'ConfidenceLevel', 0.95, ...      % 95% confidence intervals
    'ShowInvalid', true, ...          % Show outlier cycles
    'AddPhaseLines', true, ...        % Add stance/swing markers
    'SavePath', 'knee_analysis', ...  % Auto-save
    'ExportFormat', {{'png', 'pdf'}}); % Multiple formats
```

#### Plot Type Options

**Mean Plot**: Shows mean pattern with confidence bands
```matlab
'PlotType', 'mean'
```

**Spaghetti Plot**: Shows all individual cycles
```matlab
'PlotType', 'spaghetti'
```

**Combined Plot**: Individual cycles + mean overlay
```matlab
'PlotType', 'both'
```

**Ribbon Plot**: Mean with statistical confidence bands
```matlab
'PlotType', 'ribbon'
```

### 4. Task Comparison Analysis

#### Basic Task Comparison
```matlab
tasks = {'normal_walk', 'fast_walk', 'incline_walk'};
fig = loco.plotTaskComparison_v2(subject, tasks, features, ...
    'ShowConfidence', true, ...       % Show confidence bands
    'ConfidenceLevel', 0.95);         % Statistical level
```

#### Advanced Task Analysis
```matlab
fig = loco.plotTaskComparison_v2(subject, tasks, features, ...
    'Theme', 'publication', ...
    'Colors', 'tasks', ...
    'AddPhaseLines', true, ...        % Stance/swing markers
    'SavePath', 'task_comparison');
```

### 5. Population/Group Analysis

#### Simple Population Analysis
```matlab
subjects = {'SUB01', 'SUB02', 'SUB03', 'SUB04', 'SUB05'};
fig = loco.plotSubjectComparison_v2(subjects, task, features, ...
    'ShowIndividuals', false);        % Only show group statistics
```

#### Group Comparison
```matlab
% Prepare group data
groupData = table({'SUB01'; 'SUB02'; 'SUB03'; 'SUB04'}, ...
                  {'Control'; 'Control'; 'Patient'; 'Patient'}, ...
                  'VariableNames', {'subject', 'group'});

fig = loco.plotSubjectComparison_v2(subjects, task, features, ...
    'GroupBy', 'group', ...           % Group by variable
    'GroupData', groupData, ...       % Grouping table
    'ShowIndividuals', true);         % Show individual subjects
```

### 6. Publication Figure Templates

#### Multi-Panel Figure Specification
```matlab
% Define figure layout
figSpec.layout = [2, 2];             % 2x2 grid
figSpec.title = 'Comprehensive Gait Analysis';

% Panel A: Phase patterns
figSpec.panels{1} = struct( ...
    'type', 'phase_patterns', ...
    'position', 1, ...
    'subject', 'SUB01', ...
    'task', 'normal_walk', ...
    'features', {{'knee_flexion_angle_ipsi_rad'}}, ...
    'label', 'A', ...
    'options', struct('PlotType', 'both'));

% Panel B: Task comparison
figSpec.panels{2} = struct( ...
    'type', 'task_comparison', ...
    'position', 2, ...
    'subject', 'SUB01', ...
    'tasks', {{'normal_walk', 'fast_walk'}}, ...
    'features', {{'knee_flexion_angle_ipsi_rad'}}, ...
    'label', 'B');

% Panel C: Population analysis
figSpec.panels{3} = struct( ...
    'type', 'subject_comparison', ...
    'position', 3, ...
    'subjects', {{'SUB01', 'SUB02', 'SUB03'}}, ...
    'task', 'normal_walk', ...
    'features', {{'knee_flexion_angle_ipsi_rad'}}, ...
    'label', 'C');

% Panel D: ROM comparison
figSpec.panels{4} = struct( ...
    'type', 'rom_comparison', ...
    'position', 4, ...
    'subjects', {{'SUB01', 'SUB02', 'SUB03'}}, ...
    'task', 'normal_walk', ...
    'features', {{'hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad'}}, ...
    'label', 'D');

% Create publication figure
fig = loco.createPublicationFigure_v2(figSpec, ...
    'Size', 'double', ...             % 'single', 'double', 'full'
    'SavePath', 'publication_fig', ...
    'ExportFormat', {{'png', 'pdf', 'eps'}});
```

### 7. Export System

#### Basic Export
```matlab
loco.exportFigure_v2(fig, 'my_figure');
% Exports: my_figure.png, my_figure.pdf
```

#### Advanced Export Options
```matlab
loco.exportFigure_v2(fig, 'my_figure', ...
    'Format', {{'png', 'pdf', 'eps', 'svg'}}, ...  % Multiple formats
    'DPI', 600);                                    % High resolution
```

#### Export Format Guidelines

**PNG**: Web display, presentations (300 DPI default)
```matlab
'Format', {'png'}, 'DPI', 300
```

**PDF**: Publications, vector graphics
```matlab
'Format', {'pdf'}
```

**EPS**: Journal submission, vector with preview
```matlab
'Format', {'eps'}
```

**SVG**: Web graphics, scalable vector
```matlab
'Format', {'svg'}
```

**TIFF**: High-quality print
```matlab
'Format', {'tiff'}, 'DPI', 600
```

## Advanced Features

### 1. Custom Color Schemes

```matlab
% Define custom colors
customColors = struct();
customColors.primary = [0.2, 0.4, 0.8];
customColors.secondary = [0.8, 0.2, 0.2];
customColors.tertiary = [0.2, 0.8, 0.2];

% Apply to existing figure
applyBiomechTheme(fig, theme);
```

### 2. Statistical Annotations

#### Confidence Intervals
```matlab
% Calculate and plot confidence bands
[lowerBand, upperBand] = calculateConfidenceBands(data, 0.95);
```

#### Phase Markers
```matlab
% Add stance/swing phase annotations
addPhaseAnnotations(gca, [0.5, 0.5, 0.5]);
```

### 3. Accessibility Features

All color palettes are colorblind-friendly using ColorBrewer and Viridis-inspired schemes:

- **Protanopia/Deuteranopia safe**: Red-green colorblind friendly
- **Tritanopia safe**: Blue-yellow colorblind friendly  
- **High contrast**: Sufficient contrast ratios for accessibility
- **Print friendly**: Works in grayscale printing

## Best Practices

### 1. Publication Standards

```matlab
% For journal submission
fig = loco.plotPhasePatterns_v2(subject, task, features, ...
    'Theme', 'manuscript', ...        % Journal-appropriate theme
    'PlotType', 'ribbon', ...         % Statistical visualization
    'ConfidenceLevel', 0.95, ...      % Standard confidence level
    'ExportFormat', {{'pdf', 'eps'}}); % Vector formats
```

### 2. Presentation Graphics

```matlab
% For conference presentations
fig = loco.plotPhasePatterns_v2(subject, task, features, ...
    'Theme', 'presentation', ...      % Large fonts, high contrast
    'Colors', 'joints', ...           % Clear color distinction
    'ExportFormat', {{'png'}}, ...    % Raster for slides
    'DPI', 300);                      % High resolution
```

### 3. Web/Digital Display

```matlab
% For web or digital display
fig = loco.plotPhasePatterns_v2(subject, task, features, ...
    'Theme', 'publication', ...
    'ExportFormat', {{'png', 'svg'}}); % Web-friendly formats
```

## Troubleshooting

### Common Issues

#### 1. Missing Data
```matlab
% Check data availability
[data3D, features] = loco.getCycles(subject, task, features);
if isempty(data3D)
    fprintf('No data found for %s - %s\n', subject, task);
end
```

#### 2. Export Errors
```matlab
% Verify export path is writable
if ~exist(fileparts(savePath), 'dir')
    mkdir(fileparts(savePath));
end
```

#### 3. Theme Not Applied
```matlab
% Manually apply theme to existing figure
theme = getBiomechTheme('Style', 'publication');
applyBiomechTheme(gcf, theme);
```

### Performance Tips

1. **Cache data**: Use LocomotionData caching for repeated plots
2. **Vectorize operations**: Avoid loops in plotting code
3. **Limit export formats**: Only export needed formats
4. **Close figures**: Use `close all` to free memory

## Examples Gallery

### Example 1: Single Subject Analysis
```matlab
% Load data
loco = LocomotionData('subject_data.parquet');

% Create comprehensive analysis
features = {'hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad', 'ankle_flexion_angle_ipsi_rad'};

% Phase patterns
fig1 = loco.plotPhasePatterns_v2('SUB01', 'normal_walk', features, ...
    'PlotType', 'both', 'SavePath', 'subject01_patterns');

% Task comparison
tasks = {'normal_walk', 'fast_walk', 'slow_walk'};
fig2 = loco.plotTaskComparison_v2('SUB01', tasks, {'knee_flexion_angle_ipsi_rad'}, ...
    'SavePath', 'subject01_tasks');
```

### Example 2: Population Study
```matlab
% Population analysis
subjects = {'SUB01', 'SUB02', 'SUB03', 'SUB04', 'SUB05'};
fig = loco.plotSubjectComparison_v2(subjects, 'normal_walk', ...
    {'knee_flexion_angle_ipsi_rad'}, ...
    'ShowIndividuals', true, ...
    'SavePath', 'population_knee_analysis');
```

### Example 3: Publication Figure
```matlab
% Multi-panel publication figure
figSpec = createPublicationSpec('SUB01', subjects, tasks, features);
fig = loco.createPublicationFigure_v2(figSpec, ...
    'Size', 'double', ...
    'SavePath', 'figure_1', ...
    'ExportFormat', {{'png', 'pdf', 'eps'}});
```

## Integration with Existing Code

The visualization system is fully compatible with existing LocomotionData methods:

```matlab
% Use existing methods for data access
[data3D, features] = loco.getCycles(subject, task, features);
validMask = loco.validateCycles(subject, task, features);
meanPatterns = loco.getMeanPatterns(subject, task, features);
summary = loco.getSummaryStatistics(subject, task, features);

% Combine with new visualization
fig = loco.plotPhasePatterns_v2(subject, task, features);
```

## API Reference

### Main Functions

- `plotPhasePatterns_v2()` - Enhanced phase pattern visualization
- `plotTaskComparison_v2()` - Advanced task comparison plots  
- `plotSubjectComparison_v2()` - Population/group analysis
- `createPublicationFigure_v2()` - Multi-panel publication figures
- `exportFigure_v2()` - Publication-quality export

### Theme Functions

- `getBiomechTheme()` - Get theme settings
- `getBiomechColors()` - Get color palettes
- `applyBiomechTheme()` - Apply theme to figure

### Utility Functions

- `exportFigure()` - Multi-format export
- `addPhaseAnnotations()` - Add phase markers
- `calculateConfidenceBands()` - Statistical confidence intervals
- `formatFeatureName()` - Format display names
- `formatTaskName()` - Format task names

## Additional Resources

- [MATLAB LocomotionData Documentation](../getting_started_matlab.md)
- [Visualization Best Practices](../../reference/visualization_guidelines.md)
- [Color Accessibility Guidelines](../../reference/accessibility_standards.md)
- [Publication Requirements](../../reference/publication_standards.md)

---

*For questions or suggestions regarding the visualization system, please refer to the project documentation or contact the development team.*