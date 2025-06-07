# Validation Expectations Specification

**Single Source of Truth for Biomechanical Validation Rules**

This document defines expected ranges and patterns for all biomechanical variables across different locomotion tasks. It serves as both human-readable documentation and machine-parseable validation specifications.

## Format Specification

Each validation table uses the following structure:

```markdown
### Task: {task_name}

| Variable | Phase_Range | Min_Value | Max_Value | Expected_Pattern | Tolerance | Units | Notes |
|----------|-------------|-----------|-----------|------------------|-----------|-------|-------|
```

**Column Definitions:**
- `Variable`: Exact variable name (must match dataset columns)
- `Phase_Range`: Gait cycle phase range (e.g., "0-100", "0-10", "45-55")
- `Min_Value`: Minimum expected value
- `Max_Value`: Maximum expected value  
- `Expected_Pattern`: Pattern description (e.g., "peak_at_10", "valley_at_60", "monotonic_increase")
- `Tolerance`: Acceptable deviation (percentage or absolute)
- `Units`: Variable units (rad, N, m, etc.)
- `Notes`: Additional context or exceptions

## Validation Tables

### Task: level_walking

| Variable | Phase_Range | Min_Value | Max_Value | Expected_Pattern | Tolerance | Units | Notes |
|----------|-------------|-----------|-----------|------------------|-----------|-------|-------|
| hip_flexion_angle_left_rad | 0-100 | -0.3 | 0.8 | peak_at_60 | 15% | rad | Hip flexion during swing |
| hip_flexion_angle_right_rad | 0-100 | -0.3 | 0.8 | peak_at_10 | 15% | rad | Right leg leads by 50% phase |
| knee_flexion_angle_left_rad | 0-100 | -0.1 | 1.2 | peak_at_15,peak_at_75 | 20% | rad | Dual peaks: loading response and swing |
| knee_flexion_angle_right_rad | 0-100 | -0.1 | 1.2 | peak_at_65,peak_at_25 | 20% | rad | Right leg offset by 50% |
| ankle_flexion_angle_left_rad | 0-100 | -0.4 | 0.3 | valley_at_50 | 10% | rad | Plantarflexion at push-off |
| ankle_flexion_angle_right_rad | 0-100 | -0.4 | 0.3 | valley_at_0 | 10% | rad | Right leg offset |
| vertical_grf_N | 0-100 | 0 | 1500 | peak_at_15,peak_at_50 | 25% | N | Loading response and push-off |
| ap_grf_N | 0-100 | -400 | 400 | negative_to_positive | 30% | N | Braking to propulsion |
| ml_grf_N | 0-100 | -150 | 150 | near_zero | 50% | N | Minimal mediolateral forces |
| cop_x_m | 0-100 | -0.08 | 0.12 | heel_to_toe | 20% | m | Progression from heel to toe |
| cop_y_m | 0-100 | -0.06 | 0.06 | near_zero | 100% | m | Minimal mediolateral COP movement |

### Task: incline_walking

| Variable | Phase_Range | Min_Value | Max_Value | Expected_Pattern | Tolerance | Units | Notes |
|----------|-------------|-----------|-----------|------------------|-----------|-------|-------|
| hip_flexion_angle_left_rad | 0-100 | -0.2 | 1.0 | peak_at_60 | 20% | rad | Increased hip flexion for incline |
| hip_flexion_angle_right_rad | 0-100 | -0.2 | 1.0 | peak_at_10 | 20% | rad | Right leg offset |
| knee_flexion_angle_left_rad | 0-100 | -0.1 | 1.4 | peak_at_15,peak_at_75 | 25% | rad | Greater knee flexion on incline |
| knee_flexion_angle_right_rad | 0-100 | -0.1 | 1.4 | peak_at_65,peak_at_25 | 25% | rad | Right leg offset |
| ankle_flexion_angle_left_rad | 0-100 | -0.3 | 0.4 | valley_at_50 | 15% | rad | More dorsiflexion for clearance |
| ankle_flexion_angle_right_rad | 0-100 | -0.3 | 0.4 | valley_at_0 | 15% | rad | Right leg offset |
| vertical_grf_N | 0-100 | 0 | 1800 | peak_at_15,peak_at_50 | 30% | N | Higher vertical forces on incline |
| ap_grf_N | 0-100 | -500 | 300 | more_negative | 40% | N | Greater braking forces uphill |
| ml_grf_N | 0-100 | -200 | 200 | near_zero | 60% | N | Slightly higher lateral forces |

### Task: decline_walking

