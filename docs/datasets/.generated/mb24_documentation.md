## Overview

- **Short Code**: MB24
- **Year**: 2024
- **Institution**: University of Michigan

Biomechanical data from the MBLUE (Modular Bi-Lateral Lower-limb Unloading Exoskeleton) ankle exoskeleton study. Includes 10 able-bodied subjects performing various locomotion tasks with and without an ankle exoskeleton, processed through OpenSim for inverse kinematics and inverse dynamics analysis.


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
- **Number of Subjects**: 10
- **Tasks Included**: Decline Walking, Incline Walking, Level Walking, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit

### Subject Metadata
The table below summarizes the `subject_metadata` key:value pairs per subject.

| Subject | age | sex | weight_kg |
|---|---|---|---|
| MBLUE_AB01 | 28 | M | 83.3 |
| MBLUE_AB02 | 26 | F | 70.6 |
| MBLUE_AB03 | 57 | F | 64.4 |
| MBLUE_AB04 | 24 | M | 69.1 |
| MBLUE_AB05 | 56 | M | 72.3 |
| MBLUE_AB06 | 34 | M | 75.9 |
| MBLUE_AB08 | 21 | F | 60.1 |
| MBLUE_AB09 | 36 | F | 64.8 |
| MBLUE_AB10 | 25 | F | 54.3 |
| MBLUE_AB11 | 26 | M | 68.0 |

#### Task Catalog

| Task | Task ID | Task Info |
|------|---------|-----------|
| decline_walking | decline_10deg | leg:l,exo_state:no_exo |
|   |   | leg:l,exo_state:powered,exo_joints:ankle |
|   |   | leg:r,exo_state:no_exo |
|   |   | leg:r,exo_state:powered,exo_joints:ankle |
|   | decline_5deg | leg:l,exo_state:no_exo |
|   |   | leg:l,exo_state:powered,exo_joints:ankle |
|   |   | leg:r,exo_state:no_exo |
|   |   | leg:r,exo_state:powered,exo_joints:ankle |
| incline_walking | incline_10deg | leg:l,exo_state:no_exo |
|   |   | leg:l,exo_state:powered,exo_joints:ankle |
|   |   | leg:r,exo_state:no_exo |
|   |   | leg:r,exo_state:powered,exo_joints:ankle |
|   | incline_5deg | leg:l,exo_state:no_exo |
|   |   | leg:l,exo_state:powered,exo_joints:ankle |
|   |   | leg:r,exo_state:no_exo |
|   |   | leg:r,exo_state:powered,exo_joints:ankle |
| level_walking | level_0.75ms | leg:l,speed_m_s:0.75,exo_state:no_exo |
|   |   | leg:l,speed_m_s:0.75,exo_state:powered,exo_joints:ankle |
|   |   | leg:r,speed_m_s:0.75,exo_state:no_exo |
|   |   | leg:r,speed_m_s:0.75,exo_state:powered,exo_joints:ankle |
|   | level_1.0ms | leg:l,speed_m_s:1.0,exo_state:no_exo |
|   |   | leg:l,speed_m_s:1.0,exo_state:powered,exo_joints:ankle |
|   |   | leg:r,speed_m_s:1.0,exo_state:no_exo |
|   |   | leg:r,speed_m_s:1.0,exo_state:powered,exo_joints:ankle |
|   | level_1.25ms | leg:l,speed_m_s:1.25,exo_state:no_exo |
|   |   | leg:l,speed_m_s:1.25,exo_state:powered,exo_joints:ankle |
|   |   | leg:r,speed_m_s:1.25,exo_state:no_exo |
|   |   | leg:r,speed_m_s:1.25,exo_state:powered,exo_joints:ankle |
| sit_to_stand | sit_to_stand | leg:l,exo_state:no_exo |
|   |   | leg:l,exo_state:powered,exo_joints:ankle |
| squat | crouch | leg:l,exo_state:no_exo |
|   |   | leg:l,exo_state:powered,exo_joints:ankle |
| stair_ascent | stair_ascent_s2 | leg:l,exo_state:no_exo |
|   |   | leg:l,exo_state:powered,exo_joints:ankle |
|   |   | leg:r,exo_state:no_exo |
|   |   | leg:r,exo_state:powered,exo_joints:ankle |
|   | stair_ascent_s3 | leg:l,exo_state:no_exo |
|   |   | leg:l,exo_state:powered,exo_joints:ankle |
|   |   | leg:r,exo_state:no_exo |
|   |   | leg:r,exo_state:powered,exo_joints:ankle |
|   | stair_ascent_s4 | leg:l,exo_state:no_exo |
|   |   | leg:l,exo_state:powered,exo_joints:ankle |
|   |   | leg:r,exo_state:no_exo |
|   |   | leg:r,exo_state:powered,exo_joints:ankle |
| stair_descent | stair_descent_s1 | leg:l,exo_state:no_exo |
|   |   | leg:l,exo_state:powered,exo_joints:ankle |
|   |   | leg:r,exo_state:no_exo |
|   |   | leg:r,exo_state:powered,exo_joints:ankle |
|   | stair_descent_s2 | leg:l,exo_state:no_exo |
|   |   | leg:l,exo_state:powered,exo_joints:ankle |
|   |   | leg:r,exo_state:no_exo |
|   |   | leg:r,exo_state:powered,exo_joints:ankle |
|   | stair_descent_s3 | leg:l,exo_state:no_exo |
|   |   | leg:l,exo_state:powered,exo_joints:ankle |
|   |   | leg:r,exo_state:no_exo |
|   |   | leg:r,exo_state:powered,exo_joints:ankle |
|   | stair_descent_s4 | leg:l,exo_state:no_exo |
|   |   | leg:l,exo_state:powered,exo_joints:ankle |
|   |   | leg:r,exo_state:no_exo |
|   |   | leg:r,exo_state:powered,exo_joints:ankle |
| stand_to_sit | stand_to_sit | leg:l,exo_state:no_exo |
|   |   | leg:l,exo_state:powered,exo_joints:ankle |

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
<p class="feature-source">Coverage computed from `converted_datasets/mblue_ankle_phase.parquet`.</p>

