# Working with Data

Advanced techniques for analyzing standardized locomotion datasets efficiently and effectively.

## Memory-Efficient Data Loading

Large datasets require careful memory management:

=== "Python"

    ```python
    import pandas as pd
    import numpy as np
    
    # For large datasets, load specific columns only
    columns_of_interest = [
        'subject', 'task', 'step', 'phase_percent',
        'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'
    ]
    
    data = pd.read_parquet('large_dataset.parquet', columns=columns_of_interest)
    
    # Use chunked processing for very large datasets
    def process_in_chunks(filepath, chunk_size=10000):
        """Process large dataset in manageable chunks."""
        results = []
        
        # Read parquet in chunks (requires pyarrow)
        parquet_file = pd.read_parquet(filepath, engine='pyarrow')
        
        for i in range(0, len(parquet_file), chunk_size):
            chunk = parquet_file.iloc[i:i+chunk_size]
            
            # Process chunk
            processed_chunk = chunk.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
            results.append(processed_chunk)
            
            print(f"Processed chunk {i//chunk_size + 1}")
        
        # Combine results
        return pd.concat(results).groupby(level=0).mean()
    
    # Use efficient data types
    def optimize_dtypes(df):
        """Optimize dataframe memory usage."""
        for col in df.columns:
            if df[col].dtype == 'object':
                # Convert string columns to category if appropriate
                if df[col].nunique() / len(df) < 0.5:
                    df[col] = df[col].astype('category')
            elif df[col].dtype == 'float64':
                # Downcast float precision if possible
                if (df[col] >= np.finfo(np.float32).min).all() and \
                   (df[col] <= np.finfo(np.float32).max).all():
                    df[col] = df[col].astype(np.float32)
        
        return df
    ```

=== "MATLAB"

    ```matlab
    % For large datasets, use efficient reading strategies
    
    % Read only specific variables
    opts = detectImportOptions('large_dataset.parquet');
    vars_to_read = {'subject', 'task', 'step', 'phase_percent', ...
                    'knee_flexion_angle_ipsi_rad', 'hip_flexion_angle_ipsi_rad'};
    opts = setvaropts(opts, setdiff(opts.VariableNames, vars_to_read), 'Type', 'char');
    
    data = readtable('large_dataset.parquet', opts);
    
    % Process in chunks for very large files
    function result = processInChunks(filepath, chunkSize)
        % Process large dataset in manageable chunks
        info = parquetinfo(filepath);
        totalRows = info.NumRows;
        
        results = {};
        chunkCount = 1;
        
        for startRow = 1:chunkSize:totalRows
            endRow = min(startRow + chunkSize - 1, totalRows);
            
            % Read chunk
            chunk = parquetread(filepath, 'RowIndices', startRow:endRow);
            
            % Process chunk
            processedChunk = groupsummary(chunk, 'phase_percent', 'mean', 'knee_flexion_angle_ipsi_rad');
            results{chunkCount} = processedChunk;
            
            fprintf('Processed chunk %d\n', chunkCount);
            chunkCount = chunkCount + 1;
        end
        
        % Combine results
        combined = vertcat(results{:});
        result = groupsummary(combined, 'phase_percent', 'mean', 'mean_knee_flexion_angle_ipsi_rad');
    end
    
    % Optimize memory usage
    function optimizedData = optimizeTable(data)
        % Convert string columns to categorical where appropriate
        for i = 1:width(data)
            if iscell(data{:,i}) || isstring(data{:,i})
                uniqueRatio = height(unique(data(:,i))) / height(data);
                if uniqueRatio < 0.5
                    data{:,i} = categorical(data{:,i});
                end
            end
        end
        optimizedData = data;
    end
    ```

## Advanced Filtering and Selection

Complex data filtering for specific research questions:

