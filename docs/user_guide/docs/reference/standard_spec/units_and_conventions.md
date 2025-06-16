# Units and Conventions

OpenSim-compatible coordinate system, variable naming, and biomechanical reference values.

**Quick Reference:** [Coordinate System](#coordinate-system) • [Variable Naming](#variable-naming) • [Joint Angles](#joint-angles) • [Forces and Moments](#forces-and-moments) • [Typical Values](#typical-biomechanical-values)

## Coordinate System

**Global Frame** (Right-handed):
- **X**: Forward (anterior)
- **Y**: Upward (superior)
- **Z**: Rightward (lateral)

## Variable Naming

**Pattern**: `<joint>_<motion>_<measurement>_<side>_<unit>`

**Examples**:
- `knee_flexion_angle_ipsi_rad`
- `hip_flexion_moment_contra_Nm`
- `ankle_flexion_velocity_ipsi_rad_s`

**Sides**:
- `ipsi` - Ipsilateral (same side as leading leg)
- `contra` - Contralateral (opposite side)

**Units**:
- Angles: `rad` (radians)
- Moments: `Nm` (Newton-meters) 
- Velocities: `rad_s` (radians per second)
- Forces: `N` (Newtons)

## Joint Angles

---

### Hip Joint

**Hip Flexion** (`hip_flexion_angle_[ipsi|contra]_rad`):
- **Positive**: Thigh forward relative to pelvis
- **Zero**: Vertical thigh alignment
- **Range**: -20° (extension) to 110° (sitting)

**Hip Adduction** (`hip_adduction_angle_[ipsi|contra]_rad`):
- **Positive**: Thigh toward midline
- **Range**: -20° to 30°

---

### Knee Joint

**Knee Flexion** (`knee_flexion_angle_[ipsi|contra]_rad`):
- **Zero**: Full extension (OpenSim standard)
- **Positive**: Knee bending (0° → 140°)
- **Range**: 0° (extension) to 140° (maximum flexion)
- **Note**: Motion capture may show -10° due to measurement noise

**Knee Adduction** (`knee_adduction_angle_[ipsi|contra]_rad`):
- **Positive**: Valgus (toward midline)
- **Negative**: Varus (away from midline)
- **Range**: -10° to 15°

---

### Ankle Joint

**Ankle Flexion** (`ankle_flexion_angle_[ipsi|contra]_rad`):
- **Zero**: Foot flat on ground
- **Positive**: Dorsiflexion (toes up)
- **Negative**: Plantarflexion (toes down)
- **Range**: -25° (plantarflexion) to 40° (dorsiflexion)

**Ankle Inversion** (`ankle_inversion_angle_[ipsi|contra]_rad`):
- **Positive**: Sole toward midline
- **Range**: -15° to 20°

## Forces and Moments

### Ground Reaction Forces

Following the **OpenSim coordinate system**:

- **vertical_grf_N**: Vertical ground reaction force (N/kg when normalized)
  - **Positive**: Upward force (along global Y-axis)
  - **Zero reference**: No vertical force

- **ap_grf_N**: Anterior-posterior ground reaction force (N/kg when normalized)
  - **Positive**: Forward/anterior force (along global X-axis) - propulsive
  - **Negative**: Backward/posterior force - braking/decelerative
  - **Zero reference**: No anterior-posterior force

- **ml_grf_N**: Medial-lateral ground reaction force (N/kg when normalized)
  - **Positive**: Rightward/lateral force (along global Z-axis)
  - **Negative**: Leftward/medial force
  - **Zero reference**: No medial-lateral force

### Joint Moments

Following the **OpenSim right-hand rule**:

- **hip_flexion_moment_[ipsi|contra]_Nm**: Hip flexion/extension moment
  - **Positive**: Hip flexion moment (thigh forward rotation)
  - **Negative**: Hip extension moment (thigh backward rotation)
  - **Zero reference**: No hip moment
  - **Anatomical meaning**: Positive values assist hip flexor muscles, negative values assist hip extensor muscles

- **knee_flexion_moment_[ipsi|contra]_Nm**: Knee flexion/extension moment
  - **Positive**: Knee flexion moment
  - **Negative**: Knee extension moment
  - **Anatomical meaning**: Positive values assist knee flexor muscles, negative values assist knee extensor muscles

- **ankle_flexion_moment_[ipsi|contra]_Nm**: Ankle dorsiflexion/plantarflexion moment
  - **Positive**: Ankle dorsiflexion moment (dorsiflexor muscles)
  - **Negative**: Ankle plantarflexion moment (plantarflexor muscles)
  - **Anatomical meaning**: Positive values assist dorsiflexor muscles, negative values assist plantarflexor muscles

## Typical Biomechanical Values

### Reference Body Weight

- **Standard reference**: 70kg adult
- **Body weight force**: 686N (70kg × 9.8 m/s²)
- **Normalized units**: 9.8 N/kg

### Ground Reaction Force Ranges

- **Walking GRF ranges**: 0.8-1.5 BW (8-15 N/kg) for vertical, ±0.3 BW (±3 N/kg) for horizontal
- **Running GRF ranges**: 2.0-2.9 BW (20-28 N/kg) for vertical, higher horizontal forces

**Typical values by direction**:
- **vertical_grf_N_kg**: 8-15 N/kg walking, 20-28 N/kg running
- **ap_grf_N_kg**: -3 to +3 N/kg walking, -8 to +12 N/kg running
- **ml_grf_N_kg**: ±1 N/kg walking, ±2.5 N/kg running

### Joint Moment Ranges (Peak Values)

- **Hip**: 0.8-1.1 Nm/kg
- **Knee**: 0.4-0.6 Nm/kg
- **Ankle**: 1.2-1.6 Nm/kg

## Reference Table

| Joint | Motion | Positive | Zero Reference | Range |
|-------|--------|----------|----------------|-------|
| Hip | Flexion | Forward | Vertical thigh | -20° to 110° |
| Hip | Adduction | Toward midline | Neutral | -20° to 30° |
| Knee | Flexion | Bending | Full extension | 0° to 140° |
| Knee | Adduction | Valgus | Neutral | -10° to 15° |
| Ankle | Flexion | Dorsiflexion | Foot flat | -25° to 40° |
| Ankle | Inversion | Toward midline | Neutral | -15° to 20° |

## Implementation

**Dataset Compatibility**:
- OpenSim models ✓
- AddBiomechanics dataset ✓
- Standard gait analysis literature ✓

**Conversion Requirements**:
1. Identify source convention
2. Apply transformation to OpenSim standard
3. Validate using anatomical limits
4. Document in dataset README

---

*These conventions ensure consistency across datasets and validation systems.*