# Kinematic Validation Expectations Specification

**Single Source of Truth for Biomechanically Accurate Kinematic Validation Rules**

This document provides biomechanically verified kinematic validation ranges (joint angles) based on published gait analysis literature. The specification uses a modern phase system (0%, 25%, 50%, 75%) with contralateral offset logic for optimal validation efficiency.

> **📊 Related**: See [validation_expectations_kinetic.md](validation_expectations_kinetic.md) for kinetic validation rules (forces and moments).

> **📋 Version Information**: See [../development/validation_expectations_changelog.md](../development/validation_expectations_changelog.md) for detailed version history and changes.  
> **🎨 Image Generation**: See [../development/kinematic_visualization_guide.md](../development/kinematic_visualization_guide.md) for generating validation images.

> **🔄 Plot Generation**: 
> 
> **One-click regeneration (VS Code):** `Ctrl+Shift+P` → `Tasks: Run Task` → `🔄 Regenerate Kinematic Plots`
> 
> **GitHub Actions:** [![Regenerate Kinematic Plots](https://img.shields.io/badge/🔄_Regenerate-Kinematic_Plots-green?style=for-the-badge&logo=github)](https://github.com/jmontp/locomotion-data-standardization/actions/workflows/regenerate-validation-plots.yml)
> 
> **Manual commands:**
> ```bash
> python3 source/validation/generate_validation_plots.py
> # Or for specific tasks:
> python3 source/validation/generate_validation_plots.py --tasks level_walking incline_walking
> # Or for specific plot types:
> python3 source/validation/generate_validation_plots.py --forward-kinematic-only
> python3 source/validation/generate_validation_plots.py --filters-only
> ```

## Format Specification

### Two-Tier Validation Structure

**Tier 1: Generic Range Validation**
- Basic biomechanical plausibility checks
- Anatomically possible ranges across all tasks
- Applied to all variables regardless of task

**Tier 2: Task-Specific Phase Validation**
- Task-specific expected ranges and patterns
- Phase-specific validation at key points: **0%, 25%, 50%, 75%**
- Contralateral leg automatically computed with 50% phase offset
- Visual kinematic validation with min/max pose images

### Validation Table Structure

```markdown
### Task: {task_name}

**Phase-Specific Range Validation:**

#### Phase 0% (Heel Strike)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|

#### Phase 25% (Mid-Stance)  
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|

#### Phase 50% (Toe-Off)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|

#### Phase 75% (Mid-Swing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|

**Contralateral Offset Logic:**
- Contralateral leg values automatically computed with 50% phase offset
- Phase 0% ipsilateral = Phase 50% contralateral (heel strike vs toe-off)
- Phase 25% ipsilateral = Phase 75% contralateral (mid-stance vs mid-swing)

**Forward Kinematics Range Visualization:**
![Task Forward Kinematics - Phase 0%](validation/{task_name}_forward_kinematics_phase_00_range.png)
![Task Forward Kinematics - Phase 25%](validation/{task_name}_forward_kinematics_phase_25_range.png)
![Task Forward Kinematics - Phase 50%](validation/{task_name}_forward_kinematics_phase_50_range.png)
![Task Forward Kinematics - Phase 75%](validation/{task_name}_forward_kinematics_phase_75_range.png)
```

**Column Definitions:**
- `Variable`: Exact variable name (must match dataset columns)
- `Min_Value`: Minimum expected value at this phase point
- `Max_Value`: Maximum expected value at this phase point
- `Units`: Variable units (rad, N, m, etc.)
- `Notes`: Additional context or exceptions

## Validation Tables - VERIFIED




### Task: decline_walking

**🤖 AUTOMATED TUNING - DECLINE_WALKING**

⚠️  **Data-Driven Ranges**: These validation ranges were automatically generated using statistical analysis.

📊 **Source**: `umich_2021_phase.parquet` | 📈 **Method**: 95% Percentile | 🕒 **Generated**: 2025-06-12 00:25:38


**Phase-Specific Range Validation (Ipsilateral Leg Only):**

#### Phase 0% (Heel Strike)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.27 | 0.71 | rad | Data-driven statistical range |
| knee_flexion_angle_ipsi_rad | -0.08 | 0.20 | rad | Data-driven statistical range |
| ankle_flexion_angle_ipsi_rad | -0.18 | 0.35 | rad | Data-driven statistical range |

#### Phase 25% (Mid-Stance)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | -0.03 | 0.56 | rad | Data-driven statistical range |
| knee_flexion_angle_ipsi_rad | 0.08 | 0.62 | rad | Data-driven statistical range |
| ankle_flexion_angle_ipsi_rad | -0.21 | 0.01 | rad | Data-driven statistical range |

#### Phase 50% (Toe-Off)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | -0.34 | 0.37 | rad | Data-driven statistical range |
| knee_flexion_angle_ipsi_rad | 0.02 | 0.79 | rad | Data-driven statistical range |
| ankle_flexion_angle_ipsi_rad | -0.42 | -0.15 | rad | Data-driven statistical range |

#### Phase 75% (Mid-Swing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.19 | 0.73 | rad | Data-driven statistical range |
| knee_flexion_angle_ipsi_rad | 0.83 | 1.34 | rad | Data-driven statistical range |
| ankle_flexion_angle_ipsi_rad | -0.22 | 0.13 | rad | Data-driven statistical range |

**Contralateral Offset Logic:**
- **Phase 0% ipsilateral** (heel strike) = **Phase 50% contralateral** (toe-off)
- **Phase 25% ipsilateral** (mid-stance) = **Phase 75% contralateral** (mid-swing)
- **Phase 50% ipsilateral** (toe-off) = **Phase 0% contralateral** (heel strike)
- **Phase 75% ipsilateral** (mid-swing) = **Phase 25% contralateral** (mid-stance)

**Forward Kinematics Range Visualization:**

| Phase 0% (Heel Strike) | Phase 25% (Mid-Stance) | Phase 50% (Toe-Off) | Phase 75% (Mid-Swing) |
|---|---|---|---|
| ![Decline Walking Forward Kinematics Heel Strike](validation/decline_walking_forward_kinematics_phase_00_range.png) | ![Decline Walking Forward Kinematics Mid-Stance](validation/decline_walking_forward_kinematics_phase_25_range.png) | ![Decline Walking Forward Kinematics Toe-Off](validation/decline_walking_forward_kinematics_phase_50_range.png) | ![Decline Walking Forward Kinematics Mid-Swing](validation/decline_walking_forward_kinematics_phase_75_range.png) |

**Filters by Phase Validation:**

![Decline Walking Kinematic Filters by Phase](validation/decline_walking_kinematic_filters_by_phase.png)

---

### Task: incline_walking

**🤖 AUTOMATED TUNING - INCLINE_WALKING**

⚠️  **Data-Driven Ranges**: These validation ranges were automatically generated using statistical analysis.

📊 **Source**: `umich_2021_phase.parquet` | 📈 **Method**: 95% Percentile | 🕒 **Generated**: 2025-06-12 00:25:38


**Phase-Specific Range Validation (Ipsilateral Leg Only):**

#### Phase 0% (Heel Strike)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.55 | 1.25 | rad | Data-driven statistical range |
| knee_flexion_angle_ipsi_rad | 0.07 | 0.74 | rad | Data-driven statistical range |
| ankle_flexion_angle_ipsi_rad | -0.35 | 0.08 | rad | Data-driven statistical range |

#### Phase 25% (Mid-Stance)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.11 | 0.78 | rad | Data-driven statistical range |
| knee_flexion_angle_ipsi_rad | 0.08 | 0.54 | rad | Data-driven statistical range |
| ankle_flexion_angle_ipsi_rad | -0.46 | -0.12 | rad | Data-driven statistical range |

#### Phase 50% (Toe-Off)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | -0.36 | 0.41 | rad | Data-driven statistical range |
| knee_flexion_angle_ipsi_rad | -0.14 | 0.26 | rad | Data-driven statistical range |
| ankle_flexion_angle_ipsi_rad | -0.42 | -0.14 | rad | Data-driven statistical range |

#### Phase 75% (Mid-Swing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.31 | 0.93 | rad | Data-driven statistical range |
| knee_flexion_angle_ipsi_rad | 0.91 | 1.22 | rad | Data-driven statistical range |
| ankle_flexion_angle_ipsi_rad | -0.13 | 0.16 | rad | Data-driven statistical range |

**Contralateral Offset Logic:**
- **Phase 0% ipsilateral** (heel strike) = **Phase 50% contralateral** (toe-off)
- **Phase 25% ipsilateral** (mid-stance) = **Phase 75% contralateral** (mid-swing)
- **Phase 50% ipsilateral** (toe-off) = **Phase 0% contralateral** (heel strike)
- **Phase 75% ipsilateral** (mid-swing) = **Phase 25% contralateral** (mid-stance)

**Forward Kinematics Range Visualization:**

| Phase 0% (Heel Strike) | Phase 25% (Mid-Stance) | Phase 50% (Toe-Off) | Phase 75% (Mid-Swing) |
|---|---|---|---|
| ![Incline Walking Forward Kinematics Heel Strike](validation/incline_walking_forward_kinematics_phase_00_range.png) | ![Incline Walking Forward Kinematics Mid-Stance](validation/incline_walking_forward_kinematics_phase_25_range.png) | ![Incline Walking Forward Kinematics Toe-Off](validation/incline_walking_forward_kinematics_phase_50_range.png) | ![Incline Walking Forward Kinematics Mid-Swing](validation/incline_walking_forward_kinematics_phase_75_range.png) |

**Filters by Phase Validation:**

![Incline Walking Kinematic Filters by Phase](validation/incline_walking_kinematic_filters_by_phase.png)

---

### Task: level_walking

**🤖 AUTOMATED TUNING - LEVEL_WALKING**

⚠️  **Data-Driven Ranges**: These validation ranges were automatically generated using statistical analysis.

📊 **Source**: `umich_2021_phase.parquet` | 📈 **Method**: 95% Percentile | 🕒 **Generated**: 2025-06-12 00:25:38


**Phase-Specific Range Validation (Ipsilateral Leg Only):**

#### Phase 0% (Heel Strike)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.35 | 0.83 | rad | Data-driven statistical range |
| knee_flexion_angle_ipsi_rad | -0.05 | 0.25 | rad | Data-driven statistical range |
| ankle_flexion_angle_ipsi_rad | -0.15 | 0.15 | rad | Data-driven statistical range |

#### Phase 25% (Mid-Stance)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | -0.04 | 0.53 | rad | Data-driven statistical range |
| knee_flexion_angle_ipsi_rad | 0.02 | 0.36 | rad | Data-driven statistical range |
| ankle_flexion_angle_ipsi_rad | -0.22 | -0.05 | rad | Data-driven statistical range |

#### Phase 50% (Toe-Off)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | -0.36 | 0.27 | rad | Data-driven statistical range |
| knee_flexion_angle_ipsi_rad | -0.02 | 0.30 | rad | Data-driven statistical range |
| ankle_flexion_angle_ipsi_rad | -0.33 | -0.15 | rad | Data-driven statistical range |

#### Phase 75% (Mid-Swing)
| Variable | Min_Value | Max_Value | Units | Notes |
|----------|-----------|-----------|-------|-------|
| hip_flexion_angle_ipsi_rad | 0.25 | 0.78 | rad | Data-driven statistical range |
| knee_flexion_angle_ipsi_rad | 0.96 | 1.26 | rad | Data-driven statistical range |
| ankle_flexion_angle_ipsi_rad | -0.09 | 0.17 | rad | Data-driven statistical range |

**Contralateral Offset Logic:**
- **Phase 0% ipsilateral** (heel strike) = **Phase 50% contralateral** (toe-off)
- **Phase 25% ipsilateral** (mid-stance) = **Phase 75% contralateral** (mid-swing)
- **Phase 50% ipsilateral** (toe-off) = **Phase 0% contralateral** (heel strike)
- **Phase 75% ipsilateral** (mid-swing) = **Phase 25% contralateral** (mid-stance)

**Forward Kinematics Range Visualization:**

| Phase 0% (Heel Strike) | Phase 25% (Mid-Stance) | Phase 50% (Toe-Off) | Phase 75% (Mid-Swing) |
|---|---|---|---|
| ![Level Walking Forward Kinematics Heel Strike](validation/level_walking_forward_kinematics_phase_00_range.png) | ![Level Walking Forward Kinematics Mid-Stance](validation/level_walking_forward_kinematics_phase_25_range.png) | ![Level Walking Forward Kinematics Toe-Off](validation/level_walking_forward_kinematics_phase_50_range.png) | ![Level Walking Forward Kinematics Mid-Swing](validation/level_walking_forward_kinematics_phase_75_range.png) |

**Filters by Phase Validation:**

![Level Walking Kinematic Filters by Phase](validation/level_walking_kinematic_filters_by_phase.png)

## Joint Validation Range Summary

The filters by phase validation plots have been moved to their corresponding individual task sections above. Each task now includes both forward kinematics range visualizations and filters by phase validation plots.

**Reading the Filters by Phase Plots:**
- **X-axis**: Movement phase progression (0%, 25%, 50%, 75%)
- **Y-axis**: Joint angle values in radians (left) and degrees (right)
- **Layout**: 3 rows (hip, knee, ankle) × 2 columns (left leg, right leg)
- **Bounding Boxes**: Colored rectangles show valid range for each phase
- **Connecting Lines**: 
  - Red line with circles: Minimum acceptable values across phases
  - Blue line with circles: Maximum acceptable values across phases
- **Shaded Area**: Filled region between min/max shows complete acceptable range
- **Value Labels**: Degree values shown at min/max points for easy reference
- **Color Coding**: 
  - Red: Hip flexion angles
  - Teal: Knee flexion angles  
  - Blue: Ankle flexion angles

These plots make it easy to visualize how joint angle requirements change throughout the movement cycle and compare bilateral coordination patterns between left and right legs.

## Pattern Definitions

**Temporal Patterns:**
- `peak_at_X`: Maximum value occurs at phase X%
- `valley_at_X`: Minimum value occurs at phase X%
- `increasing`: Monotonic increase throughout phase range
- `decreasing`: Monotonic decrease throughout phase range
- `negative_to_positive`: Crosses zero from negative to positive
- `U_shaped`: Decreases then increases (valley in middle)
- `inverted_U`: Increases then decreases (peak in middle)

**Amplitude Patterns:**
- `near_zero`: Values close to zero throughout
- `predominantly_negative`: Mostly negative values
- `predominantly_positive`: Mostly positive values
- `variable`: High variability, no clear pattern
- `controlled_motion`: Smooth, controlled changes

## Parser Usage

This markdown file can be parsed programmatically using the companion parser:

```python
from validation_markdown_parser import ValidationMarkdownParser

parser = ValidationMarkdownParser()
validation_rules = parser.parse_file('validation_expectations.md')

# Get rules for specific task
level_walking_rules = validation_rules['level_walking']

# Validate data against rules
results = parser.validate_data(data, 'level_walking')
```

## Maintenance Guidelines

1. **Adding New Tasks**: Follow the exact table format
2. **Variable Names**: Must match dataset column names exactly
3. **Phase Ranges**: Use format "start-end" (e.g., "0-100", "45-55")  
4. **Patterns**: Use predefined pattern names from Pattern Definitions
5. **Units**: Must match standard specification units
6. **Tolerance**: Percentage (e.g., "15%") or absolute values

## References

These ranges are verified against:
1. Perry, J., & Burnfield, J. M. (2010). Gait Analysis: Normal and Pathological Function (2nd ed.)
2. Winter, D. A. (2009). Biomechanics and Motor Control of Human Movement (4th ed.)
3. Whittle, M. W. (2007). Gait Analysis: An Introduction (4th ed.)
4. Nordin, M., & Frankel, V. H. (2012). Basic Biomechanics of the Musculoskeletal System (4th ed.)
5. Schoenfeld, B. J. (2010). Squatting kinematics and kinetics and their application to exercise performance
6. Cook, G. (2010). Movement: Functional Movement Systems
7. Various peer-reviewed sources from 2024 literature searches

> **📋 Version History**: See [validation_expectations_changelog.md](validation_expectations_changelog.md) for complete version history and detailed change documentation.
> **🧪 Parser Testing**: See [test_validation_parser.md](test_validation_parser.md) for markdown parser unit test data.