=== "Python"

    ```python
    # Complex filtering examples
    
    # 1. Multiple condition filtering
    filtered_data = data[
        (data['task'].isin(['level_walking', 'incline_walking'])) &
        (data['subject'].str.startswith('SUB')) &
        (data['phase_percent'].between(0, 60))  # Stance phase only
    ]
    
    # 2. Statistical outlier removal
    def remove_outliers(group, column, n_std=3):
        """Remove statistical outliers from a group."""
        mean_val = group[column].mean()
        std_val = group[column].std()
        
        outlier_mask = np.abs(group[column] - mean_val) > n_std * std_val
        return group[~outlier_mask]
    
    # Apply outlier removal by subject and task
    clean_data = data.groupby(['subject', 'task']).apply(
        lambda x: remove_outliers(x, 'knee_flexion_angle_ipsi_rad')
    ).reset_index(drop=True)
    
    # 3. Dynamic phase selection
    def select_gait_events(data, event_phase_ranges):
        """Select specific gait events based on phase ranges."""
        selected_data = pd.DataFrame()
        
        for event_name, (start_phase, end_phase) in event_phase_ranges.items():
            event_data = data[
                (data['phase_percent'] >= start_phase) & 
                (data['phase_percent'] <= end_phase)
            ].copy()
            event_data['gait_event'] = event_name
            selected_data = pd.concat([selected_data, event_data])
        
        return selected_data
    
    # Example: Select key gait events
    gait_events = {
        'heel_strike': (0, 5),
        'mid_stance': (10, 30),
        'toe_off': (55, 65),
        'mid_swing': (70, 85)
    }
    
    event_data = select_gait_events(data, gait_events)
    
    # 4. Quality-based filtering
    def filter_by_quality(data, quality_criteria):
        """Filter data based on multiple quality criteria."""
        quality_mask = pd.Series(True, index=data.index)
        
        for criterion, (column, min_val, max_val) in quality_criteria.items():
            if column in data.columns:
                quality_mask &= data[column].between(min_val, max_val)
        
        return data[quality_mask]
    
    # Example quality criteria
    quality_criteria = {
        'knee_range': ('knee_flexion_angle_ipsi_rad', np.radians(-10), np.radians(120)),
        'hip_range': ('hip_flexion_angle_ipsi_rad', np.radians(-30), np.radians(90)),
        'phase_completeness': ('phase_percent', 0, 100)
    }
    
    high_quality_data = filter_by_quality(data, quality_criteria)
    ```

=== "MATLAB"

    ```matlab
    % Complex filtering examples
    
    % 1. Multiple condition filtering
    task_mask = ismember(data.task, {'level_walking', 'incline_walking'});
    subject_mask = startsWith(data.subject, 'SUB');
    phase_mask = data.phase_percent >= 0 & data.phase_percent <= 60;
    
    filtered_data = data(task_mask & subject_mask & phase_mask, :);
    
    % 2. Statistical outlier removal
    function clean_data = removeOutliers(data, column, n_std)
        if nargin < 3
            n_std = 3;
        end
        
        % Group by subject and task
        [groups, subjects, tasks] = findgroups(data.subject, data.task);
        
        outlier_mask = false(height(data), 1);
        
        for i = 1:max(groups)
            group_mask = groups == i;
            group_data = data.(column)(group_mask);
            
            mean_val = mean(group_data);
            std_val = std(group_data);
            
            group_outliers = abs(group_data - mean_val) > n_std * std_val;
            outlier_mask(group_mask) = group_outliers;
        end
        
        clean_data = data(~outlier_mask, :);
    end
    
    clean_data = removeOutliers(data, 'knee_flexion_angle_ipsi_rad');
    
    % 3. Dynamic phase selection
    function event_data = selectGaitEvents(data, event_ranges)
        event_data = table();
        
        event_names = fieldnames(event_ranges);
        for i = 1:length(event_names)
            event_name = event_names{i};
            phase_range = event_ranges.(event_name);
            
            event_mask = data.phase_percent >= phase_range(1) & ...
                        data.phase_percent <= phase_range(2);
            
            temp_data = data(event_mask, :);
            temp_data.gait_event = repmat({event_name}, height(temp_data), 1);
            
            event_data = [event_data; temp_data];
        end
    end
    
    % Example: Select key gait events
    gait_events.heel_strike = [0, 5];
    gait_events.mid_stance = [10, 30];
    gait_events.toe_off = [55, 65];
    gait_events.mid_swing = [70, 85];
    
    event_data = selectGaitEvents(data, gait_events);
    
    % 4. Quality-based filtering
    function high_quality_data = filterByQuality(data, quality_criteria)
        quality_mask = true(height(data), 1);
        
        field_names = fieldnames(quality_criteria);
        for i = 1:length(field_names)
            criterion = field_names{i};
            column = quality_criteria.(criterion).column;
            min_val = quality_criteria.(criterion).min_val;
            max_val = quality_criteria.(criterion).max_val;
            
            if any(strcmp(data.Properties.VariableNames, column))
                quality_mask = quality_mask & ...
                    (data.(column) >= min_val) & (data.(column) <= max_val);
            end
        end
        
        high_quality_data = data(quality_mask, :);
    end
    
    % Example quality criteria
    quality_criteria.knee_range.column = 'knee_flexion_angle_ipsi_rad';
    quality_criteria.knee_range.min_val = deg2rad(-10);
    quality_criteria.knee_range.max_val = deg2rad(120);
    
    quality_criteria.hip_range.column = 'hip_flexion_angle_ipsi_rad';
    quality_criteria.hip_range.min_val = deg2rad(-30);
    quality_criteria.hip_range.max_val = deg2rad(90);
    
    high_quality_data = filterByQuality(data, quality_criteria);
    ```

