test_that("Feature constants are properly defined", {
  # Test that constants exist and have expected structure
  expect_true(exists("ANGLE_FEATURES"))
  expect_true(exists("VELOCITY_FEATURES"))
  expect_true(exists("MOMENT_FEATURES"))
  
  # Test angle features
  expect_equal(length(ANGLE_FEATURES), 6)
  expect_true(all(grepl("angle", ANGLE_FEATURES)))
  expect_true(all(grepl("_rad$", ANGLE_FEATURES)))
  
  # Test velocity features
  expect_equal(length(VELOCITY_FEATURES), 6)
  expect_true(all(grepl("velocity", VELOCITY_FEATURES)))
  expect_true(all(grepl("_rad_s$", VELOCITY_FEATURES)))
  
  # Test moment features
  expect_equal(length(MOMENT_FEATURES), 18)
  expect_true(all(grepl("moment", MOMENT_FEATURES)))
  expect_true(all(grepl("_Nm$", MOMENT_FEATURES)))
})

test_that("Feature maps work correctly", {
  # Test kinematic feature map
  kin_map <- getKinematicFeatureMap()
  expect_equal(length(kin_map), 12)  # 6 standard + 6 legacy
  expect_true(all(names(kin_map) %in% c(ANGLE_FEATURES, c(
    'hip_flexion_angle_ipsi', 'hip_flexion_angle_contra',
    'knee_flexion_angle_ipsi', 'knee_flexion_angle_contra',
    'ankle_flexion_angle_ipsi', 'ankle_flexion_angle_contra'
  ))))
  
  # Test kinetic feature map
  kin_map <- getKineticFeatureMap()
  expect_true(length(kin_map) >= length(MOMENT_FEATURES))
  
  # Test velocity feature map
  vel_map <- getVelocityFeatureMap()
  expect_equal(length(vel_map), length(VELOCITY_FEATURES))
})

test_that("Feature list functions work", {
  # Test getFeatureList
  kin_features <- getFeatureList("kinematic")
  expect_equal(kin_features, ANGLE_FEATURES)
  
  kinetic_features <- getFeatureList("kinetic")
  expect_equal(kinetic_features, ALL_KINETIC_FEATURES)
  
  vel_features <- getFeatureList("velocity")
  expect_equal(vel_features, VELOCITY_FEATURES)
  
  # Test error handling
  expect_error(getFeatureList("invalid"), "Unsupported mode")
})

test_that("Feature constants function works", {
  constants <- getFeatureConstants()
  
  expect_true(is.list(constants))
  expect_true("angle_features" %in% names(constants))
  expect_true("velocity_features" %in% names(constants))
  expect_true("moment_features" %in% names(constants))
  expect_true("standard_joints" %in% names(constants))
  expect_true("standard_units" %in% names(constants))
  
  expect_equal(constants$angle_features, ANGLE_FEATURES)
  expect_equal(constants$velocity_features, VELOCITY_FEATURES)
  expect_equal(constants$moment_features, MOMENT_FEATURES)
})