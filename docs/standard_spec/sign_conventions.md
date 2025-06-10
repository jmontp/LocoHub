# Sign Conventions

All sign conventions follow the OpenSim coordinate system, which is:
- **Global frame**: Right-handed coordinate system
  - X: points forward
  - Y: points upward
  - Z: points to the right (lateral)

## Joint Angles

### General Principles
- Positive flexion: sagittal plane rotation that decreases joint angle (e.g., thigh forward, knee bends)
- Positive adduction: frontal plane rotation of distal segment toward the midline
- Positive internal rotation: transverse plane rotation of distal segment toward midline/front
- These conventions are consistent with anatomical right-hand rule as used in OpenSim models

### Hip Joint Angles

#### Hip Flexion (`hip_flexion_angle_[ipsi|contra]_rad`)
- **Positive hip flexion**: Thigh rotated **forward** relative to pelvis (sagittal plane)
- **Zero reference**: Thigh aligned vertically downward (anatomical standing position)
- **Typical ranges**:
  - Standing: ~0° to 10°
  - Walking heel strike: 15° to 35°
  - Walking toe-off: -20° to 0° (extension)
  - Sitting: 70° to 110°

**Biomechanical interpretation**:
- **Positive values**: Thigh moves anterior (forward) - hip flexor action
- **Negative values**: Thigh moves posterior (backward) - hip extensor action
- **Clinical significance**: Hip flexion enables limb advancement during swing phase

#### Hip Adduction (`hip_adduction_angle_[ipsi|contra]_rad`)
- **Positive hip adduction**: Thigh moves toward body midline (frontal plane)
- **Zero reference**: Thigh aligned with pelvis in coronal plane
- **Typical ranges**:
  - Standing: -5° to 5°
  - Walking: -10° to 15°
  - Lateral movements: -20° to 30°

**Biomechanical interpretation**:
- **Positive values**: Thigh toward midline - hip adductor action
- **Negative values**: Thigh away from midline (abduction) - hip abductor action

#### Hip Rotation (`hip_rotation_angle_[ipsi|contra]_rad`)
- **Positive hip internal rotation**: Thigh rotated inward (transverse plane)
- **Zero reference**: Thigh aligned with pelvis in transverse plane
- **Typical ranges**:
  - Standing: -10° to 10°
  - Walking: -15° to 20°
  - Dynamic activities: -30° to 40°

### Knee Joint Angles

#### Knee Flexion (`knee_flexion_angle_[ipsi|contra]_rad`)
- **Zero reference**: Full knee extension (shank aligned with thigh) - **OpenSim Standard**
- **Positive knee flexion**: Knee bending - angle increases from 0° (extension) toward flexion
- **Negative values**: Not physiologically possible (hyperextension beyond anatomical limits)
- **Typical ranges**:
  - Standing: 0° to 10°
  - Walking heel strike: 0° to 10°
  - Walking mid-stance: 5° to 20°
  - Walking toe-off: 35° to 50°
  - Walking mid-swing: 60° to 80°
  - Squatting: 90° to 140°

**Biomechanical interpretation**:
- **Zero degrees**: Full knee extension (reference position)
- **Positive values**: Progressive knee flexion (0° → 140°) - knee flexor muscle action
- **Physiological range**: 0° (extension) to ~140° (maximum flexion)
- **Clinical significance**: Knee flexion provides shock absorption and limb clearance

**IMPORTANT**: This follows **OpenSim convention** where extension is the zero reference and flexion is positive.

**Motion Capture Tolerance**: Due to measurement noise and calibration errors, knee angles may register as slightly negative (up to -10°) even at full extension. This is acceptable and accounted for in validation ranges.

#### Knee Adduction (`knee_adduction_angle_[ipsi|contra]_rad`)
- **Positive knee adduction**: Shank rotated toward midline relative to thigh (frontal plane)
- **Also known as**: Knee valgus (positive) vs knee varus (negative)
- **Typical ranges**:
  - Normal alignment: -5° to 5°
  - Dynamic loading: -10° to 15°

#### Knee Rotation (`knee_rotation_angle_[ipsi|contra]_rad`)
- **Positive knee internal rotation**: Shank rotated inward relative to thigh (transverse plane)
- **Typical ranges**:
  - Standing: -10° to 10°
  - Dynamic activities: -20° to 25°

### Ankle Joint Angles

#### Ankle Flexion/Dorsiflexion (`ankle_flexion_angle_[ipsi|contra]_rad`)
- **Zero reference**: Foot flat on ground (anatomical standing position)
- **Positive ankle flexion (dorsiflexion)**: Foot rotated **upward** relative to ground (toes up)
- **Negative ankle flexion (plantarflexion)**: Foot rotated **downward** relative to ground (toes down)
- **Typical ranges**:
  - Standing: -5° to 5°
  - Walking heel strike: -5° to 5°
  - Walking mid-stance: 5° to 15° (dorsiflexion)
  - Walking toe-off: -15° to -25° (plantarflexion)
  - Squatting: 15° to 40° (dorsiflexion)

**Biomechanical interpretation**:
- **Zero degrees**: Foot flat on ground (functional reference position)
- **Positive values (dorsiflexion)**: Toes up, heel down - tibialis anterior action
- **Negative values (plantarflexion)**: Toes down, heel up - gastrocnemius/soleus action
- **Clinical significance**: Dorsiflexion for ground clearance, plantarflexion for propulsion

**Visual Reference**: In validation images, 0° ankle angle shows foot horizontal (flat on ground) for intuitive interpretation.

#### Ankle Inversion (`ankle_inversion_angle_[ipsi|contra]_rad`)
- **Positive ankle inversion**: Sole of foot rotated toward midline (frontal plane)
- **Negative ankle inversion (eversion)**: Sole of foot rotated away from midline
- **Typical ranges**:
  - Standing: -5° to 5°
  - Dynamic activities: -15° to 20°

