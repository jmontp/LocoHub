# Test Fixtures Setup
# 
# Created: 2025-06-19 with user permission
# Purpose: Setup persistent test fixtures and data for testthat framework
#
# Intent: Create reusable test datasets and fixtures that persist across
# test sessions to improve test performance and consistency.

library(data.table)

# Global test fixtures - created once per test session
.test_fixtures <- new.env()

#' Initialize Test Fixtures
#' 
#' Creates standard test datasets that can be reused across multiple tests.
#' Called automatically when tests are loaded.
init_test_fixtures <- function() {
  
  # Standard test datasets
  .test_fixtures$small_dataset <- generateSyntheticGaitData(
    n_subjects = 2, n_tasks = 2, n_cycles = 3, seed = 42
  )
  
  .test_fixtures$medium_dataset <- generateSyntheticGaitData(
    n_subjects = 5, n_tasks = 3, n_cycles = 5, seed = 123
  )
  
  .test_fixtures$large_dataset <- generateSyntheticGaitData(
    n_subjects = 10, n_tasks = 4, n_cycles = 10, seed = 456
  )
  
  # Edge case datasets
  .test_fixtures$missing_values_dataset <- generateEdgeCaseData("missing_values", seed = 789)
  .test_fixtures$extreme_values_dataset <- generateEdgeCaseData("extreme_values", seed = 101)
  .test_fixtures$single_cycle_dataset <- generateEdgeCaseData("single_cycle", seed = 202)
  .test_fixtures$empty_dataset <- generateEdgeCaseData("empty_data")
  
  # Performance test datasets
  .test_fixtures$performance_small <- generatePerformanceTestData("small", seed = 303)
  .test_fixtures$performance_medium <- generatePerformanceTestData("medium", seed = 404)
  
  # Test file paths (created on demand)
  .test_fixtures$temp_files <- list()
  
  # Standard feature lists
  .test_fixtures$angle_features <- c(
    "hip_flexion_angle_ipsi_rad", "hip_flexion_angle_contra_rad",
    "knee_flexion_angle_ipsi_rad", "knee_flexion_angle_contra_rad",
    "ankle_flexion_angle_ipsi_rad", "ankle_flexion_angle_contra_rad"
  )
  
  .test_fixtures$moment_features <- c(
    "hip_flexion_moment_ipsi_Nm", "hip_flexion_moment_contra_Nm",
    "knee_flexion_moment_ipsi_Nm", "knee_flexion_moment_contra_Nm",
    "ankle_flexion_moment_ipsi_Nm", "ankle_flexion_moment_contra_Nm"
  )
  
  .test_fixtures$velocity_features <- c(
    "hip_flexion_velocity_ipsi_rad_s", "hip_flexion_velocity_contra_rad_s",
    "knee_flexion_velocity_ipsi_rad_s", "knee_flexion_velocity_contra_rad_s",
    "ankle_flexion_velocity_ipsi_rad_s", "ankle_flexion_velocity_contra_rad_s"
  )
  
  message("Test fixtures initialized successfully")
}

#' Get Test Fixture
#' 
#' Retrieves a test fixture by name.
#' 
#' @param name character name of the fixture
#' @return test fixture data or NULL if not found
get_test_fixture <- function(name) {
  if (exists(name, envir = .test_fixtures)) {
    return(get(name, envir = .test_fixtures))
  } else {
    warning(sprintf("Test fixture '%s' not found", name))
    return(NULL)
  }
}

#' Get Temporary Test File
#' 
#' Creates or retrieves a temporary file with test data.
#' 
#' @param fixture_name character name of the data fixture
#' @param file_format character file format ("parquet" or "csv")
#' @param force_recreate logical whether to recreate file if it exists
#' @return character path to temporary file
get_temp_test_file <- function(fixture_name, file_format = "parquet", force_recreate = FALSE) {
  
  # Get the data fixture
  data <- get_test_fixture(fixture_name)
  if (is.null(data)) {
    stop(sprintf("Cannot create file: fixture '%s' not found", fixture_name))
  }
  
  # Check if file already exists
  file_key <- paste(fixture_name, file_format, sep = "_")
  
  if (!force_recreate && !is.null(.test_fixtures$temp_files[[file_key]])) {
    existing_file <- .test_fixtures$temp_files[[file_key]]
    if (file.exists(existing_file)) {
      return(existing_file)
    }
  }
  
  # Create new temporary file
  temp_file <- createTempTestFile(data, file_format)
  .test_fixtures$temp_files[[file_key]] <- temp_file
  
  return(temp_file)
}

#' Create Test LocomotionData Object
#' 
#' Creates a LocomotionData object from a test fixture.
#' 
#' @param fixture_name character name of the data fixture
#' @param file_format character file format for temporary file
#' @return LocomotionData object or NULL if creation fails
create_test_locomotion_object <- function(fixture_name, file_format = "parquet") {
  
  temp_file <- get_temp_test_file(fixture_name, file_format)
  
  tryCatch({
    new("LocomotionData", data_path = temp_file)
  }, error = function(e) {
    warning(sprintf("Failed to create LocomotionData object from fixture '%s': %s", 
                   fixture_name, e$message))
    return(NULL)
  })
}

#' Cleanup Test Fixtures
#' 
#' Cleans up temporary files created during testing.
cleanup_test_fixtures <- function() {
  
  # Clean up temporary files
  temp_files <- .test_fixtures$temp_files
  
  for (file_path in temp_files) {
    if (!is.null(file_path) && file.exists(file_path)) {
      unlink(file_path)
    }
  }
  
  # Clear temp file registry
  .test_fixtures$temp_files <- list()
  
  message("Test fixtures cleaned up")
}

#' List Available Test Fixtures
#' 
#' Returns a list of available test fixtures.
#' 
#' @return character vector of fixture names
list_test_fixtures <- function() {
  fixture_names <- ls(.test_fixtures)
  fixture_names <- fixture_names[fixture_names != "temp_files"]
  return(fixture_names)
}

#' Get Test Fixture Summary
#' 
#' Provides summary information about test fixtures.
#' 
#' @param fixture_name character name of specific fixture (optional)
#' @return data.frame or list with fixture information
get_test_fixture_summary <- function(fixture_name = NULL) {
  
  if (!is.null(fixture_name)) {
    # Summary for specific fixture
    data <- get_test_fixture(fixture_name)
    if (is.null(data)) return(NULL)
    
    if (is.data.table(data) && nrow(data) > 0) {
      return(list(
        name = fixture_name,
        class = class(data),
        dimensions = dim(data),
        subjects = if("subject" %in% names(data)) length(unique(data$subject)) else NA,
        tasks = if("task" %in% names(data)) length(unique(data$task)) else NA,
        features = sum(!names(data) %in% c("subject", "task", "phase")),
        has_missing = if(is.data.table(data)) any(is.na(data)) else NA
      ))
    } else {
      return(list(
        name = fixture_name,
        class = class(data),
        length = length(data),
        type = typeof(data)
      ))
    }
  } else {
    # Summary for all fixtures
    fixture_names <- list_test_fixtures()
    summaries <- lapply(fixture_names, get_test_fixture_summary)
    names(summaries) <- fixture_names
    return(summaries)
  }
}

# Initialize fixtures when this file is loaded
if (exists("generateSyntheticGaitData")) {
  init_test_fixtures()
} else {
  message("Test data generation functions not available yet - fixtures will be initialized later")
}

# Register cleanup function to run after tests
reg.finalizer(.test_fixtures, cleanup_test_fixtures, onexit = TRUE)