# Master Validator Blueprint for Locomotion Datasets

This blueprint enables **comprehensive validation** of locomotor biomechanics datasets by combining multiple layers of automated testing. It ensures correctness of units, sign conventions, and task-specific envelopes, with additional cross-variable and subject-level sanity checks. The structure supports automated deployment in CI pipelines (e.g., pytest, Great Expectations) and avoids redundancy through layered inheritance.

---

## Layer 0: Global Sanity Rules (Hard Stops)

| Feature Pattern      | Check                                                            |
| -------------------- | ---------------------------------------------------------------- |
| `.*_angle_rad$`      | Values must be in radians; `abs(value) <= π`                     |
| `.*_velocity_rad_s$` | Units must be rad/s; cycle integral ≈ 0 ± 0.02                   |
| `.*_moment_Nm$`      | Units must be N·m or N·m·kg^-1; `abs(value) <= 4`                |
| `vertical_grf_N`     | Positive upward; peak ≤ 6 BW                                     |
| `ap_grf_N`           | Negative = braking, positive = propulsion; `abs(peak) <= 0.6 BW` |
| `ml_grf_N`           | Positive = rightward; `abs(peak) <= 0.25 BW`                     |
| `cop_[xy]_m`         | Finite during stance phase (`vertical_grf_N > 0.05 BW`)          |
| `time_s`             | Monotonic within `task_id`; matches metadata sampling rate       |
| `phase_%`            | Range 0–100; resets at heel-strike or specified markers          |

---

## Layer 1: Baseline Envelopes (Level Walking Norms)

Features use normative biomechanical bounds derived from level walking.

| Feature                            | Range/Pattern                                                          |
| ---------------------------------- | ---------------------------------------------------------------------- |
| `hip_flexion_angle_rad`            | Peak 0.30–0.60 rad @ 10–20% phase                                      |
| `knee_flexion_angle_rad`           | Peak 0.95–1.20 rad late swing                                          |
| `ankle_flexion_angle_rad`          | Dorsiflexion -0.30 to -0.15 rad (mid-stance); push-off 0.10–0.25 rad   |
| `hip/knee/ankle_*_velocity_rad_s`  | RMS ≤ 3 rad/s; peak hip swing velocity 3–5 rad/s                       |
| `hip/knee/ankle_*_moment_Nm`       | Knee extensor peak 0.35–0.60 Nm/kg; ankle plantar-flexor 1.2–1.6 Nm/kg |
| `torso_angle_y_rad`                | Max < 0.20 rad (minimal pitch)                                         |
| `thigh/shank/foot_angle_[xyz]_rad` | Range < 0.30 rad; sagittal pattern monotonic                           |
| `vertical_grf_N`                   | Double hump: 1.1–1.3 BW; valley 0.7–0.9 BW                             |
| `ap_grf_N`                         | Braking -0.15 to -0.25 BW; propulsion 0.15–0.25 BW                     |
| `ml_grf_N`                         | Peak ≤ 0.10 BW                                                         |
| `cop_x_m`                          | 0.75–0.90 × foot length                                                |
| `cop_y_m`                          | ≤ 0.30 × foot width                                                    |

---

## Layer 2: Task-Specific Overrides

Each task overrides baseline rules only for features that differ. All unspecified features inherit Level Walking rules.

### incline\_walking

* `hip_flexion_angle_rad`: +0.05–0.12 rad shift
* `knee_flexion_angle_rad`: stance increase ≥ 0.05 rad
* `ankle_flexion_angle_rad`: dorsiflexion -0.40 to -0.25 rad
* `knee_moment_Nm`: ≥ 0.60 Nm/kg
* `vertical_grf_N`: upper bound 1.5 BW

### decline\_walking

* `knee_flexion_angle_rad`: > 0.35 rad at heel-strike
* `ankle_flexion_angle_rad`: > 0.35 rad dorsiflexion
* `vertical_grf_N`: early peak ≤ 1.1 BW
* `ap_grf_N`: braking -0.25 to -0.35 BW

### run

* `vertical_grf_N`: 2.0–3.0 BW
* `ap_grf_N`: -0.25 to -0.40 BW
* `hip_flexion_velocity_rad_s`: ≥ 5 rad/s
* Widen all angular and velocity bands by 25%

### up\_stairs

* `hip_flexion_angle_rad`: 0.95–1.25 rad
* `knee_flexion_angle_rad`: 1.50–1.80 rad
* `ankle_moment_Nm`: 1.6–2.2 Nm/kg
* `vertical_grf_N`: 1.3–1.6 BW

### down\_stairs

* `ankle_flexion_angle_rad`: ≥ 0.35 rad dorsiflexion
* `knee_moment_Nm`: 1.5–2.3 Nm/kg eccentric
* `vertical_grf_N`: early peak 1.4–1.8 BW

### sit\_to\_stand / stand\_to\_sit

* `hip_flexion_angle_rad`: start ≥ 1.2 rad → end ≤ 0.3 rad (reverse for stand\_to\_sit)
* `knee_flexion_velocity_rad_s`: > 2 rad/s
* `vertical_grf_N`: 1.4–1.9 BW (sit); ≤ 1.2 BW (stand)

### lift\_weight

* `knee_moment_Nm`: 0.8–1.4 Nm/kg
* `hip_moment_Nm`: hip precedes knee; lag < 5% phase
* `vertical_grf_N`: 1.5–2.2 BW

### jump

* `vertical_grf_N`: 3–6 BW at landing
* `knee_flexion_angle_rad`: 0.8–1.4 rad
* `ankle_flexion_velocity_rad_s`: > 6 rad/s
* `cop_y_m`: ≤ 0.30 × foot width

Other tasks (e.g., lunges, squats, side\_shuffle, cutting) follow similarly structured overrides.

---

## Layer 3: Cross-Variable Physics Checks

| Check                             | Error Caught                     | Method                                                      |
| --------------------------------- | -------------------------------- | ----------------------------------------------------------- |
| Moment × Angular Velocity → Power | Sign flip in moment or angle     | `assert sign(moment * velocity) == expected_power_sign`     |
| Global vs. Local Angles           | Frame error or axis mismatch     | Compare reconstructed joint angles from segment quaternions |
| Left–Right Symmetry               | One-limb sign inversion          | Normalized cross-correlation; metric ∈ \[0.8, 1.2]          |
| Energy Balance per Gait Cycle     | Baseline shift in GRFs or angles | Net COM work ≈ 0 ± 5% BW·m                                  |

---

## Layer 4: Subject-Level Reasonableness Checks

1. **Neutral Pose:** Quiet standing hip/knee/ankle angles ∈ ±0.05 rad
2. **Anthropometry:** Segment lengths match metadata ±5%
3. **Speed-GRF Coupling:** vGRF peak ≈ 1 + 0.11 × speed (BW/m·s)

---

## Full Pipeline Order

```text
Layer 0  → Units, NaNs, axis directions (fail fast)
Layer 1  → Baseline biomechanical norms (inherit by default)
Layer 2  → Task-specific overrides (selective replacement)
Layer 3  → Cross-variable checks (frame/symmetry/physics)
Layer 4  → Subject-level sanity (neutral pose, anthropometry)
```

**Deploy all layers for maximal reliability in biomechanics pipelines**. Each layer isolates errors with traceable diagnostics, enabling robust dataset standardization before model training or downstream analysis.
