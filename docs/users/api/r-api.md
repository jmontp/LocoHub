# R API Reference

## Overview

The R API provides tidyverse-compatible functions for analyzing standardized biomechanical datasets with integrated statistical modeling capabilities.

!!! info "Coming Soon"
    The R API documentation is currently under development. Check back soon for complete function references.

## Core Functions

### Data Loading

#### `load_locomotion_data`
Load a standardized biomechanical dataset.

```r
data <- load_locomotion_data(filepath)
data <- load_locomotion_data(filepath, columns = c("col1", "col2"))
```

**Parameters:**
- `filepath` (character) - Path to parquet file
- `columns` (character vector, optional) - Specific columns to load

**Returns:**
- `data` (tibble) - Tibble containing the dataset

---

### Data Exploration

#### `get_subjects`
Get unique subject identifiers from dataset.

```r
subjects <- get_subjects(data)
```

#### `get_tasks`
Get unique task names from dataset.

```r
tasks <- get_tasks(data)
```

---

### Data Filtering

#### `filter_task`
Filter dataset for a specific task.

```r
filtered_data <- filter_task(data, "level_walking")

# Or using dplyr directly
filtered_data <- data %>% 
  filter(task == "level_walking")
```

#### `filter_subject`
Filter dataset for a specific subject.

```r
filtered_data <- filter_subject(data, "SUB01")

# Or using dplyr directly
filtered_data <- data %>% 
  filter(subject == "SUB01")
```

---

### Analysis Functions

#### `get_cycles`
Extract individual gait cycles.

```r
result <- get_cycles(data, subject = "SUB01", task = "level_walking")
cycles_3d <- result$cycles
features <- result$features
```

**Parameters:**
- `data` (tibble) - Dataset
- `subject` (character) - Subject ID
- `task` (character) - Task name

**Returns:**
- List containing:
  - `cycles` - 3D array of cycles
  - `features` - Tibble of cycle-level features

#### `get_mean_patterns`
Compute mean patterns across cycles.

```r
mean_patterns <- get_mean_patterns(data, subject = "SUB01", task = "level_walking")
```

#### `calculate_rom`
Calculate range of motion for all variables.

```r
rom <- calculate_rom(data, subject = "SUB01", task = "level_walking")
```

---

### Statistical Analysis

#### `compare_conditions`
Statistical comparison between conditions.

```r
comparison <- compare_conditions(
  data, 
  condition1 = list(task = "level_walking"),
  condition2 = list(task = "incline_walking"),
  method = "spm"
)
```

#### `mixed_effects_analysis`
Run mixed-effects models on biomechanical data.

```r
model <- mixed_effects_analysis(
  data,
  formula = knee_flexion_angle_ipsi_rad ~ task + (1|subject),
  phase_points = c(0, 25, 50, 75)
)
```

---

### Visualization

#### `plot_phase_patterns`
Create phase-averaged plots with confidence bands.

```r
plot_phase_patterns(
  data, 
  subject = "SUB01", 
  task = "level_walking",
  variables = c("knee_flexion_angle_ipsi_rad", "hip_flexion_angle_ipsi_rad")
)
```

#### `create_spaghetti_plot`
Create spaghetti plot showing all cycles.

```r
create_spaghetti_plot(
  data,
  subject = "SUB01",
  task = "level_walking",
  variable = "knee_flexion_angle_ipsi_rad"
)
```

---

## Usage Examples

### Basic Workflow

```r
library(locomotion)
library(tidyverse)

# Load data
data <- load_locomotion_data("converted_datasets/umich_2021_phase.parquet")

# Filter and analyze
level_walking <- data %>%
  filter(task == "level_walking")

# Get mean patterns
mean_patterns <- get_mean_patterns(level_walking, "SUB01", "level_walking")

# Visualize
plot_phase_patterns(
  level_walking,
  subject = "SUB01",
  task = "level_walking",
  variables = c("knee_flexion_angle_ipsi_rad")
)
```

### Statistical Analysis

```r
# Compare walking conditions
comparison <- data %>%
  filter(task %in% c("level_walking", "incline_walking")) %>%
  compare_conditions(
    condition1 = list(task = "level_walking"),
    condition2 = list(task = "incline_walking")
  )

# Mixed-effects model
model <- data %>%
  filter(phase_percent == 50) %>%
  lmer(knee_flexion_angle_ipsi_rad ~ task + (1|subject), data = .)
```

### Report Generation

```r
# Generate automated report
library(rmarkdown)

generate_gait_report(
  data,
  subject = "SUB01",
  output_file = "gait_analysis_report.html",
  template = "clinical"
)
```

## Integration with Tidyverse

The locomotion package is designed to work seamlessly with tidyverse:

```r
library(tidyverse)
library(locomotion)

# Complex pipeline
results <- data %>%
  filter(task == "level_walking") %>%
  group_by(subject, phase_percent) %>%
  summarise(
    knee_mean = mean(knee_flexion_angle_ipsi_rad),
    knee_sd = sd(knee_flexion_angle_ipsi_rad)
  ) %>%
  ungroup() %>%
  ggplot(aes(x = phase_percent, y = knee_mean)) +
  geom_line() +
  geom_ribbon(aes(ymin = knee_mean - knee_sd, 
                  ymax = knee_mean + knee_sd),
              alpha = 0.3)
```

## Data Structures

### Tibble Format
The main data structure is a tibble with columns:
- `subject` - Subject identifier
- `task` - Task name
- `cycle_id` - Gait cycle number
- `phase_percent` - Gait cycle phase (0-100)
- Biomechanical variables (angles in radians, moments in Nm, forces in N)

### Variable Naming Convention
- Format: `joint_motion_side_unit`
- Example: `knee_flexion_angle_ipsi_rad`
  - Joint: knee
  - Motion: flexion
  - Side: ipsi (ipsilateral) or contra (contralateral)
  - Unit: rad (radians)

## See Also

- [Python API Reference](locomotion-data-api.md)
- [MATLAB API Reference](matlab-api.md)
- [R Tutorials](../tutorials/r/)
- [Data Format Specification](../../reference/standard_spec/standard_spec.md)