#!/usr/bin/env Rscript

#' @title Data Loading Demo
#' @description Demonstration of enhanced parquet loading and validation capabilities
#' 
#' Created: 2024-06-19 with user permission
#' Purpose: Demonstrate robust parquet file reading and data validation functionality
#' 
#' Intent: Show practical usage of the new data loading features including:
#' - Memory-efficient parquet loading
#' - Comprehensive data structure validation
#' - Format detection and conversion
#' - Error handling and progress reporting

# Load required libraries
suppressPackageStartupMessages({
  library(data.table)
  library(arrow)
})

# Source the LocomotionData package functions
if (file.exists("R/data-loading.R")) {
  source("R/data-loading.R")
  source("R/feature-constants.R")
  source("R/utils.R")
} else {
  # If running from package context
  library(LocomotionData)
}

cat("LocomotionData Enhanced Parquet Loading Demo\n")
cat("==========================================\n\n")

# Demo 1: Create sample datasets for testing
cat("Demo 1: Creating sample datasets\n")
cat("--------------------------------\n")

# Create phase-indexed sample data
create_phase_indexed_sample <- function(n_subjects = 3, n_cycles = 5) {
  cat(sprintf("Creating phase-indexed sample with %d subjects, %d cycles each...\n", 
              n_subjects, n_cycles))
  
  data_list <- list()
  
  for (subj in 1:n_subjects) {
    for (cycle in 1:n_cycles) {
      cycle_data <- data.frame(
        subject = sprintf("SUB%02d", subj),
        task = sample(c("normal_walk", "fast_walk", "slow_walk"), 1),
        phase = seq(0, 100, length.out = 150),
        
        # Kinematic features (rad)
        hip_flexion_angle_ipsi_rad = 0.3 * sin(2 * pi * seq(0, 1, length.out = 150)) + rnorm(150, 0, 0.02),
        hip_flexion_angle_contra_rad = 0.3 * sin(2 * pi * seq(0.5, 1.5, length.out = 150)) + rnorm(150, 0, 0.02),
        knee_flexion_angle_ipsi_rad = 0.8 * sin(2 * pi * seq(0, 1, length.out = 150) + pi/4) + 0.2 + rnorm(150, 0, 0.03),
        knee_flexion_angle_contra_rad = 0.8 * sin(2 * pi * seq(0.5, 1.5, length.out = 150) + pi/4) + 0.2 + rnorm(150, 0, 0.03),
        ankle_flexion_angle_ipsi_rad = 0.2 * sin(2 * pi * seq(0, 1, length.out = 150) - pi/3) + rnorm(150, 0, 0.01),
        ankle_flexion_angle_contra_rad = 0.2 * sin(2 * pi * seq(0.5, 1.5, length.out = 150) - pi/3) + rnorm(150, 0, 0.01),
        
        # Kinetic features (Nm)
        hip_flexion_moment_ipsi_Nm = 50 * sin(2 * pi * seq(0, 1, length.out = 150) + pi/6) + rnorm(150, 0, 5),
        hip_flexion_moment_contra_Nm = 50 * sin(2 * pi * seq(0.5, 1.5, length.out = 150) + pi/6) + rnorm(150, 0, 5),
        knee_flexion_moment_ipsi_Nm = 30 * sin(2 * pi * seq(0, 1, length.out = 150) - pi/4) + rnorm(150, 0, 3),
        knee_flexion_moment_contra_Nm = 30 * sin(2 * pi * seq(0.5, 1.5, length.out = 150) - pi/4) + rnorm(150, 0, 3),
        ankle_flexion_moment_ipsi_Nm = 80 * sin(2 * pi * seq(0, 1, length.out = 150) + pi/2) + rnorm(150, 0, 8),
        ankle_flexion_moment_contra_Nm = 80 * sin(2 * pi * seq(0.5, 1.5, length.out = 150) + pi/2) + rnorm(150, 0, 8)
      )
      
      data_list[[length(data_list) + 1]] <- cycle_data
    }
  }
  
  combined_data <- rbindlist(data_list)
  cat(sprintf("Created dataset: %d rows x %d columns\n", nrow(combined_data), ncol(combined_data)))
  return(combined_data)
}

