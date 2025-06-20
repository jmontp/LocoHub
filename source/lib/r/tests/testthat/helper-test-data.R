# Test Data Generation Helper Functions
# 
# Created: 2025-06-19 with user permission
# Purpose: Generate synthetic biomechanical datasets for comprehensive testing
#
# Intent: Provide reproducible test data generation utilities for unit tests,
# integration tests, and edge case validation. Supports both phase-indexed
# and time-indexed data with realistic biomechanical patterns.

library(data.table)

#' Generate Synthetic Gait Cycle Data
#' 
#' Creates realistic synthetic biomechanical data for testing purposes.
#' Uses sinusoidal patterns based on typical gait characteristics.
#' 
#' @param n_subjects integer number of subjects to generate
#' @param n_tasks integer number of tasks per subject  
#' @param n_cycles integer number of gait cycles per subject-task combination
#' @param points_per_cycle integer number of phase points per cycle (default: 150)
#' @param add_noise logical whether to add realistic noise to data
#' @param seed integer random seed for reproducibility
#' @return data.table with synthetic phase-indexed biomechanical data
generateSyntheticGaitData <- function(n_subjects = 3, n_tasks = 2, n_cycles = 5,
                                     points_per_cycle = 150L, add_noise = TRUE, 
                                     seed = 42) {
  set.seed(seed)
  
  # Define tasks and subjects
  subjects <- sprintf("SUB%02d", seq_len(n_subjects))
  tasks <- c("normal_walk", "slow_walk", "fast_walk", "incline_walk", "decline_walk")[seq_len(n_tasks)]
  
  # Generate phase vector (0 to 100)
  phase_vec <- seq(0, 100, length.out = points_per_cycle)
  phase_rad <- phase_vec * 2 * pi / 100
  
  # Initialize data container
  all_data <- list()
  data_idx <- 1
  
  for (subj in subjects) {
    for (task in tasks) {
      for (cycle in seq_len(n_cycles)) {
        
        # Task-specific parameters
        speed_factor <- switch(task,
          "normal_walk" = 1.0,
          "slow_walk" = 0.7,
          "fast_walk" = 1.4,
          "incline_walk" = 0.8,
          "decline_walk" = 1.1
        )
        
        # Individual subject variation (±15%)
        subj_variation <- 1 + 0.15 * (as.numeric(substr(subj, 4, 5)) - n_subjects/2) / (n_subjects/2)
        
        # Cycle-to-cycle variation (±10%)
        cycle_variation <- 1 + 0.1 * rnorm(1)
        
        # Combined scaling factor
        scale_factor <- speed_factor * subj_variation * cycle_variation
        
        # Generate realistic joint angles (in radians)
        hip_flexion_ipsi <- 0.5236 * sin(phase_rad - pi/6) * scale_factor  # ~30deg peak
        hip_flexion_contra <- 0.5236 * sin(phase_rad + pi - pi/6) * scale_factor
        
        knee_flexion_ipsi <- 0.8727 * (sin(2 * phase_rad) + 0.5 * sin(phase_rad)) * scale_factor  # ~50deg peak
        knee_flexion_contra <- 0.8727 * (sin(2 * (phase_rad + pi)) + 0.5 * sin(phase_rad + pi)) * scale_factor
        
        ankle_flexion_ipsi <- 0.3491 * sin(phase_rad - pi/3) * scale_factor  # ~20deg peak
        ankle_flexion_contra <- 0.3491 * sin(phase_rad + pi - pi/3) * scale_factor
        
        # Generate joint velocities (rad/s)
        hip_velocity_ipsi <- 2 * pi * 0.5236 * cos(phase_rad - pi/6) * scale_factor / 100
        hip_velocity_contra <- 2 * pi * 0.5236 * cos(phase_rad + pi - pi/6) * scale_factor / 100
        
        knee_velocity_ipsi <- 2 * pi * 0.8727 * (2 * cos(2 * phase_rad) + 0.5 * cos(phase_rad)) * scale_factor / 100
        knee_velocity_contra <- 2 * pi * 0.8727 * (2 * cos(2 * (phase_rad + pi)) + 0.5 * cos(phase_rad + pi)) * scale_factor / 100
        
        ankle_velocity_ipsi <- 2 * pi * 0.3491 * cos(phase_rad - pi/3) * scale_factor / 100
        ankle_velocity_contra <- 2 * pi * 0.3491 * cos(phase_rad + pi - pi/3) * scale_factor / 100
        
        # Generate joint moments (Nm) - more complex patterns
        hip_flexion_moment_ipsi <- 80 * sin(phase_rad) * scale_factor
        hip_flexion_moment_contra <- 80 * sin(phase_rad + pi) * scale_factor
        hip_abduction_moment_ipsi <- 60 * sin(phase_rad - pi/4) * scale_factor
        hip_abduction_moment_contra <- 60 * sin(phase_rad + pi - pi/4) * scale_factor
        hip_rotation_moment_ipsi <- 30 * sin(2 * phase_rad) * scale_factor
        hip_rotation_moment_contra <- 30 * sin(2 * (phase_rad + pi)) * scale_factor
        
        knee_flexion_moment_ipsi <- 100 * sin(phase_rad + pi/2) * scale_factor
        knee_flexion_moment_contra <- 100 * sin(phase_rad + pi + pi/2) * scale_factor
        knee_abduction_moment_ipsi <- 40 * sin(phase_rad) * scale_factor
        knee_abduction_moment_contra <- 40 * sin(phase_rad + pi) * scale_factor
        knee_rotation_moment_ipsi <- 20 * sin(3 * phase_rad) * scale_factor
        knee_rotation_moment_contra <- 20 * sin(3 * (phase_rad + pi)) * scale_factor
        
        ankle_flexion_moment_ipsi <- 120 * sin(phase_rad - pi/3) * scale_factor
        ankle_flexion_moment_contra <- 120 * sin(phase_rad + pi - pi/3) * scale_factor
        ankle_abduction_moment_ipsi <- 25 * sin(phase_rad + pi/4) * scale_factor
        ankle_abduction_moment_contra <- 25 * sin(phase_rad + pi + pi/4) * scale_factor
        ankle_rotation_moment_ipsi <- 15 * sin(2 * phase_rad + pi/6) * scale_factor
        ankle_rotation_moment_contra <- 15 * sin(2 * (phase_rad + pi) + pi/6) * scale_factor
        
        # Add realistic noise if requested
        if (add_noise) {
          noise_level <- 0.05  # 5% noise
          
          hip_flexion_ipsi <- hip_flexion_ipsi + rnorm(points_per_cycle, 0, noise_level * abs(hip_flexion_ipsi))
          hip_flexion_contra <- hip_flexion_contra + rnorm(points_per_cycle, 0, noise_level * abs(hip_flexion_contra))
          knee_flexion_ipsi <- knee_flexion_ipsi + rnorm(points_per_cycle, 0, noise_level * abs(knee_flexion_ipsi))
          knee_flexion_contra <- knee_flexion_contra + rnorm(points_per_cycle, 0, noise_level * abs(knee_flexion_contra))
          ankle_flexion_ipsi <- ankle_flexion_ipsi + rnorm(points_per_cycle, 0, noise_level * abs(ankle_flexion_ipsi))
          ankle_flexion_contra <- ankle_flexion_contra + rnorm(points_per_cycle, 0, noise_level * abs(ankle_flexion_contra))
          
          # Add noise to moments
          hip_flexion_moment_ipsi <- hip_flexion_moment_ipsi + rnorm(points_per_cycle, 0, 5)
          hip_flexion_moment_contra <- hip_flexion_moment_contra + rnorm(points_per_cycle, 0, 5)
          knee_flexion_moment_ipsi <- knee_flexion_moment_ipsi + rnorm(points_per_cycle, 0, 8)
          knee_flexion_moment_contra <- knee_flexion_moment_contra + rnorm(points_per_cycle, 0, 8)
          ankle_flexion_moment_ipsi <- ankle_flexion_moment_ipsi + rnorm(points_per_cycle, 0, 10)
          ankle_flexion_moment_contra <- ankle_flexion_moment_contra + rnorm(points_per_cycle, 0, 10)
        }
        
        # Create data.table for this cycle
        cycle_data <- data.table(
          subject = rep(subj, points_per_cycle),
          task = rep(task, points_per_cycle),
          phase = phase_vec,
          
          # Angles (rad)
          hip_flexion_angle_ipsi_rad = hip_flexion_ipsi,
          hip_flexion_angle_contra_rad = hip_flexion_contra,
          knee_flexion_angle_ipsi_rad = knee_flexion_ipsi,
          knee_flexion_angle_contra_rad = knee_flexion_contra,
          ankle_flexion_angle_ipsi_rad = ankle_flexion_ipsi,
          ankle_flexion_angle_contra_rad = ankle_flexion_contra,
          
          # Velocities (rad/s)
          hip_flexion_velocity_ipsi_rad_s = hip_velocity_ipsi,
          hip_flexion_velocity_contra_rad_s = hip_velocity_contra,
          knee_flexion_velocity_ipsi_rad_s = knee_velocity_ipsi,
          knee_flexion_velocity_contra_rad_s = knee_velocity_contra,
          ankle_flexion_velocity_ipsi_rad_s = ankle_velocity_ipsi,
          ankle_flexion_velocity_contra_rad_s = ankle_velocity_contra,
          
          # Moments (Nm)
          hip_flexion_moment_ipsi_Nm = hip_flexion_moment_ipsi,
          hip_flexion_moment_contra_Nm = hip_flexion_moment_contra,
          hip_abduction_moment_ipsi_Nm = hip_abduction_moment_ipsi,
          hip_abduction_moment_contra_Nm = hip_abduction_moment_contra,
          hip_rotation_moment_ipsi_Nm = hip_rotation_moment_ipsi,
          hip_rotation_moment_contra_Nm = hip_rotation_moment_contra,
          
          knee_flexion_moment_ipsi_Nm = knee_flexion_moment_ipsi,
          knee_flexion_moment_contra_Nm = knee_flexion_moment_contra,
          knee_abduction_moment_ipsi_Nm = knee_abduction_moment_ipsi,
          knee_abduction_moment_contra_Nm = knee_abduction_moment_contra,
          knee_rotation_moment_ipsi_Nm = knee_rotation_moment_ipsi,
          knee_rotation_moment_contra_Nm = knee_rotation_moment_contra,
          
          ankle_flexion_moment_ipsi_Nm = ankle_flexion_moment_ipsi,
          ankle_flexion_moment_contra_Nm = ankle_flexion_moment_contra,
          ankle_abduction_moment_ipsi_Nm = ankle_abduction_moment_ipsi,
          ankle_abduction_moment_contra_Nm = ankle_abduction_moment_contra,
          ankle_rotation_moment_ipsi_Nm = ankle_rotation_moment_ipsi,
          ankle_rotation_moment_contra_Nm = ankle_rotation_moment_contra
        )
        
        all_data[[data_idx]] <- cycle_data
        data_idx <- data_idx + 1
      }
    }
  }
  
  # Combine all data
  final_data <- rbindlist(all_data)
  
  return(final_data)
}

