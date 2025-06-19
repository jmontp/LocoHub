# Research Platform Integration Guide

**Complete integration guide for biomechanical research platforms and analysis tools**

## Overview

This guide demonstrates how to integrate the locomotion data platform with major research platforms including OpenSim, Biomechanical ToolKit (BTK), MATLAB, R, and cloud-based research computing environments.

## OpenSim Integration

### Data Export for OpenSim Analysis

```python
from lib.core.locomotion_analysis import LocomotionData
import numpy as np
import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path

class OpenSimExporter:
    """Export locomotion data to OpenSim-compatible formats."""
    
    def __init__(self, loco_data):
        self.loco_data = loco_data
        
    def export_kinematics_mot(self, subject, task, output_path, time_step=0.01):
        """Export kinematics data to OpenSim .mot format."""
        
        # Get gait cycle data
        data_3d, features = self.loco_data.get_cycles(subject, task)
        if data_3d is None:
            raise ValueError(f"No data found for {subject}-{task}")
        
        # Create time vector for one representative cycle
        n_points = data_3d.shape[1]  # 150 points
        cycle_duration = 1.0  # Assume 1 second per cycle (adjust as needed)
        time_vector = np.linspace(0, cycle_duration, n_points)
        
        # Take mean cycle for representative kinematics
        mean_cycle = np.mean(data_3d, axis=0)  # Shape: (150, n_features)
        
        # Create DataFrame for .mot file
        mot_data = pd.DataFrame()
        mot_data['time'] = time_vector
        
        # Map features to OpenSim coordinate names
        opensim_mapping = {
            'hip_flexion_angle_ipsi_rad': 'hip_flexion_r',
            'hip_flexion_angle_contra_rad': 'hip_flexion_l',
            'knee_flexion_angle_ipsi_rad': 'knee_angle_r',
            'knee_flexion_angle_contra_rad': 'knee_angle_l',
            'ankle_flexion_angle_ipsi_rad': 'ankle_angle_r',
            'ankle_flexion_angle_contra_rad': 'ankle_angle_l'
        }
        
        for i, feature in enumerate(features):
            if feature in opensim_mapping:
                opensim_coord = opensim_mapping[feature]
                # Convert to degrees for OpenSim
                mot_data[opensim_coord] = np.degrees(mean_cycle[:, i])
        
        # Write .mot file
        with open(output_path, 'w') as f:
            f.write(f"{output_path.name}\n")
            f.write("version=1\n")
            f.write(f"nRows={len(mot_data)}\n")
            f.write(f"nColumns={len(mot_data.columns)}\n")
            f.write("inDegrees=yes\n")
            f.write("endheader\n")
            
            # Write column headers
            headers = '\t'.join(mot_data.columns)
            f.write(f"{headers}\n")
            
            # Write data
            for _, row in mot_data.iterrows():
                row_str = '\t'.join([f"{val:.6f}" for val in row])
                f.write(f"{row_str}\n")
        
        print(f"Kinematics exported to {output_path}")
        return output_path
    
    def export_external_loads(self, subject, task, output_path):
        """Export ground reaction forces to OpenSim external loads format."""
        
        # This would require force plate data - create template for now
        # In practice, you'd have GRF data in your locomotion dataset
        
        # Get timing information
        data_3d, features = self.loco_data.get_cycles(subject, task)
        if data_3d is None:
            raise ValueError(f"No data found for {subject}-{task}")
        
        n_points = data_3d.shape[1]
        cycle_duration = 1.0
        time_vector = np.linspace(0, cycle_duration, n_points)
        
        # Create template external loads (replace with actual GRF data)
        loads_data = pd.DataFrame()
        loads_data['time'] = time_vector
        loads_data['ground_force_vx'] = np.zeros(n_points)  # Anterior-posterior
        loads_data['ground_force_vy'] = np.ones(n_points) * 800  # Vertical (example)
        loads_data['ground_force_vz'] = np.zeros(n_points)  # Medial-lateral
        loads_data['ground_force_px'] = np.zeros(n_points)  # Point of application
        loads_data['ground_force_py'] = np.zeros(n_points)
        loads_data['ground_force_pz'] = np.zeros(n_points)
        loads_data['ground_torque_x'] = np.zeros(n_points)  # Free moments
        loads_data['ground_torque_y'] = np.zeros(n_points)
        loads_data['ground_torque_z'] = np.zeros(n_points)
        
        # Write external loads file
        with open(output_path, 'w') as f:
            f.write(f"{output_path.name}\n")
            f.write("version=1\n")
            f.write(f"nRows={len(loads_data)}\n")
            f.write(f"nColumns={len(loads_data.columns)}\n")
            f.write("inDegrees=no\n")
            f.write("endheader\n")
            
            # Write headers and data
            headers = '\t'.join(loads_data.columns)
            f.write(f"{headers}\n")
            
            for _, row in loads_data.iterrows():
                row_str = '\t'.join([f"{val:.6f}" for val in row])
                f.write(f"{row_str}\n")
        
        print(f"External loads exported to {output_path}")
        return output_path
    
    def create_opensim_setup_xml(self, subject, task, output_dir):
        """Create OpenSim analysis setup XML files."""
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Inverse Kinematics Setup
        ik_setup = ET.Element("OpenSimDocument", Version="40000")
        ik_tool = ET.SubElement(ik_setup, "InverseKinematicsTool", name=f"{subject}_{task}_IK")
        
        # Model file
        ET.SubElement(ik_tool, "model_file").text = "generic_model.osim"
        
        # Marker data
        marker_data = ET.SubElement(ik_tool, "marker_file")
        marker_data.text = f"{subject}_{task}_markers.trc"
        
        # Coordinate data (our kinematics)
        coord_data = ET.SubElement(ik_tool, "coordinate_file")
        coord_data.text = f"{subject}_{task}_kinematics.mot"
        
        # Time range
        ET.SubElement(ik_tool, "time_range").text = "0.0 1.0"
        
        # Output
        ET.SubElement(ik_tool, "output_motion_file").text = f"{subject}_{task}_ik.mot"
        
        # Write IK setup file
        ik_path = output_dir / f"{subject}_{task}_ik_setup.xml"
        tree = ET.ElementTree(ik_setup)
        tree.write(ik_path, encoding='utf-8', xml_declaration=True)
        
        # Inverse Dynamics Setup
        id_setup = ET.Element("OpenSimDocument", Version="40000")
        id_tool = ET.SubElement(id_setup, "InverseDynamicsTool", name=f"{subject}_{task}_ID")
        
        ET.SubElement(id_tool, "model_file").text = "generic_model.osim"
        ET.SubElement(id_tool, "coordinates_file").text = f"{subject}_{task}_ik.mot"
        ET.SubElement(id_tool, "external_loads_file").text = f"{subject}_{task}_loads.xml"
        ET.SubElement(id_tool, "time_range").text = "0.0 1.0"
        ET.SubElement(id_tool, "output_gen_force_file").text = f"{subject}_{task}_id.sto"
        
        # Write ID setup file
        id_path = output_dir / f"{subject}_{task}_id_setup.xml"
        tree = ET.ElementTree(id_setup)
        tree.write(id_path, encoding='utf-8', xml_declaration=True)
        
        print(f"OpenSim setup files created in {output_dir}")
        return {"ik_setup": ik_path, "id_setup": id_path}
    
    def export_full_opensim_workflow(self, subject, task, output_dir):
        """Export complete OpenSim analysis workflow."""
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export kinematics
        mot_path = output_dir / f"{subject}_{task}_kinematics.mot"
        self.export_kinematics_mot(subject, task, mot_path)
        
        # Export external loads
        loads_path = output_dir / f"{subject}_{task}_loads.mot"
        self.export_external_loads(subject, task, loads_path)
        
        # Create setup files
        setup_files = self.create_opensim_setup_xml(subject, task, output_dir)
        
        # Create analysis script
        script_content = f"""
% OpenSim Analysis Script for {subject} - {task}
% Generated automatically by Locomotion Data Platform

import org.opensim.modeling.*

% Load model
model = Model('generic_model.osim');

% Inverse Kinematics
ikTool = InverseKinematicsTool('{setup_files["ik_setup"].name}');
ikTool.run();

% Inverse Dynamics  
idTool = InverseDynamicsTool('{setup_files["id_setup"].name}');
idTool.run();

% Load results for analysis
ikResults = Storage('{subject}_{task}_ik.mot');
idResults = Storage('{subject}_{task}_id.sto');

fprintf('OpenSim analysis completed for {subject} - {task}\\n');
"""
        
        script_path = output_dir / f"{subject}_{task}_analysis.m"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        print(f"Complete OpenSim workflow exported to {output_dir}")
        return {
            "kinematics": mot_path,
            "loads": loads_path,
            "setup_files": setup_files,
            "analysis_script": script_path
        }

# Usage
loco = LocomotionData('research_dataset_phase.parquet')
opensim_exporter = OpenSimExporter(loco)

# Export complete workflow
workflow_files = opensim_exporter.export_full_opensim_workflow(
    'SUB01', 'normal_walk', 'opensim_analysis/'
)
```