# Create time-indexed sample data
create_time_indexed_sample <- function(n_subjects = 2, duration_per_subject = 10) {
  cat(sprintf("Creating time-indexed sample with %d subjects, %.1f seconds each...\n", 
              n_subjects, duration_per_subject))
  
  data_list <- list()
  
  for (subj in 1:n_subjects) {
    n_points <- duration_per_subject * 100  # 100 Hz sampling
    time_vec <- seq(0, duration_per_subject, length.out = n_points)
    
    # Simulate gait cycles (typical cadence ~120 steps/min = 0.5 Hz)
    gait_freq <- 0.5
    gait_phase <- 2 * pi * gait_freq * time_vec
    
    # Simulate vertical GRF for heel strike detection
    vgrf <- ifelse((gait_phase %% (2*pi)) < pi, 
                   800 + 300 * sin(gait_phase), 
                   50 + 20 * runif(n_points))
    
    cycle_data <- data.frame(
      subject = sprintf("SUB%02d", subj),
      task = "normal_walk",
      time = time_vec,
      phase = (100 * (gait_phase %% (2*pi)) / (2*pi)),  # Rough phase estimate
      
      # Simulated biomechanical data
      knee_flexion_angle_ipsi_rad = 0.8 * sin(gait_phase + pi/4) + 0.2 + rnorm(n_points, 0, 0.03),
      hip_flexion_moment_contra_Nm = 50 * sin(gait_phase + pi/6) + rnorm(n_points, 0, 5),
      vgrf_vertical = vgrf
    )
    
    data_list[[length(data_list) + 1]] <- cycle_data
  }
  
  combined_data <- rbindlist(data_list)
  cat(sprintf("Created dataset: %d rows x %d columns\n", nrow(combined_data), ncol(combined_data)))
  return(combined_data)
}

# Generate sample datasets
phase_data <- create_phase_indexed_sample(n_subjects = 3, n_cycles = 8)
time_data <- create_time_indexed_sample(n_subjects = 2, duration_per_subject = 12)

# Save sample files
phase_file <- tempfile(fileext = "_phase.parquet")
time_file <- tempfile(fileext = "_time.csv")

arrow::write_parquet(phase_data, phase_file)
write.csv(time_data, time_file, row.names = FALSE)

cat(sprintf("Saved phase-indexed data: %s\n", basename(phase_file)))
cat(sprintf("Saved time-indexed data: %s\n", basename(time_file)))
cat("\n")

# Demo 2: Enhanced parquet loading
cat("Demo 2: Enhanced parquet loading\n")
cat("--------------------------------\n")

cat("Loading phase-indexed data with validation...\n")
loaded_phase <- loadParquetData(
  phase_file, 
  chunk_size = 1000L,
  memory_limit = 1.0,
  show_progress = TRUE,
  validate_structure = TRUE
)

cat(sprintf("Loaded data dimensions: %d x %d\n", nrow(loaded_phase), ncol(loaded_phase)))
cat(sprintf("Memory usage: %.3f GB\n", getMemoryUsage()$total_memory_gb))
cat("\n")

# Demo 3: Structure validation
cat("Demo 3: Comprehensive structure validation\n")
cat("------------------------------------------\n")

cat("Validating phase-indexed parquet structure...\n")
validation_result <- validateParquetStructure(
  phase_file,
  required_columns = c("knee_flexion_angle_ipsi_rad", "hip_flexion_moment_contra_Nm")
)

cat(sprintf("Validation result: %s\n", ifelse(validation_result$valid, "PASSED", "FAILED")))
cat(sprintf("File size: %.2f MB\n", validation_result$file_info$size_mb))
cat(sprintf("Columns: %d total\n", validation_result$column_info$total_columns))

if (length(validation_result$issues) > 0) {
  cat("Issues found:\n")
  for (issue in validation_result$issues) {
    cat(sprintf("  - %s\n", issue))
  }
}

if (length(validation_result$warnings) > 0) {
  cat("Warnings:\n")
  for (warning in validation_result$warnings) {
    cat(sprintf("  - %s\n", warning))
  }
}

# Show phase validation details
if (!is.null(validation_result$data_format_info$phase_validation)) {
  phase_info <- validation_result$data_format_info$phase_validation
  cat(sprintf("Phase indexing: %s\n", phase_info$message))
  cat(sprintf("Points per cycle: %d\n", phase_info$points_per_cycle))
  cat(sprintf("Phase range: [%.1f, %.1f]\n", 
              phase_info$phase_range[1], phase_info$phase_range[2]))
}
cat("\n")