## Time Series Analysis

Advanced techniques for temporal analysis:

=== "Python"

    ```python
    from scipy import signal
    from scipy.fft import fft, fftfreq
    
    # 1. Smoothing and filtering
    def smooth_gait_data(data, method='savgol', **kwargs):
        """Apply smoothing to gait data."""
        if method == 'savgol':
            window_length = kwargs.get('window_length', 15)
            polyorder = kwargs.get('polyorder', 3)
            return signal.savgol_filter(data, window_length, polyorder)
        
        elif method == 'gaussian':
            sigma = kwargs.get('sigma', 2)
            return scipy.ndimage.gaussian_filter1d(data, sigma)
        
        elif method == 'moving_average':
            window = kwargs.get('window', 10)
            return data.rolling(window=window, center=True).mean()
    
    # Apply smoothing to each gait cycle
    smoothed_data = data.copy()
    for (subject, task, step), group in data.groupby(['subject', 'task', 'step']):
        mask = (data['subject'] == subject) & (data['task'] == task) & (data['step'] == step)
        
        smoothed_knee = smooth_gait_data(
            group['knee_flexion_angle_ipsi_rad'].values,
            method='savgol', window_length=15, polyorder=3
        )
        
        smoothed_data.loc[mask, 'knee_flexion_angle_ipsi_rad_smooth'] = smoothed_knee
    
    # 2. Gait cycle variability analysis
    def calculate_variability_metrics(data, variable):
        """Calculate various measures of gait variability."""
        cycles = []
        
        for (subject, task, step), group in data.groupby(['subject', 'task', 'step']):
            cycle_data = group.sort_values('phase_percent')[variable].values
            cycles.append(cycle_data)
        
        cycles_array = np.array(cycles)
        
        # Calculate metrics
        metrics = {
            'mean_pattern': np.mean(cycles_array, axis=0),
            'std_pattern': np.std(cycles_array, axis=0),
            'cv_pattern': np.std(cycles_array, axis=0) / np.abs(np.mean(cycles_array, axis=0)),
            'coefficient_of_variation': np.mean(np.std(cycles_array, axis=0) / np.abs(np.mean(cycles_array, axis=0))),
            'range_of_motion_variability': np.std([np.ptp(cycle) for cycle in cycles]),
            'peak_timing_variability': np.std([np.argmax(cycle) for cycle in cycles])
        }
        
        return metrics
    
    # Calculate variability for knee angle
    knee_variability = calculate_variability_metrics(data, 'knee_flexion_angle_ipsi_rad')
    
    # 3. Frequency domain analysis
    def analyze_frequency_content(cycle_data, sampling_rate=150):
        """Analyze frequency content of gait cycles."""
        # Apply FFT to each cycle
        fft_results = []
        
        for cycle in cycle_data:
            fft_result = fft(cycle)
            fft_results.append(np.abs(fft_result))
        
        # Average frequency spectrum
        avg_spectrum = np.mean(fft_results, axis=0)
        freqs = fftfreq(len(cycle_data[0]), 1/sampling_rate)
        
        # Find dominant frequencies
        positive_freqs = freqs[:len(freqs)//2]
        positive_spectrum = avg_spectrum[:len(avg_spectrum)//2]
        
        dominant_freq_idx = np.argmax(positive_spectrum[1:]) + 1  # Skip DC component
        dominant_frequency = positive_freqs[dominant_freq_idx]
        
        return {
            'frequencies': positive_freqs,
            'spectrum': positive_spectrum,
            'dominant_frequency': dominant_frequency,
            'spectral_centroid': np.sum(positive_freqs * positive_spectrum) / np.sum(positive_spectrum)
        }
    
    # 4. Cross-correlation analysis
    def calculate_joint_coordination(data, joint1_var, joint2_var):
        """Calculate coordination between joints using cross-correlation."""
        coordination_results = []
        
        for (subject, task, step), group in data.groupby(['subject', 'task', 'step']):
            joint1_data = group.sort_values('phase_percent')[joint1_var].values
            joint2_data = group.sort_values('phase_percent')[joint2_var].values
            
            # Calculate cross-correlation
            correlation = signal.correlate(joint1_data, joint2_data, mode='full')
            lags = signal.correlation_lags(len(joint1_data), len(joint2_data), mode='full')
            
            # Find peak correlation and lag
            max_corr_idx = np.argmax(np.abs(correlation))
            max_correlation = correlation[max_corr_idx]
            lag_at_max_corr = lags[max_corr_idx]
            
            coordination_results.append({
                'subject': subject,
                'task': task,
                'step': step,
                'max_correlation': max_correlation,
                'lag_at_max_correlation': lag_at_max_corr,
                'phase_lag_percent': (lag_at_max_corr / len(joint1_data)) * 100
            })
        
        return pd.DataFrame(coordination_results)
    
    # Example: Hip-knee coordination
    hip_knee_coord = calculate_joint_coordination(
        data, 'hip_flexion_angle_ipsi_rad', 'knee_flexion_angle_ipsi_rad'
    )
    ```

