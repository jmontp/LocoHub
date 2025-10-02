## Overview

- **Short Code**: GT21
- **Year**: 2021
- **Institution**: Epic Lab

We introduce a novel dataset containing 3-dimensional biomechanical and wearable sensor data from 22 able-bodied adults for multiple locomotion modes (level-ground/treadmill walking, stair ascent/descent, and ramp ascent/descent) and multiple terrain conditions of each mode (walking speed, stair height, and ramp inclination). In this paper, we present the data collection methods, explain the structure of the open dataset, and report the sensor data along with the kinematic and kinetic profiles of joint biomechanics as a function of the gait phase. This dataset offers a comprehensive source of locomotion information for the same set of subjects to motivate applications in locomotion recognition, developments in robotic assistive devices, and improvement of biomimetic controllers that better adapt to terrain conditions. With such a dataset, models for these applications can be either subject-dependent or subject-independent, allowing greater flexibility for researchers to advance the field.

## Downloads

<style>
.download-grid { display:flex; flex-wrap:wrap; gap:0.75rem; margin-bottom:1rem; }
.download-button { display:inline-block; padding:0.65rem 1.4rem; border-radius:0.5rem; font-weight:600; text-decoration:none; }
.download-button.available { background:#1f78d1; color:#fff; }
.download-button.available:hover { background:#1663ad; }
.download-button.unavailable { background:#d1d5db; color:#6b7280; cursor:not-allowed; }
</style>
<div class="download-grid">
  <a class="download-button available" href="https://www.dropbox.com/scl/fi/h2aitlo77ujndhcqzhswo/gtech_2021_phase_clean.parquet?rlkey=zitswlvbc7g8bgt2f3jx3zyfx&st=26wq9hpi&raw=1" target="_blank" rel="noopener">Download Clean Dataset</a>
  <a class="download-button available" href="https://www.dropbox.com/scl/fi/fvv83iipnhtapkaa1z70g/gtech_2021_phase_dirty.parquet?rlkey=fp7q7a3b0t8t6bivc9lynu5uj&st=idfk1sk4&raw=1" target="_blank" rel="noopener">Download Full Dataset (Dirty)</a>
</div>

## Dataset Information

### Subjects and Tasks
- **Number of Subjects**: 15
- **Tasks Included**: Level Walking, Stair Ascent, Stair Descent, Transition

#### Task Catalog

| Task | Task ID | Task Info |
|------|---------|-----------|
| level_walking | level | speed_m_s:0.50,treadmill:true,surface:treadmill |
|   |   | speed_m_s:0.55,treadmill:true,surface:treadmill |
|   |   | speed_m_s:0.60,treadmill:true,surface:treadmill |
|   |   | speed_m_s:0.65,treadmill:true,surface:treadmill |
|   |   | speed_m_s:0.70,treadmill:true,surface:treadmill |
|   |   | speed_m_s:0.75,treadmill:true,surface:treadmill |
|   |   | speed_m_s:0.80,treadmill:true,surface:treadmill |
|   |   | speed_m_s:0.85,treadmill:true,surface:treadmill |
|   |   | speed_m_s:0.88,surface:overground |
|   |   | speed_m_s:0.90,treadmill:true,surface:treadmill |
|   |   | speed_m_s:0.95,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.00,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.05,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.10,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.15,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.17,surface:overground |
|   |   | speed_m_s:1.20,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.25,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.30,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.35,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.40,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.45,surface:overground |
|   |   | speed_m_s:1.45,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.50,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.55,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.60,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.65,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.70,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.75,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.80,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.85,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.90,treadmill:true,surface:treadmill |
|   |   | speed_m_s:1.95,treadmill:true,surface:treadmill |
|   |   | speed_m_s:2.00,treadmill:true,surface:treadmill |
| stair_ascent | stair_ascent | step_height_m:0.102,surface:stairs |
|   |   | step_height_m:0.127,surface:stairs |
|   |   | step_height_m:0.152,surface:stairs |
|   |   | step_height_m:0.178,surface:stairs |
| stair_descent | stair_descent | step_height_m:0.102,surface:stairs |
|   |   | step_height_m:0.127,surface:stairs |
|   |   | step_height_m:0.152,surface:stairs |
|   |   | step_height_m:0.178,surface:stairs |
| transition | stair_ascent_to_walk | step_height_m:0.102,surface:stairs,gait_transition:true,transition_from:stair_ascent,transition_to:level_walking |
|   |   | step_height_m:0.127,surface:stairs,gait_transition:true,transition_from:stair_ascent,transition_to:level_walking |
|   |   | step_height_m:0.152,surface:stairs,gait_transition:true,transition_from:stair_ascent,transition_to:level_walking |
|   |   | step_height_m:0.178,surface:stairs,gait_transition:true,transition_from:stair_ascent,transition_to:level_walking |
|   | stair_descent_to_walk | step_height_m:0.102,surface:stairs,gait_transition:true,transition_from:stair_descent,transition_to:level_walking |
|   |   | step_height_m:0.127,surface:stairs,gait_transition:true,transition_from:stair_descent,transition_to:level_walking |
|   |   | step_height_m:0.152,surface:stairs,gait_transition:true,transition_from:stair_descent,transition_to:level_walking |
|   |   | step_height_m:0.178,surface:stairs,gait_transition:true,transition_from:stair_descent,transition_to:level_walking |
|   | stand_to_walk | speed_m_s:1.17,surface:overground,gait_transition:true,transition_from:stand,transition_to:level_walking |
|   | walk_to_stair_ascent | step_height_m:0.102,surface:stairs,gait_transition:true,transition_from:level_walking,transition_to:stair_ascent |
|   | walk_to_stair_descent | step_height_m:0.102,surface:stairs,gait_transition:true,transition_from:level_walking,transition_to:stair_descent |
|   |   | step_height_m:0.127,surface:stairs,gait_transition:true,transition_from:level_walking,transition_to:stair_descent |
|   |   | step_height_m:0.152,surface:stairs,gait_transition:true,transition_from:level_walking,transition_to:stair_descent |
|   |   | step_height_m:0.178,surface:stairs,gait_transition:true,transition_from:level_walking,transition_to:stair_descent |
|   | walk_to_stand | speed_m_s:0.88,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:stand |
|   |   | speed_m_s:1.17,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:stand |
|   |   | speed_m_s:1.45,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:stand |

### Feature Availability by Task
<style>
.feature-chip {display:inline-flex;align-items:center;justify-content:center;min-width:1.6rem;padding:0.1rem 0.55rem;border-radius:999px;font-weight:600;font-size:0.85rem;line-height:1;color:#ffffff;}
.feature-chip.feature-complete {background:#16a34a;}
.feature-chip.feature-partial {background:#facc15;color:#1f2937;}
.feature-chip.feature-missing {background:#ef4444;}
.feature-legend {margin-bottom:0.5rem;display:flex;gap:0.75rem;flex-wrap:wrap;}
.feature-legend .legend-item {display:flex;align-items:center;gap:0.35rem;font-size:0.9rem;}
.feature-source {font-size:0.85rem;color:#4b5563;margin:0.25rem 0 0.75rem 0;}
</style>

<div class="feature-legend"><span class="legend-item"><span class="feature-chip feature-complete">✔</span>Complete</span><span class="legend-item"><span class="feature-chip feature-partial">≈</span>Partial</span><span class="legend-item"><span class="feature-chip feature-missing">✖</span>Missing</span></div>
<p class="feature-source">Coverage computed from `converted_datasets/gtech_2021_phase_clean.parquet`.</p>

#### Ground Reaction Forces

| Feature | Level Walking | Stair Ascent | Stair Descent | Transition |
|---|---|---|---|---|
| `anterior_grf_contra_BW` | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `anterior_grf_ipsi_BW` | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-partial" title="96.4% available">≈ 96.40</span> | <span class="feature-chip feature-partial" title="49.9% available">≈ 49.90</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `lateral_grf_contra_BW` | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `lateral_grf_ipsi_BW` | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-partial" title="96.4% available">≈ 96.40</span> | <span class="feature-chip feature-partial" title="49.9% available">≈ 49.90</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `vertical_grf_contra_BW` | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `vertical_grf_ipsi_BW` | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-partial" title="96.4% available">≈ 96.40</span> | <span class="feature-chip feature-partial" title="49.9% available">≈ 49.90</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |

#### Joint Angles

| Feature | Level Walking | Stair Ascent | Stair Descent | Transition |
|---|---|---|---|---|
| `ankle_dorsiflexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_sagittal_angle_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `trunk_sagittal_angle_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Moments

| Feature | Level Walking | Stair Ascent | Stair Descent | Transition |
|---|---|---|---|---|
| `ankle_dorsiflexion_moment_contra_Nm_kg` | <span class="feature-chip feature-partial" title="92.9% available">≈ 92.90</span> | <span class="feature-chip feature-partial" title="40.8% available">≈ 40.80</span> | <span class="feature-chip feature-partial" title="70.8% available">≈ 70.80</span> | <span class="feature-chip feature-partial" title="68.2% available">≈ 68.20</span> |
| `ankle_dorsiflexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-partial" title="93.3% available">≈ 93.30</span> | <span class="feature-chip feature-partial" title="98.2% available">≈ 98.20</span> | <span class="feature-chip feature-partial" title="72.7% available">≈ 72.70</span> | <span class="feature-chip feature-partial" title="94.8% available">≈ 94.80</span> |
| `hip_flexion_moment_contra_Nm_kg` | <span class="feature-chip feature-partial" title="92.9% available">≈ 92.90</span> | <span class="feature-chip feature-partial" title="40.8% available">≈ 40.80</span> | <span class="feature-chip feature-partial" title="70.8% available">≈ 70.80</span> | <span class="feature-chip feature-partial" title="68.2% available">≈ 68.20</span> |
| `hip_flexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-partial" title="93.3% available">≈ 93.30</span> | <span class="feature-chip feature-partial" title="98.2% available">≈ 98.20</span> | <span class="feature-chip feature-partial" title="72.7% available">≈ 72.70</span> | <span class="feature-chip feature-partial" title="94.8% available">≈ 94.80</span> |
| `knee_flexion_moment_contra_Nm_kg` | <span class="feature-chip feature-partial" title="92.9% available">≈ 92.90</span> | <span class="feature-chip feature-partial" title="40.8% available">≈ 40.80</span> | <span class="feature-chip feature-partial" title="70.8% available">≈ 70.80</span> | <span class="feature-chip feature-partial" title="68.2% available">≈ 68.20</span> |
| `knee_flexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-partial" title="93.3% available">≈ 93.30</span> | <span class="feature-chip feature-partial" title="98.2% available">≈ 98.20</span> | <span class="feature-chip feature-partial" title="72.7% available">≈ 72.70</span> | <span class="feature-chip feature-partial" title="94.8% available">≈ 94.80</span> |

#### Joint Velocities

| Feature | Level Walking | Stair Ascent | Stair Descent | Transition |
|---|---|---|---|---|
| `ankle_dorsiflexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_sagittal_velocity_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `trunk_sagittal_velocity_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

### Data Structure
- **Format**: Phase-normalized (150 points per gait cycle)
- **Sampling**: Phase-indexed from 0-100%
- **Variables**: Standard biomechanical naming convention

## Validation Snapshot

- **Status**: ⚠️ Partial (89.0%)
- **Stride Pass Rate**: 89.0%
- **Validation Ranges**: [Download validation ranges](./gt21_validation_ranges.yaml) (source: contributor_tools/validation_ranges/default_ranges_v3.yaml)
- **Detailed Report**: [View validation report](#validation)

## Citation
https://doi.org/10.1016/j.jbiomech.2021.110320

## Collection Details

### Protocol
Standard motion capture protocol was used.

### Processing Notes
No additional notes.

## Files Included

- `converted_datasets/gtech_2021_phase_dirty.parquet` — Phase-normalized dataset
- [Validation report](#validation)
- Conversion script in `contributor_tools/conversion_scripts/gt21/`

---

*Generated by Dataset Submission Tool on 2025-10-02 09:57*