### OpenSim Python API Integration

```python
try:
    import opensim as osim
    OPENSIM_AVAILABLE = True
except ImportError:
    OPENSIM_AVAILABLE = False
    print("OpenSim Python API not available")

class OpenSimAnalyzer:
    """Direct integration with OpenSim Python API."""
    
    def __init__(self, model_path, loco_data):
        if not OPENSIM_AVAILABLE:
            raise ImportError("OpenSim Python API required")
        
        self.model = osim.Model(model_path)
        self.loco_data = loco_data
        
    def run_inverse_kinematics(self, subject, task, marker_file=None):
        """Run inverse kinematics analysis."""
        
        # Get kinematics data
        data_3d, features = self.loco_data.get_cycles(subject, task)
        if data_3d is None:
            raise ValueError(f"No data found for {subject}-{task}")
        
        # Create IK tool
        ik_tool = osim.InverseKinematicsTool()
        ik_tool.setModel(self.model)
        
        if marker_file:
            ik_tool.setMarkerDataFileName(marker_file)
        
        # Set time range
        ik_tool.setStartTime(0.0)
        ik_tool.setEndTime(1.0)
        
        # Run analysis
        ik_tool.run()
        
        return ik_tool
    
    def calculate_joint_moments(self, subject, task, external_loads_file=None):
        """Calculate joint moments using inverse dynamics."""
        
        # Create ID tool
        id_tool = osim.InverseDynamicsTool()
        id_tool.setModel(self.model)
        
        if external_loads_file:
            id_tool.setExternalLoadsFileName(external_loads_file)
        
        # Set time range
        id_tool.setStartTime(0.0)
        id_tool.setEndTime(1.0)
        
        # Run analysis
        id_tool.run()
        
        return id_tool
```

