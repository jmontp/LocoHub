# Kinematic Visualization Guide

This guide documents how to generate and update kinematic pose visualizations for biomechanical validation.

## Overview

The kinematic visualization system generates static pose images showing the minimum and maximum joint angle ranges for each locomotion task at key phase points (0%, 33%, 50%, 66%). These visualizations help validate that the biomechanical ranges are anatomically plausible.

## Components

### 1. Kinematic Pose Generator (`source/visualization/kinematic_pose_generator.py`)

The core visualization module that:
- Performs forward kinematics calculations to position body segments
- Generates stick figure poses based on joint angles
- Creates side-by-side comparisons of minimum and maximum ranges
- Annotates images with angle values in degrees

### 2. Update Validation Images Script (`scripts/update_validation_images.py`)

Automated script that:
- Parses the `validation_expectations.md` file
- Extracts joint angle ranges for all tasks and phases
- Generates complete set of validation images
- Saves images to specified output directory

## Usage

### Updating All Validation Images

To regenerate all validation images after updating the ranges in `validation_expectations.md`:

```bash
python3 scripts/update_validation_images.py
```

Options:
- `--output-dir`: Specify output directory (default: `validation_images/`)
- `--validation-file`: Path to validation expectations file

### Generating Images for Specific Tasks

```python
from source.visualization.kinematic_pose_generator import KinematicPoseGenerator

# Create generator
generator = KinematicPoseGenerator()

# Define joint ranges for a specific phase
joint_ranges = {
    'hip_flexion_angle': {'min': 0.15, 'max': 0.6},    # radians
    'knee_flexion_angle': {'min': -0.05, 'max': 0.15},
    'ankle_flexion_angle': {'min': -0.05, 'max': 0.05}
}

# Generate visualization
filepath = generator.generate_range_visualization(
    task_name='level_walking',
    phase_point=0,  # 0% phase (heel strike)
    joint_ranges=joint_ranges,
    output_path='validation_images'
)
```

## Image Features

Each generated image includes:

1. **Bilateral Stick Figure Poses**:
   - Blue pose: Minimum joint angles for both legs
   - Red pose: Maximum joint angles for both legs
   - Green torso: Fixed reference segment
   - Solid lines: Left leg
   - Dashed lines: Right leg
   - Black joints: Hip (shared), knee, and ankle markers

2. **Annotations**:
   - Task name and phase percentage in title
   - Bilateral joint angle ranges in degrees (left and right leg separately)
   - Ground reference line
   - Axis labels (Anterior-Posterior, Vertical)
   - Legend distinguishing left/right legs

3. **Visual Validation**:
   - Poses should look anatomically plausible
   - Proper bilateral coordination (e.g., right leg forward at heel strike)
   - No impossible joint configurations
   - Clear differentiation between min/max ranges
   - Realistic gait mechanics representation

## Workflow for Updating Ranges

1. **Update validation ranges** in `docs/standard_spec/validation_expectations.md`
2. **Run update script**: `python3 scripts/update_validation_images.py`
3. **Review generated images** in `validation_images/` directory
4. **Check for issues**:
   - Hyperextended knees (negative knee flexion)
   - Excessive joint angles
   - Unrealistic poses
5. **Iterate if needed**: Adjust ranges and regenerate

## File Organization

Generated images follow this naming convention:
```
<task_name>_phase_<phase_percentage>_range.png
```

Examples:
- `level_walking_phase_00_range.png` (heel strike)
- `level_walking_phase_50_range.png` (push-off)
- `squats_phase_50_range.png` (bottom position)

## Technical Details

### Coordinate System
- **Origin**: Hip joint
- **Positive X**: Anterior (forward)
- **Positive Y**: Superior (upward)
- **Angles**: Measured from vertical reference

### Segment Lengths (normalized)
- Thigh: 1.0 units
- Shank: 1.0 units
- Foot: 0.5 units
- Torso: 2.0 units

### Joint Angle Conventions
- **Hip flexion**: Positive = thigh forward from vertical
- **Knee flexion**: Positive = knee bent (shank back from thigh)
- **Ankle flexion**: Positive = dorsiflexion (foot up)

### Sign Convention Correction for Visualization
The kinematic pose generator applies a sign correction to ensure proper anterior-posterior positioning:
- Hip angles are negated (`-hip_angle`) before forward kinematics calculation
- This correction ensures that positive hip flexion values correctly show the leg moving forward
- Without this correction, the visualization would show legs moving in the opposite direction
- The correction is applied only for visualization purposes and does not affect the underlying validation ranges

## Troubleshooting

### Common Issues

1. **"Broken" knee appearance**:
   - Check knee flexion ranges at push-off (should be 30-45°)
   - Ensure positive values (no hyperextension)

2. **Incorrect bilateral coordination**:
   - For level walking heel strike: right leg should be forward (positive hip flexion)
   - For level walking push-off: right leg should be behind (negative hip flexion)
   - Verify that contralateral leg positioning makes biomechanical sense

3. **Floating or underground feet**:
   - Verify ankle angle ranges
   - Check phase-specific expectations

4. **Unrealistic poses**:
   - Compare with biomechanics literature
   - Verify sign conventions are correct
   - Check that bilateral coordination matches expected gait patterns

### Validation Checklist

- [ ] All poses look anatomically plausible
- [ ] Bilateral coordination is realistic (right leg forward at heel strike for normal gait)
- [ ] Joint angles match expected ranges from literature
- [ ] Min/max poses show clear differences
- [ ] No impossible configurations (e.g., knee hyperextension)
- [ ] Ground contact appears realistic for stance phases
- [ ] Left leg (solid line) and right leg (dashed line) are clearly distinguishable
- [ ] Annotation boxes show separate ranges for left and right legs

## Integration with Validation System

The generated images are referenced in:
- `validation_expectations.md` - Four images per task (one for each phase: 0%, 33%, 50%, 66%)
- Validation reports - Visual confirmation of ranges
- Dataset documentation - Task-specific visualizations

### Image References in Documentation
Each task in `validation_expectations.md` now includes four bilateral kinematic visualizations:
- Phase 0% (Heel Strike/Initial): Shows initial contact or starting position
- Phase 33% (Mid-Stance/Loading): Shows mid-cycle positioning
- Phase 50% (Push-Off/Peak): Shows transition or peak activity
- Phase 66% (Mid-Swing/Return): Shows swing or return phase

All image references have been updated to use the new bilateral format with proper left/right leg coordination.

## Future Enhancements

- 3D visualization support
- Animation between min/max poses
- Multi-plane views (frontal, transverse)
- Overlay with actual data distributions
- Interactive angle adjustment