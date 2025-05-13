# Sign Conventions

All sign conventions follow the OpenSim coordinate system, which is:
- **Global frame**: Right-handed coordinate system
  - X: points forward
  - Y: points upward
  - Z: points to the right (lateral)

## Joint Angles
- Positive flexion: sagittal plane rotation that decreases joint angle (e.g., thigh forward, knee bends)
- Positive adduction: frontal plane rotation of distal segment toward the midline
- Positive internal rotation: transverse plane rotation of distal segment toward midline/front
- These conventions are consistent with anatomical right-hand rule as used in OpenSim models

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