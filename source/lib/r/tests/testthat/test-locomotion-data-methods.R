# LocomotionData Methods Tests
# 
# Created: 2025-06-19 with user permission
# Purpose: Comprehensive testing of LocomotionData 3D array operations and statistical methods
#
# Intent: Ensure all LocomotionData analysis methods work correctly with various
# data scenarios, handle edge cases gracefully, and produce mathematically
# correct results for biomechanical analysis workflows.

# Test getCycles Method - Core 3D Array Operations
test_that("getCycles returns correct 3D array structure", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("get_cycles_basic", create_object = TRUE, 
                               n_subjects = 2, n_tasks = 1, n_cycles = 5)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  result <- getCycles(locomotion_obj, subject, task)
  
  expect_3d_array_result(result, expected_cycles = 5, expected_phases = 150, 
                        expected_features = length(locomotion_obj@features))
  
  # Check array dimensions
  expect_equal(dim(result$data_3d), c(5, 150, length(locomotion_obj@features)))
  
  # Check dimension names
  dimnames_result <- dimnames(result$data_3d)
  expect_equal(length(dimnames_result[[1]]), 5)  # cycles
  expect_equal(length(dimnames_result[[2]]), 150)  # phases  
  expect_equal(dimnames_result[[3]], result$feature_names)
})

test_that("getCycles works with feature subset", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("get_cycles_subset", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  # Test with subset of features
  angle_features <- locomotion_obj@features[grepl("angle.*_rad$", locomotion_obj@features)]
  selected_features <- angle_features[1:2]
  
  result <- getCycles(locomotion_obj, subject, task, features = selected_features)
  
  expect_3d_array_result(result, expected_cycles = 3, expected_phases = 150, 
                        expected_features = 2)
  expect_equal(result$feature_names, selected_features)
})

test_that("getCycles handles non-existent subject-task combinations", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("get_cycles_nonexistent", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  # Test with non-existent subject
  expect_warning({
    result <- getCycles(locomotion_obj, "NONEXISTENT", "normal_walk")
  }, "No data found")
  
  result <- suppressWarnings(getCycles(locomotion_obj, "NONEXISTENT", "normal_walk"))
  expect_null(result$data_3d)
  expect_equal(length(result$feature_names), 0)
})

test_that("getCycles validates data length", {
  skip_if_not_installed("arrow")
  
  # Create data with wrong cycle length
  bad_data <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 1)
  # Add extra rows
  extra_rows <- bad_data[1:25]
  bad_data <- rbind(bad_data, extra_rows)
  
  temp_file <- createTempTestFile(bad_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  expect_warning({
    result <- getCycles(locomotion_obj, subject, task)
  }, "not divisible")
  
  result <- suppressWarnings(getCycles(locomotion_obj, subject, task))
  expect_null(result$data_3d)
})

# Test Statistical Pattern Methods
test_that("getMeanPatterns calculates correct statistics", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("mean_patterns", create_object = TRUE, n_cycles = 10)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  mean_patterns <- getMeanPatterns(locomotion_obj, subject, task)
  
  expect_valid_statistics(mean_patterns, expected_features = locomotion_obj@features)
  
  # Check that each pattern has correct length
  for (feature in names(mean_patterns)) {
    expect_equal(length(mean_patterns[[feature]]), 150)
    expect_true(all(is.finite(mean_patterns[[feature]])))
  }
  
  # Verify mathematical correctness with manual calculation
  cycles_result <- getCycles(locomotion_obj, subject, task)
  if (!is.null(cycles_result$data_3d)) {
    feature_idx <- 1
    manual_mean <- apply(cycles_result$data_3d[, , feature_idx], 2, mean, na.rm = TRUE)
    calculated_mean <- mean_patterns[[cycles_result$feature_names[feature_idx]]]
    
    expect_biomech_equal(calculated_mean, manual_mean, tolerance = 1e-10)
  }
})

test_that("getStdPatterns calculates correct standard deviations", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("std_patterns", create_object = TRUE, n_cycles = 10)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  std_patterns <- getStdPatterns(locomotion_obj, subject, task)
  
  expect_valid_statistics(std_patterns, expected_features = locomotion_obj@features)
  
  # Check that each pattern has correct length and non-negative values
  for (feature in names(std_patterns)) {
    expect_equal(length(std_patterns[[feature]]), 150)
    expect_true(all(std_patterns[[feature]] >= 0))
    expect_true(all(is.finite(std_patterns[[feature]])))
  }
  
  # Verify mathematical correctness
  cycles_result <- getCycles(locomotion_obj, subject, task)
  if (!is.null(cycles_result$data_3d)) {
    feature_idx <- 1
    manual_std <- apply(cycles_result$data_3d[, , feature_idx], 2, sd, na.rm = TRUE)
    calculated_std <- std_patterns[[cycles_result$feature_names[feature_idx]]]
    
    expect_biomech_equal(calculated_std, manual_std, tolerance = 1e-10)
  }
})