## MATLAB Integration

### MATLAB Data Export

```python
import scipy.io as sio

class MATLABExporter:
    """Export locomotion data to MATLAB-compatible formats."""
    
    def __init__(self, loco_data):
        self.loco_data = loco_data
        
    def export_to_mat(self, subjects=None, tasks=None, output_path='gait_data.mat'):
        """Export data to MATLAB .mat format."""
        
        if subjects is None:
            subjects = self.loco_data.get_subjects()
        if tasks is None:
            tasks = self.loco_data.get_tasks()
        
        matlab_data = {}
        
        for subject in subjects:
            subject_data = {}
            
            for task in tasks:
                # Get 3D data
                data_3d, features = self.loco_data.get_cycles(subject, task)
                if data_3d is not None:
                    
                    task_data = {
                        'cycles': data_3d,  # (n_cycles, 150, n_features)
                        'features': features,
                        'n_cycles': data_3d.shape[0],
                        'n_points': data_3d.shape[1],
                        'n_features': data_3d.shape[2]
                    }
                    
                    # Add summary statistics
                    try:
                        stats = self.loco_data.get_summary_statistics(subject, task)
                        if not stats.empty:
                            task_data['statistics'] = {
                                'mean': stats['mean'].values,
                                'std': stats['std'].values,
                                'min': stats['min'].values,
                                'max': stats['max'].values
                            }
                    except:
                        pass
                    
                    # Add ROM data
                    try:
                        rom_data = self.loco_data.calculate_rom(subject, task, by_cycle=False)
                        task_data['rom'] = {k: v for k, v in rom_data.items()}
                    except:
                        pass
                    
                    subject_data[task] = task_data
            
            if subject_data:
                matlab_data[subject] = subject_data
        
        # Add metadata
        matlab_data['metadata'] = {
            'export_date': str(pd.Timestamp.now()),
            'subjects': subjects,
            'tasks': tasks,
            'points_per_cycle': 150,
            'description': 'Gait analysis data exported from Locomotion Data Platform'
        }
        
        # Save to .mat file
        sio.savemat(output_path, matlab_data)
        print(f"Data exported to MATLAB format: {output_path}")
        
        return output_path
    
    def create_matlab_analysis_script(self, output_path='analyze_gait_data.m'):
        """Create MATLAB analysis script template."""
        
        script_content = """
function analyze_gait_data(mat_file)
% ANALYZE_GAIT_DATA - Comprehensive gait analysis in MATLAB
% 
% Usage: analyze_gait_data('gait_data.mat')
%
% Generated by Locomotion Data Platform

if nargin < 1
    mat_file = 'gait_data.mat';
end

% Load data
fprintf('Loading gait data from %s...\\n', mat_file);
data = load(mat_file);

% Get subjects and tasks
subjects = fieldnames(data);
subjects = subjects(~strcmp(subjects, 'metadata'));

fprintf('Found %d subjects\\n', length(subjects));

%% Analysis for each subject
for s = 1:length(subjects)
    subject = subjects{s};
    fprintf('\\nAnalyzing subject: %s\\n', subject);
    
    subject_data = data.(subject);
    tasks = fieldnames(subject_data);
    
    for t = 1:length(tasks)
        task = tasks{t};
        task_data = subject_data.(task);
        
        fprintf('  Task: %s (%d cycles)\\n', task, task_data.n_cycles);
        
        % Extract cycle data
        cycles = task_data.cycles;  % (n_cycles, 150, n_features)
        features = task_data.features;
        
        % Calculate mean pattern
        mean_pattern = squeeze(mean(cycles, 1));  % (150, n_features)
        
        % Calculate variability
        std_pattern = squeeze(std(cycles, [], 1));  % (150, n_features)
        
        % Plot results
        figure('Name', sprintf('%s - %s', subject, task));
        
        n_features = length(features);
        n_cols = min(3, n_features);
        n_rows = ceil(n_features / n_cols);
        
        phase = linspace(0, 100, 150);
        
        for f = 1:n_features
            subplot(n_rows, n_cols, f);
            
            % Plot individual cycles in light gray
            for c = 1:size(cycles, 1)
                plot(phase, cycles(c, :, f), 'Color', [0.8 0.8 0.8]);
                hold on;
            end
            
            % Plot mean ± std
            fill([phase, fliplr(phase)], ...
                 [mean_pattern(:,f)' + std_pattern(:,f)', ...
                  fliplr(mean_pattern(:,f)' - std_pattern(:,f)')], ...
                 'b', 'FaceAlpha', 0.3, 'EdgeColor', 'none');
            
            % Plot mean
            plot(phase, mean_pattern(:,f), 'b-', 'LineWidth', 2);
            
            xlabel('Gait Cycle (%)');
            ylabel(strrep(features{f}, '_', ' '));
            title(strrep(features{f}, '_', ' '));
            grid on;
            hold off;
        end
        
        % Save figure
        savefig(sprintf('%s_%s_patterns.fig', subject, task));
        
        % Calculate and display ROM
        if isfield(task_data, 'rom')
            fprintf('    ROM Analysis:\\n');
            rom_fields = fieldnames(task_data.rom);
            for r = 1:length(rom_fields)
                rom_field = rom_fields{r};
                rom_value = task_data.rom.(rom_field);
                if contains(rom_field, 'angle')
                    fprintf('      %s: %.1f degrees\\n', ...
                           strrep(rom_field, '_', ' '), rad2deg(rom_value));
                end
            end
        end
    end
end

fprintf('\\nAnalysis complete. Figures saved.\\n');

end

%% Additional analysis functions

function [symmetry_index] = calculate_symmetry(left_data, right_data)
% Calculate gait symmetry index
% SI = 100 * abs(left - right) / (0.5 * (left + right))

symmetry_index = 100 * abs(left_data - right_data) ./ (0.5 * (left_data + right_data));
end

function [variability] = calculate_variability(cycle_data)
% Calculate coefficient of variation for gait variability
% CV = (std / mean) * 100

means = mean(cycle_data, 2);
stds = std(cycle_data, [], 2);
variability = (stds ./ means) * 100;
end
"""
        
        with open(output_path, 'w') as f:
            f.write(script_content)
        
        print(f"MATLAB analysis script created: {output_path}")
        return output_path

# Usage
loco = LocomotionData('research_dataset_phase.parquet')
matlab_exporter = MATLABExporter(loco)

# Export to MATLAB
mat_file = matlab_exporter.export_to_mat(
    subjects=['SUB01', 'SUB02'], 
    tasks=['normal_walk', 'fast_walk'],
    output_path='gait_analysis.mat'
)

# Create analysis script
script_file = matlab_exporter.create_matlab_analysis_script('analyze_gait.m')
```