#### Ankle Rotation (`ankle_rotation_angle_[ipsi|contra]_rad`)
- **Positive ankle internal rotation**: Foot rotated inward relative to shank (transverse plane)
- **Typical ranges**:
  - Standing: -10° to 10°
  - Dynamic activities: -20° to 20°

## Joint Angle Zero References and Anatomical Positions

### Standing Reference Position
All joint angles are defined relative to a **neutral standing position**:
- **Hip**: Thigh vertical, aligned with pelvis
- **Knee**: Shank aligned with thigh (full extension)
- **Ankle**: Foot perpendicular to shank (90° anatomical position)

### Clinical Interpretation Guidelines
- **Flexion patterns**: Generally positive values indicate joint closure/bending
- **Extension patterns**: Generally zero or negative values indicate joint opening/straightening  
- **Functional ranges**: Each joint has task-specific functional ranges documented in validation specifications
- **Pathological indicators**: Values outside normal ranges may indicate movement dysfunction

## Visual Reference

### Forward Kinematics Chain
The joint angle definitions above are implemented in our forward kinematics calculations:

```
Pelvis (fixed reference)
    ↓ [hip_flexion_angle] 
Thigh (rotates about hip joint)
    ↓ [knee_flexion_angle]
Shank (rotates about knee joint)  
    ↓ [ankle_flexion_angle]
Foot (rotates about ankle joint)
```

### Sign Convention Summary Table

| Joint | Motion | Positive Direction | Zero Reference | Biomechanical Meaning |
|-------|--------|-------------------|----------------|----------------------|
| Hip | Flexion | Thigh forward | Vertical thigh | Limb advancement |
| Hip | Adduction | Toward midline | Neutral alignment | Medial stability |
| Hip | Internal Rotation | Inward rotation | Neutral alignment | Transverse plane control |
| Knee | Flexion | Knee bending (0° → 140°) | Full extension (0°) | Shock absorption/clearance |
| Knee | Adduction | Toward midline (valgus) | Neutral alignment | Frontal plane stability |
| Knee | Internal Rotation | Inward rotation | Neutral alignment | Transverse plane control |
| Ankle | Flexion (Dorsiflexion) | Toes up | Foot flat on ground (0°) | Ground clearance |
| Ankle | Inversion | Sole toward midline | Neutral alignment | Foot positioning |
| Ankle | Internal Rotation | Inward rotation | Neutral alignment | Transverse plane control |

### Validation Image Reference
See validation images in `../../validation_images/` for visual examples of these joint angle ranges applied to realistic stick figure representations during different movement phases.

**Visual Features**:
- **Average-centered display**: Solid lines show middle of validation ranges (typical expected posture)
- **Subtle range bounds**: Min (dashed, 10% alpha) and Max (solid, 10% alpha) provide context without distraction
- **True frontal plane view**: Both legs shown from perfect perpendicular perspective (as if viewing person directly from the side)
- **Identical hip positions**: Both legs originate from exactly the same point for true anatomical accuracy
- **Ultra-clean presentation**: No axes, grid, or coordinate numbers - pure focus on biomechanical data
- **Walking direction indicator**: Green arrow shows forward movement orientation
- **Anatomical ankle reference**: 0° ankle angle displays foot flat on ground for intuitive interpretation
- **Bilateral coordination**: Ipsilateral (blue) and contralateral (red) legs show proper bilateral relationships
- **Comprehensive annotations**: Min / Avg / Max values displayed for each joint angle

## Implementation Notes

### Dataset Compatibility
These sign conventions are **verified to be consistent** with:
- **OpenSim models** and coordinate systems (confirmed via web search 2025-06-08)
  - Hip flexion positive ✅
  - Knee flexion positive ✅  
  - Ankle dorsiflexion positive, plantarflexion negative ✅
- **AddBiomechanics** dataset format
- **Standard gait analysis** literature (Perry & Burnfield, Winter, etc.)
- **Clinical biomechanics** conventions

### Conversion Requirements
When converting datasets that use different sign conventions:
1. **Identify source convention** (e.g., Vicon, C3D, custom)
2. **Apply transformation** to match OpenSim conventions
3. **Validate transformation** using known anatomical limits
4. **Document conversion** in dataset-specific README files

### Validation Integration
The validation ranges in `validation_expectations.md` are defined using these exact sign conventions:
- **Positive knee flexion** at toe-off (29-46°) matches OpenSim definition of knee bending from 0° extension
- **Positive ankle dorsiflexion** at mid-stance (3-14°) matches our definition of toes up
- **Negative ankle plantarflexion** at toe-off (-23 to -11°) matches our definition of toes down

This ensures consistency between sign conventions, validation ranges, and visual stick figure representations.

**Note**: All validation ranges assume the **OpenSim convention** where knee extension = 0° and knee flexion = positive values.

## Joint Moments
- Positive values follow the **right-hand rule** about the joint’s axis of rotation
- Moment directions align with the coordinate frame of the parent segment (OpenSim default)

## Ground Reaction Forces (GRF)
- `vertical_grf_N`: positive **upward** (along global Y)
- `ap_grf_N`: positive **anterior/forward** (along global X)
- `ml_grf_N`: positive **rightward/lateral** (along global Z)

## Center of Pressure (COP)
- `cop_x_m`: anterior–posterior, positive in global X (forward)
- `cop_y_m`: mediolateral, positive in global Z (right/lateral)
- `cop_z_m`: vertical, positive in global Y (up)

Note: Segment and marker definitions must be rotated into OpenSim-compatible frames during preprocessing if collected in alternate reference frames (e.g., Vicon).