| Variable | Phase_Range | Min_Value | Max_Value | Expected_Pattern | Tolerance | Units | Notes |
|----------|-------------|-----------|-----------|------------------|-----------|-------|-------|
| hip_flexion_angle_left_rad | 0-100 | -0.4 | 0.6 | peak_at_60 | 20% | rad | Reduced hip flexion downhill |
| hip_flexion_angle_right_rad | 0-100 | -0.4 | 0.6 | peak_at_10 | 20% | rad | Right leg offset |
| knee_flexion_angle_left_rad | 0-100 | -0.1 | 1.0 | peak_at_15,peak_at_75 | 25% | rad | Controlled descent |
| knee_flexion_angle_right_rad | 0-100 | -0.1 | 1.0 | peak_at_65,peak_at_25 | 25% | rad | Right leg offset |
| ankle_flexion_angle_left_rad | 0-100 | -0.5 | 0.2 | valley_at_50 | 15% | rad | Greater plantarflexion |
| ankle_flexion_angle_right_rad | 0-100 | -0.5 | 0.2 | valley_at_0 | 15% | rad | Right leg offset |
| vertical_grf_N | 0-100 | 0 | 1200 | peak_at_15,peak_at_50 | 25% | N | Reduced vertical impact |
| ap_grf_N | 0-100 | -300 | 500 | more_positive | 40% | N | Greater propulsive forces |
| ml_grf_N | 0-100 | -150 | 150 | near_zero | 50% | N | Similar to level walking |

### Task: up_stairs

| Variable | Phase_Range | Min_Value | Max_Value | Expected_Pattern | Tolerance | Units | Notes |
|----------|-------------|-----------|-----------|------------------|-----------|-------|-------|
| hip_flexion_angle_left_rad | 0-100 | 0.0 | 1.4 | peak_at_70 | 25% | rad | High hip flexion for step clearance |
| hip_flexion_angle_right_rad | 0-100 | 0.0 | 1.4 | peak_at_20 | 25% | rad | Right leg offset |
| knee_flexion_angle_left_rad | 0-100 | 0.0 | 1.6 | peak_at_70 | 30% | rad | Maximum knee flexion for clearance |
| knee_flexion_angle_right_rad | 0-100 | 0.0 | 1.6 | peak_at_20 | 30% | rad | Right leg offset |
| ankle_flexion_angle_left_rad | 0-100 | -0.2 | 0.5 | peak_at_80 | 20% | rad | Dorsiflexion for clearance |
| ankle_flexion_angle_right_rad | 0-100 | -0.2 | 0.5 | peak_at_30 | 20% | rad | Right leg offset |
| vertical_grf_N | 0-100 | 0 | 2000 | peak_at_20 | 35% | N | High vertical forces pushing up |
| ap_grf_N | 0-100 | -600 | 200 | predominantly_negative | 50% | N | Strong braking to control ascent |
| ml_grf_N | 0-100 | -250 | 250 | variable | 70% | N | Higher lateral variability |

### Task: down_stairs

| Variable | Phase_Range | Min_Value | Max_Value | Expected_Pattern | Tolerance | Units | Notes |
|----------|-------------|-----------|-----------|------------------|-----------|-------|-------|
| hip_flexion_angle_left_rad | 0-100 | -0.2 | 0.8 | controlled_extension | 20% | rad | Controlled lowering |
| hip_flexion_angle_right_rad | 0-100 | -0.2 | 0.8 | controlled_extension | 20% | rad | Right leg offset |
| knee_flexion_angle_left_rad | 0-100 | 0.0 | 1.2 | gradual_flexion | 25% | rad | Eccentric control |
| knee_flexion_angle_right_rad | 0-100 | 0.0 | 1.2 | gradual_flexion | 25% | rad | Right leg offset |
| ankle_flexion_angle_left_rad | 0-100 | -0.3 | 0.3 | controlled_motion | 15% | rad | Controlled descent |
| ankle_flexion_angle_right_rad | 0-100 | -0.3 | 0.3 | controlled_motion | 15% | rad | Right leg offset |
| vertical_grf_N | 0-100 | 0 | 2500 | peak_at_30 | 40% | N | High impact forces |
| ap_grf_N | 0-100 | -200 | 600 | predominantly_positive | 50% | N | Forward momentum control |
| ml_grf_N | 0-100 | -200 | 200 | variable | 60% | N | Increased lateral control |

### Task: run

| Variable | Phase_Range | Min_Value | Max_Value | Expected_Pattern | Tolerance | Units | Notes |
|----------|-------------|-----------|-----------|------------------|-----------|-------|-------|
| hip_flexion_angle_left_rad | 0-100 | -0.5 | 1.2 | peak_at_65 | 30% | rad | Greater range of motion |
| hip_flexion_angle_right_rad | 0-100 | -0.5 | 1.2 | peak_at_15 | 30% | rad | Right leg offset |
| knee_flexion_angle_left_rad | 0-100 | 0.0 | 2.0 | peak_at_70 | 35% | rad | High knee flexion in swing |
| knee_flexion_angle_right_rad | 0-100 | 0.0 | 2.0 | peak_at_20 | 35% | rad | Right leg offset |
| ankle_flexion_angle_left_rad | 0-100 | -0.6 | 0.4 | valley_at_40 | 25% | rad | Strong push-off |
| ankle_flexion_angle_right_rad | 0-100 | -0.6 | 0.4 | valley_at_90 | 25% | rad | Right leg offset |
| vertical_grf_N | 0-100 | 0 | 3000 | peak_at_25 | 50% | N | High impact forces in running |
| ap_grf_N | 0-100 | -800 | 800 | negative_to_positive | 60% | N | Strong braking and propulsion |
| ml_grf_N | 0-100 | -300 | 300 | variable | 80% | N | Higher lateral forces |