## R Integration

### R Data Export and Analysis

```python
import rpy2.robjects as robjects
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr

class RAnalysisExporter:
    """Export locomotion data for R statistical analysis."""
    
    def __init__(self, loco_data):
        self.loco_data = loco_data
        
        # Activate pandas-R interface
        pandas2ri.activate()
        
        try:
            self.r_stats = importr('stats')
            self.r_base = importr('base')
        except:
            print("R packages not available - install rpy2 and R")
    
    def export_to_r_dataframe(self, subjects=None, tasks=None):
        """Convert locomotion data to R-compatible long format."""
        
        if subjects is None:
            subjects = self.loco_data.get_subjects()
        if tasks is None:
            tasks = self.loco_data.get_tasks()
        
        all_data = []
        
        for subject in subjects:
            for task in tasks:
                data_3d, features = self.loco_data.get_cycles(subject, task)
                if data_3d is None:
                    continue
                
                # Convert to long format
                n_cycles, n_phases, n_features = data_3d.shape
                
                for cycle_idx in range(n_cycles):
                    for phase_idx in range(n_phases):
                        for feat_idx, feature in enumerate(features):
                            row = {
                                'subject': subject,
                                'task': task,
                                'cycle': cycle_idx + 1,
                                'phase': phase_idx,
                                'phase_percent': (phase_idx / (n_phases - 1)) * 100,
                                'variable': feature,
                                'value': data_3d[cycle_idx, phase_idx, feat_idx]
                            }
                            all_data.append(row)
        
        df = pd.DataFrame(all_data)
        
        # Convert to R dataframe
        r_df = pandas2ri.py2rpy(df)
        
        return r_df, df
    
    def create_r_analysis_script(self, output_path='gait_analysis.R'):
        """Create comprehensive R analysis script."""
        
        r_script = """
# Gait Analysis in R
# Generated by Locomotion Data Platform

library(ggplot2)
library(dplyr)
library(tidyr)
library(lme4)
library(broom)

# Load data
# data <- read.csv('gait_data.csv')  # Uncomment if loading from CSV

# Data exploration
cat("Data Summary:\\n")
print(summary(data))

cat("\\nSubjects:", length(unique(data$subject)))
cat("\\nTasks:", paste(unique(data$task), collapse=", "))
cat("\\nVariables:", paste(unique(data$variable), collapse=", "))

#' Mixed Effects Analysis
#' 
#' Analyze gait patterns using linear mixed effects models
analyze_gait_patterns <- function(data, variable_name) {
  
  # Filter to specific variable
  var_data <- data %>% filter(variable == variable_name)
  
  # Mixed effects model: value ~ task + phase + (1|subject)
  model <- lmer(value ~ task * phase_percent + (1|subject), data = var_data)
  
  # Model summary
  cat("\\n=== Mixed Effects Analysis:", variable_name, "===\\n")
  print(summary(model))
  
  # Plot results
  p <- ggplot(var_data, aes(x = phase_percent, y = value, color = task)) +
    geom_smooth(method = "loess", se = TRUE, alpha = 0.3) +
    stat_summary(fun = mean, geom = "line", alpha = 0.7) +
    facet_wrap(~ task) +
    labs(
      title = paste("Gait Pattern Analysis:", variable_name),
      x = "Gait Cycle (%)",
      y = "Value",
      color = "Task"
    ) +
    theme_minimal() +
    theme(
      strip.text = element_text(size = 12),
      plot.title = element_text(size = 14, hjust = 0.5)
    )
  
  ggsave(paste0(variable_name, "_analysis.png"), p, width = 12, height = 8, dpi = 300)
  
  return(model)
}

#' Calculate Symmetry Index
#' 
#' Calculate symmetry between ipsilateral and contralateral limbs
calculate_symmetry <- function(data) {
  
  # Find paired variables
  ipsi_vars <- data %>% filter(grepl("ipsi", variable)) %>% 
               select(variable) %>% distinct() %>% pull()
  
  symmetry_results <- data.frame()
  
  for (var in ipsi_vars) {
    contra_var <- gsub("ipsi", "contra", var)
    
    if (contra_var %in% unique(data$variable)) {
      # Get data for both sides
      ipsi_data <- data %>% filter(variable == var) %>%
                   group_by(subject, task, phase_percent) %>%
                   summarise(ipsi_value = mean(value), .groups = "drop")
      
      contra_data <- data %>% filter(variable == contra_var) %>%
                     group_by(subject, task, phase_percent) %>%
                     summarise(contra_value = mean(value), .groups = "drop")
      
      # Merge and calculate symmetry
      merged <- merge(ipsi_data, contra_data, 
                     by = c("subject", "task", "phase_percent"))
      
      merged$symmetry_index <- abs(merged$ipsi_value - merged$contra_value) / 
                              (0.5 * (abs(merged$ipsi_value) + abs(merged$contra_value))) * 100
      
      merged$variable <- var
      
      symmetry_results <- rbind(symmetry_results, merged)
    }
  }
  
  return(symmetry_results)
}

#' Gait Variability Analysis
#' 
#' Calculate coefficient of variation for gait variability
calculate_variability <- function(data) {
  
  variability <- data %>%
    group_by(subject, task, variable, phase_percent) %>%
    summarise(
      mean_value = mean(value),
      sd_value = sd(value),
      cv = (sd_value / abs(mean_value)) * 100,
      .groups = "drop"
    ) %>%
    filter(!is.infinite(cv) & !is.na(cv))
  
  return(variability)
}

#' Statistical Comparisons
#' 
#' Compare tasks using appropriate statistical tests
compare_tasks <- function(data, variable_name) {
  
  var_data <- data %>% filter(variable == variable_name)
  
  # Calculate summary statistics per subject-task
  summary_stats <- var_data %>%
    group_by(subject, task) %>%
    summarise(
      mean_value = mean(value),
      range_value = max(value) - min(value),
      .groups = "drop"
    )
  
  # Test for task differences
  if (length(unique(summary_stats$task)) == 2) {
    # Paired t-test for two tasks
    test_result <- t.test(mean_value ~ task, data = summary_stats, paired = TRUE)
  } else {
    # ANOVA for multiple tasks
    test_result <- aov(mean_value ~ task, data = summary_stats)
  }
  
  cat("\\n=== Statistical Comparison:", variable_name, "===\\n")
  print(test_result)
  
  return(test_result)
}

#' Main Analysis Pipeline
#' 
#' Run complete gait analysis pipeline
run_gait_analysis <- function(data) {
  
  # Get unique variables
  variables <- unique(data$variable)
  
  # Analyze each variable
  models <- list()
  for (var in variables) {
    if (grepl("angle", var)) {  # Focus on angle variables
      models[[var]] <- analyze_gait_patterns(data, var)
      compare_tasks(data, var)
    }
  }
  
  # Symmetry analysis
  cat("\\n=== Symmetry Analysis ===\\n")
  symmetry_data <- calculate_symmetry(data)
  
  if (nrow(symmetry_data) > 0) {
    symmetry_plot <- ggplot(symmetry_data, aes(x = phase_percent, y = symmetry_index)) +
      geom_smooth(method = "loess", se = TRUE) +
      facet_grid(variable ~ task, scales = "free_y") +
      labs(
        title = "Gait Symmetry Analysis",
        x = "Gait Cycle (%)",
        y = "Symmetry Index (%)"
      ) +
      theme_minimal()
    
    ggsave("symmetry_analysis.png", symmetry_plot, width = 14, height = 10, dpi = 300)
  }
  
  # Variability analysis
  cat("\\n=== Variability Analysis ===\\n")
  variability_data <- calculate_variability(data)
  
  variability_summary <- variability_data %>%
    group_by(task, variable) %>%
    summarise(
      mean_cv = mean(cv),
      sd_cv = sd(cv),
      .groups = "drop"
    )
  
  print(variability_summary)
  
  variability_plot <- ggplot(variability_data, aes(x = task, y = cv, fill = task)) +
    geom_boxplot() +
    facet_wrap(~ variable, scales = "free_y") +
    labs(
      title = "Gait Variability Analysis",
      x = "Task",
      y = "Coefficient of Variation (%)"
    ) +
    theme_minimal() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))
  
  ggsave("variability_analysis.png", variability_plot, width = 12, height = 8, dpi = 300)
  
  return(list(
    models = models,
    symmetry = symmetry_data,
    variability = variability_data
  ))
}

# Run analysis if data is loaded
if (exists("data")) {
  results <- run_gait_analysis(data)
  cat("\\nAnalysis complete. Plots and results saved.\\n")
} else {
  cat("Load gait data first, then run: results <- run_gait_analysis(data)\\n")
}
"""
        
        with open(output_path, 'w') as f:
            f.write(r_script)
        
        print(f"R analysis script created: {output_path}")
        return output_path
    
    def run_r_analysis(self, subjects=None, tasks=None):
        """Execute R analysis directly from Python."""
        
        try:
            # Get data
            r_df, py_df = self.export_to_r_dataframe(subjects, tasks)
            
            # Assign to R environment
            robjects.globalenv['data'] = r_df
            
            # Run basic analysis
            r_code = """
            library(dplyr)
            
            # Basic summary
            summary_stats <- data %>%
              group_by(subject, task, variable) %>%
              summarise(
                mean_value = mean(value),
                sd_value = sd(value),
                .groups = "drop"
              )
            
            print("Summary statistics calculated")
            """
            
            robjects.r(r_code)
            
            # Get results back to Python
            summary_stats = robjects.globalenv['summary_stats']
            summary_df = pandas2ri.rpy2py(summary_stats)
            
            return summary_df
            
        except Exception as e:
            print(f"R analysis failed: {e}")
            return None

# Usage
loco = LocomotionData('research_dataset_phase.parquet')
r_exporter = RAnalysisExporter(loco)

# Create R script
r_script = r_exporter.create_r_analysis_script('comprehensive_gait_analysis.R')

# Export data to CSV for R
r_df, py_df = r_exporter.export_to_r_dataframe()
py_df.to_csv('gait_data_for_r.csv', index=False)
print("Data exported to CSV for R analysis")
```