test_that("Statistical methods handle single cycle data", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("single_cycle_stats", create_object = TRUE, n_cycles = 1)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  # Mean should work with single cycle
  mean_patterns <- getMeanPatterns(locomotion_obj, subject, task)
  expect_true(length(mean_patterns) > 0)
  
  # Standard deviation should be zero for single cycle
  std_patterns <- getStdPatterns(locomotion_obj, subject, task)
  expect_true(length(std_patterns) > 0)
  
  for (feature in names(std_patterns)) {
    expect_true(all(std_patterns[[feature]] == 0))
  }
})

# Test Data Validation Methods
test_that("validateCycles identifies valid cycles", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("validate_cycles", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  valid_cycles <- validateCycles(locomotion_obj, subject, task)
  
  expect_true(is.logical(valid_cycles))
  expect_true(length(valid_cycles) > 0)
  
  # Should have some valid cycles with synthetic data
  expect_true(any(valid_cycles))
})

test_that("validateCycles detects invalid data ranges", {
  skip_if_not_installed("arrow")
  
  # Create data with extreme values
  bad_data <- generateEdgeCaseData("extreme_values")
  temp_file <- createTempTestFile(bad_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  valid_cycles <- validateCycles(locomotion_obj, subject, task)
  
  # Should detect invalid cycles due to extreme values
  expect_true(is.logical(valid_cycles))
  expect_true(any(!valid_cycles))  # Some cycles should be invalid
})

test_that("findOutlierCycles identifies statistical outliers", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("outlier_cycles", create_object = TRUE, n_cycles = 20)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  outlier_indices <- findOutlierCycles(locomotion_obj, subject, task, threshold = 2.0)
  
  expect_true(is.integer(outlier_indices))
  expect_true(all(outlier_indices > 0))
  expect_true(all(outlier_indices <= 20))  # Within expected cycle range
})

test_that("findOutlierCycles threshold parameter works", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("outlier_threshold", create_object = TRUE, n_cycles = 20)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  # Higher threshold should find fewer outliers
  outliers_strict <- findOutlierCycles(locomotion_obj, subject, task, threshold = 3.0)
  outliers_lenient <- findOutlierCycles(locomotion_obj, subject, task, threshold = 1.0)
  
  expect_true(length(outliers_strict) <= length(outliers_lenient))
})

# Test Summary Statistics Methods
test_that("getSummaryStatistics returns comprehensive statistics", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("summary_stats", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  subject <- locomotion_obj@subjects[1] 
  task <- locomotion_obj@tasks[1]
  
  stats <- getSummaryStatistics(locomotion_obj, subject, task)
  
  expect_true(is.data.frame(stats))
  
  # Check required columns
  required_cols <- c("feature", "mean", "std", "min", "max", "median", "q25", "q75")
  expect_true(all(required_cols %in% names(stats)))
  
  # Check data integrity
  expect_equal(nrow(stats), length(locomotion_obj@features))
  expect_true(all(stats$feature %in% locomotion_obj@features))
  
  # Check statistical relationships
  expect_true(all(stats$min <= stats$q25))
  expect_true(all(stats$q25 <= stats$median))
  expect_true(all(stats$median <= stats$q75))
  expect_true(all(stats$q75 <= stats$max))
  expect_true(all(stats$std >= 0))
})

test_that("calculateROM computes range of motion correctly", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("rom_calculation", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  # Test per-cycle ROM
  rom_by_cycle <- calculateROM(locomotion_obj, subject, task, by_cycle = TRUE)
  
  expect_true(is.list(rom_by_cycle))
  expect_true(length(rom_by_cycle) > 0)
  
  for (feature in names(rom_by_cycle)) {
    expect_true(is.numeric(rom_by_cycle[[feature]]))
    expect_true(all(rom_by_cycle[[feature]] >= 0))  # ROM should be non-negative
  }
  
  # Test overall ROM
  rom_overall <- calculateROM(locomotion_obj, subject, task, by_cycle = FALSE)
  
  expect_true(is.list(rom_overall))
  
  for (feature in names(rom_overall)) {
    expect_true(is.numeric(rom_overall[[feature]]))
    expect_equal(length(rom_overall[[feature]]), 1)  # Single value per feature
    expect_true(rom_overall[[feature]] >= 0)
  }
})

