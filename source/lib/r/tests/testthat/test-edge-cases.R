# Edge Cases and Boundary Condition Tests
# 
# Created: 2025-06-19 with user permission
# Purpose: Comprehensive testing of edge cases, boundary conditions, and error handling
#
# Intent: Ensure LocomotionData package handles all possible data scenarios
# gracefully, provides meaningful error messages, and maintains robustness
# under stress conditions and unusual data patterns.

# Test Missing Data Handling
test_that("LocomotionData handles missing values gracefully", {
  skip_if_not_installed("arrow")
  
  # Create data with systematic missing values
  missing_data <- generateEdgeCaseData("missing_values")
  temp_file <- createTempTestFile(missing_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  expect_no_error({
    locomotion_obj <- new("LocomotionData", data_path = temp_file)
  })
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  # Methods should handle missing data
  expect_no_error({
    cycles_result <- getCycles(locomotion_obj, subject, task)
  })
  
  expect_no_error({
    mean_patterns <- getMeanPatterns(locomotion_obj, subject, task)
  })
  
  expect_no_error({
    stats <- getSummaryStatistics(locomotion_obj, subject, task)
  })
  
  # Summary should report missing values
  output <- capture.output(summary(locomotion_obj))
  expect_true(any(grepl("missing", output, ignore.case = TRUE)))
})

test_that("LocomotionData handles completely missing features", {
  skip_if_not_installed("arrow")
  
  # Create data where entire feature columns are missing
  test_data <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 2)
  test_data[, hip_flexion_angle_ipsi_rad := NA_real_]
  test_data[, knee_flexion_moment_ipsi_Nm := NA_real_]
  
  temp_file <- createTempTestFile(test_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  # Should handle all-missing features gracefully
  stats <- getSummaryStatistics(locomotion_obj, subject, task)
  
  expect_true(is.data.frame(stats))
  
  # Check that missing features are reported correctly
  hip_stats <- stats[stats$feature == "hip_flexion_angle_ipsi_rad", ]
  if (nrow(hip_stats) > 0) {
    expect_true(is.na(hip_stats$mean) || !is.finite(hip_stats$mean))
  }
})

# Test Extreme Value Handling
test_that("LocomotionData handles extreme biomechanical values", {
  skip_if_not_installed("arrow")
  
  extreme_data <- generateEdgeCaseData("extreme_values")
  temp_file <- createTempTestFile(extreme_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  # Validation should detect extreme values
  valid_cycles <- validateCycles(locomotion_obj, subject, task)
  expect_true(any(!valid_cycles))  # Some cycles should be invalid
  
  # Outlier detection should identify extreme cycles
  outliers <- findOutlierCycles(locomotion_obj, subject, task, threshold = 1.0)
  expect_true(length(outliers) > 0)
  
  # Statistical methods should still work
  expect_no_error({
    stats <- getSummaryStatistics(locomotion_obj, subject, task)
  })
})

test_that("LocomotionData handles infinite and NaN values", {
  skip_if_not_installed("arrow")
  
  test_data <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 2)
  
  # Introduce infinite and NaN values
  test_data[1:5, hip_flexion_angle_ipsi_rad := Inf]
  test_data[6:10, knee_flexion_angle_ipsi_rad := -Inf]
  test_data[11:15, ankle_flexion_moment_ipsi_Nm := NaN]
  
  temp_file <- createTempTestFile(test_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  # Validation should detect non-finite values
  valid_cycles <- validateCycles(locomotion_obj, subject, task)
  expect_true(any(!valid_cycles))
  
  # Statistical methods should handle non-finite values
  stats <- getSummaryStatistics(locomotion_obj, subject, task)
  expect_true(is.data.frame(stats))
  
  # Check that non-finite values are handled in patterns
  mean_patterns <- getMeanPatterns(locomotion_obj, subject, task)
  for (pattern in mean_patterns) {
    expect_true(all(is.finite(pattern)))  # Should exclude non-finite values
  }
})

# Test Data Dimension Edge Cases
test_that("LocomotionData handles single subject data", {
  skip_if_not_installed("arrow")
  
  single_subject_data <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 2, n_cycles = 5)
  temp_file <- createTempTestFile(single_subject_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  expect_no_error({
    locomotion_obj <- new("LocomotionData", data_path = temp_file)
  })
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  expect_equal(length(locomotion_obj@subjects), 1)
  expect_equal(length(locomotion_obj@tasks), 2)
  
  # All methods should work with single subject
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  expect_no_error({
    cycles_result <- getCycles(locomotion_obj, subject, task)
    mean_patterns <- getMeanPatterns(locomotion_obj, subject, task)
    stats <- getSummaryStatistics(locomotion_obj, subject, task)
  })
})

test_that("LocomotionData handles single task data", {
  skip_if_not_installed("arrow")
  
  single_task_data <- generateSyntheticGaitData(n_subjects = 3, n_tasks = 1, n_cycles = 5)
  temp_file <- createTempTestFile(single_task_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  expect_equal(length(locomotion_obj@subjects), 3)
  expect_equal(length(locomotion_obj@tasks), 1)
  
  # Multi-subject analysis should work
  task <- locomotion_obj@tasks[1]
  group_stats <- getMultiSubjectStatistics(locomotion_obj, task = task)
  
  expect_true(is.data.table(group_stats))
  expect_equal(unique(group_stats$subject_count), 3)
})

test_that("LocomotionData handles single cycle data", {
  skip_if_not_installed("arrow")
  
  single_cycle_data <- generateEdgeCaseData("single_cycle")
  temp_file <- createTempTestFile(single_cycle_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  # Should work but with limitations
  cycles_result <- getCycles(locomotion_obj, subject, task)
  expect_equal(dim(cycles_result$data_3d)[1], 1)  # One cycle
  
  # Standard deviation should be zero
  std_patterns <- getStdPatterns(locomotion_obj, subject, task)
  for (pattern in std_patterns) {
    expect_true(all(pattern == 0))
  }
  
  # Correlation analysis should return NULL (insufficient data)
  correlations <- getPhaseCorrelations(locomotion_obj, subject, task)
  expect_null(correlations)
})

# Test Memory and Performance Edge Cases
test_that("LocomotionData handles large datasets efficiently", {
  skip_if_not_installed("arrow")
  
  # Create large dataset
  large_data <- generatePerformanceTestData("large")
  temp_file <- createTempTestFile(large_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  # Constructor should handle large data
  expect_fast_execution({
    locomotion_obj <- new("LocomotionData", data_path = temp_file)
  }, max_time = 10.0, description = "Large dataset constructor")
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  # Core methods should remain efficient
  expect_fast_execution({
    cycles_result <- getCycles(locomotion_obj, subject, task)
  }, max_time = 3.0, description = "getCycles on large dataset")
  
  expect_fast_execution({
    mean_patterns <- getMeanPatterns(locomotion_obj, subject, task)
  }, max_time = 3.0, description = "getMeanPatterns on large dataset")
})

test_that("LocomotionData methods handle memory constraints", {
  skip_if_not_installed("arrow")
  
  medium_data <- generatePerformanceTestData("medium")
  temp_file <- createTempTestFile(medium_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  # Methods should not consume excessive memory
  if (requireNamespace("pryr", quietly = TRUE)) {
    subject <- locomotion_obj@subjects[1]
    task <- locomotion_obj@tasks[1]
    
    expect_reasonable_memory_usage({
      cycles_result <- getCycles(locomotion_obj, subject, task)
    }, max_memory_mb = 50, description = "getCycles memory usage")
    
    expect_reasonable_memory_usage({
      stats <- getSummaryStatistics(locomotion_obj, subject, task)
    }, max_memory_mb = 20, description = "getSummaryStatistics memory usage")
  }
})

# Test Unusual Data Patterns
test_that("LocomotionData handles non-standard phase ranges", {
  skip_if_not_installed("arrow")
  
  test_data <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 2)
  
  # Modify phase range to be non-standard
  test_data[, phase := phase * 0.5]  # 0-50 instead of 0-100
  
  temp_file <- createTempTestFile(test_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  # Should still create object
  expect_no_error({
    locomotion_obj <- new("LocomotionData", data_path = temp_file)
  })
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  # Methods should work but may have warnings
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  expect_no_error({
    cycles_result <- getCycles(locomotion_obj, subject, task)
  })
})

test_that("LocomotionData handles irregular phase spacing", {
  skip_if_not_installed("arrow")
  
  test_data <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 2)
  
  # Create irregular phase spacing
  n_points <- nrow(test_data)
  test_data[, phase := cumsum(runif(n_points, 0.5, 1.5))]
  test_data[, phase := phase / max(phase) * 100]  # Normalize to 0-100
  
  temp_file <- createTempTestFile(test_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  # Should still work for most operations
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  expect_no_error({
    stats <- getSummaryStatistics(locomotion_obj, subject, task)
  })
})

# Test Data Type Edge Cases
test_that("LocomotionData handles mixed numeric types", {
  skip_if_not_installed("arrow")
  
  test_data <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 2)
  
  # Convert some columns to different numeric types
  test_data[, hip_flexion_angle_ipsi_rad := as.integer(hip_flexion_angle_ipsi_rad * 1000) / 1000]
  test_data[, knee_flexion_moment_ipsi_Nm := as.single(knee_flexion_moment_ipsi_Nm)]
  
  temp_file <- createTempTestFile(test_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  expect_no_error({
    locomotion_obj <- new("LocomotionData", data_path = temp_file)
  })
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  # Should handle mixed types in analysis
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  expect_no_error({
    cycles_result <- getCycles(locomotion_obj, subject, task)
    stats <- getSummaryStatistics(locomotion_obj, subject, task)
  })
})

# Test Filtering and Subsetting Edge Cases
test_that("filterSubjects handles edge cases", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("filter_subjects_edge", create_object = TRUE, n_subjects = 3)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  # Filter to non-existent subjects
  expect_warning({
    filtered_obj <- filterSubjects(locomotion_obj, c("NONEXISTENT"))
  }, "not found")
  
  # Filter to single subject
  expect_no_error({
    single_subject_obj <- filterSubjects(locomotion_obj, locomotion_obj@subjects[1])
  })
  
  single_subject_obj <- filterSubjects(locomotion_obj, locomotion_obj@subjects[1])
  expect_equal(length(single_subject_obj@subjects), 1)
  
  # Filter to all subjects (should be unchanged)
  all_subjects_obj <- filterSubjects(locomotion_obj, locomotion_obj@subjects)
  expect_equal(length(all_subjects_obj@subjects), length(locomotion_obj@subjects))
})

test_that("filterTasks handles edge cases", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("filter_tasks_edge", create_object = TRUE, n_tasks = 3)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  # Filter to non-existent tasks
  expect_warning({
    filtered_obj <- filterTasks(locomotion_obj, c("nonexistent_task"))
  }, "not found")
  
  # Filter to single task
  single_task_obj <- filterTasks(locomotion_obj, locomotion_obj@tasks[1])
  expect_equal(length(single_task_obj@tasks), 1)
  
  # Verify data consistency after filtering
  expect_true(all(single_task_obj@subjects %in% 
                 unique(single_task_obj@data[[single_task_obj@subject_col]])))
})

# Test Validation Report Edge Cases
test_that("getValidationReport handles unusual variable names", {
  skip_if_not_installed("arrow")
  
  test_data <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 2)
  
  # Add non-standard variable names
  test_data[, weird_variable_name := hip_flexion_angle_ipsi_rad * 2]
  test_data[, `variable with spaces` := knee_flexion_moment_ipsi_Nm / 2]
  test_data[, `123_numeric_start` := ankle_flexion_velocity_ipsi_rad_s]
  
  temp_file <- createTempTestFile(test_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  # Should handle unusual names in validation
  validation_report <- getValidationReport(locomotion_obj)
  expect_true(is.list(validation_report))
})

# Test Empty Data Edge Cases
test_that("LocomotionData handles completely empty datasets", {
  skip_if_not_installed("arrow")
  
  empty_data <- generateEdgeCaseData("empty_data")
  temp_file <- createTempTestFile(empty_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  # Should fail gracefully with meaningful error
  expect_error({
    locomotion_obj <- new("LocomotionData", data_path = temp_file)
  })
})

test_that("Methods handle empty results gracefully", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("empty_results", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  # Request data for non-existent combination
  empty_result <- suppressWarnings(getCycles(locomotion_obj, "NONEXISTENT", "NONEXISTENT"))
  
  expect_null(empty_result$data_3d)
  expect_equal(length(empty_result$feature_names), 0)
  
  # Methods depending on getCycles should handle empty input
  empty_means <- suppressWarnings(getMeanPatterns(locomotion_obj, "NONEXISTENT", "NONEXISTENT"))
  expect_equal(length(empty_means), 0)
  
  empty_stats <- suppressWarnings(getSummaryStatistics(locomotion_obj, "NONEXISTENT", "NONEXISTENT"))
  expect_true(is.data.frame(empty_stats))
  expect_equal(nrow(empty_stats), 0)
})