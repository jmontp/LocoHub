# Test Helper Functions and Custom Assertions
# 
# Created: 2025-06-19 with user permission
# Purpose: Custom test assertions and helper functions for LocomotionData testing
#
# Intent: Provide specialized testing utilities for biomechanical data validation,
# S4 object testing, and 3D array operations. Ensures consistent test patterns
# and reduces code duplication across test files.

library(testthat)

#' Custom Assertion: LocomotionData Object Structure
#' 
#' Validates that an object is a properly constructed LocomotionData instance.
#' 
#' @param object object to test
#' @param expected_subjects integer expected number of subjects (optional)
#' @param expected_tasks integer expected number of tasks (optional)
#' @param expected_features integer expected number of features (optional)
expect_locomotion_data <- function(object, expected_subjects = NULL, 
                                  expected_tasks = NULL, expected_features = NULL) {
  
  # Check class
  expect_s4_class(object, "LocomotionData")
  
  # Check basic slots exist and have correct types
  expect_true(is.data.table(object@data))
  expect_true(is.character(object@subjects))
  expect_true(is.character(object@tasks))
  expect_true(is.character(object@features))
  expect_true(is.character(object@data_path))
  expect_true(is.list(object@feature_mappings))
  expect_true(is.list(object@validation_report))
  expect_true(is.list(object@cache))
  expect_true(is.integer(object@points_per_cycle))
  
  # Check expected dimensions if provided
  if (!is.null(expected_subjects)) {
    expect_equal(length(object@subjects), expected_subjects)
  }
  
  if (!is.null(expected_tasks)) {
    expect_equal(length(object@tasks), expected_tasks)
  }
  
  if (!is.null(expected_features)) {
    expect_equal(length(object@features), expected_features)
  }
  
  # Check data consistency
  expect_true(nrow(object@data) > 0)
  expect_true(all(object@subjects %in% unique(object@data[[object@subject_col]])))
  expect_true(all(object@tasks %in% unique(object@data[[object@task_col]])))
  
  # Check points per cycle
  expect_equal(object@points_per_cycle, 150L)
  
  invisible(object)
}

#' Custom Assertion: 3D Array Structure
#' 
#' Validates 3D array output from getCycles method.
#' 
#' @param result list with 'data_3d' and 'feature_names' components
#' @param expected_cycles integer expected number of cycles
#' @param expected_phases integer expected number of phase points (default: 150)
#' @param expected_features integer expected number of features
expect_3d_array_result <- function(result, expected_cycles, expected_phases = 150, 
                                  expected_features) {
  
  expect_type(result, "list")
  expect_true("data_3d" %in% names(result))
  expect_true("feature_names" %in% names(result))
  
  if (!is.null(result$data_3d)) {
    expect_true(is.array(result$data_3d))
    expect_equal(length(dim(result$data_3d)), 3)
    expect_equal(dim(result$data_3d), c(expected_cycles, expected_phases, expected_features))
    expect_equal(length(result$feature_names), expected_features)
    
    # Check dimension names
    dimnames_result <- dimnames(result$data_3d)
    expect_equal(length(dimnames_result), 3)
    expect_true(grepl("cycle_", dimnames_result[[1]][1]))
    expect_true(grepl("phase_", dimnames_result[[2]][1]))
    expect_equal(dimnames_result[[3]], result$feature_names)
  } else {
    # NULL result should have empty feature names
    expect_equal(length(result$feature_names), 0)
  }
  
  invisible(result)
}

