# Integration Tests
# 
# Created: 2025-06-19 with user permission
# Purpose: End-to-end integration testing of LocomotionData workflows
#
# Intent: Test complete analysis workflows that combine multiple methods,
# verify data consistency across operations, and ensure the package works
# as intended for real-world biomechanical analysis scenarios.

# Test Complete Analysis Workflow
test_that("Complete biomechanical analysis workflow works end-to-end", {
  skip_if_not_installed("arrow")
  
  # Setup larger dataset for realistic workflow
  env <- setup_test_environment("complete_workflow", create_object = TRUE, 
                               n_subjects = 5, n_tasks = 3, n_cycles = 10)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  # Step 1: Data exploration
  subjects <- getSubjects(locomotion_obj)
  tasks <- getTasks(locomotion_obj)
  features <- getFeatures(locomotion_obj)
  
  expect_equal(length(subjects), 5)
  expect_equal(length(tasks), 3)
  expect_true(length(features) > 10)
  
  # Step 2: Single subject analysis
  subject <- subjects[1]
  task <- tasks[1]
  
  # Get raw cycles
  cycles_result <- getCycles(locomotion_obj, subject, task)
  expect_3d_array_result(cycles_result, expected_cycles = 10, expected_phases = 150, 
                        expected_features = length(features))
  
  # Calculate patterns
  mean_patterns <- getMeanPatterns(locomotion_obj, subject, task)
  std_patterns <- getStdPatterns(locomotion_obj, subject, task)
  
  expect_equal(length(mean_patterns), length(features))
  expect_equal(length(std_patterns), length(features))
  
  # Validate data quality
  valid_cycles <- validateCycles(locomotion_obj, subject, task)
  outlier_cycles <- findOutlierCycles(locomotion_obj, subject, task)
  
  expect_equal(length(valid_cycles), 10)
  expect_true(is.integer(outlier_cycles))
  
  # Calculate summary statistics
  stats <- getSummaryStatistics(locomotion_obj, subject, task)
  expect_true(is.data.frame(stats))
  expect_equal(nrow(stats), length(features))
  
  # Step 3: Multi-subject analysis
  group_stats <- getMultiSubjectStatistics(locomotion_obj, subjects = subjects[1:3], task = task)
  expect_true(is.data.table(group_stats))
  expect_equal(unique(group_stats$subject_count), 3)
  
  group_patterns <- getGroupMeanPatterns(locomotion_obj, subjects = subjects[1:3], task = task)
  expect_true(is.list(group_patterns))
  expect_equal(group_patterns$subject_count, 3)
  
  # Step 4: Multi-task analysis
  task_stats <- getMultiTaskStatistics(locomotion_obj, subject = subject, tasks = tasks)
  expect_true(is.data.table(task_stats))
  expect_equal(unique(task_stats$task_count), 3)
  
  # Step 5: Range of motion analysis
  rom_by_cycle <- calculateROM(locomotion_obj, subject, task, by_cycle = TRUE)
  rom_overall <- calculateROM(locomotion_obj, subject, task, by_cycle = FALSE)
  
  expect_true(is.list(rom_by_cycle))
  expect_true(is.list(rom_overall))
  
  # Verify ROM consistency
  for (feature in names(rom_by_cycle)) {
    expect_true(all(rom_by_cycle[[feature]] <= rom_overall[[feature]] * 1.1))  # Allow small tolerance
  }
  
  # Step 6: Correlation analysis (on subset for performance)
  angle_features <- features[grepl("angle.*_rad$", features)][1:3]
  correlations <- getPhaseCorrelations(locomotion_obj, subject, task, features = angle_features)
  
  if (!is.null(correlations)) {
    expect_true(is.array(correlations))
    expect_equal(dim(correlations), c(150, 3, 3))
  }
})

