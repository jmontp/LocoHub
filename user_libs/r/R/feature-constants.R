#' @title Locomotion Data Feature Constants
#' @description Centralized feature definitions and mappings for the LocomotionData package
#' 
#' @details
#' This module provides the single source of truth for biomechanical feature ordering and mappings
#' used throughout the locomotion data standardization framework. It defines the canonical feature
#' order that matches plotting function expectations and ensures consistency across all components.
#' 
#' The feature order defined here matches the plotting function expectations:
#' [hip_ipsi, hip_contra, knee_ipsi, knee_contra, ankle_ipsi, ankle_contra]
#' 
#' @name feature-constants
NULL

# Standard feature groups - ordered to match plotting function expectations
# Order: [hip_ipsi, hip_contra, knee_ipsi, knee_contra, ankle_ipsi, ankle_contra]

#' @title Kinematic Features (Joint Angles)
#' @description Standard ordered list of joint angle features
#' @export
ANGLE_FEATURES <- c(
  'hip_flexion_angle_ipsi_rad', 'hip_flexion_angle_contra_rad',
  'knee_flexion_angle_ipsi_rad', 'knee_flexion_angle_contra_rad', 
  'ankle_flexion_angle_ipsi_rad', 'ankle_flexion_angle_contra_rad'
)

#' @title Kinematic Velocities (Joint Velocities)
#' @description Standard ordered list of joint velocity features
#' @export
VELOCITY_FEATURES <- c(
  'hip_flexion_velocity_ipsi_rad_s', 'hip_flexion_velocity_contra_rad_s',
  'knee_flexion_velocity_ipsi_rad_s', 'knee_flexion_velocity_contra_rad_s',
  'ankle_flexion_velocity_ipsi_rad_s', 'ankle_flexion_velocity_contra_rad_s'
)

#' @title Kinetic Features (Joint Moments)
#' @description Standard ordered list of joint moment features
#' @details Standard order: [hip, knee, ankle] x [flexion, adduction, rotation] x [ipsi, contra]
#' @export
MOMENT_FEATURES <- c(
  'hip_flexion_moment_ipsi_Nm', 'hip_flexion_moment_contra_Nm',
  'hip_adduction_moment_ipsi_Nm', 'hip_adduction_moment_contra_Nm',
  'hip_rotation_moment_ipsi_Nm', 'hip_rotation_moment_contra_Nm',
  'knee_flexion_moment_ipsi_Nm', 'knee_flexion_moment_contra_Nm',
  'knee_adduction_moment_ipsi_Nm', 'knee_adduction_moment_contra_Nm',
  'knee_rotation_moment_ipsi_Nm', 'knee_rotation_moment_contra_Nm',
  'ankle_flexion_moment_ipsi_Nm', 'ankle_flexion_moment_contra_Nm',
  'ankle_adduction_moment_ipsi_Nm', 'ankle_adduction_moment_contra_Nm',
  'ankle_rotation_moment_ipsi_Nm', 'ankle_rotation_moment_contra_Nm'
)

#' @title Normalized Kinetic Features
#' @description Alternative kinetic features normalized by body weight
#' @export
MOMENT_FEATURES_NORMALIZED <- c(
  'hip_flexion_moment_ipsi_Nm_kg', 'hip_flexion_moment_contra_Nm_kg',
  'hip_adduction_moment_ipsi_Nm_kg', 'hip_adduction_moment_contra_Nm_kg',
  'hip_rotation_moment_ipsi_Nm_kg', 'hip_rotation_moment_contra_Nm_kg',
  'knee_flexion_moment_ipsi_Nm_kg', 'knee_flexion_moment_contra_Nm_kg',
  'knee_adduction_moment_ipsi_Nm_kg', 'knee_adduction_moment_contra_Nm_kg',
  'knee_rotation_moment_ipsi_Nm_kg', 'knee_rotation_moment_contra_Nm_kg',
  'ankle_flexion_moment_ipsi_Nm_kg', 'ankle_flexion_moment_contra_Nm_kg',
  'ankle_adduction_moment_ipsi_Nm_kg', 'ankle_adduction_moment_contra_Nm_kg',
  'ankle_rotation_moment_ipsi_Nm_kg', 'ankle_rotation_moment_contra_Nm_kg'
)

#' @title Ground Reaction Force Features
#' @description Standard ground reaction force measurements
#' @export
GRF_FEATURES <- c(
  'grf_vertical_ipsi_N', 'grf_vertical_contra_N',
  'grf_anterior_ipsi_N', 'grf_anterior_contra_N',
  'grf_lateral_ipsi_N', 'grf_lateral_contra_N'
)

