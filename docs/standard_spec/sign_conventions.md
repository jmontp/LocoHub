# Sign Conventions

OpenSim-compatible coordinate system and joint angle definitions.

**Quick Reference:** [Joint Angles](#joint-angles) • [Forces](#forces) • [Coordinate System](#coordinate-system)

## Coordinate System

**Global Frame** (Right-handed):
- **X**: Forward (anterior)
- **Y**: Upward (superior)
- **Z**: Rightward (lateral)

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

## Forces

**Ground Reaction Forces**:
- `vertical_grf_N`: Positive upward (Y)
- `anterior_grf_N`: Positive forward (X)
- `lateral_grf_N`: Positive rightward (Z)

**Joint Moments**:
- Follow right-hand rule about joint axis
- Aligned with parent segment coordinate frame

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