test_that("Unit conversion functions work", {
  # Test degree to radian conversion
  expect_equal(deg2rad(0), 0)
  expect_equal(deg2rad(90), pi/2, tolerance = 1e-10)
  expect_equal(deg2rad(180), pi, tolerance = 1e-10)
  expect_equal(deg2rad(360), 2*pi, tolerance = 1e-10)
  
  # Test radian to degree conversion
  expect_equal(rad2deg(0), 0)
  expect_equal(rad2deg(pi/2), 90, tolerance = 1e-10)
  expect_equal(rad2deg(pi), 180, tolerance = 1e-10)
  expect_equal(rad2deg(2*pi), 360, tolerance = 1e-10)
  
  # Test round-trip conversions
  test_degrees <- c(-180, -90, 0, 45, 90, 135, 180)
  expect_equal(rad2deg(deg2rad(test_degrees)), test_degrees, tolerance = 1e-10)
  
  test_radians <- c(-pi, -pi/2, 0, pi/4, pi/2, 3*pi/4, pi)
  expect_equal(deg2rad(rad2deg(test_radians)), test_radians, tolerance = 1e-10)
})

test_that("Phase calculation works", {
  # Simple test case
  time <- seq(0, 2, by = 0.1)
  events <- c(0, 1, 2)  # Two complete cycles
  
  phase <- calculatePhase(time, events)
  
  expect_equal(length(phase), length(time))
  expect_true(all(phase >= 0 & phase <= 100, na.rm = TRUE))
  
  # Check that phase starts at 0 for each cycle
  expect_equal(phase[1], 0)  # First event
  expect_equal(phase[11], 0)  # Second event (at t=1)
  
  # Test error handling
  expect_error(calculatePhase(time, c(0)), "Need at least 2 gait events")
})

test_that("Phase interpolation works", {
  # Test simple interpolation
  phase <- c(0, 25, 50, 75, 100)
  data <- c(0, 1, 0, -1, 0)
  
  interpolated <- interpolateToPhase(phase, data, n_points = 5)
  expect_equal(length(interpolated), 5)
  expect_equal(interpolated, data, tolerance = 1e-10)
  
  # Test with more points
  interpolated_dense <- interpolateToPhase(phase, data, n_points = 9)
  expect_equal(length(interpolated_dense), 9)
  expect_equal(interpolated_dense[1], 0)
  expect_equal(interpolated_dense[9], 0)
  
  # Test error handling
  expect_error(interpolateToPhase(c(1, 2), c(1)), "same length")
})

test_that("Data dimension validation works", {
  # Valid dimensions
  expect_true(validateDataDimensions(150, 150))  # 1 cycle
  expect_true(validateDataDimensions(300, 150))  # 2 cycles
  expect_true(validateDataDimensions(1500, 150)) # 10 cycles
  
  # Invalid dimensions
  expect_false(validateDataDimensions(0, 150))    # No data
  expect_false(validateDataDimensions(100, 150))  # Incomplete cycle
  expect_false(validateDataDimensions(200, 150))  # Not divisible
  expect_false(validateDataDimensions(150, 0))    # Invalid points per cycle
})

test_that("Feature summary creation works", {
  # Test with mixed features
  features <- c(
    "hip_flexion_angle_ipsi_rad",
    "knee_flexion_angle_contra_rad", 
    "ankle_flexion_velocity_ipsi_rad_s",
    "hip_flexion_moment_ipsi_Nm",
    "knee_adduction_moment_contra_Nm",
    "vertical_grf_N",
    "cop_x_m"
  )
  
  summary_df <- createFeatureSummary(features)
  
  expect_true(is.data.frame(summary_df))
  expect_true("type" %in% names(summary_df))
  expect_true("count" %in% names(summary_df))
  expect_true("examples" %in% names(summary_df))
  
  # Check counts
  expect_equal(summary_df[summary_df$type == "Angles", "count"], 2)
  expect_equal(summary_df[summary_df$type == "Velocities", "count"], 1)
  expect_equal(summary_df[summary_df$type == "Moments", "count"], 2)
  expect_equal(summary_df[summary_df$type == "GRF", "count"], 1)
  expect_equal(summary_df[summary_df$type == "COP", "count"], 1)
  
  # Test with empty features
  empty_summary <- createFeatureSummary(character(0))
  expect_equal(nrow(empty_summary), 0)
})

test_that("Feature name formatting works", {
  # Test basic formatting
  expect_equal(formatFeatureName("hip_flexion_angle_ipsi_rad"), 
               "Hip Flexion Angle Ipsi rad")
  
  expect_equal(formatFeatureName("knee_adduction_moment_contra_Nm"), 
               "Knee Adduction Moment Contra Nm")
  
  expect_equal(formatFeatureName("ankle_flexion_velocity_ipsi_rad_s"), 
               "Ankle Flexion Velocity Ipsi rad S")
  
  # Test abbreviation handling
  expect_true(grepl("GRF", formatFeatureName("vertical_grf_N")))
  expect_true(grepl("COP", formatFeatureName("cop_x_m")))
}