## Cloud Computing Integration

### AWS Integration

```python
import boto3
import json
from pathlib import Path

class AWSResearchPlatform:
    """Integration with AWS cloud computing for large-scale gait analysis."""
    
    def __init__(self, aws_access_key_id, aws_secret_access_key, region='us-east-1'):
        self.session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region
        )
        self.s3 = self.session.client('s3')
        self.batch = self.session.client('batch')
        self.ec2 = self.session.client('ec2')
    
    def upload_dataset_to_s3(self, dataset_path, bucket_name, s3_key):
        """Upload locomotion dataset to S3."""
        
        try:
            self.s3.upload_file(dataset_path, bucket_name, s3_key)
            print(f"Dataset uploaded to s3://{bucket_name}/{s3_key}")
            return f"s3://{bucket_name}/{s3_key}"
        except Exception as e:
            print(f"Upload failed: {e}")
            return None
    
    def create_batch_job_definition(self, job_name, docker_image):
        """Create AWS Batch job definition for gait analysis."""
        
        job_definition = {
            'jobDefinitionName': job_name,
            'type': 'container',
            'containerProperties': {
                'image': docker_image,
                'vcpus': 4,
                'memory': 8192,
                'jobRoleArn': 'arn:aws:iam::account:role/BatchExecutionRole',
                'environment': [
                    {'name': 'AWS_DEFAULT_REGION', 'value': self.session.region_name}
                ]
            },
            'timeout': {'attemptDurationSeconds': 3600}
        }
        
        try:
            response = self.batch.register_job_definition(**job_definition)
            print(f"Job definition created: {response['jobDefinitionArn']}")
            return response
        except Exception as e:
            print(f"Failed to create job definition: {e}")
            return None
    
    def submit_analysis_job(self, job_name, job_queue, job_definition, parameters):
        """Submit gait analysis job to AWS Batch."""
        
        job_submission = {
            'jobName': job_name,
            'jobQueue': job_queue,
            'jobDefinition': job_definition,
            'parameters': parameters
        }
        
        try:
            response = self.batch.submit_job(**job_submission)
            print(f"Job submitted: {response['jobId']}")
            return response
        except Exception as e:
            print(f"Failed to submit job: {e}")
            return None
    
    def create_analysis_container(self, dockerfile_content, image_name):
        """Create Docker container for gait analysis."""
        
        dockerfile = f"""
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy analysis scripts
COPY analysis_scripts/ /app/analysis_scripts/
COPY lib/ /app/lib/

WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app

# Entry point
ENTRYPOINT ["python", "analysis_scripts/batch_analysis.py"]
"""
        
        # Create batch analysis script
        batch_script = """
#!/usr/bin/env python3
import sys
import os
import boto3
from lib.core.locomotion_analysis import LocomotionData
import pandas as pd
import numpy as np

def run_batch_analysis(input_s3_path, output_s3_path, analysis_type='summary'):
    '''Run gait analysis on AWS Batch.'''
    
    # Download data from S3
    s3 = boto3.client('s3')
    bucket, key = input_s3_path.replace('s3://', '').split('/', 1)
    
    local_input = '/tmp/input_data.parquet'
    s3.download_file(bucket, key, local_input)
    
    # Load and analyze data
    loco = LocomotionData(local_input)
    subjects = loco.get_subjects()
    tasks = loco.get_tasks()
    
    results = []
    
    for subject in subjects:
        for task in tasks:
            try:
                # Summary statistics
                stats = loco.get_summary_statistics(subject, task)
                rom_data = loco.calculate_rom(subject, task, by_cycle=False)
                
                result = {
                    'subject': subject,
                    'task': task,
                    'stats': stats.to_dict() if not stats.empty else {},
                    'rom': {k: float(v) for k, v in rom_data.items()}
                }
                results.append(result)
                
            except Exception as e:
                print(f"Error processing {subject}-{task}: {e}")
    
    # Save results
    output_df = pd.DataFrame(results)
    local_output = '/tmp/analysis_results.csv'
    output_df.to_csv(local_output, index=False)
    
    # Upload to S3
    output_bucket, output_key = output_s3_path.replace('s3://', '').split('/', 1)
    s3.upload_file(local_output, output_bucket, output_key)
    
    print(f"Analysis complete. Results uploaded to {output_s3_path}")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python batch_analysis.py <input_s3_path> <output_s3_path>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    run_batch_analysis(input_path, output_path)
"""
        
        return dockerfile, batch_script

# Usage
"""
aws_platform = AWSResearchPlatform(
    aws_access_key_id='your_access_key',
    aws_secret_access_key='your_secret_key'
)

# Upload dataset
s3_path = aws_platform.upload_dataset_to_s3(
    'large_dataset_phase.parquet', 
    'gait-analysis-bucket', 
    'datasets/study_001.parquet'
)

# Create and submit batch job
job_def = aws_platform.create_batch_job_definition(
    'gait-analysis-job', 
    'your-account.dkr.ecr.us-east-1.amazonaws.com/gait-analysis:latest'
)

job = aws_platform.submit_analysis_job(
    'analysis-job-001',
    'gait-analysis-queue',
    'gait-analysis-job',
    {
        'input_s3_path': s3_path,
        'output_s3_path': 's3://gait-analysis-bucket/results/study_001_results.csv'
    }
)
"""
```