# Test Phase Correlation Analysis
test_that("getPhaseCorrelations computes correlation matrices", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("phase_correlations", create_object = TRUE, n_cycles = 10)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  # Test with subset of features to reduce computation
  angle_features <- locomotion_obj@features[grepl("angle.*_rad$", locomotion_obj@features)][1:3]
  
  correlations <- getPhaseCorrelations(locomotion_obj, subject, task, features = angle_features)
  
  expect_true(is.array(correlations))
  expect_equal(length(dim(correlations)), 3)
  expect_equal(dim(correlations), c(150, 3, 3))  # phases x features x features
  
  # Check correlation properties
  for (phase in 1:10) {  # Check first 10 phases
    cor_matrix <- correlations[phase, , ]
    
    # Diagonal should be 1 (self-correlation)
    expect_equal(diag(cor_matrix), rep(1, 3), tolerance = 1e-10)
    
    # Matrix should be symmetric
    expect_equal(cor_matrix, t(cor_matrix), tolerance = 1e-10)
    
    # Correlations should be between -1 and 1
    finite_values <- cor_matrix[is.finite(cor_matrix)]
    if (length(finite_values) > 0) {
      expect_true(all(finite_values >= -1 & finite_values <= 1))
    }
  }
})

test_that("getPhaseCorrelations handles insufficient data", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("phase_corr_insufficient", create_object = TRUE, n_cycles = 1)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  # Should return NULL with insufficient cycles for correlation
  correlations <- getPhaseCorrelations(locomotion_obj, subject, task)
  expect_null(correlations)
})

# Test Multi-Subject and Multi-Task Methods
test_that("getMultiSubjectStatistics aggregates across subjects", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("multi_subject_stats", create_object = TRUE, 
                               n_subjects = 5, n_tasks = 1, n_cycles = 3)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  task <- locomotion_obj@tasks[1]
  
  group_stats <- getMultiSubjectStatistics(locomotion_obj, 
                                          subjects = locomotion_obj@subjects[1:3], 
                                          task = task)
  
  expect_true(is.data.table(group_stats))
  
  required_cols <- c("feature", "group_mean", "group_std", "subject_count", "between_subject_cv")
  expect_true(all(required_cols %in% names(group_stats)))
  
  # Check subject count
  expect_true(all(group_stats$subject_count == 3))
  
  # Check that between-subject CV is reasonable
  expect_true(all(is.finite(group_stats$between_subject_cv)))
})

test_that("getMultiTaskStatistics aggregates across tasks", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("multi_task_stats", create_object = TRUE, 
                               n_subjects = 1, n_tasks = 3, n_cycles = 3)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  subject <- locomotion_obj@subjects[1]
  
  task_stats <- getMultiTaskStatistics(locomotion_obj, subject = subject, 
                                      tasks = locomotion_obj@tasks)
  
  expect_true(is.data.table(task_stats))
  
  required_cols <- c("feature", "across_task_mean", "across_task_std", "task_count", "between_task_cv")
  expect_true(all(required_cols %in% names(task_stats)))
  
  # Check task count
  expect_true(all(task_stats$task_count == 3))
})

test_that("getGroupMeanPatterns computes group averages", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("group_mean_patterns", create_object = TRUE, 
                               n_subjects = 4, n_tasks = 1, n_cycles = 5)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  task <- locomotion_obj@tasks[1]
  
  group_result <- getGroupMeanPatterns(locomotion_obj, 
                                      subjects = locomotion_obj@subjects, 
                                      task = task)
  
  expect_true(is.list(group_result))
  expect_true(all(c("group_means", "group_stds", "subject_count", "subjects_included") %in% names(group_result)))
  
  expect_equal(group_result$subject_count, 4)
  expect_equal(length(group_result$subjects_included), 4)
  
  # Check group means and standard deviations
  expect_true(length(group_result$group_means) > 0)
  expect_true(length(group_result$group_stds) > 0)
  
  for (feature in names(group_result$group_means)) {
    expect_equal(length(group_result$group_means[[feature]]), 150)
    expect_equal(length(group_result$group_stds[[feature]]), 150)
    expect_true(all(is.finite(group_result$group_means[[feature]])))
    expect_true(all(group_result$group_stds[[feature]] >= 0))
  }
})

# Test Performance with Large Datasets
test_that("Methods perform efficiently with large datasets", {
  skip_if_not_installed("arrow")
  
  # Create larger dataset for performance testing
  large_data <- generatePerformanceTestData("medium")
  temp_file <- createTempTestFile(large_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  # Test key methods with timing
  expect_fast_execution({
    cycles_result <- getCycles(locomotion_obj, subject, task)
  }, max_time = 2.0, description = "getCycles on medium dataset")
  
  expect_fast_execution({
    mean_patterns <- getMeanPatterns(locomotion_obj, subject, task)
  }, max_time = 2.0, description = "getMeanPatterns on medium dataset")
  
  expect_fast_execution({
    stats <- getSummaryStatistics(locomotion_obj, subject, task)
  }, max_time = 2.0, description = "getSummaryStatistics on medium dataset")
})