# locomotion-data-standardization
[Standarlized parquet files](https://www.dropbox.com/scl/fo/mhkiv4d3zvnbtdlujvgje/ACPxjnoj6XxL60QZCuK1WCw?rlkey=nm5a22pktlcemud4gzod3ow09&dl=0)
# Time indexing vs Phase indexing
Tabular formats will be provided for both time indexed data and phase indexed data. The time indexed dat is generaly better to train since it can include transition and non-cyclic task, while the phase indexed data can provide easy ways to plot and analyze performance along a given task. 

Each dataset will describe at which frequency (hz) the time indexed data is sampled at, and how many points per step in contained in the phase index data. 


# Limitations
For now, we only have a subset of what is commonly found in datasets as standardized. The list of currently supported data is
* Joint Angles
* Joint Kinetics
* Link Angles (Global Angles)

# Kinematics
The kinematics have indicator variables to give the joint in the different planes of the human and leg
* plane - s (sagittal), f (frontal), t (transversal)
* leg - r (right), l (left)

## Joint Angles
* hip_angle_{plane}_{leg}
* knee_angle_{plane}_{leg}
* ankle_angle_{plane}_{leg}

## Joint Velocities
* hip_vel_{plane}_{leg}
* knee_vel_{plane}_{leg}
* ankle_vel_{plane}_{leg}

## Link angles (Global Angles)
* thigh_angle_{plane}_{leg}
* shank_angle_{plane}_{leg}
* foot_angle_{plane}_{leg}

## Link Velocities (Global velocities)
* thigh_vel_{plane}_{leg}
* shank_vel_{plane}_{leg}
* foot_vel_{plane}_{leg}

# Kinetics
* hip_torque_{plane}_{leg}
* knee_torque_{plane}_{leg}
* ankle_torque_{plane}_{leg}


# Forces
Annotation regulations:
* axis - z (up+), x (left+), y (forward+)
* leg - r (right), l (left)
  
## Ground Reaction Force
* force_{axis}_{leg}
* COP_{axis}_{leg}
  

# Sagital plane conventions
* Ankle dorsiflexion -> Positive
* Knee Extension -> Positive
* Hip Extension -> Positive


# Task variables
* subject - subject name. Usually contains the filel forlder in it
* task - the current task being performed
* sub_task - additional task info
* time - the time for a given task



# Task naming
* level_walking -> level ground walking at varying velocities
* incline_walking -> walking at an upward sloped angle
* decline_walking -> walking at an downwards sloped angle
* up_stairs -> going up stairs
* down_stairs -> going down stairs
* run -> runing at level ground
* sit_to_stand
* stand_to_sit
* ball_toss_(l,m,r) -> tossing the ball at left, mid, right
* transitions -> transitions between different tasks


# Joint angle representation
![Joint angle convention](joint_angle_references.png)
