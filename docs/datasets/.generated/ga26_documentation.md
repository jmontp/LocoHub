## Overview

- **Short Code**: GA26
- **Year**: 2026
- **Institution**: [Please add institution name]

Large-scale human locomotion dataset with 120 healthy male subjects (ages 20-59)
performing 7 tasks. Includes full-body joint kinematics from OpenSim inverse
kinematics. Force plate data available for level walking and sit-stand tasks
(subjects S011-S120 only).


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
- **Tasks Included**: Decline Walking, Incline Walking, Level Walking, Sit To Stand, Stair Ascent, Stair Descent, Stand To Sit

#### Task Catalog

| Task | Task ID | Task Info |
|------|---------|-----------|
| decline_walking | slope_descent | leg:l,exo_state:no_exo |
|   |   | leg:r,exo_state:no_exo |
| incline_walking | slope_ascent | leg:l,exo_state:no_exo |
|   |   | leg:r,exo_state:no_exo |
| level_walking | level_walking | leg:l,exo_state:no_exo |
|   |   | leg:r,exo_state:no_exo |
| sit_to_stand | sit_to_stand | leg:l,exo_state:no_exo |
|   |   | leg:r,exo_state:no_exo |
| stair_ascent | stair_ascent | leg:l,exo_state:no_exo |
|   |   | leg:r,exo_state:no_exo |
| stair_descent | stair_descent | leg:l,exo_state:no_exo |
|   |   | leg:r,exo_state:no_exo |
| stand_to_sit | stand_to_sit | leg:l,exo_state:no_exo |
|   |   | leg:r,exo_state:no_exo |

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
<p class="feature-source">Coverage computed from `converted_datasets/gait120_phase_clean.parquet`.</p>

#### Joint Angles

| Feature | Decline Walking | Incline Walking | Level Walking | Sit To Stand | Stair Ascent | Stair Descent | Stand To Sit |
|---|---|---|---|---|---|---|---|
| `ankle_dorsiflexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_sagittal_angle_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Velocities

| Feature | Decline Walking | Incline Walking | Level Walking | Sit To Stand | Stair Ascent | Stair Descent | Stand To Sit |
|---|---|---|---|---|---|---|---|
| `ankle_dorsiflexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_sagittal_velocity_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-missing" title="0.0% available">✖</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

### Data Structure
- **Format**: Phase-normalized (150 points per gait cycle)
- **Sampling**: Phase-indexed from 0-100%
- **Variables**: Standard biomechanical naming convention

## Validation Snapshot

- **Status**: ❌ Needs Review (17.1%)
- **Stride Pass Rate**: 17.1%
- **Validation Ranges**: [Download validation ranges](./ga26_validation_ranges.yaml) (source: contributor_tools/validation_ranges/default_ranges.yaml)
- **Detailed Report**: [View validation report](#validation)

## Citation
Boo, J., Seo, D., Kim, M. & Koo, S. Comprehensive human locomotion and
electromyography dataset: Gait120. Sci Data (2025).
https://doi.org/10.1038/s41597-025-05391-0


## Collection Details

### Protocol

### Processing Notes
- Joint angles computed via OpenSim inverse kinematics
- Knee angle sign convention converted (source: extension+, output: flexion+)
- Force plate data missing for S001-S010 (calibration issue)
- EMG data available in source but not included in parquet conversion
- Full-body bilateral kinematics available


## Files Included

- `converted_datasets/gait120_phase.parquet` — Phase-normalized dataset
- [Validation report](#validation)
- Conversion script in `contributor_tools/conversion_scripts/ga26/`

---

*Generated by Dataset Submission Tool on 2026-01-22 13:59*