#### Ground Reaction Forces

| Feature | Decline Walking | Incline Walking | Level Walking | Sit To Stand | Squat | Stair Ascent | Stair Descent | Stand To Sit |
|---|---|---|---|---|---|---|---|---|
| `grf_vertical_contra_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_vertical_ipsi_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Angles

| Feature | Decline Walking | Incline Walking | Level Walking | Sit To Stand | Squat | Stair Ascent | Stair Descent | Stand To Sit |
|---|---|---|---|---|---|---|---|---|
| `ankle_dorsiflexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_sagittal_angle_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Moments

| Feature | Decline Walking | Incline Walking | Level Walking | Sit To Stand | Squat | Stair Ascent | Stair Descent | Stand To Sit |
|---|---|---|---|---|---|---|---|---|
| `ankle_dorsiflexion_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Velocities

| Feature | Decline Walking | Incline Walking | Level Walking | Sit To Stand | Squat | Stair Ascent | Stair Descent | Stand To Sit |
|---|---|---|---|---|---|---|---|---|
| `ankle_dorsiflexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_sagittal_velocity_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Other Features

| Feature | Decline Walking | Incline Walking | Level Walking | Sit To Stand | Squat | Stair Ascent | Stair Descent | Stand To Sit |
|---|---|---|---|---|---|---|---|---|
| `cop_anterior_contra_m` | <span class="feature-chip feature-partial" title="64.2% available">≈ 64.20</span> | <span class="feature-chip feature-partial" title="65.1% available">≈ 65.10</span> | <span class="feature-chip feature-partial" title="64.9% available">≈ 64.90</span> | <span class="feature-chip feature-partial" title="90.1% available">≈ 90.10</span> | <span class="feature-chip feature-partial" title="93.7% available">≈ 93.70</span> | <span class="feature-chip feature-partial" title="58.6% available">≈ 58.60</span> | <span class="feature-chip feature-partial" title="55.9% available">≈ 55.90</span> | <span class="feature-chip feature-partial" title="90.1% available">≈ 90.10</span> |
| `cop_anterior_ipsi_m` | <span class="feature-chip feature-partial" title="64.2% available">≈ 64.20</span> | <span class="feature-chip feature-partial" title="65.1% available">≈ 65.10</span> | <span class="feature-chip feature-partial" title="64.9% available">≈ 64.90</span> | <span class="feature-chip feature-partial" title="90.1% available">≈ 90.10</span> | <span class="feature-chip feature-partial" title="95.5% available">≈ 95.50</span> | <span class="feature-chip feature-partial" title="58.6% available">≈ 58.60</span> | <span class="feature-chip feature-partial" title="55.9% available">≈ 55.90</span> | <span class="feature-chip feature-partial" title="90.1% available">≈ 90.10</span> |
| `cop_lateral_contra_m` | <span class="feature-chip feature-partial" title="64.2% available">≈ 64.20</span> | <span class="feature-chip feature-partial" title="65.1% available">≈ 65.10</span> | <span class="feature-chip feature-partial" title="64.9% available">≈ 64.90</span> | <span class="feature-chip feature-partial" title="90.1% available">≈ 90.10</span> | <span class="feature-chip feature-partial" title="93.7% available">≈ 93.70</span> | <span class="feature-chip feature-partial" title="58.6% available">≈ 58.60</span> | <span class="feature-chip feature-partial" title="55.9% available">≈ 55.90</span> | <span class="feature-chip feature-partial" title="90.1% available">≈ 90.10</span> |
| `cop_lateral_ipsi_m` | <span class="feature-chip feature-partial" title="64.2% available">≈ 64.20</span> | <span class="feature-chip feature-partial" title="65.1% available">≈ 65.10</span> | <span class="feature-chip feature-partial" title="64.9% available">≈ 64.90</span> | <span class="feature-chip feature-partial" title="90.1% available">≈ 90.10</span> | <span class="feature-chip feature-partial" title="95.5% available">≈ 95.50</span> | <span class="feature-chip feature-partial" title="58.6% available">≈ 58.60</span> | <span class="feature-chip feature-partial" title="55.9% available">≈ 55.90</span> | <span class="feature-chip feature-partial" title="90.1% available">≈ 90.10</span> |