#' Custom Assertion: Biomechanical Data Ranges
#' 
#' Validates that biomechanical data falls within realistic ranges.
#' 
#' @param data data.table or matrix with biomechanical data
#' @param feature_name character name of the feature to validate
#' @param tolerance numeric tolerance factor for range validation (default: 1.5)
expect_realistic_biomech_ranges <- function(data, feature_name, tolerance = 1.5) {
  
  if (is.data.table(data)) {
    values <- data[[feature_name]]
  } else if (is.matrix(data) || is.array(data)) {
    values <- as.numeric(data)
  } else {
    values <- as.numeric(data)
  }
  
  # Remove missing values
  values <- values[!is.na(values)]
  
  if (length(values) == 0) {
    skip("No valid values to test")
  }
  
  # Define realistic ranges based on feature type
  if (grepl("angle.*_rad$", feature_name)) {
    # Angles in radians - typically -π to π, but allow some tolerance
    expected_range <- c(-pi * tolerance, pi * tolerance)
    expect_true(all(values >= expected_range[1] & values <= expected_range[2]),
                info = sprintf("Angle %s outside realistic range [%.2f, %.2f]: min=%.2f, max=%.2f",
                              feature_name, expected_range[1], expected_range[2], 
                              min(values), max(values)))
    
  } else if (grepl("velocity.*_rad_s$", feature_name)) {
    # Angular velocities in rad/s - typically within ±20 rad/s
    expected_range <- c(-20 * tolerance, 20 * tolerance)
    expect_true(all(values >= expected_range[1] & values <= expected_range[2]),
                info = sprintf("Velocity %s outside realistic range [%.2f, %.2f]: min=%.2f, max=%.2f",
                              feature_name, expected_range[1], expected_range[2], 
                              min(values), max(values)))
    
  } else if (grepl("moment.*_Nm$", feature_name)) {
    # Moments in Nm - typically within ±300 Nm for adults
    expected_range <- c(-300 * tolerance, 300 * tolerance)
    expect_true(all(values >= expected_range[1] & values <= expected_range[2]),
                info = sprintf("Moment %s outside realistic range [%.2f, %.2f]: min=%.2f, max=%.2f",
                              feature_name, expected_range[1], expected_range[2], 
                              min(values), max(values)))
  }
  
  invisible(values)
}

#' Custom Assertion: Phase Data Structure
#' 
#' Validates phase-indexed data structure.
#' 
#' @param data data.table with phase-indexed data
#' @param points_per_cycle integer expected points per cycle (default: 150)
expect_phase_indexed_structure <- function(data, points_per_cycle = 150) {
  
  expect_s3_class(data, "data.table")
  
  # Check required columns
  expect_true("phase" %in% names(data))
  expect_true("subject" %in% names(data) || "task" %in% names(data))
  
  # Check phase range
  expect_true(all(data$phase >= 0 & data$phase <= 100))
  
  # Check cycle structure if subject and task columns exist
  if ("subject" %in% names(data) && "task" %in% names(data)) {
    cycle_counts <- data[, .N, by = .(subject, task)]
    
    # Should be multiples of points_per_cycle
    expect_true(all(cycle_counts$N %% points_per_cycle == 0),
                info = sprintf("Not all subject-task combinations have multiples of %d points", 
                              points_per_cycle))
  }
  
  invisible(data)
}

#' Custom Assertion: Statistical Results
#' 
#' Validates statistical analysis results.
#' 
#' @param stats_result result from statistical analysis method
#' @param expected_features character vector of expected feature names
expect_valid_statistics <- function(stats_result, expected_features = NULL) {
  
  if (is.data.frame(stats_result)) {
    expect_true("feature" %in% names(stats_result))
    
    # Check common statistical columns
    stat_columns <- c("mean", "std", "min", "max", "median")
    present_stat_columns <- intersect(stat_columns, names(stats_result))
    expect_true(length(present_stat_columns) > 0)
    
    # Check for valid values
    for (col in present_stat_columns) {
      expect_true(all(is.finite(stats_result[[col]])),
                  info = sprintf("Non-finite values in %s column", col))
    }
    
    # Check expected features if provided
    if (!is.null(expected_features)) {
      expect_true(all(expected_features %in% stats_result$feature))
    }
    
  } else if (is.list(stats_result)) {
    expect_true(length(stats_result) > 0)
    
    # Check each element is numeric
    for (name in names(stats_result)) {
      expect_true(is.numeric(stats_result[[name]]))
      expect_true(all(is.finite(stats_result[[name]])))
    }
    
    # Check expected features if provided
    if (!is.null(expected_features)) {
      expect_true(all(expected_features %in% names(stats_result)))
    }
  }
  
  invisible(stats_result)
}