### Google Cloud Platform Integration

```python
from google.cloud import storage, compute_v1, batch_v1
import json

class GCPResearchPlatform:
    """Integration with Google Cloud Platform for gait analysis."""
    
    def __init__(self, project_id, credentials_path=None):
        self.project_id = project_id
        
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        self.storage_client = storage.Client(project=project_id)
        self.compute_client = compute_v1.InstancesClient()
        
    def upload_to_gcs(self, local_path, bucket_name, blob_name):
        """Upload dataset to Google Cloud Storage."""
        
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        blob.upload_from_filename(local_path)
        print(f"Dataset uploaded to gs://{bucket_name}/{blob_name}")
        
        return f"gs://{bucket_name}/{blob_name}"
    
    def create_compute_instance_for_analysis(self, instance_name, zone, machine_type='n1-standard-4'):
        """Create compute instance for gait analysis."""
        
        # Startup script for gait analysis environment
        startup_script = """
#!/bin/bash
apt-get update
apt-get install -y python3-pip git

# Install locomotion analysis library
git clone https://github.com/your-org/locomotion-data-standardization.git
cd locomotion-data-standardization
pip3 install -r requirements.txt

# Install additional research packages
pip3 install scipy scikit-learn matplotlib seaborn

echo "Gait analysis environment ready"
"""
        
        instance_config = {
            'name': instance_name,
            'machine_type': f"zones/{zone}/machineTypes/{machine_type}",
            'disks': [{
                'boot': True,
                'auto_delete': True,
                'initialize_params': {
                    'source_image': 'projects/ubuntu-os-cloud/global/images/family/ubuntu-2004-lts'
                }
            }],
            'network_interfaces': [{
                'network': 'global/networks/default',
                'access_configs': [{'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}]
            }],
            'metadata': {
                'items': [{
                    'key': 'startup-script',
                    'value': startup_script
                }]
            },
            'service_accounts': [{
                'email': 'default',
                'scopes': ['https://www.googleapis.com/auth/cloud-platform']
            }]
        }
        
        operation = self.compute_client.insert(
            project=self.project_id,
            zone=zone,
            instance_resource=instance_config
        )
        
        print(f"Creating compute instance: {instance_name}")
        return operation

# Usage
"""
gcp_platform = GCPResearchPlatform('your-project-id', 'path/to/credentials.json')

# Upload dataset
gcs_path = gcp_platform.upload_to_gcs(
    'large_dataset_phase.parquet',
    'gait-analysis-bucket',
    'datasets/study_001.parquet'
)

# Create analysis instance
instance_op = gcp_platform.create_compute_instance_for_analysis(
    'gait-analysis-vm',
    'us-central1-a',
    'n1-highmem-4'
)
"""
```

This comprehensive research platform integration guide provides complete patterns for integrating the locomotion data platform with major research tools and cloud computing environments for large-scale biomechanical analysis.