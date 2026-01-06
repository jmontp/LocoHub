test_that("loadParquetData handles basic parquet files", {
  skip_if_not_installed("arrow")
  
  # Create a temporary parquet file for testing
  temp_file <- tempfile(fileext = ".parquet")
  
  # Create test data
  test_data <- data.frame(
    subject = rep(c("SUB01", "SUB02"), each = 300),
    task = rep("normal_walk", 600),
    phase = rep(seq(0, 100, length.out = 150), 4),
    knee_flexion_angle_ipsi_rad = sin(seq(0, 4*pi, length.out = 600)),
    hip_flexion_moment_contra_Nm = cos(seq(0, 4*pi, length.out = 600))
  )
  
  # Write test parquet file
  arrow::write_parquet(test_data, temp_file)
  
  # Test loading
  loaded_data <- loadParquetData(temp_file, show_progress = FALSE)
  
  expect_s3_class(loaded_data, "data.table")
  expect_equal(nrow(loaded_data), 600)
  expect_equal(ncol(loaded_data), 5)
  expect_true(all(c("subject", "task", "phase") %in% names(loaded_data)))
  
  # Clean up
  unlink(temp_file)
})

test_that("loadParquetData handles missing files gracefully", {
  expect_error(
    loadParquetData("nonexistent_file.parquet"),
    "Parquet file not found"
  )
})

test_that("validateParquetStructure detects required columns", {
  skip_if_not_installed("arrow")
  
  # Create test data without required columns
  temp_file <- tempfile(fileext = ".parquet")
  test_data <- data.frame(
    id = 1:100,
    value = rnorm(100)
  )
  
  arrow::write_parquet(test_data, temp_file)
  
  # Test validation
  result <- validateParquetStructure(temp_file)
  
  expect_false(result$valid)
  expect_true(length(result$issues) > 0)
  expect_true(any(grepl("Missing required columns", result$issues)))
  
  # Clean up
  unlink(temp_file)
})

test_that("validateParquetStructure handles valid phase-indexed data", {
  skip_if_not_installed("arrow")
  
  # Create proper phase-indexed test data
  temp_file <- tempfile(fileext = ".parquet")
  
  test_data <- data.frame(
    subject = rep("SUB01", 150),
    task = rep("normal_walk", 150),
    phase = seq(0, 100, length.out = 150),
    knee_flexion_angle_ipsi_rad = sin(seq(0, 2*pi, length.out = 150))
  )
  
  arrow::write_parquet(test_data, temp_file)
  
  # Test validation
  result <- validateParquetStructure(temp_file)
  
  expect_true(result$valid)
  expect_equal(result$column_info$total_columns, 4)
  expect_true(result$data_format_info$phase_validation$is_phase_indexed)
  
  # Clean up
  unlink(temp_file)
})

test_that("detectDataFormat identifies phase-indexed data", {
  skip_if_not_installed("arrow")
  
  # Create phase-indexed test data
  temp_file <- tempfile(fileext = ".parquet")
  
  # Multiple subjects and cycles
  test_data <- do.call(rbind, lapply(1:3, function(subj) {
    do.call(rbind, lapply(1:2, function(cycle) {
      data.frame(
        subject = paste0("SUB", sprintf("%02d", subj)),
        task = "normal_walk",
        phase = seq(0, 100, length.out = 150),
        knee_flexion_angle_ipsi_rad = sin(seq(0, 2*pi, length.out = 150))
      )
    }))
  }))
  
  arrow::write_parquet(test_data, temp_file)
  
  # Test format detection
  result <- detectDataFormat(temp_file)
  
  expect_equal(result$format, "phase_indexed")
  expect_true(result$confidence > 0.8)
  expect_true(result$details$phase_info$is_phase_indexed)
  
  # Clean up
  unlink(temp_file)
})

test_that("detectDataFormat identifies time-indexed data", {
  # Create time-indexed test data
  temp_file <- tempfile(fileext = ".csv")
  
  test_data <- data.frame(
    subject = rep("SUB01", 1000),
    task = rep("normal_walk", 1000),
    time = seq(0, 10, length.out = 1000),
    phase = rep(c(10, 25, 50, 75), 250),  # Few unique phases
    knee_flexion_angle_ipsi_rad = sin(seq(0, 4*pi, length.out = 1000))
  )
  
  write.csv(test_data, temp_file, row.names = FALSE)
  
  # Test format detection
  result <- detectDataFormat(temp_file)
  
  expect_equal(result$format, "time_indexed")
  expect_true(result$details$column_info$has_time_columns)
  expect_false(result$details$phase_info$is_phase_indexed)
  
  # Clean up
  unlink(temp_file)
})

