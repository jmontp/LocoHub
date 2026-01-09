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
  <a class="download-button available" href="https://www.dropbox.com/scl/fi/bje9vy7ykyo8f7eio4l53/gtech_2021_phase_clean.parquet?rlkey=uowmh48suof9efvoknuh381lf&dl=0" target="_blank" rel="noopener">Download Clean Dataset</a>
  <a class="download-button available" href="https://www.dropbox.com/scl/fi/cjlj0s89f2x8y1fur33ad/gtech_2021_phase_dirty.parquet?rlkey=oc809b1cv8c0yqc2pa3e7d5je&dl=0" target="_blank" rel="noopener">Download Full Dataset (Dirty)</a>
</div>

## Dataset Information

### Subjects and Tasks
- **Number of Subjects**: 15
- **Tasks Included**: Decline Walking, Incline Walking, Level Walking, Stair Ascent, Stair Descent, Transition

### Subject Metadata
The table below summarizes the `subject_metadata` key:value pairs per subject.

| Subject | weight_kg | foot_length_m | shank_length_m | thigh_length_m |
|---|---|---|---|---|
| GT21_AB06 | 74.8 | 0.219 | 0.435 | 0.348 |
| GT21_AB07 | 55.3 | 0.205 | 0.390 | 0.277 |
| GT21_AB08 | 72.6 | 0.217 | 0.419 | 0.340 |
| GT21_AB09 | 63.5 | 0.190 | 0.364 | 0.322 |
| GT21_AB10 | 83.9 | 0.212 | 0.395 | 0.332 |
| GT21_AB11 | 77.1 | 0.211 | 0.408 | 0.331 |
| GT21_AB13 | 59.0 | 0.211 | 0.420 | 0.299 |
| GT21_AB14 | 58.4 | 0.187 | 0.364 | 0.254 |
| GT21_AB16 | 55.8 | 0.204 | 0.391 | 0.298 |
| GT21_AB18 | 60.1 | 0.199 | 0.429 | 0.301 |
| GT21_AB20 | 68.0 | 0.210 | 0.436 | 0.281 |
| GT21_AB21 | 58.1 | 0.194 | 0.390 | 0.279 |
| GT21_AB24 | 72.6 | 0.205 | 0.420 | 0.285 |
| GT21_AB25 | 52.2 | 0.190 | 0.390 | 0.281 |
| GT21_AB30 | 77.0 | 0.215 | 0.421 | 0.277 |

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
|   |   | incline_deg:5.2,surface:overground,gait_transition:true,transition_from:incline_walking,transition_to:level_walking |
|   |   | incline_deg:7.8,surface:overground,gait_transition:true,transition_from:incline_walking,transition_to:level_walking |
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
|   | stand_to_walk | speed_m_s:1.17,surface:overground,gait_transition:true,transition_from:stand,transition_to:level_walking |
|   | walk_to_ramp_ascent | incline_deg:11.0,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:incline_walking |
|   |   | incline_deg:12.4,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:incline_walking |
|   |   | incline_deg:18.0,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:incline_walking |
|   | walk_to_ramp_descent | incline_deg:-5.2,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:decline_walking |
|   |   | incline_deg:-7.8,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:decline_walking |
|   |   | incline_deg:-9.2,surface:overground,gait_transition:true,transition_from:level_walking,transition_to:decline_walking |
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
<p class="feature-source">Coverage computed from `gtech_2021_phase_clean.parquet`.</p>

#### Ground Reaction Forces

| Feature | Decline Walking | Incline Walking | Level Walking | Stair Ascent | Stair Descent | Transition |
|---|---|---|---|---|---|---|
| `grf_anterior_contra_BW` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `grf_anterior_ipsi_BW` | <span class="feature-chip feature-partial" title="26.0% available">≈ 26.00</span> | <span class="feature-chip feature-partial" title="31.2% available">≈ 31.20</span> | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-partial" title="97.4% available">≈ 97.40</span> | <span class="feature-chip feature-partial" title="49.9% available">≈ 49.90</span> | <span class="feature-chip feature-partial" title="54.0% available">≈ 54.00</span> |
| `grf_lateral_contra_BW` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `grf_lateral_ipsi_BW` | <span class="feature-chip feature-partial" title="26.0% available">≈ 26.00</span> | <span class="feature-chip feature-partial" title="31.2% available">≈ 31.20</span> | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-partial" title="97.4% available">≈ 97.40</span> | <span class="feature-chip feature-partial" title="49.9% available">≈ 49.90</span> | <span class="feature-chip feature-partial" title="54.0% available">≈ 54.00</span> |
| `grf_vertical_contra_BW` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `grf_vertical_ipsi_BW` | <span class="feature-chip feature-partial" title="26.0% available">≈ 26.00</span> | <span class="feature-chip feature-partial" title="31.2% available">≈ 31.20</span> | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-partial" title="97.4% available">≈ 97.40</span> | <span class="feature-chip feature-partial" title="49.9% available">≈ 49.90</span> | <span class="feature-chip feature-partial" title="54.0% available">≈ 54.00</span> |

#### Joint Angles

| Feature | Decline Walking | Incline Walking | Level Walking | Stair Ascent | Stair Descent | Transition |
|---|---|---|---|---|---|---|
| `ankle_dorsiflexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_sagittal_angle_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `trunk_sagittal_angle_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Moments

