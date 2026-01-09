## Overview

- **Short Code**: GT24
- **Year**: 2024
- **Institution**: EPIC Lab (Georgia Tech)

Dataset from "Task-agnostic exoskeleton control via biological joint moment estimation" (Nature 2024). Contains comprehensive biomechanical data from 25 able-bodied adults performing 28 different activities while wearing a clothing-integrated hip exoskeleton. Includes joint kinematics, kinetics, ground reaction forces, and exoskeleton sensor data collected at 200 Hz across three collection phases.


## Downloads

<style>
.download-grid { display:flex; flex-wrap:wrap; gap:0.75rem; margin-bottom:1rem; }
.download-button { display:inline-block; padding:0.65rem 1.4rem; border-radius:0.5rem; font-weight:600; text-decoration:none; }
.download-button.available { background:#1f78d1; color:#fff; }
.download-button.available:hover { background:#1663ad; }
.download-button.unavailable { background:#d1d5db; color:#6b7280; cursor:not-allowed; }
</style>
<div class="download-grid">
  <a class="download-button available" href="https://www.dropbox.com/scl/fi/addnrep8tyxbdycij746z/gtech_2024_phase_clean.parquet?rlkey=37mauhfmexyvcx9rgovqg3bow&dl=1" target="_blank" rel="noopener">Download Clean Dataset</a>
  <a class="download-button available" href="https://www.dropbox.com/scl/fi/rq9ljak2fmzxhqx68iw2u/gtech_2024_phase.parquet?rlkey=b08njvj2cga8iyo7u48s493uy&dl=1" target="_blank" rel="noopener">Download Full Dataset (Dirty)</a>
</div>

## Dataset Information

### Subjects and Tasks
- **Number of Subjects**: 22
- **Tasks Included**: Backward Walking, Cutting, Decline Walking, Incline Walking, Jump, Level Walking, Lunge, Run, Sit To Stand, Squat, Stair Ascent, Stair Descent, Stand To Sit

### Subject Metadata
The table below summarizes the `subject_metadata` key:value pairs per subject.

| Subject | weight_kg | day | phase |
|---|---|---|---|
| GT24_BT01 | 84.3 | 1 | 1 |
| GT24_BT02 | 79.1 | 1 | 1 |
| GT24_BT03 | 101.5 | 1 | 1 |
| GT24_BT06 | 85.8 | 1 | 1 |
| GT24_BT07 | 70.6 | 1 | 1 |
| GT24_BT08 | 75.7 | 1 | 1 |
| GT24_BT09 | 89.0 | 1 | 1 |
| GT24_BT10 | 100.1 | 1 | 1 |
| GT24_BT11 | 57.0 | 1 | 1 |
| GT24_BT12 | 84.6 | 1 | 1 |
| GT24_BT13 | 96.0 | 1 | 2 |
| GT24_BT14 | 74.3 | 1 | 2 |
| GT24_BT15 | 65.9 | 1 | 2 |
| GT24_BT16 | 72.0 | 1 | 2 |
| GT24_BT17 | 67.4 | 1 | 2 |
| GT24_BT18 | 75.0 | 1 | 3 |
| GT24_BT19 | 76.8 | 1 | 3 |
| GT24_BT20 | 62.5 | 1 | 3 |
| GT24_BT21 | 65.9 | 1 | 3 |
| GT24_BT22 | 84.3 | 1 | 3 |
| GT24_BT23 | 74.2 | 1 | 3 |
| GT24_BT24 | 84.8 | 1 | 3 |

#### Task Catalog

| Task | Task ID | Task Info |
|------|---------|-----------|
| backward_walking | backward_walking | leg:l,exo_state:powered,exo_joints:hip_knee,speed_m_s:0.6 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,speed_m_s:0.8 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,speed_m_s:1.0 |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:0.6 |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:0.8 |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:1.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,speed_m_s:0.6 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,speed_m_s:0.8 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,speed_m_s:1.0 |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:0.6 |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:0.8 |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:1.0 |
| cutting | cutting | leg:l,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee |
| decline_walking | decline_10deg | leg:l,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee |
|   | decline_5deg | leg:l,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee |
| incline_walking | incline_10deg | leg:l,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,exo_controller:hilo |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,exo_controller:hilo |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee |
|   | incline_5deg | leg:l,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,exo_controller:hilo |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,exo_controller:hilo |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee |
| jump | jump | leg:l,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee |
| level_walking | level_0.6ms | leg:l,exo_state:powered,exo_joints:hip_knee,speed_m_s:0.6 |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:0.6 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,speed_m_s:0.6 |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:0.6 |
|   | level_1.2ms | leg:l,exo_state:powered,exo_joints:hip_knee,exo_controller:hilo,speed_m_s:1.2 |
|   |   | leg:l,exo_state:powered,exo_joints:hip_knee,speed_m_s:1.2 |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:1.2 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,exo_controller:hilo,speed_m_s:1.2 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,speed_m_s:1.2 |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:1.2 |
|   | level_1.8ms | leg:l,exo_state:powered,exo_joints:hip_knee,speed_m_s:1.8 |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:1.8 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,speed_m_s:1.8 |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:1.8 |
| lunge | lunge | leg:l,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee |
| run | run_2.0ms | leg:l,exo_state:powered,exo_joints:hip_knee,speed_m_s:2.0 |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:2.0 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,speed_m_s:2.0 |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:2.0 |
|   | run_2.5ms | leg:l,exo_state:powered,exo_joints:hip_knee,speed_m_s:2.5 |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:2.5 |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee,speed_m_s:2.5 |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee,speed_m_s:2.5 |
| sit_to_stand | sit_to_stand | leg:l,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee |
| squat | squat | leg:l,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee |
| stair_ascent | curb_up | leg:l,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee |
|   | step_up | leg:l,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee |
| stair_descent | curb_down | leg:l,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:r,exo_state:worn_unpowered,exo_joints:hip_knee |
| stand_to_sit | stand_to_sit | leg:l,exo_state:powered,exo_joints:hip_knee |
|   |   | leg:l,exo_state:worn_unpowered,exo_joints:hip_knee |

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
<p class="feature-source">Coverage computed from `gtech_2024_phase_clean.parquet`.</p>

#### Ground Reaction Forces

| Feature | Backward Walking | Cutting | Decline Walking | Incline Walking | Jump | Level Walking | Lunge | Run | Sit To Stand | Squat | Stair Ascent | Stair Descent | Stand To Sit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `grf_anterior_contra_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="96.9% available">≈ 96.90</span> | <span class="feature-chip feature-partial" title="97.8% available">≈ 97.80</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="98.2% available">≈ 98.20</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_anterior_ipsi_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_lateral_contra_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="96.9% available">≈ 96.90</span> | <span class="feature-chip feature-partial" title="97.8% available">≈ 97.80</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="98.2% available">≈ 98.20</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_lateral_ipsi_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_vertical_contra_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="96.9% available">≈ 96.90</span> | <span class="feature-chip feature-partial" title="97.8% available">≈ 97.80</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="98.2% available">≈ 98.20</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_vertical_ipsi_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Angles

| Feature | Backward Walking | Cutting | Decline Walking | Incline Walking | Jump | Level Walking | Lunge | Run | Sit To Stand | Squat | Stair Ascent | Stair Descent | Stand To Sit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ankle_dorsiflexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Moments

| Feature | Backward Walking | Cutting | Decline Walking | Incline Walking | Jump | Level Walking | Lunge | Run | Sit To Stand | Squat | Stair Ascent | Stair Descent | Stand To Sit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ankle_dorsiflexion_moment_contra_Nm_kg` | <span class="feature-chip feature-partial" title="95.7% available">≈ 95.70</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="96.9% available">≈ 96.90</span> | <span class="feature-chip feature-partial" title="97.8% available">≈ 97.80</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="94.4% available">≈ 94.40</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-partial" title="95.4% available">≈ 95.40</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="95.7% available">≈ 95.70</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_moment_contra_Nm_kg` | <span class="feature-chip feature-partial" title="95.7% available">≈ 95.70</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="96.9% available">≈ 96.90</span> | <span class="feature-chip feature-partial" title="97.8% available">≈ 97.80</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="94.4% available">≈ 94.40</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-partial" title="95.4% available">≈ 95.40</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="95.7% available">≈ 95.70</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_moment_contra_Nm_kg` | <span class="feature-chip feature-partial" title="95.7% available">≈ 95.70</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="96.9% available">≈ 96.90</span> | <span class="feature-chip feature-partial" title="97.8% available">≈ 97.80</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="94.4% available">≈ 94.40</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-partial" title="95.4% available">≈ 95.40</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="95.7% available">≈ 95.70</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Velocities

| Feature | Backward Walking | Cutting | Decline Walking | Incline Walking | Jump | Level Walking | Lunge | Run | Sit To Stand | Squat | Stair Ascent | Stair Descent | Stand To Sit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ankle_dorsiflexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Other Features

| Feature | Backward Walking | Cutting | Decline Walking | Incline Walking | Jump | Level Walking | Lunge | Run | Sit To Stand | Squat | Stair Ascent | Stair Descent | Stand To Sit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `cop_anterior_contra_m` | <span class="feature-chip feature-partial" title="95.7% available">≈ 95.70</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="96.9% available">≈ 96.90</span> | <span class="feature-chip feature-partial" title="97.8% available">≈ 97.80</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="94.4% available">≈ 94.40</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_anterior_ipsi_m` | <span class="feature-chip feature-partial" title="95.4% available">≈ 95.40</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="95.7% available">≈ 95.70</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_lateral_contra_m` | <span class="feature-chip feature-partial" title="95.7% available">≈ 95.70</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="96.9% available">≈ 96.90</span> | <span class="feature-chip feature-partial" title="97.8% available">≈ 97.80</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="94.4% available">≈ 94.40</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_lateral_ipsi_m` | <span class="feature-chip feature-partial" title="95.4% available">≈ 95.40</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-partial" title="95.7% available">≈ 95.70</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_vertical_contra_m` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_vertical_ipsi_m` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

### Data Structure
- **Format**: Phase-normalized (150 points per gait cycle)
- **Sampling**: Phase-indexed from 0-100%
- **Variables**: Standard biomechanical naming convention

## Validation Snapshot

- **Status**: ⚠️ Partial (83.2%)
- **Stride Pass Rate**: 83.2%
- **Validation Ranges**: [Download validation ranges](./gt24_validation_ranges.yaml) (source: contributor_tools/validation_ranges/default_ranges.yaml)
- **Detailed Report**: [View validation report](#validation)

## Citation
Slade, P., Kochenderfer, M.J., Delp, S.L. et al. Task-agnostic exoskeleton control via biological joint moment estimation. Nature (2024). https://doi.org/10.1038/s41586-024-08157-7


## Collection Details

### Protocol
Data collection occurred in three phases: Phase 1 (BT01-BT12) with unpowered exoskeleton and some heuristic controller trials, Phase 2 (BT13-BT17) with preliminary neural network model, and Phase 3 (BT01, BT02, BT13, BT18-BT24) as validation with final model. Subjects performed 28 activities including treadmill walking (0.6-2.5 m/s), incline/decline walking (5-10 deg), stairs, backward walking, sit-to-stand, squats, jumping, lunges, and cutting maneuvers.


### Processing Notes
Gait cycles detected using vertical GRF threshold crossing (20 N). First 2 and last 1 strides per trial excluded as transitions. IQR-based filtering removes outlier stride durations. Biological moments (exoskeleton torque subtracted) used when available. Data phase-normalized to 150 points per gait cycle. Source data available at Georgia Tech Digital Repository: https://repository.gatech.edu/handle/1853/75759


## Files Included

- `gtech_2024_phase.parquet` — Phase-normalized dataset
- [Validation report](#validation)
- Conversion script in `contributor_tools/conversion_scripts/gt24/`

---

*Generated by Dataset Submission Tool on 2026-01-09 09:51*