### Task: sit_to_stand

| Variable | Phase_Range | Min_Value | Max_Value | Expected_Pattern | Tolerance | Units | Notes |
|----------|-------------|-----------|-----------|------------------|-----------|-------|-------|
| hip_flexion_angle_left_rad | 0-100 | 0.5 | 2.0 | decreasing | 20% | rad | Hip extension from seated |
| hip_flexion_angle_right_rad | 0-100 | 0.5 | 2.0 | decreasing | 20% | rad | Bilateral movement |
| knee_flexion_angle_left_rad | 0-100 | 0.0 | 1.8 | decreasing | 25% | rad | Knee extension to stand |
| knee_flexion_angle_right_rad | 0-100 | 0.0 | 1.8 | decreasing | 25% | rad | Bilateral movement |
| ankle_flexion_angle_left_rad | 0-100 | -0.2 | 0.4 | slight_dorsiflexion | 15% | rad | Ankle adjustment |
| ankle_flexion_angle_right_rad | 0-100 | -0.2 | 0.4 | slight_dorsiflexion | 15% | rad | Bilateral movement |
| vertical_grf_N | 0-100 | 400 | 1200 | increasing | 30% | N | Weight transfer to feet |
| ap_grf_N | 0-100 | -300 | 300 | variable | 70% | N | Balance adjustment |
| ml_grf_N | 0-100 | -200 | 200 | variable | 70% | N | Balance adjustment |

### Task: jump

| Variable | Phase_Range | Min_Value | Max_Value | Expected_Pattern | Tolerance | Units | Notes |
|----------|-------------|-----------|-----------|------------------|-----------|-------|-------|
| hip_flexion_angle_left_rad | 0-100 | -0.5 | 1.5 | flexion_then_extension | 40% | rad | Countermovement jump |
| hip_flexion_angle_right_rad | 0-100 | -0.5 | 1.5 | flexion_then_extension | 40% | rad | Bilateral movement |
| knee_flexion_angle_left_rad | 0-100 | -0.2 | 2.2 | flexion_then_extension | 45% | rad | Deep knee bend |
| knee_flexion_angle_right_rad | 0-100 | -0.2 | 2.2 | flexion_then_extension | 45% | rad | Bilateral movement |
| ankle_flexion_angle_left_rad | 0-100 | -0.8 | 0.6 | plantarflexion_peak | 30% | rad | Strong push-off |
| ankle_flexion_angle_right_rad | 0-100 | -0.8 | 0.6 | plantarflexion_peak | 30% | rad | Bilateral movement |
| vertical_grf_N | 0-100 | 0 | 4000 | peak_at_takeoff | 60% | N | Very high forces at takeoff |
| ap_grf_N | 0-100 | -500 | 500 | variable | 80% | N | Direction-dependent |
| ml_grf_N | 0-100 | -300 | 300 | variable | 80% | N | Balance-dependent |

### Task: squats

| Variable | Phase_Range | Min_Value | Max_Value | Expected_Pattern | Tolerance | Units | Notes |
|----------|-------------|-----------|-----------|------------------|-----------|-------|-------|
| hip_flexion_angle_left_rad | 0-100 | 0.0 | 2.2 | increasing_then_decreasing | 30% | rad | Deep hip flexion |
| hip_flexion_angle_right_rad | 0-100 | 0.0 | 2.2 | increasing_then_decreasing | 30% | rad | Bilateral movement |
| knee_flexion_angle_left_rad | 0-100 | 0.0 | 2.4 | increasing_then_decreasing | 35% | rad | Deep knee flexion |
| knee_flexion_angle_right_rad | 0-100 | 0.0 | 2.4 | increasing_then_decreasing | 35% | rad | Bilateral movement |
| ankle_flexion_angle_left_rad | 0-100 | -0.2 | 0.6 | dorsiflexion_peak | 20% | rad | Forward lean compensation |
| ankle_flexion_angle_right_rad | 0-100 | -0.2 | 0.6 | dorsiflexion_peak | 20% | rad | Bilateral movement |
| vertical_grf_N | 0-100 | 500 | 1800 | U_shaped | 40% | N | Lower during descent |
| ap_grf_N | 0-100 | -400 | 400 | variable | 70% | N | Balance maintenance |
| ml_grf_N | 0-100 | -200 | 200 | near_zero | 60% | N | Bilateral symmetry |

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

## Version History

- v1.0: Initial comprehensive validation specification
- Created: 2025-06-06
- Last Updated: 2025-06-06