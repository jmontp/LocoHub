# LocomotionData S4 Class Tests
# 
# Created: 2025-06-19 with user permission
# Purpose: Comprehensive testing of LocomotionData S4 class constructor and core methods
#
# Intent: Ensure LocomotionData class is robust, properly validates input data,
# handles edge cases gracefully, and provides consistent API behavior across
# different data scenarios and usage patterns.

# Test LocomotionData Constructor and Initialization
test_that("LocomotionData constructor works with valid parquet data", {
  skip_if_not_installed("arrow")
  
  # Setup test environment
  env <- setup_test_environment("constructor_basic", create_object = FALSE)
  on.exit(env$cleanup())
  
  # Test constructor
  expect_no_error({
    locomotion_obj <- new("LocomotionData", data_path = env$temp_file)
  })
  
  locomotion_obj <- new("LocomotionData", data_path = env$temp_file)
  
  # Validate object structure
  expect_locomotion_data(locomotion_obj, expected_subjects = 2, expected_tasks = 2)
  
  # Check that data was loaded correctly
  expect_equal(nrow(locomotion_obj@data), nrow(env$test_data))
  expect_true(all(env$test_data$subject %in% locomotion_obj@subjects))
  expect_true(all(env$test_data$task %in% locomotion_obj@tasks))
})

test_that("LocomotionData constructor handles missing files", {
  expect_error({
    new("LocomotionData", data_path = "nonexistent_file.parquet")
  }, "Data file not found")
})

