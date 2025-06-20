test_that("Standard compliance checking works", {
  # Test valid standard names
  valid_names <- c(
    "hip_flexion_angle_ipsi_rad",
    "knee_flexion_moment_contra_Nm", 
    "ankle_flexion_velocity_ipsi_rad_s",
    "hip_adduction_moment_contra_Nm_kg"
  )
  
  for (name in valid_names) {
    expect_true(isStandardCompliant(name), 
                info = sprintf("'%s' should be standard compliant", name))
  }
  
  # Test invalid names
  invalid_names <- c(
    "hip_angle",  # Missing parts
    "invalid_joint_angle_ipsi_rad",  # Invalid joint
    "hip_invalid_motion_ipsi_rad",  # Invalid motion
    "hip_flexion_invalid_ipsi_rad",  # Invalid measurement
    "hip_flexion_angle_invalid_rad",  # Invalid side
    "hip_flexion_angle_ipsi_invalid"  # Invalid unit
  )
  
  for (name in invalid_names) {
    expect_false(isStandardCompliant(name),
                 info = sprintf("'%s' should not be standard compliant", name))
  }
})

test_that("Standard name suggestion works", {
  # Test some basic suggestions
  suggestions <- c(
    "hip_angle" = "hip_flexion_angle_ipsi_rad",
    "knee_moment" = "knee_flexion_moment_ipsi_Nm",
    "ankle_velocity" = "ankle_flexion_velocity_ipsi_rad_s"
  )
  
  for (i in seq_along(suggestions)) {
    input_name <- names(suggestions)[i]
    expected <- suggestions[i]
    actual <- suggestStandardName(input_name)
    
    expect_true(isStandardCompliant(actual),
                info = sprintf("Suggested name '%s' should be compliant", actual))
  }
})

test_that("Suggestion handles different cases", {
  # Test case insensitivity
  expect_true(grepl("hip", suggestStandardName("HIP_ANGLE")))
  expect_true(grepl("knee", suggestStandardName("knee_MOMENT")))
  
  # Test side detection
  expect_true(grepl("contra", suggestStandardName("hip_contra_angle")))
  expect_true(grepl("ipsi", suggestStandardName("knee_ipsi_moment")))
  
  # Test unit detection
  expect_true(grepl("rad_s", suggestStandardName("hip_velocity_rad_s")))
  expect_true(grepl("Nm_kg", suggestStandardName("knee_moment_nm_kg")))
})