# Test Data Filtering and Subsetting Workflows
test_that("Data filtering and subsetting workflow maintains consistency", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("filtering_workflow", create_object = TRUE, 
                               n_subjects = 6, n_tasks = 4, n_cycles = 5)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  original_subjects <- getSubjects(locomotion_obj)
  original_tasks <- getTasks(locomotion_obj)
  
  # Filter to subset of subjects
  subset_subjects <- original_subjects[1:3]
  filtered_obj <- filterSubjects(locomotion_obj, subset_subjects)
  
  expect_equal(getSubjects(filtered_obj), subset_subjects)
  expect_equal(getTasks(filtered_obj), original_tasks)  # Tasks should remain the same
  
  # Verify data consistency in filtered object
  for (subject in subset_subjects) {
    for (task in original_tasks) {
      original_result <- getCycles(locomotion_obj, subject, task)
      filtered_result <- getCycles(filtered_obj, subject, task)
      
      if (!is.null(original_result$data_3d) && !is.null(filtered_result$data_3d)) {
        expect_equal(dim(original_result$data_3d), dim(filtered_result$data_3d))
        expect_biomech_equal(original_result$data_3d, filtered_result$data_3d, tolerance = 1e-12)
      }
    }
  }
  
  # Filter to subset of tasks
  subset_tasks <- original_tasks[1:2]
  task_filtered_obj <- filterTasks(locomotion_obj, subset_tasks)
  
  expect_equal(getTasks(task_filtered_obj), subset_tasks)
  
  # Chain filtering operations
  double_filtered_obj <- filterSubjects(task_filtered_obj, subset_subjects)
  
  expect_equal(getSubjects(double_filtered_obj), subset_subjects)
  expect_equal(getTasks(double_filtered_obj), subset_tasks)
  
  # Verify analysis still works on filtered data
  subject <- subset_subjects[1]
  task <- subset_tasks[1]
  
  expect_no_error({
    cycles_result <- getCycles(double_filtered_obj, subject, task)
    mean_patterns <- getMeanPatterns(double_filtered_obj, subject, task)
    stats <- getSummaryStatistics(double_filtered_obj, subject, task)
  })
})