=== "MATLAB"

    ```matlab
    % Time series analysis functions
    
    % 1. Smoothing and filtering
    function smoothed_data = smoothGaitData(data, method, varargin)
        switch method
            case 'savgol'
                p = inputParser;
                addParameter(p, 'WindowLength', 15, @isnumeric);
                addParameter(p, 'PolynomialOrder', 3, @isnumeric);
                parse(p, varargin{:});
                
                smoothed_data = sgolayfilt(data, p.Results.PolynomialOrder, p.Results.WindowLength);
                
            case 'gaussian'
                p = inputParser;
                addParameter(p, 'Sigma', 2, @isnumeric);
                parse(p, varargin{:});
                
                % Create Gaussian kernel
                kernel_size = ceil(6 * p.Results.Sigma);
                x = -kernel_size:kernel_size;
                kernel = exp(-x.^2 / (2 * p.Results.Sigma^2));
                kernel = kernel / sum(kernel);
                
                smoothed_data = conv(data, kernel, 'same');
                
            case 'moving_average'
                p = inputParser;
                addParameter(p, 'Window', 10, @isnumeric);
                parse(p, varargin{:});
                
                smoothed_data = movmean(data, p.Results.Window);
        end
    end
    
    % Apply smoothing to dataset
    smoothed_table = data;
    [groups, subjects, tasks, steps] = findgroups(data.subject, data.task, data.step);
    
    smoothed_knee = splitapply(@(x) smoothGaitData(x, 'savgol', 'WindowLength', 15), ...
        data.knee_flexion_angle_ipsi_rad, groups);
    
    % Reconstruct smoothed data
    smoothed_table.knee_flexion_angle_ipsi_rad_smooth = smoothed_knee;
    
    % 2. Gait cycle variability analysis
    function metrics = calculateVariabilityMetrics(data, variable)
        [groups, ~] = findgroups(data.subject, data.task, data.step);
        cycles = splitapply(@(phase, var) var(phase == sort(unique(phase))), ...
            data.phase_percent, data.(variable), groups);
        
        cycles_matrix = cell2mat(cycles');
        
        metrics.mean_pattern = mean(cycles_matrix, 1);
        metrics.std_pattern = std(cycles_matrix, 0, 1);
        metrics.cv_pattern = std(cycles_matrix, 0, 1) ./ abs(mean(cycles_matrix, 1));
        metrics.coefficient_of_variation = mean(metrics.cv_pattern);
        metrics.range_of_motion_variability = std(range(cycles_matrix, 2));
        
        % Peak timing variability
        [~, peak_indices] = max(cycles_matrix, [], 2);
        metrics.peak_timing_variability = std(peak_indices);
    end
    
    % 3. Frequency domain analysis
    function freq_analysis = analyzeFrequencyContent(cycle_data, sampling_rate)
        if nargin < 2
            sampling_rate = 150;
        end
        
        % Apply FFT to each cycle
        fft_results = zeros(size(cycle_data));
        for i = 1:size(cycle_data, 1)
            fft_results(i, :) = abs(fft(cycle_data(i, :)));
        end
        
        % Average frequency spectrum
        avg_spectrum = mean(fft_results, 1);
        freqs = 0:(sampling_rate/length(avg_spectrum)):(sampling_rate/2);
        
        % Keep positive frequencies only
        n_pos = floor(length(avg_spectrum)/2) + 1;
        positive_spectrum = avg_spectrum(1:n_pos);
        positive_freqs = freqs(1:n_pos);
        
        % Find dominant frequency (skip DC component)
        [~, dominant_idx] = max(positive_spectrum(2:end));
        dominant_idx = dominant_idx + 1;
        
        freq_analysis.frequencies = positive_freqs;
        freq_analysis.spectrum = positive_spectrum;
        freq_analysis.dominant_frequency = positive_freqs(dominant_idx);
        freq_analysis.spectral_centroid = sum(positive_freqs .* positive_spectrum) / sum(positive_spectrum);
    end
    
    % 4. Cross-correlation analysis
    function coord_results = calculateJointCoordination(data, joint1_var, joint2_var)
        [groups, subjects, tasks, steps] = findgroups(data.subject, data.task, data.step);
        
        coord_data = table();
        coord_data.subject = subjects;
        coord_data.task = tasks;
        coord_data.step = steps;
        
        % Calculate coordination metrics for each cycle
        max_correlations = splitapply(@(j1, j2) calculateCrossCorr(j1, j2), ...
            data.(joint1_var), data.(joint2_var), groups);
        
        coord_data.max_correlation = max_correlations;
        coord_results = coord_data;
    end
    
    function max_corr = calculateCrossCorr(joint1_data, joint2_data)
        % Sort by phase
        [joint1_sorted, sort_idx] = sort(joint1_data);
        joint2_sorted = joint2_data(sort_idx);
        
        % Calculate cross-correlation
        [correlation, lags] = xcorr(joint1_sorted, joint2_sorted);
        
        % Find maximum correlation
        [max_corr, ~] = max(abs(correlation));
    end
    ```