test_that("convertTimeToPhase converts simple time data", {
  # Create simple time-indexed data
  temp_input <- tempfile(fileext = ".csv")
  temp_output <- tempfile(fileext = ".parquet")
  
  # Simple test data with regular sampling
  n_points <- 300
  time_vec <- seq(0, 6, length.out = n_points)  # 6 seconds of data
  
  test_data <- data.frame(
    subject = rep("SUB01", n_points),
    task = rep("normal_walk", n_points),
    time = time_vec,
    # Simulate vertical GRF with heel strikes at 0, 1.2, 2.4, 3.6, 4.8 seconds
    vgrf_vertical = ifelse(
      (time_vec %% 1.2) < 0.6, 
      800 + 200 * sin(2 * pi * (time_vec %% 1.2) / 0.6),  # stance phase
      50  # swing phase
    ),
    knee_flexion_angle_ipsi_rad = 0.5 * sin(2 * pi * time_vec / 1.2)
  )
  
  write.csv(test_data, temp_input, row.names = FALSE)
  
  # Test conversion
  phase_data <- convertTimeToPhase(
    temp_input, 
    temp_output,
    time_col = "time",
    points_per_cycle = 150L,
    show_progress = FALSE
  )
  
  expect_s3_class(phase_data, "data.table")
  expect_true("phase" %in% names(phase_data))
  
  # Check if we have approximately 150 points per cycle
  phase_counts <- phase_data[, .N, by = .(subject, task)]
  expect_true(all(phase_counts$N >= 100))  # Allow some tolerance
  
  # Check phase range
  expect_true(min(phase_data$phase) >= 0)
  expect_true(max(phase_data$phase) <= 100)
  
  # Clean up
  unlink(temp_input)
  unlink(temp_output)
})

test_that("getMemoryUsage returns valid information", {
  result <- getMemoryUsage()
  
  expect_type(result, "list")
  expect_true(is.numeric(result$total_memory_gb))
  expect_true(result$total_memory_gb >= 0)
  expect_true("r_version" %in% names(result))
  expect_true("memory_method" %in% names(result))
})

test_that("loadParquetData handles chunk loading parameters", {
  skip_if_not_installed("arrow")
  
  # Create a larger test file
  temp_file <- tempfile(fileext = ".parquet")
  
  # Create test data with multiple subjects and cycles
  test_data <- do.call(rbind, lapply(1:5, function(subj) {
    do.call(rbind, lapply(1:10, function(cycle) {
      data.frame(
        subject = paste0("SUB", sprintf("%02d", subj)),
        task = "normal_walk",
        phase = seq(0, 100, length.out = 150),
        knee_flexion_angle_ipsi_rad = sin(seq(0, 2*pi, length.out = 150)),
        hip_flexion_moment_contra_Nm = cos(seq(0, 2*pi, length.out = 150))
      )
    }))
  }))  # Total: 5 subjects * 10 cycles * 150 points = 7500 rows
  
  arrow::write_parquet(test_data, temp_file)
  
  # Test with small chunk size to trigger chunked loading
  loaded_data <- loadParquetData(
    temp_file, 
    chunk_size = 1000L,
    memory_limit = 0.001,  # Very small limit to force chunking
    show_progress = FALSE
  )
  
  expect_s3_class(loaded_data, "data.table")
  expect_equal(nrow(loaded_data), 7500)
  expect_equal(ncol(loaded_data), 5)
  
  # Check data integrity
  expect_equal(length(unique(loaded_data$subject)), 5)
  expect_true(all(!is.na(loaded_data$knee_flexion_angle_ipsi_rad)))
  
  # Clean up
  unlink(temp_file)
})

test_that("validateParquetStructure provides detailed validation info", {
  skip_if_not_installed("arrow")
  
  # Create test data with some issues
  temp_file <- tempfile(fileext = ".parquet")
  
  test_data <- data.frame(
    subject = c(rep("SUB01", 100), rep(NA, 50)),  # Some missing subjects
    task = rep("normal_walk", 150),
    phase = seq(0, 100, length.out = 150),
    knee_flexion_angle_ipsi_rad = c(rnorm(100), rep(NA, 50)),  # Some missing values
    non_numeric_phase = rep("text", 150)  # Wrong data type
  )
  
  arrow::write_parquet(test_data, temp_file)
  
  # Test detailed validation
  result <- validateParquetStructure(temp_file)
  
  expect_type(result, "list")
  expect_true("file_info" %in% names(result))
  expect_true("column_info" %in% names(result))
  expect_true("data_format_info" %in% names(result))
  
  expect_true(result$file_info$size_mb > 0)
  expect_equal(result$column_info$total_columns, 5)
  expect_true(length(result$warnings) > 0)  # Should have warnings about missing values
  
  # Clean up
  unlink(temp_file)
})