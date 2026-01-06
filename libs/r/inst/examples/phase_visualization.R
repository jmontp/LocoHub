# Phase Pattern Visualization Example
# ==================================

library(LocomotionData)
library(ggplot2)

#' Demonstrate phase pattern visualization capabilities
#' 
#' This example shows how to create publication-quality plots
#' of gait cycle phase patterns with confidence intervals

# Create example locomotion data
create_realistic_gait_data <- function() {
  subjects <- paste0("SUB", sprintf("%02d", 1:3))
  tasks <- c("normal_walk", "fast_walk")
  
  data_list <- list()
  
  for (subj in subjects) {
    for (task in tasks) {
      # Create multiple gait cycles for this subject-task
      n_cycles <- 5
      
      for (cycle in 1:n_cycles) {
        phase <- seq(0, 100, length.out = 150)
        
        # Task-specific parameters
        if (task == "normal_walk") {
          knee_amplitude <- 0.8 + rnorm(1, 0, 0.1)
          hip_amplitude <- 0.5 + rnorm(1, 0, 0.05)
          ankle_amplitude <- 0.3 + rnorm(1, 0, 0.05)
        } else { # fast_walk
          knee_amplitude <- 1.0 + rnorm(1, 0, 0.1)
          hip_amplitude <- 0.7 + rnorm(1, 0, 0.05)
          ankle_amplitude <- 0.4 + rnorm(1, 0, 0.05)
        }
        
        # Generate realistic joint patterns
        knee_angle <- knee_amplitude * sin(2 * pi * phase / 100) + 
                     rnorm(150, 0, 0.02)
        
        hip_angle <- hip_amplitude * sin(2 * pi * phase / 100 + pi/6) + 
                    rnorm(150, 0, 0.02)
        
        ankle_angle <- ankle_amplitude * sin(2 * pi * phase / 100 - pi/3) + 
                      rnorm(150, 0, 0.02)
        
        cycle_data <- data.frame(
          subject = subj,
          task = task,
          phase = phase,
          knee_flexion_angle_contra_rad = knee_angle,
          hip_flexion_angle_contra_rad = hip_angle,
          ankle_flexion_angle_contra_rad = ankle_angle,
          step_number = cycle
        )
        
        data_list[[length(data_list) + 1]] <- cycle_data
      }
    }
  }
  
  return(do.call(rbind, data_list))
}

# Create example data
gait_data <- create_realistic_gait_data()
write.csv(gait_data, "gait_visualization_data.csv", row.names = FALSE)

# Load with LocomotionData
loco <- loadLocomotionData("gait_visualization_data.csv")

cat("=== Phase Pattern Visualization Examples ===\n")

# 1. Single feature mean pattern with confidence bands
cat("\n1. Single Feature Visualization\n")
cat("   Creating knee flexion pattern plot...\n")

p1 <- plotPhasePatterns(loco, "SUB01", "normal_walk",
                       features = "knee_flexion_angle_contra_rad",
                       plot_type = "mean")

print(p1)

# 2. Multiple features comparison
cat("\n2. Multiple Joint Patterns\n")
cat("   Creating multi-joint comparison plot...\n")

p2 <- plotPhasePatterns(loco, "SUB01", "normal_walk",
                       features = c("knee_flexion_angle_contra_rad",
                                   "hip_flexion_angle_contra_rad",
                                   "ankle_flexion_angle_contra_rad"),
                       plot_type = "mean")

print(p2)

# 3. Task comparison
cat("\n3. Task Comparison Visualization\n")
cat("   Comparing normal vs fast walking...\n")

p3 <- plotTaskComparison(loco, "SUB01",
                        tasks = c("normal_walk", "fast_walk"),
                        features = "knee_flexion_angle_contra_rad")

print(p3)

# 4. Individual cycles (spaghetti plot)
cat("\n4. Individual Cycles Visualization\n")
cat("   Showing variability across cycles...\n")

p4 <- plotPhasePatterns(loco, "SUB01", "normal_walk",
                       features = "knee_flexion_angle_contra_rad",
                       plot_type = "spaghetti")

print(p4)

# 5. Combined view (mean + individual cycles)
cat("\n5. Combined Visualization\n")
cat("   Mean pattern with individual cycle overlay...\n")

p5 <- plotPhasePatterns(loco, "SUB01", "normal_walk",
                       features = "knee_flexion_angle_contra_rad",
                       plot_type = "both")

print(p5)

# 6. Custom styling example
cat("\n6. Custom Styling Example\n")
cat("   Adding publication-ready formatting...\n")

p6 <- plotPhasePatterns(loco, "SUB01", "normal_walk",
                       features = "knee_flexion_angle_contra_rad",
                       plot_type = "mean") +
  theme_minimal() +
  labs(title = "Knee Flexion During Normal Walking",
       subtitle = "Mean ± 95% Confidence Interval",
       x = "Gait Cycle (%)",
       y = "Knee Flexion Angle (rad)",
       caption = "Subject SUB01, n=5 cycles") +
  theme(plot.title = element_text(size = 14, face = "bold"),
        plot.subtitle = element_text(size = 12),
        axis.title = element_text(size = 12),
        axis.text = element_text(size = 10))

print(p6)

# 7. Statistical summary of patterns
cat("\n7. Pattern Statistics\n")

# Calculate ROM and peak values
rom_results <- calculateROM(loco, "SUB01", "normal_walk",
                           features = "knee_flexion_angle_contra_rad")

summary_stats <- getSummaryStatistics(loco, "SUB01", "normal_walk")

cat("Knee Flexion Range of Motion (ROM):\n")
if (length(rom_results) > 0) {
  knee_rom <- rom_results[["knee_flexion_angle_contra_rad"]]
  cat("  Mean ROM:", round(mean(knee_rom, na.rm = TRUE), 3), "rad\n")
  cat("  ROM Range:", round(range(knee_rom, na.rm = TRUE), 3), "rad\n")
}

# 8. Multi-subject comparison
cat("\n8. Multi-Subject Comparison\n")
cat("   Comparing patterns across subjects...\n")

subjects_to_compare <- c("SUB01", "SUB02", "SUB03")
colors <- c("#1f77b4", "#ff7f0e", "#2ca02c")

# Create comparison plot manually for demonstration
comparison_data <- data.frame()

for (i in seq_along(subjects_to_compare)) {
  subj <- subjects_to_compare[i]
  mean_pattern <- getMeanPatterns(loco, subj, "normal_walk")
  
  if (!is.null(mean_pattern[["knee_flexion_angle_contra_rad"]])) {
    phase_data <- data.frame(
      phase = seq(0, 100, length.out = 150),
      angle = mean_pattern[["knee_flexion_angle_contra_rad"]],
      subject = subj
    )
    comparison_data <- rbind(comparison_data, phase_data)
  }
}

if (nrow(comparison_data) > 0) {
  p8 <- ggplot(comparison_data, aes(x = phase, y = angle, color = subject)) +
    geom_line(size = 1.2) +
    scale_color_manual(values = colors) +
    labs(title = "Knee Flexion Patterns - Multi-Subject Comparison",
         x = "Gait Cycle (%)",
         y = "Knee Flexion Angle (rad)",
         color = "Subject") +
    theme_minimal()
  
  print(p8)
}

# Clean up
file.remove("gait_visualization_data.csv")

cat("\n=== Visualization examples completed! ===\n")
cat("Tip: All plots are ggplot2 objects and can be further customized\n")
cat("     Save plots with ggsave() for publication use\n")