# Test Data Validation Integration
test_that("Data validation integrates properly with analysis methods", {
  skip_if_not_installed("arrow")
  
  # Create mixed quality dataset
  good_data <- generateSyntheticGaitData(n_subjects = 2, n_tasks = 1, n_cycles = 5, seed = 100)
  bad_data <- generateEdgeCaseData("extreme_values", seed = 200)
  
  # Combine datasets
  mixed_data <- rbind(good_data, bad_data, fill = TRUE)
  
  temp_file <- createTempTestFile(mixed_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  subjects <- getSubjects(locomotion_obj)
  tasks <- getTasks(locomotion_obj)
  
  # Validation should identify quality issues
  validation_summary <- list()
  
  for (subject in subjects) {
    for (task in tasks) {
      valid_cycles <- validateCycles(locomotion_obj, subject, task)
      outlier_cycles <- findOutlierCycles(locomotion_obj, subject, task)
      
      validation_summary[[paste(subject, task, sep = "_")]] <- list(
        valid_cycles = valid_cycles,
        outlier_cycles = outlier_cycles,
        valid_proportion = mean(valid_cycles),
        outlier_count = length(outlier_cycles)
      )
    }
  }
  
  # Should detect quality differences between subjects
  valid_proportions <- sapply(validation_summary, function(x) x$valid_proportion)
  expect_true(length(unique(round(valid_proportions, 1))) > 1)  # Different quality levels
  
  # Analysis should still work but with appropriate warnings/handling
  for (subject in subjects[1:2]) {  # Test first 2 subjects
    task <- tasks[1]
    
    expect_no_error({
      stats <- getSummaryStatistics(locomotion_obj, subject, task)
      mean_patterns <- getMeanPatterns(locomotion_obj, subject, task)
    })
  }
})

# Test Multi-Modal Analysis Integration
test_that("Multi-modal biomechanical analysis workflow", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("multimodal_analysis", create_object = TRUE,
                               n_subjects = 4, n_tasks = 2, n_cycles = 8)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  features <- getFeatures(locomotion_obj)
  
  # Separate features by type
  angle_features <- features[grepl("angle.*_rad$", features)]
  velocity_features <- features[grepl("velocity.*_rad_s$", features)]
  moment_features <- features[grepl("moment.*_Nm$", features)]
  
  expect_true(length(angle_features) > 0)
  expect_true(length(velocity_features) > 0)
  expect_true(length(moment_features) > 0)
  
  subject <- getSubjects(locomotion_obj)[1]
  task <- getTasks(locomotion_obj)[1]
  
  # Analyze each modality separately
  kinematic_analysis <- list()
  kinetic_analysis <- list()
  
  # Kinematic analysis (angles + velocities)
  kinematic_features <- c(angle_features, velocity_features)
  kinematic_cycles <- getCycles(locomotion_obj, subject, task, features = kinematic_features)
  kinematic_analysis$mean_patterns <- getMeanPatterns(locomotion_obj, subject, task, features = kinematic_features)
  kinematic_analysis$stats <- getSummaryStatistics(locomotion_obj, subject, task, features = kinematic_features)
  kinematic_analysis$rom <- calculateROM(locomotion_obj, subject, task, features = kinematic_features)
  
  # Kinetic analysis (moments)
  kinetic_cycles <- getCycles(locomotion_obj, subject, task, features = moment_features)
  kinetic_analysis$mean_patterns <- getMeanPatterns(locomotion_obj, subject, task, features = moment_features)
  kinetic_analysis$stats <- getSummaryStatistics(locomotion_obj, subject, task, features = moment_features)
  kinetic_analysis$rom <- calculateROM(locomotion_obj, subject, task, features = moment_features)
  
  # Verify analysis completeness
  expect_equal(length(kinematic_analysis$mean_patterns), length(kinematic_features))
  expect_equal(length(kinetic_analysis$mean_patterns), length(moment_features))
  
  expect_equal(nrow(kinematic_analysis$stats), length(kinematic_features))
  expect_equal(nrow(kinetic_analysis$stats), length(moment_features))
  
  # Cross-modal correlation analysis (subset for performance)
  selected_angles <- angle_features[1:2]
  selected_moments <- moment_features[1:2]
  cross_modal_features <- c(selected_angles, selected_moments)
  
  if (length(cross_modal_features) >= 2) {
    cross_correlations <- getPhaseCorrelations(locomotion_obj, subject, task, 
                                              features = cross_modal_features)
    
    if (!is.null(cross_correlations)) {
      expect_equal(dim(cross_correlations)[2], length(cross_modal_features))
      expect_equal(dim(cross_correlations)[3], length(cross_modal_features))
    }
  }
})

# Test Performance and Scalability Integration
test_that("Package scales appropriately with data size", {
  skip_if_not_installed("arrow")
  
  # Test with progressively larger datasets
  size_performance <- list()
  
  for (size in c("small", "medium")) {  # Skip large for CI performance
    test_data <- generatePerformanceTestData(size)
    temp_file <- createTempTestFile(test_data, "parquet")
    
    # Measure constructor performance
    constructor_time <- system.time({
      locomotion_obj <- new("LocomotionData", data_path = temp_file)
    })
    
    subject <- getSubjects(locomotion_obj)[1]
    task <- getTasks(locomotion_obj)[1]
    
    # Measure method performance
    cycles_time <- system.time({
      cycles_result <- getCycles(locomotion_obj, subject, task)
    })
    
    stats_time <- system.time({
      stats <- getSummaryStatistics(locomotion_obj, subject, task)
    })
    
    size_performance[[size]] <- list(
      n_subjects = length(getSubjects(locomotion_obj)),
      n_tasks = length(getTasks(locomotion_obj)),
      n_features = length(getFeatures(locomotion_obj)),
      data_size = nrow(locomotion_obj@data),
      constructor_time = constructor_time[["elapsed"]],
      cycles_time = cycles_time[["elapsed"]],
      stats_time = stats_time[["elapsed"]]
    )
    
    cleanupTestFiles(temp_file)
  }
  
  # Verify reasonable scaling
  small_perf <- size_performance[["small"]]
  medium_perf <- size_performance[["medium"]]
  
  # Data size should scale appropriately
  expect_true(medium_perf$data_size > small_perf$data_size)
  
  # Performance should scale sub-linearly for most operations
  size_ratio <- medium_perf$data_size / small_perf$data_size
  time_ratio <- medium_perf$cycles_time / small_perf$cycles_time
  
  # getCycles time should not scale worse than O(n) with data size
  expect_true(time_ratio <= size_ratio * 2)  # Allow 2x tolerance
})