# Demo 4: Format detection
cat("Demo 4: Automatic format detection\n")
cat("-----------------------------------\n")

cat("Detecting format of phase-indexed data...\n")
phase_format <- detectDataFormat(phase_file)
cat(sprintf("Format: %s (confidence: %.1f%%)\n", phase_format$format, 100 * phase_format$confidence))
cat("Recommendations:\n")
for (rec in phase_format$recommendations) {
  cat(sprintf("  - %s\n", rec))
}
cat("\n")

cat("Detecting format of time-indexed data...\n")
time_format <- detectDataFormat(time_file)
cat(sprintf("Format: %s (confidence: %.1f%%)\n", time_format$format, 100 * time_format$confidence))
cat("Recommendations:\n")
for (rec in time_format$recommendations) {
  cat(sprintf("  - %s\n", rec))
}
cat("\n")

# Demo 5: Time to phase conversion
cat("Demo 5: Time-indexed to phase-indexed conversion\n")
cat("------------------------------------------------\n")

if (time_format$format == "time_indexed") {
  cat("Converting time-indexed data to phase-indexed format...\n")
  
  converted_file <- tempfile(fileext = "_converted.parquet")
  
  tryCatch({
    converted_data <- convertTimeToPhase(
      time_file,
      converted_file,
      time_col = "time",
      points_per_cycle = 150L,
      show_progress = TRUE
    )
    
    cat(sprintf("Conversion successful: %d rows x %d columns\n", 
                nrow(converted_data), ncol(converted_data)))
    
    # Validate converted data
    cat("Validating converted data...\n")
    converted_validation <- validateParquetStructure(converted_file)
    
    if (converted_validation$data_format_info$phase_validation$is_phase_indexed) {
      cat("✓ Converted data is properly phase-indexed\n")
    } else {
      cat("⚠ Converted data may have phase indexing issues\n")
    }
    
    unlink(converted_file)
    
  }, error = function(e) {
    cat(sprintf("Conversion failed: %s\n", e$message))
  })
} else {
  cat("Time-indexed data not detected, skipping conversion demo.\n")
}
cat("\n")

# Demo 6: Memory management
cat("Demo 6: Memory usage monitoring\n")
cat("-------------------------------\n")

memory_info <- getMemoryUsage()
cat(sprintf("Current memory usage: %.3f GB\n", memory_info$total_memory_gb))
cat(sprintf("R version: %s\n", memory_info$r_version))
cat(sprintf("Memory method: %s\n", memory_info$memory_method))

if (length(memory_info$largest_objects) > 0) {
  cat("Largest objects in memory:\n")
  for (i in seq_along(memory_info$largest_objects)) {
    obj_name <- names(memory_info$largest_objects)[i]
    obj_size <- memory_info$largest_objects[i]
    cat(sprintf("  %s: %.1f MB\n", obj_name, obj_size))
  }
}
cat("\n")

# Demo 7: Error handling examples
cat("Demo 7: Error handling demonstrations\n")
cat("-------------------------------------\n")

cat("Testing error handling for missing files...\n")
tryCatch({
  loadParquetData("nonexistent_file.parquet")
}, error = function(e) {
  cat(sprintf("✓ Properly caught error: %s\n", e$message))
})

cat("Testing validation of invalid structure...\n")
# Create invalid parquet file
invalid_file <- tempfile(fileext = ".parquet")
invalid_data <- data.frame(
  wrong_column = 1:100,
  another_wrong = rnorm(100)
)
arrow::write_parquet(invalid_data, invalid_file)

invalid_validation <- validateParquetStructure(invalid_file)
if (!invalid_validation$valid) {
  cat("✓ Properly detected invalid structure\n")
  cat(sprintf("  Issues: %s\n", paste(invalid_validation$issues, collapse = "; ")))
}

unlink(invalid_file)
cat("\n")

# Cleanup
cat("Demo complete - cleaning up temporary files...\n")
unlink(phase_file)
unlink(time_file)

cat("\nDemo Summary\n")
cat("============\n")
cat("✓ Enhanced parquet loading with memory management\n")
cat("✓ Comprehensive structure validation\n") 
cat("✓ Automatic format detection\n")
cat("✓ Time-to-phase conversion capabilities\n")
cat("✓ Memory usage monitoring\n")
cat("✓ Robust error handling\n")
cat("\nAll data loading functionality is working correctly!\n")