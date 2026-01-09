## Overview

- **Short Code**: HA13
- **Year**: 2013
- **Institution**: Stanford University

Running dataset at multiple speeds (2-5 m/s). Data processed through AddBiomechanics
pipeline for standardized musculoskeletal modeling.


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
- **Number of Subjects**: 1
- **Tasks Included**: Run

#### Task Catalog

| Task | Task ID | Task Info |
|------|---------|-----------|
| run | run_2.0ms | speed_m_s:2.0 |
|   | run_3.0ms | speed_m_s:3.0 |
|   | run_4.0ms | speed_m_s:4.0 |
|   | run_5.0ms | speed_m_s:5.0 |

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
<p class="feature-source">Coverage computed from `converted_datasets/Hamner2013_phase.parquet`.</p>

#### Ground Reaction Forces

| Feature | Run |
|---|---|
| `grf_anterior_contra_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_anterior_ipsi_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_lateral_contra_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_lateral_ipsi_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_vertical_contra_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_vertical_ipsi_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Angles

| Feature | Run |
|---|---|
| `ankle_dorsiflexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_rotation_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_rotation_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `foot_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_adduction_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_adduction_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_rotation_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_rotation_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_frontal_angle_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_sagittal_angle_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_transverse_angle_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `shank_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_angle_contra_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `thigh_sagittal_angle_ipsi_rad` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Moments

| Feature | Run |
|---|---|
| `ankle_dorsiflexion_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_rotation_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_rotation_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_adduction_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_adduction_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_rotation_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_rotation_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_moment_contra_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_moment_ipsi_Nm_kg` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Velocities

| Feature | Run |
|---|---|
| `ankle_dorsiflexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_dorsiflexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_rotation_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `ankle_rotation_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_adduction_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_adduction_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_rotation_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `hip_rotation_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_velocity_contra_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `knee_flexion_velocity_ipsi_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_frontal_velocity_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_sagittal_velocity_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `pelvis_transverse_velocity_rad_s` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Other Features

| Feature | Run |
|---|---|
| `cop_anterior_contra_m` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_anterior_ipsi_m` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_lateral_contra_m` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_lateral_ipsi_m` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_vertical_contra_m` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `cop_vertical_ipsi_m` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

### Data Structure
- **Format**: Phase-normalized (150 points per gait cycle)
- **Sampling**: Phase-indexed from 0-100%
- **Variables**: Standard biomechanical naming convention

## Validation Snapshot

- **Status**: ❌ Needs Review (0.0%)
- **Stride Pass Rate**: 0.0%
- **Validation Ranges**: [Download validation ranges](./ha13_validation_ranges.yaml) (source: contributor_tools/validation_ranges/default_ranges.yaml)
- **Detailed Report**: [View validation report](#validation)

## Citation
Hamner SR, Seth A, Delp SL (2013) Muscle contributions to propulsion and support
during running. J Biomech. DOI: 10.1016/j.jbiomech.2012.08.014


## Collection Details

### Protocol
Standard motion capture protocol was used.

### Processing Notes
No additional notes.

## Files Included

- `converted_datasets/Hamner2013_phase.parquet` — Phase-normalized dataset
- [Validation report](#validation)
- Conversion script in `contributor_tools/conversion_scripts/ha13/`

---

*Generated by Dataset Submission Tool on 2025-12-21 18:50*