# Test Error Recovery and Robustness
test_that("Package recovers gracefully from errors in workflow", {
  skip_if_not_installed("arrow")
  
  # Create dataset with mixed quality
  good_data <- generateSyntheticGaitData(n_subjects = 2, n_tasks = 2, n_cycles = 3, seed = 300)
  
  # Introduce various data issues
  good_data[1:10, hip_flexion_angle_ipsi_rad := NA]  # Missing values
  good_data[11:15, knee_flexion_moment_ipsi_Nm := Inf]  # Infinite values
  good_data[151:160, phase := phase + 100]  # Wrong phase range for one cycle
  
  temp_file <- createTempTestFile(good_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  # Constructor should handle issues gracefully
  expect_no_error({
    locomotion_obj <- new("LocomotionData", data_path = temp_file)
  })
  
  locomotion_obj <- new("LocomotionData", data_path = temp_file)
  
  # Workflow should continue despite data issues
  subjects <- getSubjects(locomotion_obj)
  tasks <- getTasks(locomotion_obj)
  
  for (subject in subjects) {
    for (task in tasks) {
      # Some operations may warn but should not error
      expect_no_error({
        cycles_result <- suppressWarnings(getCycles(locomotion_obj, subject, task))
        stats <- suppressWarnings(getSummaryStatistics(locomotion_obj, subject, task))
        valid_cycles <- suppressWarnings(validateCycles(locomotion_obj, subject, task))
      })
      
      # Results should be reasonable even with data issues
      if (!is.null(cycles_result$data_3d)) {
        expect_true(length(cycles_result$feature_names) > 0)
      }
      
      if (is.data.frame(stats) && nrow(stats) > 0) {
        expect_true(all(stats$feature %in% getFeatures(locomotion_obj)))
      }
    }
  }
})

# Test Reproducibility and Consistency
test_that("Analysis results are reproducible and consistent", {
  skip_if_not_installed("arrow")
  
  # Create identical datasets
  data1 <- generateSyntheticGaitData(n_subjects = 2, n_tasks = 1, n_cycles = 5, seed = 42)
  data2 <- generateSyntheticGaitData(n_subjects = 2, n_tasks = 1, n_cycles = 5, seed = 42)
  
  # Verify datasets are identical
  expect_equal(data1, data2)
  
  # Create objects from identical data
  temp_file1 <- createTempTestFile(data1, "parquet")
  temp_file2 <- createTempTestFile(data2, "parquet")
  on.exit(cleanupTestFiles(c(temp_file1, temp_file2)))
  
  locomotion_obj1 <- new("LocomotionData", data_path = temp_file1)
  locomotion_obj2 <- new("LocomotionData", data_path = temp_file2)
  
  subject <- getSubjects(locomotion_obj1)[1]
  task <- getTasks(locomotion_obj1)[1]
  
  # Results should be identical
  cycles1 <- getCycles(locomotion_obj1, subject, task)
  cycles2 <- getCycles(locomotion_obj2, subject, task)
  
  expect_biomech_equal(cycles1$data_3d, cycles2$data_3d, tolerance = 1e-15)
  
  mean_patterns1 <- getMeanPatterns(locomotion_obj1, subject, task)
  mean_patterns2 <- getMeanPatterns(locomotion_obj2, subject, task)
  
  for (feature in names(mean_patterns1)) {
    expect_biomech_equal(mean_patterns1[[feature]], mean_patterns2[[feature]], tolerance = 1e-15)
  }
  
  stats1 <- getSummaryStatistics(locomotion_obj1, subject, task)
  stats2 <- getSummaryStatistics(locomotion_obj2, subject, task)
  
  expect_equal(stats1, stats2)
})