### Data Structure
- **Format**: Phase-normalized (150 points per gait cycle)
- **Sampling**: Phase-indexed from 0-100%
- **Variables**: Standard biomechanical naming convention

## Validation Snapshot

- **Status**: ⚠️ Partial (87.4%)
- **Stride Pass Rate**: 87.4%
- **Validation Ranges**: docs/datasets/mb24_validation_ranges.yaml (source: docs/datasets/mb24_validation_ranges.yaml)
- **Detailed Report**: [View validation report](#validation)

## Citation
Walters, K. MBLUE Ankle Exoskeleton Study, University of Michigan, 2024.


## Collection Details

### Protocol
Subjects performed locomotion tasks on a treadmill (level walking at 0.75, 1.0, 1.25 m/s; incline/decline at 5 and 10 degrees) and overground (stairs, sit-to-stand, crouch). Data collected with Vicon motion capture and processed through OpenSim for inverse kinematics and dynamics. Both bare (no exoskeleton) and exo (with ankle exoskeleton) conditions were recorded.


### Processing Notes
Data is phase-normalized (101 points in source, interpolated to 150 points for standard format). Joint angles converted from degrees to radians. Knee angle sign convention flipped to flexion-positive. Moments normalized by body mass (Nm/kg). GRF normalized by body weight (BW). Only vertical GRF available in the processed data.


## Files Included

- `converted_datasets/mblue_ankle_phase.parquet` — Phase-normalized dataset
- [Validation report](#validation)
- Conversion script in `contributor_tools/conversion_scripts/mb24/`

---

*Generated by Dataset Submission Tool on 2026-01-12 20:08*
