# Basic Data Loading Example
# ========================

library(LocomotionData)

#' Load locomotion data and explore basic structure
#' 
#' This example demonstrates how to load phase-indexed biomechanical
#' data and perform basic exploration
#' 
#' @example
#' # Assuming you have a locomotion dataset
#' loco <- loadLocomotionData("gait_study.parquet")

# Create example data for demonstration (replace with your data file)
create_example_data <- function() {
  # This would typically be your actual data file
  subjects <- paste0("SUB", sprintf("%02d", 1:5))
  tasks <- c("normal_walk", "fast_walk", "slow_walk")
  
  # Generate phase-indexed data (150 points per cycle)
  data_list <- list()
  
  for (subj in subjects) {
    for (task in tasks) {
      # Create one gait cycle (150 points)
      phase <- seq(0, 100, length.out = 150)
      
      # Generate realistic knee flexion pattern
      knee_angle <- 0.2 * sin(2 * pi * phase / 100) + rnorm(150, 0, 0.02)
      
      # Generate realistic hip flexion pattern  
      hip_angle <- 0.3 * sin(2 * pi * phase / 100 + pi/4) + rnorm(150, 0, 0.02)
      
      cycle_data <- data.frame(
        subject = subj,
        task = task,
        phase = phase,
        knee_flexion_angle_contra_rad = knee_angle,
        hip_flexion_angle_contra_rad = hip_angle
      )
      
      data_list[[length(data_list) + 1]] <- cycle_data
    }
  }
  
  # Combine all data
  combined_data <- do.call(rbind, data_list)
  return(combined_data)
}

# Create and save example data
example_data <- create_example_data()

# Save as CSV for demonstration
write.csv(example_data, "example_gait_data.csv", row.names = FALSE)

# Now load with LocomotionData
loco <- loadLocomotionData("example_gait_data.csv")

# Explore the data structure
cat("=== LocomotionData Object ===\n")
show(loco)

cat("\n=== Detailed Summary ===\n")
summary(loco)

# Basic data access
cat("\n=== Basic Data Access ===\n")
cat("Subjects:", paste(getSubjects(loco), collapse = ", "), "\n")
cat("Tasks:", paste(getTasks(loco), collapse = ", "), "\n")
cat("Features:", paste(getFeatures(loco), collapse = ", "), "\n")

# Extract cycles for one subject-task combination
cat("\n=== Extract Gait Cycles ===\n")
cycles_result <- getCycles(loco, "SUB01", "normal_walk")

if (!is.null(cycles_result$data_3d)) {
  cat("Cycles array dimensions:", dim(cycles_result$data_3d), "\n")
  cat("Features:", paste(cycles_result$feature_names, collapse = ", "), "\n")
  
  # Calculate mean patterns
  mean_patterns <- getMeanPatterns(loco, "SUB01", "normal_walk")
  cat("Mean patterns calculated for", length(mean_patterns), "features\n")
  
  # Show knee flexion statistics
  knee_mean <- mean_patterns[["knee_flexion_angle_contra_rad"]]
  cat("Knee flexion statistics:\n")
  cat("  Mean:", round(mean(knee_mean), 3), "rad\n")
  cat("  Range:", round(range(knee_mean), 3), "rad\n")
  cat("  Max flexion:", round(max(knee_mean), 3), "rad\n")
}

# Data quality assessment
cat("\n=== Data Quality Assessment ===\n")
validation_report <- getValidationReport(loco)

if (length(validation_report) > 0) {
  cat("Standard compliant variables:", length(validation_report$standard_compliant), "\n")
  cat("Non-standard variables:", length(validation_report$non_standard), "\n")
}

# Clean up
file.remove("example_gait_data.csv")

cat("\n=== Example completed successfully! ===\n")