## Advanced Visualization

Create publication-quality figures:

=== "Python"

    ```python
    import matplotlib.pyplot as plt
    import seaborn as sns
    from matplotlib.patches import Rectangle
    import matplotlib.patches as mpatches
    
    # Set publication style
    plt.style.use(['seaborn-v0_8-paper', 'seaborn-v0_8-colorblind'])
    
    # 1. Multi-panel comparison figure
    def create_publication_figure(data, save_path='publication_figure.png'):
        """Create publication-ready multi-panel figure."""
        fig = plt.figure(figsize=(12, 10))
        gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.4)
        
        # Panel A: Average patterns by task
        ax1 = fig.add_subplot(gs[0, :2])
        
        colors = plt.cm.Set2(np.linspace(0, 1, len(data['task'].unique())))
        
        for i, task in enumerate(data['task'].unique()):
            task_data = data[data['task'] == task]
            
            # Calculate mean and SEM
            mean_pattern = task_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].mean()
            sem_pattern = task_data.groupby('phase_percent')['knee_flexion_angle_ipsi_rad'].sem()
            
            phase = mean_pattern.index
            mean_deg = np.degrees(mean_pattern.values)
            sem_deg = np.degrees(sem_pattern.values)
            
            # Plot mean with error band
            ax1.plot(phase, mean_deg, color=colors[i], linewidth=2, 
                    label=task.replace('_', ' ').title())
            ax1.fill_between(phase, mean_deg - sem_deg, mean_deg + sem_deg, 
                           color=colors[i], alpha=0.2)
        
        ax1.set_xlabel('Gait Cycle (%)')
        ax1.set_ylabel('Knee Flexion Angle (°)')
        ax1.set_title('A. Average Gait Patterns by Task', fontweight='bold')
        ax1.legend(frameon=True, fancybox=True, shadow=True)
        ax1.grid(True, alpha=0.3)
        
        # Add gait phase annotations
        ax1.axvspan(0, 60, alpha=0.1, color='blue', label='Stance')
        ax1.axvspan(60, 100, alpha=0.1, color='red', label='Swing')
        
        # Panel B: Variability comparison
        ax2 = fig.add_subplot(gs[0, 2])
        
        # Calculate coefficient of variation for each task
        cv_data = []
        for task in data['task'].unique():
            task_data = data[data['task'] == task]
            cv_by_cycle = task_data.groupby(['subject', 'step'])['knee_flexion_angle_ipsi_rad'].apply(
                lambda x: np.std(x) / np.abs(np.mean(x)) if np.mean(x) != 0 else 0
            )
            cv_data.extend([(task, cv) for cv in cv_by_cycle])
        
        cv_df = pd.DataFrame(cv_data, columns=['Task', 'CV'])
        
        box_plot = ax2.boxplot([cv_df[cv_df['Task'] == task]['CV'].values 
                               for task in data['task'].unique()],
                              labels=[task.replace('_', '\n') for task in data['task'].unique()],
                              patch_artist=True)
        
        for patch, color in zip(box_plot['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax2.set_ylabel('Coefficient of Variation')
        ax2.set_title('B. Gait Variability', fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        # Panel C: Joint coordination
        ax3 = fig.add_subplot(gs[1, :])
        
        # Create coordination plot (hip vs knee)
        for i, task in enumerate(data['task'].unique()):
            task_data = data[data['task'] == task]
            
            # Sample one representative cycle
            sample_cycle = task_data[task_data['step'] == 1]
            if len(sample_cycle) > 0:
                hip_angle = np.degrees(sample_cycle['hip_flexion_angle_ipsi_rad'])
                knee_angle = np.degrees(sample_cycle['knee_flexion_angle_ipsi_rad'])
                
                ax3.plot(hip_angle, knee_angle, color=colors[i], linewidth=2,
                        alpha=0.8, label=task.replace('_', ' ').title())
                
                # Mark start and end points
                ax3.scatter(hip_angle.iloc[0], knee_angle.iloc[0], 
                           color=colors[i], s=50, marker='o', zorder=5)
                ax3.scatter(hip_angle.iloc[-1], knee_angle.iloc[-1], 
                           color=colors[i], s=50, marker='s', zorder=5)
        
        ax3.set_xlabel('Hip Flexion Angle (°)')
        ax3.set_ylabel('Knee Flexion Angle (°)')
        ax3.set_title('C. Hip-Knee Coordination Patterns', fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Panel D: Statistical comparison
        ax4 = fig.add_subplot(gs[2, :2])
        
        # Create violin plot for peak knee flexion
        peak_data = []
        for task in data['task'].unique():
            task_data = data[data['task'] == task]
            peaks = task_data.groupby(['subject', 'step'])['knee_flexion_angle_ipsi_rad'].max()
            peak_data.extend([(task, np.degrees(peak)) for peak in peaks])
        
        peak_df = pd.DataFrame(peak_data, columns=['Task', 'Peak_Knee'])
        
        violin_parts = ax4.violinplot([peak_df[peak_df['Task'] == task]['Peak_Knee'].values 
                                      for task in data['task'].unique()],
                                     positions=range(len(data['task'].unique())),
                                     showmeans=True, showmedians=True)
        
        for i, pc in enumerate(violin_parts['bodies']):
            pc.set_facecolor(colors[i])
            pc.set_alpha(0.7)
        
        ax4.set_xticks(range(len(data['task'].unique())))
        ax4.set_xticklabels([task.replace('_', '\n') for task in data['task'].unique()])
        ax4.set_ylabel('Peak Knee Flexion (°)')
        ax4.set_title('D. Peak Flexion Distribution', fontweight='bold')
        ax4.grid(True, alpha=0.3)
        
        # Panel E: Quality metrics
        ax5 = fig.add_subplot(gs[2, 2])
        
        # Calculate quality metrics
        cycle_counts = data.groupby(['subject', 'task', 'step']).size()
        complete_cycles = (cycle_counts == 150).sum()
        total_cycles = len(cycle_counts)
        
        missing_data = data.isnull().sum().sum()
        total_points = data.size
        
        outliers = np.abs(data['knee_flexion_angle_ipsi_rad'] - 
                         data['knee_flexion_angle_ipsi_rad'].mean()) > \
                  3 * data['knee_flexion_angle_ipsi_rad'].std()
        outlier_count = outliers.sum()
        
        quality_metrics = [
            ('Complete\nCycles', (complete_cycles/total_cycles)*100),
            ('Data\nCompleteness', ((total_points-missing_data)/total_points)*100),
            ('Inlier\nData', ((len(data)-outlier_count)/len(data))*100)
        ]
        
        labels, values = zip(*quality_metrics)
        bars = ax5.bar(labels, values, color=['green', 'blue', 'orange'], alpha=0.7)
        
        ax5.set_ylabel('Quality Score (%)')
        ax5.set_title('E. Data Quality', fontweight='bold')
        ax5.set_ylim(0, 105)
        
        # Add percentage labels on bars
        for bar, value in zip(bars, values):
            ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # Add overall figure title and save
        fig.suptitle('Comprehensive Gait Analysis', fontsize=16, fontweight='bold')
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.show()
        
        return fig
    
    # Create the publication figure
    fig = create_publication_figure(data)
    ```

