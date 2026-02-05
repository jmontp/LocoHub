## Overview

- **Short Code**: GT25D
- **Year**: 2025
- **Institution**: EPIC Lab (Georgia Tech)

Dataset from "Deep Domain Adaptation Eliminates Costly Data Required for Task-Agnostic Wearable Robotic Control" (Science Robotics 2025). Contains biomechanical data from 8 able-bodied adults performing 6 activity categories while wearing a hip-knee exoskeleton with 3 domain adaptation model variants (baseline, 4t4s, 0task). Includes joint kinematics, kinetics, ground reaction forces, exoskeleton torques, and IMU-derived segment angles at 200 Hz.


## Downloads

<style>
.download-grid { display:flex; flex-wrap:wrap; gap:0.75rem; margin-bottom:1rem; }
.download-button { display:inline-block; padding:0.65rem 1.4rem; border-radius:0.5rem; font-weight:600; text-decoration:none; }
.download-button.available { background:#1f78d1; color:#fff; }
.download-button.available:hover { background:#1663ad; }
.download-button.unavailable { background:#d1d5db; color:#6b7280; cursor:not-allowed; }
</style>
<div class="download-grid">
  <a class="download-button available" href="https://www.dropbox.com/scl/fi/ni7qgftpoq2klndsrwkz1/gtech_2025_da_phase_clean.parquet?rlkey=j5ssc03k2sprw09vfzr370nh1&dl=1">Clean Dataset (4,948 strides)</a>
  <a class="download-button available" href="https://www.dropbox.com/scl/fi/jye5hdd9z6ftjf6yogtm8/gtech_2025_da_phase_dirty.parquet?rlkey=edfildc8cwk4sipp4dkccy761&dl=1">Full Dataset (5,470 strides)</a>
</div>

## Dataset Information

### Subjects and Tasks
- **Number of Subjects**: 8
- **Tasks Included**: Backward Walking, Level Walking, Sit To Stand, Stand To Sit

#### Task Catalog

| Task | Task ID | Task Info |
|------|---------|-----------|
| backward_walking | backward_0.6ms | leg:l,exo_state:powered,exo_joints:hip_knee,model:0task,speed_m_s:0.6,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:4t4s,speed_m_s:0.6,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:baseline,speed_m_s:0.6,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:0task,speed_m_s:0.6,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:4t4s,speed_m_s:0.6,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:baseline,speed_m_s:0.6,incline_deg:0.0 |
|   | backward_0.8ms | leg:l,exo_state:powered,exo_joints:hip_knee,model:0task,speed_m_s:0.8,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:4t4s,speed_m_s:0.8,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:baseline,speed_m_s:0.8,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:0task,speed_m_s:0.8,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:4t4s,speed_m_s:0.8,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:baseline,speed_m_s:0.8,incline_deg:0.0 |
|   | backward_1.0ms | leg:l,exo_state:powered,exo_joints:hip_knee,model:0task,speed_m_s:1.0,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:4t4s,speed_m_s:1.0,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:baseline,speed_m_s:1.0,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:0task,speed_m_s:1.0,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:4t4s,speed_m_s:1.0,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:baseline,speed_m_s:1.0,incline_deg:0.0 |
| level_walking | level_0.6ms | leg:l,exo_state:powered,exo_joints:hip_knee,model:0task,speed_m_s:0.6,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:4t4s,speed_m_s:0.6,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:baseline,speed_m_s:0.6,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:0task,speed_m_s:0.6,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:4t4s,speed_m_s:0.6,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:baseline,speed_m_s:0.6,incline_deg:0.0 |
|   | level_1.2ms | leg:l,exo_state:powered,exo_joints:hip_knee,model:0task,speed_m_s:1.2,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:4t4s,speed_m_s:1.2,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:baseline,speed_m_s:1.2,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:0task,speed_m_s:1.2,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:4t4s,speed_m_s:1.2,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:baseline,speed_m_s:1.2,incline_deg:0.0 |
|   | level_1.8ms | leg:l,exo_state:powered,exo_joints:hip_knee,model:0task,speed_m_s:1.8,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:4t4s,speed_m_s:1.8,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:baseline,speed_m_s:1.8,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:0task,speed_m_s:1.8,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:4t4s,speed_m_s:1.8,incline_deg:0.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,model:baseline,speed_m_s:1.8,incline_deg:0.0 |
| sit_to_stand | sit_to_stand | leg:l,exo_state:powered,exo_joints:hip_knee,model:0task,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:4t4s,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:baseline,incline_deg:0.0 |
| stand_to_sit | stand_to_sit | leg:l,exo_state:powered,exo_joints:hip_knee,model:0task,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:4t4s,incline_deg:0.0 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,model:baseline,incline_deg:0.0 |

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
<p class="feature-source">Coverage computed from `converted_datasets/gtech_2025_da_phase_dirty.parquet`.</p>

#### Ground Reaction Forces

| Feature | Backward Walking | Level Walking | Sit To Stand | Stand To Sit |
|---|---|---|---|---|
| `grf_anterior_contra_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_anterior_ipsi_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_lateral_contra_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_lateral_ipsi_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_vertical_contra_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_vertical_ipsi_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Angles

| Feature | Backward Walking | Level Walking | Sit To Stand | Stand To Sit |
|---|---|---|---|---|
| `ankle_dorsiflexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Moments

| Feature | Backward Walking | Level Walking | Sit To Stand | Stand To Sit |
|---|---|---|---|---|
| `ankle_dorsiflexion_assistance_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_assistance_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_biological_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_biological_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_assistance_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_assistance_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_biological_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_biological_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_assistance_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_assistance_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_biological_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_biological_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Velocities

| Feature | Backward Walking | Level Walking | Sit To Stand | Stand To Sit |
|---|---|---|---|---|
| `ankle_dorsiflexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Other Features

| Feature | Backward Walking | Level Walking | Sit To Stand | Stand To Sit |
|---|---|---|---|---|
| `cop_anterior_contra_m` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_anterior_ipsi_m` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_lateral_contra_m` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_lateral_ipsi_m` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_vertical_contra_m` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_vertical_ipsi_m` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

### Data Structure
- **Format**: Phase-normalized (150 points per gait cycle)
- **Sampling**: Phase-indexed from 0-100%
- **Variables**: Standard biomechanical naming convention

## Validation Snapshot

- **Status**: ⚠️ Partial (90.5%)
- **Stride Pass Rate**: 90.5%
- **Validation Ranges**: [Download validation ranges](./gt25d_validation_ranges.yaml) (source: contributor_tools/validation_ranges/default_ranges.yaml)
- **Detailed Report**: [View validation report](#validation)

## Citation
Scherpereel, K.L. et al. Deep domain adaptation eliminates costly data required for task-agnostic wearable robotic control. Science Robotics (2025). https://doi.org/10.1126/scirobotics.ado6509


## Collection Details

### Protocol
Data collected from 8 able-bodied adults wearing a clothing-integrated hip-knee exoskeleton. Subjects performed 6 activity categories: level walking (0.6, 1.2, 1.8 m/s on treadmill), backward walking (0.6, 0.8, 1.0 m/s), stair ascent/descent, sit-to-stand transfers, ball tossing, and cutting maneuvers. Three domain adaptation model variants were tested per subject: baseline (semisupervised), 4t4s (semisupervised with domain adaptation), and 0task (unsupervised). Model variant is stored in task_info as model:<variant>. Despite overlapping subject ID labels (BT01-BT08), these are different participants from the GaTech 2024 TaskAgnostic dataset.


### Processing Notes
Gait cycles detected using vertical GRF threshold crossing (20 N). First 2 and last 1 strides per trial excluded as transitions. IQR-based filtering removes outlier stride durations. Sit-to-stand and stand-to-sit transfers segmented using GRF state machine. Data phase-normalized to 150 points per cycle. Stair ascent/descent trials were too short for stride extraction with current filtering. All data collected with powered exoskeleton. Source data from Georgia Tech Digital Repository.


## Files Included

- `converted_datasets/gtech_2025_da_phase_dirty.parquet` — Phase-normalized dataset
- [Validation report](#validation)
- Conversion script in `contributor_tools/conversion_scripts/gt25d/`

---

*Generated by Dataset Submission Tool on 2026-02-05 14:38*