#' @title Center of Pressure Features
#' @description Standard center of pressure measurements
#' @export
COP_FEATURES <- c(
  'cop_anterior_ipsi_m', 'cop_anterior_contra_m',
  'cop_lateral_ipsi_m', 'cop_lateral_contra_m',
  'cop_vertical_ipsi_m', 'cop_vertical_contra_m'
)

#' @title All Kinetic Features
#' @description Combined list of all kinetic features
#' @export
ALL_KINETIC_FEATURES <- c(MOMENT_FEATURES, GRF_FEATURES, COP_FEATURES)

# Standard variable naming convention components
STANDARD_JOINTS <- c('hip', 'knee', 'ankle')
STANDARD_MOTIONS <- c('flexion', 'adduction', 'rotation')
STANDARD_MEASUREMENTS <- c('angle', 'velocity', 'moment', 'power')
STANDARD_SIDES <- c('contra', 'ipsi')
STANDARD_UNITS <- c('rad', 'rad_s', 'Nm', 'Nm_kg', 'W', 'W_kg', 'deg', 'deg_s', 'N', 'm')

#' @title Get Kinematic Feature Map
#' @description Get feature index mapping for kinematic variables
#' @return Named integer vector mapping variable names to array indices (0-5)
#' @export
getKinematicFeatureMap <- function() {
  feature_map <- setNames(seq_along(ANGLE_FEATURES) - 1, ANGLE_FEATURES)
  
  # Legacy naming convention (for backward compatibility)
  legacy_features <- c(
    'hip_flexion_angle_ipsi', 'hip_flexion_angle_contra',
    'knee_flexion_angle_ipsi', 'knee_flexion_angle_contra',
    'ankle_flexion_angle_ipsi', 'ankle_flexion_angle_contra'
  )
  legacy_map <- setNames(seq_along(legacy_features) - 1, legacy_features)
  
  return(c(feature_map, legacy_map))
}

#' @title Get Kinetic Feature Map
#' @description Get feature index mapping for kinetic variables
#' @return Named integer vector mapping variable names to array indices
#' @export
getKineticFeatureMap <- function() {
  # Standard naming convention (Nm)
  feature_map <- setNames(seq_along(MOMENT_FEATURES) - 1, MOMENT_FEATURES)
  
  # Normalized naming convention (Nm/kg)
  normalized_map <- setNames(seq_along(MOMENT_FEATURES_NORMALIZED) - 1, MOMENT_FEATURES_NORMALIZED)
  
  return(c(feature_map, normalized_map))
}

#' @title Get Velocity Feature Map
#' @description Get feature index mapping for velocity variables
#' @return Named integer vector mapping variable names to array indices (0-5)
#' @export
getVelocityFeatureMap <- function() {
  return(setNames(seq_along(VELOCITY_FEATURES) - 1, VELOCITY_FEATURES))
}

#' @title Get Feature List
#' @description Get the ordered feature list for the specified mode
#' @param mode Character string: 'kinematic', 'kinetic', or 'velocity'
#' @return Character vector of feature names in canonical order
#' @export
getFeatureList <- function(mode) {
  switch(mode,
    "kinematic" = ANGLE_FEATURES,
    "kinetic" = ALL_KINETIC_FEATURES,
    "velocity" = VELOCITY_FEATURES,
    stop(sprintf("Unsupported mode: %s. Use 'kinematic', 'kinetic', or 'velocity'", mode))
  )
}

#' @title Get Feature Map
#' @description Get feature index mapping for the specified mode
#' @param mode Character string: 'kinematic', 'kinetic', or 'velocity'
#' @return Named integer vector mapping variable names to array indices
#' @export
getFeatureMap <- function(mode) {
  switch(mode,
    "kinematic" = getKinematicFeatureMap(),
    "kinetic" = getKineticFeatureMap(),
    "velocity" = getVelocityFeatureMap(),
    stop(sprintf("Unsupported mode: %s. Use 'kinematic', 'kinetic', or 'velocity'", mode))
  )
}

#' @title Get Feature Constants
#' @description Get all feature constants as a named list
#' @return List containing all feature constant vectors
#' @export
getFeatureConstants <- function() {
  list(
    angle_features = ANGLE_FEATURES,
    velocity_features = VELOCITY_FEATURES,
    moment_features = MOMENT_FEATURES,
    moment_features_normalized = MOMENT_FEATURES_NORMALIZED,
    grf_features = GRF_FEATURES,
    cop_features = COP_FEATURES,
    all_kinetic_features = ALL_KINETIC_FEATURES,
    standard_joints = STANDARD_JOINTS,
    standard_motions = STANDARD_MOTIONS,
    standard_measurements = STANDARD_MEASUREMENTS,
    standard_sides = STANDARD_SIDES,
    standard_units = STANDARD_UNITS
  )
}