#' Test Setup Helper
#' 
#' Sets up common test environment and creates test data.
#' 
#' @param test_name character name of the test (for debugging)
#' @param create_object logical whether to create LocomotionData object
#' @param n_subjects integer number of subjects for test data
#' @param n_tasks integer number of tasks for test data
#' @param n_cycles integer number of cycles for test data
#' @return list with test environment components
setup_test_environment <- function(test_name = "generic_test", create_object = TRUE,
                                  n_subjects = 2, n_tasks = 2, n_cycles = 3) {
  
  # Generate test data
  test_data <- generateSyntheticGaitData(
    n_subjects = n_subjects, 
    n_tasks = n_tasks, 
    n_cycles = n_cycles
  )
  
  # Create temporary file
  temp_file <- createTempTestFile(test_data, "parquet")
  
  # Create LocomotionData object if requested
  locomotion_obj <- NULL
  if (create_object) {
    locomotion_obj <- tryCatch({
      new("LocomotionData", data_path = temp_file)
    }, error = function(e) {
      warning(sprintf("Failed to create LocomotionData object in %s: %s", test_name, e$message))
      NULL
    })
  }
  
  return(list(
    test_data = test_data,
    temp_file = temp_file,
    locomotion_obj = locomotion_obj,
    cleanup = function() cleanupTestFiles(temp_file)
  ))
}

#' Performance Test Helper  
#' 
#' Measures execution time of a function call.
#' 
#' @param expr expression to evaluate
#' @param max_time numeric maximum allowed time in seconds
#' @param description character description of the operation
expect_fast_execution <- function(expr, max_time = 5.0, description = "operation") {
  
  start_time <- Sys.time()
  result <- force(expr)
  end_time <- Sys.time()
  
  elapsed_time <- as.numeric(difftime(end_time, start_time, units = "secs"))
  
  expect_true(elapsed_time <= max_time,
              info = sprintf("%s took %.2f seconds (max: %.2f)", 
                           description, elapsed_time, max_time))
  
  invisible(result)
}

#' Memory Usage Test Helper
#' 
#' Monitors memory usage during function execution.
#' 
#' @param expr expression to evaluate
#' @param max_memory_mb numeric maximum allowed memory increase in MB
#' @param description character description of the operation
expect_reasonable_memory_usage <- function(expr, max_memory_mb = 100, description = "operation") {
  
  if (!requireNamespace("pryr", quietly = TRUE)) {
    skip("pryr package not available for memory testing")
  }
  
  initial_memory <- pryr::mem_used()
  result <- force(expr)
  final_memory <- pryr::mem_used()
  
  memory_increase_mb <- as.numeric(final_memory - initial_memory) / 1024^2
  
  expect_true(memory_increase_mb <= max_memory_mb,
              info = sprintf("%s used %.2f MB (max: %.2f MB)", 
                           description, memory_increase_mb, max_memory_mb))
  
  invisible(result)
}

#' Tolerance-based Numeric Comparison
#' 
#' Compares numeric values with appropriate tolerance for biomechanical data.
#' 
#' @param actual numeric actual values
#' @param expected numeric expected values  
#' @param tolerance numeric relative tolerance (default: 1e-6)
#' @param absolute_tolerance numeric absolute tolerance (default: 1e-10)
expect_biomech_equal <- function(actual, expected, tolerance = 1e-6, absolute_tolerance = 1e-10) {
  
  expect_equal(actual, expected, tolerance = tolerance, 
               info = sprintf("Biomechanical data comparison failed"))
  
  invisible(actual)
}

#' Check S4 Method Existence
#' 
#' Validates that required S4 methods are defined for LocomotionData class.
#' 
#' @param method_name character name of the method to check
#' @param signature character class signature (default: "LocomotionData")
expect_s4_method_exists <- function(method_name, signature = "LocomotionData") {
  
  expect_true(existsMethod(method_name, signature),
              info = sprintf("S4 method '%s' not defined for class '%s'", 
                           method_name, signature))
  
  invisible(TRUE)
}