| Feature | Decline Walking | Incline Walking | Level Walking | Stair Ascent | Stair Descent | Transition |
|---|---|---|---|---|---|---|
| `ankle_dorsiflexion_moment_contra_Nm_kg` | <span class="feature-chip feature-partial" title="58.2% available">≈ 58.20</span> | <span class="feature-chip feature-partial" title="58.7% available">≈ 58.70</span> | <span class="feature-chip feature-partial" title="92.9% available">≈ 92.90</span> | <span class="feature-chip feature-partial" title="40.0% available">≈ 40.00</span> | <span class="feature-chip feature-partial" title="70.8% available">≈ 70.80</span> | <span class="feature-chip feature-partial" title="90.3% available">≈ 90.30</span> |
| `ankle_dorsiflexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-partial" title="58.8% available">≈ 58.80</span> | <span class="feature-chip feature-partial" title="58.6% available">≈ 58.60</span> | <span class="feature-chip feature-partial" title="93.3% available">≈ 93.30</span> | <span class="feature-chip feature-partial" title="98.5% available">≈ 98.50</span> | <span class="feature-chip feature-partial" title="72.7% available">≈ 72.70</span> | <span class="feature-chip feature-partial" title="96.3% available">≈ 96.30</span> |
| `hip_flexion_moment_contra_Nm_kg` | <span class="feature-chip feature-partial" title="58.2% available">≈ 58.20</span> | <span class="feature-chip feature-partial" title="58.7% available">≈ 58.70</span> | <span class="feature-chip feature-partial" title="92.9% available">≈ 92.90</span> | <span class="feature-chip feature-partial" title="40.0% available">≈ 40.00</span> | <span class="feature-chip feature-partial" title="70.8% available">≈ 70.80</span> | <span class="feature-chip feature-partial" title="90.3% available">≈ 90.30</span> |
| `hip_flexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-partial" title="58.8% available">≈ 58.80</span> | <span class="feature-chip feature-partial" title="58.6% available">≈ 58.60</span> | <span class="feature-chip feature-partial" title="93.3% available">≈ 93.30</span> | <span class="feature-chip feature-partial" title="98.5% available">≈ 98.50</span> | <span class="feature-chip feature-partial" title="72.7% available">≈ 72.70</span> | <span class="feature-chip feature-partial" title="96.3% available">≈ 96.30</span> |
| `knee_flexion_moment_contra_Nm_kg` | <span class="feature-chip feature-partial" title="58.2% available">≈ 58.20</span> | <span class="feature-chip feature-partial" title="58.7% available">≈ 58.70</span> | <span class="feature-chip feature-partial" title="92.9% available">≈ 92.90</span> | <span class="feature-chip feature-partial" title="40.0% available">≈ 40.00</span> | <span class="feature-chip feature-partial" title="70.8% available">≈ 70.80</span> | <span class="feature-chip feature-partial" title="90.3% available">≈ 90.30</span> |
| `knee_flexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-partial" title="58.8% available">≈ 58.80</span> | <span class="feature-chip feature-partial" title="58.6% available">≈ 58.60</span> | <span class="feature-chip feature-partial" title="93.3% available">≈ 93.30</span> | <span class="feature-chip feature-partial" title="98.5% available">≈ 98.50</span> | <span class="feature-chip feature-partial" title="72.7% available">≈ 72.70</span> | <span class="feature-chip feature-partial" title="96.3% available">≈ 96.30</span> |

#### Joint Velocities

| Feature | Decline Walking | Incline Walking | Level Walking | Stair Ascent | Stair Descent | Transition |
|---|---|---|---|---|---|---|
| `ankle_dorsiflexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_sagittal_velocity_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `trunk_sagittal_velocity_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Other Features

| Feature | Decline Walking | Incline Walking | Level Walking | Stair Ascent | Stair Descent | Transition |
|---|---|---|---|---|---|---|
| `cop_anterior_contra_m` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `cop_anterior_ipsi_m` | <span class="feature-chip feature-partial" title="26.0% available">≈ 26.00</span> | <span class="feature-chip feature-partial" title="31.2% available">≈ 31.20</span> | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-partial" title="97.4% available">≈ 97.40</span> | <span class="feature-chip feature-partial" title="49.9% available">≈ 49.90</span> | <span class="feature-chip feature-partial" title="54.0% available">≈ 54.00</span> |
| `cop_lateral_contra_m` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `cop_lateral_ipsi_m` | <span class="feature-chip feature-partial" title="26.0% available">≈ 26.00</span> | <span class="feature-chip feature-partial" title="31.2% available">≈ 31.20</span> | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-partial" title="97.4% available">≈ 97.40</span> | <span class="feature-chip feature-partial" title="49.9% available">≈ 49.90</span> | <span class="feature-chip feature-partial" title="54.0% available">≈ 54.00</span> |
| `cop_vertical_contra_m` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `cop_vertical_ipsi_m` | <span class="feature-chip feature-partial" title="26.0% available">≈ 26.00</span> | <span class="feature-chip feature-partial" title="31.2% available">≈ 31.20</span> | <span class="feature-chip feature-partial" title="86.7% available">≈ 86.70</span> | <span class="feature-chip feature-partial" title="97.4% available">≈ 97.40</span> | <span class="feature-chip feature-partial" title="49.9% available">≈ 49.90</span> | <span class="feature-chip feature-partial" title="54.0% available">≈ 54.00</span> |

### Data Structure
- **Format**: Phase-normalized (150 points per gait cycle)
- **Sampling**: Phase-indexed from 0-100%
- **Variables**: Standard biomechanical naming convention

## Validation Snapshot

- **Status**: ⚠️ Partial (90.8%)
- **Stride Pass Rate**: 90.8%
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

- `gtech_2021_phase_dirty.parquet` — Phase-normalized dataset
- [Validation report](#validation)
- Conversion script in `contributor_tools/conversion_scripts/gt21/`

---

*Generated by Dataset Submission Tool on 2026-01-08 21:52*