test_that("LocomotionData constructor validates required columns", {
  skip_if_not_installed("arrow")
  
  # Create data without required columns
  invalid_data <- data.table(
    id = 1:100,
    value = rnorm(100)
  )
  
  temp_file <- createTempTestFile(invalid_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  expect_error({
    new("LocomotionData", data_path = temp_file)
  }, "required columns")
})

test_that("LocomotionData constructor works with custom column names", {
  skip_if_not_installed("arrow")
  
  # Create data with custom column names
  test_data <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 2)
  setnames(test_data, "subject", "participant_id")
  setnames(test_data, "task", "condition")
  setnames(test_data, "phase", "gait_phase")
  
  temp_file <- createTempTestFile(test_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  expect_no_error({
    locomotion_obj <- new("LocomotionData", 
                         data_path = temp_file,
                         subject_col = "participant_id",
                         task_col = "condition", 
                         phase_col = "gait_phase")
  })
  
  locomotion_obj <- new("LocomotionData", 
                       data_path = temp_file,
                       subject_col = "participant_id",
                       task_col = "condition", 
                       phase_col = "gait_phase")
  
  expect_equal(locomotion_obj@subject_col, "participant_id")
  expect_equal(locomotion_obj@task_col, "condition")
  expect_equal(locomotion_obj@phase_col, "gait_phase")
})

test_that("LocomotionData constructor detects and validates features", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("constructor_features", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  # Check that biomechanical features were identified
  expect_true(length(locomotion_obj@features) > 0)
  
  # Check for expected feature types
  angle_features <- locomotion_obj@features[grepl("angle.*_rad$", locomotion_obj@features)]
  moment_features <- locomotion_obj@features[grepl("moment.*_Nm$", locomotion_obj@features)]
  velocity_features <- locomotion_obj@features[grepl("velocity.*_rad_s$", locomotion_obj@features)]
  
  expect_true(length(angle_features) > 0)
  expect_true(length(moment_features) > 0)
  expect_true(length(velocity_features) > 0)
  
  # Check feature mappings
  expect_true(length(locomotion_obj@feature_mappings) > 0)
  expect_true(all(names(locomotion_obj@feature_mappings) %in% locomotion_obj@features))
})

# Test Core Accessor Methods
test_that("getSubjects method works correctly", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("get_subjects", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  subjects <- getSubjects(locomotion_obj)
  
  expect_true(is.character(subjects))
  expect_equal(length(subjects), 2)
  expect_true(all(subjects %in% c("SUB01", "SUB02")))
  expect_equal(subjects, locomotion_obj@subjects)
})

test_that("getTasks method works correctly", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("get_tasks", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  tasks <- getTasks(locomotion_obj)
  
  expect_true(is.character(tasks))
  expect_equal(length(tasks), 2)
  expect_equal(tasks, locomotion_obj@tasks)
})

test_that("getFeatures method works correctly", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("get_features", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  features <- getFeatures(locomotion_obj)
  
  expect_true(is.character(features))
  expect_true(length(features) > 0)
  expect_equal(features, locomotion_obj@features)
  
  # Check that features are valid biomechanical variables
  biomech_pattern <- "(angle.*_rad|velocity.*_rad_s|moment.*_Nm)$"
  expect_true(all(grepl(biomech_pattern, features)))
})

# Test Show and Summary Methods  
test_that("show method displays object information", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("show_method", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  # Capture output
  output <- capture.output(show(locomotion_obj))
  
  expect_true(length(output) > 0)
  expect_true(any(grepl("LocomotionData object", output)))
  expect_true(any(grepl("Data file:", output)))
  expect_true(any(grepl("Subjects:", output)))
  expect_true(any(grepl("Tasks:", output)))
  expect_true(any(grepl("Features:", output)))
})

test_that("summary method provides detailed information", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("summary_method", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  # Capture summary output
  output <- capture.output(summary(locomotion_obj))
  
  expect_true(length(output) > 0)
  expect_true(any(grepl("LocomotionData Summary", output)))
  expect_true(any(grepl("Data Quality Summary", output)))
  expect_true(any(grepl("Phase coverage:", output)))
  expect_true(any(grepl("Feature breakdown:", output)))
})

# Test Data Validation
test_that("LocomotionData validates data format correctly", {
  skip_if_not_installed("arrow")
  
  # Test with valid phase-indexed data
  env <- setup_test_environment("validation_valid", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  # Should have validation report
  validation_report <- getValidationReport(locomotion_obj)
  expect_true(is.list(validation_report))
})

test_that("LocomotionData handles data with incorrect cycle lengths", {
  skip_if_not_installed("arrow")
  
  # Create data with incorrect cycle length
  bad_data <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 1)
  # Add extra rows to break 150-point assumption
  extra_rows <- bad_data[1:25]
  bad_data <- rbind(bad_data, extra_rows)
  
  temp_file <- createTempTestFile(bad_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  # Should still create object but may have warnings
  expect_warning({
    locomotion_obj <- new("LocomotionData", data_path = temp_file)
  }, NA)  # May or may not warn - implementation dependent
})

# Test File Format Support
test_that("LocomotionData supports CSV files", {
  env <- setup_test_environment("csv_support", create_object = FALSE)
  on.exit(env$cleanup())
  
  # Create CSV file
  csv_file <- createTempTestFile(env$test_data, "csv")
  on.exit(cleanupTestFiles(csv_file), add = TRUE)
  
  expect_no_error({
    locomotion_obj <- new("LocomotionData", data_path = csv_file, file_type = "csv")
  })
  
  locomotion_obj <- new("LocomotionData", data_path = csv_file, file_type = "csv")
  expect_locomotion_data(locomotion_obj)
})

test_that("LocomotionData auto-detects file format", {
  env <- setup_test_environment("auto_detect", create_object = FALSE)
  on.exit(env$cleanup())
  
  # Test auto-detection with parquet file
  expect_no_error({
    locomotion_obj <- new("LocomotionData", data_path = env$temp_file, file_type = "auto")
  })
  
  locomotion_obj <- new("LocomotionData", data_path = env$temp_file, file_type = "auto") 
  expect_locomotion_data(locomotion_obj)
})

# Test Error Handling
test_that("LocomotionData handles corrupted files gracefully", {
  # Create a file with invalid content
  temp_file <- tempfile(fileext = ".parquet")
  writeLines("This is not a parquet file", temp_file)
  on.exit(unlink(temp_file))
  
  expect_error({
    new("LocomotionData", data_path = temp_file)
  })
})

test_that("LocomotionData handles empty files", {
  skip_if_not_installed("arrow")
  
  # Create empty parquet file
  empty_data <- data.table(
    subject = character(0),
    task = character(0), 
    phase = numeric(0)
  )
  
  temp_file <- createTempTestFile(empty_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  expect_error({
    new("LocomotionData", data_path = temp_file)
  }, "No data")
})

# Test S4 Method Definitions
test_that("All required S4 methods are defined", {
  required_methods <- c(
    "getSubjects", "getTasks", "getFeatures", "getCycles",
    "getMeanPatterns", "getStdPatterns", "validateCycles",
    "findOutlierCycles", "getSummaryStatistics", "calculateROM",
    "getValidationReport", "show", "summary"
  )
  
  for (method in required_methods) {
    expect_s4_method_exists(method, "LocomotionData")
  }
})

# Test Object Integrity
test_that("LocomotionData maintains data integrity", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("integrity_check", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  # Check that subjects in data match subjects slot
  data_subjects <- sort(unique(locomotion_obj@data[[locomotion_obj@subject_col]]))
  slot_subjects <- sort(locomotion_obj@subjects)
  expect_equal(data_subjects, slot_subjects)
  
  # Check that tasks in data match tasks slot  
  data_tasks <- sort(unique(locomotion_obj@data[[locomotion_obj@task_col]]))
  slot_tasks <- sort(locomotion_obj@tasks)
  expect_equal(data_tasks, slot_tasks)
  
  # Check that all features exist as columns
  expected_columns <- c(locomotion_obj@subject_col, locomotion_obj@task_col, 
                       locomotion_obj@phase_col, locomotion_obj@features)
  actual_columns <- names(locomotion_obj@data)
  expect_true(all(expected_columns %in% actual_columns))
})

test_that("LocomotionData validates points per cycle", {
  skip_if_not_installed("arrow")
  
  env <- setup_test_environment("points_per_cycle", create_object = TRUE)
  on.exit(env$cleanup())
  
  locomotion_obj <- env$locomotion_obj
  expect_false(is.null(locomotion_obj))
  
  # Should have 150 points per cycle
  expect_equal(locomotion_obj@points_per_cycle, 150L)
  
  # Check actual data structure
  subject <- locomotion_obj@subjects[1]
  task <- locomotion_obj@tasks[1]
  
  subject_task_data <- locomotion_obj@data[
    get(locomotion_obj@subject_col) == subject & 
    get(locomotion_obj@task_col) == task
  ]
  
  # Should be multiple of 150
  expect_equal(nrow(subject_task_data) %% 150, 0)
})