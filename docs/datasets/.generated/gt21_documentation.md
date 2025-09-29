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
  <span class="download-button unavailable" title="Clean dataset download not yet available">Clean Dataset (coming soon)</span>
  <span class="download-button unavailable" title="Full dataset download not yet available">Full Dataset (coming soon)</span>
</div>
*Downloads coming soon. Contact the authors for data access.*

## Dataset Information

### Subjects and Tasks
- **Number of Subjects**: 15
- **Tasks Included**: Decline Walking, Incline Walking, Level Walking, Stair Ascent, Stair Descent, Transition

#### Task Catalog

| Task | Task ID | Task Info |
|------|---------|-----------|
| decline_walking | decline_-11.0deg | incline_deg:-11.0,surface:overground |
|   | decline_-12.4deg | incline_deg:-12.4,surface:overground |
|   | decline_-18.0deg | incline_deg:-18.0,surface:overground |
|   | decline_-5.2deg | incline_deg:-5.2,surface:overground |
|   | decline_-7.8deg | incline_deg:-7.8,surface:overground |
|   | decline_-9.2deg | incline_deg:-9.2,surface:overground |
| incline_walking | incline_11.0deg | incline_deg:11.0,surface:overground |
|   | incline_12.4deg | incline_deg:12.4,surface:overground |
|   | incline_18.0deg | incline_deg:18.0,surface:overground |
|   | incline_5.2deg | incline_deg:5.2,surface:overground |
|   | incline_7.8deg | incline_deg:7.8,surface:overground |
|   | incline_9.2deg | incline_deg:9.2,surface:overground |
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
| transition | ramp_ascent_to_walk | incline_deg:11.0,surface:overground,gait_transition:true,transition_from:incline_walking,transition_to:level_walking |
|   |   | incline_deg:12.4,surface:overground,gait_transition:true,transition_from:incline_walking,transition_to:level_walking |
|   |   | incline_deg:18.0,surface:overground,gait_transition:true,transition_from:incline_walking,transition_to:level_walking |
|   |   | incline_deg:5.2,surface:overground,gait_transition:true,transition_from:incline_walking,transition_to:level_walking |
|   |   | incline_deg:7.8,surface:overground,gait_transition:true,transition_from:incline_walking,transition_to:level_walking |
|   |   | incline_deg:9.2,surface:overground,gait_transition:true,transition_from:incline_walking,transition_to:level_walking |
|   | ramp_descent_to_walk | incline_deg:-11.0,surface:overground,gait_transition:true,transition_from:decline_walking,transition_to:level_walking |
|   |   | incline_deg:-12.4,surface:overground,gait_transition:true,transition_from:decline_walking,transition_to:level_walking |
|   |   | incline_deg:-18.0,surface:overground,gait_transition:true,transition_from:decline_walking,transition_to:level_walking |
|   |   | incline_deg:-5.2,surface:overground,gait_transition:true,transition_from:decline_walking,transition_to:level_walking |
|   |   | incline_deg:-7.8,surface:overground,gait_transition:true,transition_from:decline_walking,transition_to:level_walking |
|   |   | incline_deg:-9.2,surface:overground,gait_transition:true,transition_from:decline_walking,transition_to:level_walking |
|   | stair_ascent_to_walk | step_height_m:0.102,surface:stairs,gait_transition:true,transition_from:stair_ascent,transition_to:level_walking |
|   |   | step_height_m:0.127,surface:stairs,gait_transition:true,transition_from:stair_ascent,transition_to:level_walking |
|   |   | step_height_m:0.152,surface:stairs,gait_transition:true,transition_from:stair_ascent,transition_to:level_walking |
|   |   | step_height_m:0.178,surface:stairs,gait_transition:true,transition_from:stair_ascent,transition_to:level_walking |
|   | stair_descent_to_walk | step_height_m:0.102,surface:stairs,gait_transition:true,transition_from:stair_descent,transition_to:level_walking |
|   |   | step_height_m:0.127,surface:stairs,gait_transition:true,transition_from:stair_descent,transition_to:level_walking |
|   |   | step_height_m:0.152,surface:stairs,gait_transition:true,transition_from:stair_descent,transition_to:level_walking |
|   |   | step_height_m:0.178,surface:stairs,gait_transition:true,transition_from:stair_descent,transition_to:level_walking |
|   | stand_to_walk | speed_m_s:0.88,surface:overground,gait_transition:true,transition_from:stand,transition_to:level_walking |
|   |   | speed_m_s:1.17,surface:overground,gait_transition:true,transition_from:stand,transition_to:level_walking |
|   |   | speed_m_s:1.45,surface:overground,gait_transition:true,transition_from:stand,transition_to:level_walking |
|   | walk_to_ramp_ascent | incline_deg:11.0,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:incline_walking |
|   |   | incline_deg:12.4,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:incline_walking |
|   |   | incline_deg:18.0,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:incline_walking |
|   |   | incline_deg:5.2,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:incline_walking |
|   |   | incline_deg:7.8,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:incline_walking |
|   |   | incline_deg:9.2,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:incline_walking |
|   | walk_to_ramp_descent | incline_deg:-11.0,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:decline_walking |
|   |   | incline_deg:-12.4,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:decline_walking |
|   |   | incline_deg:-18.0,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:decline_walking |
|   |   | incline_deg:-5.2,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:decline_walking |
|   |   | incline_deg:-7.8,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:decline_walking |
|   |   | incline_deg:-9.2,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:decline_walking |
|   | walk_to_stair_ascent | step_height_m:0.102,surface:stairs,gait_transition:true,transition_from:level_walking,transition_to:stair_ascent |
|   |   | step_height_m:0.127,surface:stairs,gait_transition:true,transition_from:level_walking,transition_to:stair_ascent |
|   |   | step_height_m:0.152,surface:stairs,gait_transition:true,transition_from:level_walking,transition_to:stair_ascent |
|   |   | step_height_m:0.178,surface:stairs,gait_transition:true,transition_from:level_walking,transition_to:stair_ascent |
|   | walk_to_stair_descent | step_height_m:0.102,surface:stairs,gait_transition:true,transition_from:level_walking,transition_to:stair_descent |
|   |   | step_height_m:0.127,surface:stairs,gait_transition:true,transition_from:level_walking,transition_to:stair_descent |
|   |   | step_height_m:0.152,surface:stairs,gait_transition:true,transition_from:level_walking,transition_to:stair_descent |
|   |   | step_height_m:0.178,surface:stairs,gait_transition:true,transition_from:level_walking,transition_to:stair_descent |
|   | walk_to_stand | speed_m_s:0.88,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:stand |
|   |   | speed_m_s:1.17,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:stand |
|   |   | speed_m_s:1.45,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:stand |

### Data Structure
- **Format**: Phase-normalized (150 points per gait cycle)
- **Sampling**: Phase-indexed from 0-100%
- **Variables**: Standard biomechanical naming convention

## Validation Snapshot

- **Status**: ⚠️ Partial (81.3%)
- **Stride Pass Rate**: 81.3%
- **Validation Ranges**: [Download validation ranges](./gt21_validation_ranges.yaml) (source: contributor_tools/validation_ranges/default_ranges_v3.yaml)
- **Detailed Report**: [View validation report](#validation)

## Citation
Please cite appropriately when using this dataset.

## Collection Details

### Protocol
Standard motion capture protocol was used.

### Processing Notes
No additional notes.

## Files Included

- `converted_datasets/gtech_2021_phase_raw.parquet` — Phase-normalized dataset
- [Validation report](#validation)
- Conversion script in `contributor_tools/conversion_scripts/gt21/`

---

*Generated by Dataset Submission Tool on 2025-09-29 15:47*
