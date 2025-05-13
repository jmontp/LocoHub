# Units & Conventions

## SI Units
- Mass: kilograms (kg)
- Length: meters (m)
- Time: seconds (s)
- Angle: radians (rad) or degrees (deg)
- Force: Newtons (N)
- Moment: Newton-meters (N·m)
- Power: Watts (W)

## Variables & Standard Units

### Subject Metadata
| Variable     | Standard Units | Notes                  |
|--------------|----------------|------------------------|
| body_mass    | kg             | from subject metadata  |
| height       | m              | optional               |
| leg_length   | m              | optional               |

### Joint Angles (3DOF where available)
| Variable                      | Standard Units | Notes                          |
|-------------------------------|----------------|--------------------------------|
| hip_flexion_angle             | rad            | sagittal plane                 |
| hip_adduction_angle           | rad            | optional: frontal plane        |
| hip_rotation_angle            | rad            | optional: transverse plane     |
| knee_flexion_angle            | rad            | sagittal plane                 |
| ankle_flexion_angle           | rad            | sagittal plane                 |
| ankle_inversion_angle         | rad            | optional: frontal plane        |
| ankle_rotation_angle          | rad            | optional: transverse plane     |

### Joint Angular Velocities
| Variable                      | Standard Units | Notes                          |
|-------------------------------|----------------|--------------------------------|
| hip_flexion_velocity          | rad/s          | angular velocity               |
| hip_adduction_velocity        | rad/s          | optional                       |
| hip_rotation_velocity         | rad/s          | optional                       |
| knee_flexion_velocity         | rad/s          | angular velocity               |
| ankle_flexion_velocity        | rad/s          | angular velocity               |
| ankle_inversion_velocity      | rad/s          | optional                       |
| ankle_rotation_velocity       | rad/s          | optional                       |

### Joint Moments
| Variable        | Standard Units | Notes              |
|-----------------|----------------|--------------------|
| hip_moment      | N·m            |                    |
| knee_moment     | N·m            |                    |
| ankle_moment    | N·m            |                    |

### Ground Reaction Forces (GRF)
| Variable      | Standard Units | Notes                        |
|---------------|----------------|------------------------------|
| vertical_grf  | N              | positive upward              |
| ap_grf        | N              | positive anterior            |
| ml_grf        | N              | positive medial/right        |

### Center of Pressure (COP)
| Variable | Standard Units | Notes                     |
|----------|----------------|---------------------------|
| cop_x    | m              | mediolateral              |
| cop_y    | m              | anterior-posterior        |
| cop_z    | m              | vertical                  |

### Global Link Angles
| Variable          | Standard Units | Notes                                |
|-------------------|----------------|--------------------------------------|
| torso_angle_x     | rad            | global orientation X (OpenSim)       |
| torso_angle_y     | rad            | global orientation Y (OpenSim)       |
| torso_angle_z     | rad            | global orientation Z (OpenSim)       |
| thigh_angle_x     | rad            | global orientation X                 |
| thigh_angle_y     | rad            | global orientation Y                 |
| thigh_angle_z     | rad            | global orientation Z                 |
| shank_angle_x     | rad            | global orientation X                 |
| shank_angle_y     | rad            | global orientation Y                 |
| shank_angle_z     | rad            | global orientation Z                 |
| foot_angle_x      | rad            | global orientation X                 |
| foot_angle_y      | rad            | global orientation Y                 |
| foot_angle_z      | rad            | global orientation Z                 |

### Global Link Angular Velocities
| Variable            | Standard Units | Notes                         |
|---------------------|----------------|-------------------------------|
| torso_velocity_x    | rad/s          | global angular velocity       |
| torso_velocity_y    | rad/s          |                               |
| torso_velocity_z    | rad/s          |                               |
| thigh_velocity_x    | rad/s          |                               |
| thigh_velocity_y    | rad/s          |                               |
| thigh_velocity_z    | rad/s          |                               |
| shank_velocity_x    | rad/s          |                               |
| shank_velocity_y    | rad/s          |                               |
| shank_velocity_z    | rad/s          |                               |
| foot_velocity_x     | rad/s          |                               |
| foot_velocity_y     | rad/s          |                               |
| foot_velocity_z     | rad/s          |                               |

## Column Naming
Use `<variable>_<unit>`:
- `hip_flexion_angle_rad`  
- `knee_moment_Nm`