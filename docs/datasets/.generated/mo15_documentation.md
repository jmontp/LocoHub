## Overview

- **Short Code**: MO15
- **Year**: 2015
- **Institution**: Cleveland State University

Treadmill walking dataset from Moore et al. (2015) with 11 subjects walking at
0.8, 1.2, and 1.6 m/s. Data processed through AddBiomechanics pipeline for
standardized musculoskeletal modeling. Part of the AddBiomechanics dataset collection.


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
- **Number of Subjects**: 11
- **Tasks Included**: Level Walking

#### Task Catalog

| Task | Task ID | Task Info |
|------|---------|-----------|
| level_walking | level_0.8ms | speed_m_s:0.8,treadmill:true |
|   | level_1.2ms | speed_m_s:1.2,treadmill:true |
|   | level_1.6ms | speed_m_s:1.6,treadmill:true |

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
<p class="feature-source">Coverage computed from `converted_datasets/Moore2015_phase.parquet`.</p>

#### Ground Reaction Forces

| Feature | Level Walking |
|---|---|
| `grf_anterior_contra_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_anterior_ipsi_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_lateral_contra_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_lateral_ipsi_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_vertical_contra_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |
| `grf_vertical_ipsi_BW` | <span class="feature-chip feature-complete" title="100.0% available">✔</span> |

#### Joint Angles

| Feature | Level Walking |
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

| Feature | Level Walking |
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

| Feature | Level Walking |
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

| Feature | Level Walking |
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
- **Validation Ranges**: [Download validation ranges](./mo15_validation_ranges.yaml) (source: contributor_tools/validation_ranges/default_ranges.yaml)
- **Detailed Report**: [View validation report](#validation)

## Citation
Moore JK, Hnat SK, van den Bogert AJ (2015) An elaborate data set on human gait
and the effect of mechanical perturbations. PeerJ 3:e918. DOI: 10.7717/peerj.918


## Collection Details

### Protocol
Standard motion capture protocol was used.

### Processing Notes
No additional notes.

## Files Included

- `converted_datasets/Moore2015_phase.parquet` — Phase-normalized dataset
- [Validation report](#validation)
- Conversion script in `contributor_tools/conversion_scripts/mo15/`

---

*Generated by Dataset Submission Tool on 2025-12-21 19:29*