#' Generate Edge Case Test Data
#' 
#' Creates data with various edge cases for robust testing.
#' 
#' @param test_case character type of edge case to generate
#' @param seed integer random seed for reproducibility
#' @return data.table with edge case data
generateEdgeCaseData <- function(test_case = "missing_values", seed = 42) {
  set.seed(seed)
  
  switch(test_case,
    "missing_values" = {
      base_data <- generateSyntheticGaitData(n_subjects = 2, n_tasks = 1, n_cycles = 2, seed = seed)
      # Introduce missing values in random locations
      n_missing <- round(0.1 * nrow(base_data))  # 10% missing
      missing_rows <- sample(nrow(base_data), n_missing)
      missing_cols <- sample(names(base_data)[4:ncol(base_data)], 3)  # Skip subject, task, phase
      
      for (col in missing_cols) {
        base_data[missing_rows, (col) := NA]
      }
      
      return(base_data)
    },
    
    "extreme_values" = {
      base_data <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 1, seed = seed, add_noise = FALSE)
      # Add extreme values
      extreme_rows <- sample(nrow(base_data), 5)
      base_data[extreme_rows, hip_flexion_angle_ipsi_rad := pi + 1]  # Beyond normal range
      base_data[extreme_rows, knee_flexion_moment_ipsi_Nm := 500]    # Very high moment
      
      return(base_data)
    },
    
    "wrong_dimensions" = {
      base_data <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 1, seed = seed)
      # Add extra rows to break 150-point cycle assumption
      extra_rows <- base_data[1:25]
      extra_rows[, phase := phase + 100]  # Extend phase beyond normal range
      
      return(rbind(base_data, extra_rows))
    },
    
    "single_cycle" = {
      generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 1, seed = seed)
    },
    
    "large_dataset" = {
      generateSyntheticGaitData(n_subjects = 10, n_tasks = 5, n_cycles = 20, seed = seed)
    },
    
    "empty_data" = {
      data.table(
        subject = character(0),
        task = character(0),
        phase = numeric(0),
        hip_flexion_angle_ipsi_rad = numeric(0)
      )
    },
    
    stop(sprintf("Unknown test case: %s", test_case))
  )
}

