## Overview

- **Short Code**: UM24K
- **Year**: 2024
- **Institution**: Locomotor Control Systems Lab (University of Michigan)

Dataset from "A Versatile Knee Exoskeleton Mitigates Quadriceps Fatigue
in Lifting, Lowering, and Carrying Tasks" (Science Robotics 2024). Contains
ensemble-averaged biomechanical data from 10 able-bodied adults performing
lifting-lowering-carrying (LLC) tasks while wearing a bilateral knee exoskeleton.
Includes knee kinematics, segment angles, exoskeleton torque, and ground reaction forces.


## Downloads

<style>
.download-grid { display:flex; flex-wrap:wrap; gap:0.75rem; margin-bottom:1rem; }
.download-button { display:inline-block; padding:0.65rem 1.4rem; border-radius:0.5rem; font-weight:600; text-decoration:none; }
.download-button.available { background:#1f78d1; color:#fff; }
.download-button.available:hover { background:#1663ad; }
.download-button.unavailable { background:#d1d5db; color:#6b7280; cursor:not-allowed; }
</style>
<div class="download-grid">
  <a class="download-button available" href="https://www.dropbox.com/scl/fi/modvp9vqkzn3ezsgvmtxe/umich_2024_knee_exo_phase.parquet?rlkey=8ipitw8y88t7cdf7jblrd36h2&dl=0" target="_blank" rel="noopener">Download Clean Dataset</a>
  <span class="download-button unavailable" title="Full dataset download not yet available">Full Dataset (coming soon)</span>
</div>

## Dataset Information

### Subjects and Tasks
- **Number of Subjects**: 10
- **Tasks Included**: Decline Walking, Incline Walking, Level Walking, Squat, Stair Ascent, Stair Descent

### Subject Metadata
The table below summarizes the `subject_metadata` key:value pairs per subject.

| Subject | exo | population |
|---|---|---|
| UM24_AB01 | worn_powered | able_bodied |
| UM24_AB02 | worn_powered | able_bodied |
| UM24_AB03 | worn_powered | able_bodied |
| UM24_AB04 | worn_powered | able_bodied |
| UM24_AB05 | worn_powered | able_bodied |
| UM24_AB06 | worn_powered | able_bodied |
| UM24_AB07 | worn_powered | able_bodied |
| UM24_AB08 | worn_powered | able_bodied |
| UM24_AB09 | worn_powered | able_bodied |
| UM24_AB10 | worn_powered | able_bodied |

#### Task Catalog

| Task | Task ID | Task Info |
|------|---------|-----------|
| decline_walking | decline_15deg | incline_deg:-15,treadmill:false,assistance:exo_worn |
| incline_walking | incline_15deg | incline_deg:15,treadmill:false,assistance:exo_worn |
| level_walking | level | treadmill:false,assistance:exo_worn |
| squat | squat_lifting | variant:squat_lifting,assistance:exo_worn |
| stair_ascent | stair_ascent | step_height_m:0.178,step_number:4,assistance:exo_worn |
| stair_descent | stair_descent | step_height_m:0.178,step_number:4,assistance:exo_worn |

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
<p class="feature-source">Coverage computed from `umich_2024_knee_exo_phase.parquet`.</p>

#### Ground Reaction Forces

| Feature | Decline Walking | Incline Walking | Level Walking | Squat | Stair Ascent | Stair Descent |
|---|---|---|---|---|---|---|
| `grf_anterior_contra_BW` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `grf_anterior_ipsi_BW` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `grf_lateral_contra_BW` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `grf_lateral_ipsi_BW` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `grf_vertical_contra_BW` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `grf_vertical_ipsi_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Angles

| Feature | Decline Walking | Incline Walking | Level Walking | Squat | Stair Ascent | Stair Descent |
|---|---|---|---|---|---|---|
| `ankle_dorsiflexion_angle_contra_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `ankle_dorsiflexion_angle_ipsi_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `foot_sagittal_angle_contra_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `foot_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `hip_flexion_angle_contra_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `hip_flexion_angle_ipsi_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `knee_flexion_angle_contra_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `knee_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_frontal_angle_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `pelvis_sagittal_angle_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `pelvis_transverse_angle_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `shank_sagittal_angle_contra_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `shank_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_angle_contra_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `thigh_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `trunk_frontal_angle_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `trunk_sagittal_angle_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `trunk_transverse_angle_rad` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |

#### Joint Moments

| Feature | Decline Walking | Incline Walking | Level Walking | Squat | Stair Ascent | Stair Descent |
|---|---|---|---|---|---|---|
| `ankle_dorsiflexion_moment_contra_Nm_kg` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `ankle_dorsiflexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `hip_flexion_moment_contra_Nm_kg` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `hip_flexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `knee_flexion_moment_contra_Nm_kg` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `knee_flexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |

#### Joint Velocities

| Feature | Decline Walking | Incline Walking | Level Walking | Squat | Stair Ascent | Stair Descent |
|---|---|---|---|---|---|---|
| `ankle_dorsiflexion_velocity_contra_rad_s` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `ankle_dorsiflexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `hip_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `hip_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `knee_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> |
| `knee_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

### Data Structure
- **Format**: Phase-normalized (150 points per gait cycle)
- **Sampling**: Phase-indexed from 0-100%
- **Variables**: Standard biomechanical naming convention

## Validation Snapshot

- **Status**: ✅ Validated
- **Stride Pass Rate**: 100.0%
- **Validation Ranges**: [Download validation ranges](./um24k_validation_ranges.yaml) (source: contributor_tools/validation_ranges/default_ranges.yaml)
- **Detailed Report**: [View validation report](#validation)

## Citation
Divekar, N.V., Thomas, G.C., Yerva, A.R., Frame, H.B., Gregg, R.D. A versatile
knee exoskeleton mitigates quadriceps fatigue in lifting, lowering, and carrying
tasks. Science Robotics 9, eadr8282 (2024). https://doi.org/10.1126/scirobotics.adr8282


## Collection Details

### Protocol
Data collected from 10 able-bodied participants performing fatiguing and
non-fatiguing lifting-lowering-carrying (LLC) tasks with a bilateral knee exoskeleton.
Tasks include squat lift-lower, level walking, stair ascent/descent (7 inch steps),
and ramp ascent/descent (15 degrees). Data is ensemble-averaged across subjects
and cycles, normalized to 0-100% task cycle.


### Processing Notes
Source data is already ensemble-averaged (101 points per cycle), resampled
to 150 points for standardized format. Only knee angle available (no hip/ankle).
Exoskeleton torque stored in custom column (exo_torque_knee_ipsi_Nm). GRF is
body-weight normalized. Data repository: https://doi.org/10.5061/dryad.z34tmpgks


## Files Included

- `umich_2024_knee_exo_phase.parquet` — Phase-normalized dataset
- [Validation report](#validation)
- Conversion script in `contributor_tools/conversion_scripts/um24k/`

---

*Generated by Dataset Submission Tool on 2026-01-08 21:53*
