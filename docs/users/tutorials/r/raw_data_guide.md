# Working with Raw Biomechanical Data in R

Guide for analyzing biomechanical data directly from parquet files without the LocomotionData R package.

## Loading Raw Data

```r
library(arrow)
library(dplyr)
library(ggplot2)

# Load phase-indexed data
data <- read_parquet("converted_datasets/umich_2021_phase.parquet")

# Examine structure
glimpse(data)
str(data)
```

## Data Structure

Raw parquet files contain:
- `subject`: Subject identifier
- `task`: Locomotion task (level_walking, incline_walking, etc.)
- `phase`: Gait cycle percentage (0-149, representing 0-100%)
- Biomechanical variables: `knee_flexion_angle_ipsi_rad`, `hip_moment_contra_Nm`, etc.

## Basic Analysis

```r
# Filter for specific subject and task
subject_data <- data %>%
  filter(subject == "SUB01", task == "level_walking")

# Calculate mean patterns
mean_patterns <- subject_data %>%
  group_by(phase) %>%
  summarise(across(where(is.numeric), mean, na.rm = TRUE))

# Plot knee angle
ggplot(mean_patterns, aes(x = phase, y = knee_flexion_angle_ipsi_rad)) +
  geom_line() +
  labs(title = "Mean Knee Flexion Angle",
       x = "Gait Cycle %", 
       y = "Angle (radians)")
```

## Advanced Processing

```r
# Calculate range of motion
rom_data <- subject_data %>%
  group_by(subject, task) %>%
  summarise(
    knee_rom = max(knee_flexion_angle_ipsi_rad) - min(knee_flexion_angle_ipsi_rad),
    .groups = "drop"
  )

# Group comparisons
group_comparison <- data %>%
  filter(task == "level_walking") %>%
  group_by(subject, phase) %>%
  summarise(mean_knee = mean(knee_flexion_angle_ipsi_rad, na.rm = TRUE), 
            .groups = "drop")
```

For more structured analysis, consider using the [LocomotionData R package](index.md).