#' Create Temporary Test File
#' 
#' Creates a temporary parquet file with test data for file-based tests.
#' 
#' @param data data.table to write to file
#' @param format character file format ("parquet" or "csv")
#' @return character path to temporary file
createTempTestFile <- function(data, format = "parquet") {
  temp_file <- tempfile(fileext = paste0(".", format))
  
  if (format == "parquet") {
    if (!requireNamespace("arrow", quietly = TRUE)) {
      skip("arrow package not available")
    }
    arrow::write_parquet(data, temp_file)
  } else if (format == "csv") {
    write.csv(data, temp_file, row.names = FALSE)
  } else {
    stop(sprintf("Unsupported format: %s", format))
  }
  
  return(temp_file)
}

#' Clean Up Test Files
#' 
#' Removes temporary test files created during testing.
#' 
#' @param file_paths character vector of file paths to remove
cleanupTestFiles <- function(file_paths) {
  for (file_path in file_paths) {
    if (file.exists(file_path)) {
      unlink(file_path)
    }
  }
}

#' Validate Test Data Structure
#' 
#' Checks if generated test data has expected structure for biomechanical analysis.
#' 
#' @param data data.table to validate
#' @param expected_subjects integer expected number of subjects
#' @param expected_tasks integer expected number of tasks
#' @param expected_cycles integer expected number of cycles per subject-task
#' @return logical TRUE if structure is valid
validateTestDataStructure <- function(data, expected_subjects, expected_tasks, expected_cycles) {
  
  # Check basic structure
  if (!is.data.table(data)) return(FALSE)
  if (nrow(data) == 0) return(FALSE)
  
  # Check required columns
  required_cols <- c("subject", "task", "phase")
  if (!all(required_cols %in% names(data))) return(FALSE)
  
  # Check dimensions
  actual_subjects <- length(unique(data$subject))
  actual_tasks <- length(unique(data$task))
  
  if (actual_subjects != expected_subjects) return(FALSE)
  if (actual_tasks != expected_tasks) return(FALSE)
  
  # Check cycle structure (should be 150 points per cycle)
  cycle_counts <- data[, .N, by = .(subject, task)]
  expected_points <- expected_cycles * 150
  
  if (!all(cycle_counts$N == expected_points)) return(FALSE)
  
  # Check phase range
  if (min(data$phase) < 0 || max(data$phase) > 100) return(FALSE)
  
  # Check for biomechanical features
  angle_cols <- names(data)[grepl("angle.*_rad$", names(data))]
  moment_cols <- names(data)[grepl("moment.*_Nm$", names(data))]
  
  if (length(angle_cols) == 0 && length(moment_cols) == 0) return(FALSE)
  
  return(TRUE)
}

#' Generate Performance Test Data
#' 
#' Creates large datasets for performance testing.
#' 
#' @param size character size category ("small", "medium", "large", "xlarge")
#' @param seed integer random seed
#' @return data.table with performance test data
generatePerformanceTestData <- function(size = "medium", seed = 42) {
  
  params <- switch(size,
    "small" = list(n_subjects = 5, n_tasks = 2, n_cycles = 5),
    "medium" = list(n_subjects = 20, n_tasks = 3, n_cycles = 10),
    "large" = list(n_subjects = 50, n_tasks = 5, n_cycles = 20),
    "xlarge" = list(n_subjects = 100, n_tasks = 8, n_cycles = 30),
    stop(sprintf("Unknown size: %s", size))
  )
  
  return(generateSyntheticGaitData(
    n_subjects = params$n_subjects, 
    n_tasks = params$n_tasks, 
    n_cycles = params$n_cycles,
    seed = seed
  ))
}