## Export and Integration

Prepare data for external analysis tools:

=== "Python"

    ```python
    # Export to various formats for different analysis tools
    
    # 1. Export for statistical software (R, SPSS, SAS)
    def export_for_statistics(data, output_dir='statistical_exports'):
        """Export data in formats suitable for statistical analysis."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Create cycle-level summary for statistical analysis
        cycle_summary = data.groupby(['subject', 'task', 'step']).agg({
            'knee_flexion_angle_ipsi_rad': ['min', 'max', 'mean', 'std'],
            'hip_flexion_angle_ipsi_rad': ['min', 'max', 'mean', 'std'],
            'ankle_flexion_angle_ipsi_rad': ['min', 'max', 'mean', 'std']
        }).round(6)
        
        # Flatten column names
        cycle_summary.columns = ['_'.join(col).strip() for col in cycle_summary.columns]
        cycle_summary = cycle_summary.reset_index()
        
        # Add derived variables
        cycle_summary['knee_rom'] = (cycle_summary['knee_flexion_angle_ipsi_rad_max'] - 
                                    cycle_summary['knee_flexion_angle_ipsi_rad_min'])
        
        # Export formats
        cycle_summary.to_csv(f'{output_dir}/cycle_summary.csv', index=False)
        cycle_summary.to_excel(f'{output_dir}/cycle_summary.xlsx', index=False)
        
        # For R
        cycle_summary.to_csv(f'{output_dir}/data_for_R.csv', index=False)
        
        # For SPSS (with variable labels)
        import json
        variable_labels = {
            'subject': 'Subject ID',
            'task': 'Locomotion Task',
            'step': 'Gait Cycle Number',
            'knee_flexion_angle_ipsi_rad_mean': 'Mean Knee Flexion Angle (rad)',
            'knee_rom': 'Knee Range of Motion (rad)'
        }
        
        with open(f'{output_dir}/variable_labels.json', 'w') as f:
            json.dump(variable_labels, f, indent=2)
        
        print(f"Statistical exports saved to '{output_dir}/'")
    
    # 2. Export for machine learning
    def export_for_ml(data, output_dir='ml_exports', test_size=0.2):
        """Export data formatted for machine learning applications."""
        import os
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import LabelEncoder, StandardScaler
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Create feature matrix (each row is one gait cycle)
        features = []
        labels = []
        metadata = []
        
        for (subject, task, step), group in data.groupby(['subject', 'task', 'step']):
            if len(group) == 150:  # Only complete cycles
                # Features: time series of joint angles
                cycle_features = np.concatenate([
                    group['knee_flexion_angle_ipsi_rad'].values,
                    group['hip_flexion_angle_ipsi_rad'].values,
                    group['ankle_flexion_angle_ipsi_rad'].values
                ])
                
                features.append(cycle_features)
                labels.append(task)
                metadata.append({'subject': subject, 'task': task, 'step': step})
        
        # Convert to arrays
        X = np.array(features)
        y = np.array(labels)
        
        # Encode labels
        le = LabelEncoder()
        y_encoded = le.fit_transform(y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=test_size, stratify=y_encoded, random_state=42
        )
        
        # Save datasets
        np.save(f'{output_dir}/X_train.npy', X_train)
        np.save(f'{output_dir}/X_test.npy', X_test)
        np.save(f'{output_dir}/y_train.npy', y_train)
        np.save(f'{output_dir}/y_test.npy', y_test)
        
        # Save label encoder and metadata
        import pickle
        with open(f'{output_dir}/label_encoder.pkl', 'wb') as f:
            pickle.dump(le, f)
        
        with open(f'{output_dir}/metadata.json', 'w') as f:
            json.dump({
                'feature_names': ['knee_angle', 'hip_angle', 'ankle_angle'],
                'feature_length': 150,
                'total_features': X.shape[1],
                'classes': le.classes_.tolist(),
                'train_samples': len(X_train),
                'test_samples': len(X_test)
            }, f, indent=2)
        
        print(f"ML exports saved to '{output_dir}/'")
        print(f"Feature matrix shape: {X.shape}")
        print(f"Classes: {le.classes_}")
    
    # 3. Export for biomechanical software (OpenSim, Visual3D)
    def export_for_biomech_software(data, output_dir='biomech_exports'):
        """Export data for biomechanical analysis software."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # OpenSim compatible format
        opensim_data = data.copy()
        opensim_data['time'] = opensim_data['phase_percent'] / 100  # Normalize to 0-1
        
        # Rename columns to OpenSim convention
        column_mapping = {
            'knee_flexion_angle_ipsi_rad': 'knee_angle_r',
            'hip_flexion_angle_ipsi_rad': 'hip_flexion_r', 
            'ankle_flexion_angle_ipsi_rad': 'ankle_angle_r'
        }
        
        opensim_data = opensim_data.rename(columns=column_mapping)
        
        # Save by task and subject
        for task in opensim_data['task'].unique():
            task_data = opensim_data[opensim_data['task'] == task]
            
            for subject in task_data['subject'].unique():
                subject_data = task_data[task_data['subject'] == subject]
                
                # Create OpenSim-style .sto file
                filename = f'{output_dir}/{subject}_{task}_kinematics.sto'
                
                with open(filename, 'w') as f:
                    # Write header
                    f.write('Coordinates\n')
                    f.write('version=1\n')
                    f.write(f'nRows={len(subject_data)}\n')
                    f.write('nColumns=5\n')  # time + 4 angles
                    f.write('inDegrees=no\n')
                    f.write('endheader\n')
                    
                    # Write column headers
                    f.write('time\tknee_angle_r\thip_flexion_r\tankle_angle_r\n')
                    
                    # Write data
                    for _, row in subject_data.iterrows():
                        f.write(f"{row['time']:.6f}\t{row['knee_angle_r']:.6f}\t"
                               f"{row['hip_flexion_r']:.6f}\t{row['ankle_angle_r']:.6f}\n")
        
        print(f"Biomechanical software exports saved to '{output_dir}/'")
    
    # Run exports
    export_for_statistics(data)
    export_for_ml(data)
    export_for_biomech_software(data)
    ```

## Performance Optimization Tips

1. **Memory Management**: Use appropriate data types and chunked processing
2. **Vectorization**: Prefer pandas/numpy operations over loops
3. **Indexing**: Set appropriate indexes for faster groupby operations
4. **Caching**: Cache expensive computations using `functools.lru_cache`
5. **Parallel Processing**: Use `multiprocessing` for independent computations

## Next Steps

- **[Validation Reports](validation_reports/)** - Understanding quality assessment
- **[Troubleshooting](troubleshooting/)** - Common issues and solutions
- **[API Reference](../reference/api_reference/)** - Complete function documentation

---

*These advanced techniques enable sophisticated analysis of standardized locomotion data. For specific use cases, consult the [API Reference](../reference/api_reference/) or [Tutorials](../tutorials/).*