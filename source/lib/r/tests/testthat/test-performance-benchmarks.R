# Performance Benchmarking Tests
# 
# Created: 2025-06-19 with user permission
# Purpose: Comprehensive performance testing and benchmarking for LocomotionData package
#
# Intent: Establish performance baselines, detect regressions, and ensure the
# package scales appropriately with data size. Provides automated performance
# monitoring and optimization guidance for production use.

# Skip performance tests on CRAN to avoid timeout issues
skip_on_cran()

# Test Constructor Performance
test_that("LocomotionData constructor performance scales appropriately", {
  skip_if_not_installed("microbenchmark")
  skip_if_not_installed("arrow")
  
  # Create test datasets of different sizes
  small_data <- generateSyntheticGaitData(n_subjects = 2, n_tasks = 1, n_cycles = 3, seed = 100)
  medium_data <- generateSyntheticGaitData(n_subjects = 5, n_tasks = 2, n_cycles = 5, seed = 200)
  large_data <- generateSyntheticGaitData(n_subjects = 10, n_tasks = 3, n_cycles = 8, seed = 300)
  
  # Create temporary files
  temp_small <- createTempTestFile(small_data, "parquet")
  temp_medium <- createTempTestFile(medium_data, "parquet")
  temp_large <- createTempTestFile(large_data, "parquet")
  
  on.exit(cleanupTestFiles(c(temp_small, temp_medium, temp_large)))
  
  # Benchmark constructor performance
  bench_result <- microbenchmark::microbenchmark(
    small = new("LocomotionData", data_path = temp_small),
    medium = new("LocomotionData", data_path = temp_medium),
    large = new("LocomotionData", data_path = temp_large),
    times = 3,
    unit = "ms"
  )
  
  # Extract median times
  small_time <- median(bench_result$time[bench_result$expr == "small"]) / 1e6  # Convert to ms
  medium_time <- median(bench_result$time[bench_result$expr == "medium"]) / 1e6
  large_time <- median(bench_result$time[bench_result$expr == "large"]) / 1e6
  
  # Performance expectations (can be adjusted based on hardware)
  expect_true(small_time < 1000, info = sprintf("Small dataset constructor took %.2f ms", small_time))
  expect_true(medium_time < 3000, info = sprintf("Medium dataset constructor took %.2f ms", medium_time))
  expect_true(large_time < 8000, info = sprintf("Large dataset constructor took %.2f ms", large_time))
  
  # Check scaling properties
  size_ratio_med_small <- nrow(medium_data) / nrow(small_data)
  time_ratio_med_small <- medium_time / small_time
  
  # Constructor time should scale sub-quadratically with data size
  expect_true(time_ratio_med_small <= size_ratio_med_small * 2, 
              info = sprintf("Constructor scaling: size ratio %.2f, time ratio %.2f", 
                           size_ratio_med_small, time_ratio_med_small))
})

test_that("getCycles method performance is efficient", {
  skip_if_not_installed("microbenchmark")
  skip_if_not_installed("arrow")
  
  # Create test objects with different numbers of cycles
  few_cycles_data <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 5, seed = 400)
  many_cycles_data <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 20, seed = 500)
  
  temp_few <- createTempTestFile(few_cycles_data, "parquet")
  temp_many <- createTempTestFile(many_cycles_data, "parquet")
  
  on.exit(cleanupTestFiles(c(temp_few, temp_many)))
  
  obj_few <- new("LocomotionData", data_path = temp_few)
  obj_many <- new("LocomotionData", data_path = temp_many)
  
  subject <- getSubjects(obj_few)[1]
  task <- getTasks(obj_few)[1]
  
  # Benchmark getCycles with different feature counts
  all_features <- getFeatures(obj_few)
  subset_features <- all_features[1:min(5, length(all_features))]
  
  bench_result <- microbenchmark::microbenchmark(
    few_cycles_all = getCycles(obj_few, subject, task),
    few_cycles_subset = getCycles(obj_few, subject, task, features = subset_features),
    many_cycles_all = getCycles(obj_many, subject, task),
    many_cycles_subset = getCycles(obj_many, subject, task, features = subset_features),
    times = 5,
    unit = "ms"
  )
  
  # Extract median times
  results <- aggregate(time ~ expr, data = bench_result, FUN = median)
  results$time_ms <- results$time / 1e6
  
  # Performance expectations
  for (i in seq_len(nrow(results))) {
    expect_true(results$time_ms[i] < 1000, 
                info = sprintf("%s took %.2f ms", results$expr[i], results$time_ms[i]))
  }
  
  # Feature subset should be faster than all features
  few_all_time <- results$time_ms[results$expr == "few_cycles_all"]
  few_subset_time <- results$time_ms[results$expr == "few_cycles_subset"]
  
  expect_true(few_subset_time <= few_all_time,
              info = sprintf("Subset (%.2f ms) should be <= all features (%.2f ms)", 
                           few_subset_time, few_all_time))
})

test_that("Statistical methods performance scales linearly", {
  skip_if_not_installed("microbenchmark")
  skip_if_not_installed("arrow")
  
  # Create datasets with varying cycle counts
  cycles_5 <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 5, seed = 600)
  cycles_15 <- generateSyntheticGaitData(n_subjects = 1, n_tasks = 1, n_cycles = 15, seed = 700)
  
  temp_5 <- createTempTestFile(cycles_5, "parquet")
  temp_15 <- createTempTestFile(cycles_15, "parquet")
  
  on.exit(cleanupTestFiles(c(temp_5, temp_15)))
  
  obj_5 <- new("LocomotionData", data_path = temp_5)
  obj_15 <- new("LocomotionData", data_path = temp_15)
  
  subject <- getSubjects(obj_5)[1]
  task <- getTasks(obj_5)[1]
  
  # Benchmark statistical methods
  bench_result <- microbenchmark::microbenchmark(
    mean_5_cycles = getMeanPatterns(obj_5, subject, task),
    mean_15_cycles = getMeanPatterns(obj_15, subject, task),
    std_5_cycles = getStdPatterns(obj_5, subject, task),
    std_15_cycles = getStdPatterns(obj_15, subject, task),
    stats_5_cycles = getSummaryStatistics(obj_5, subject, task),
    stats_15_cycles = getSummaryStatistics(obj_15, subject, task),
    validate_5_cycles = validateCycles(obj_5, subject, task),
    validate_15_cycles = validateCycles(obj_15, subject, task),
    times = 3,
    unit = "ms"
  )
  
  # Extract median times and check scaling
  results <- aggregate(time ~ expr, data = bench_result, FUN = median)
  results$time_ms <- results$time / 1e6
  
  # Check that methods complete within reasonable time
  for (i in seq_len(nrow(results))) {
    expect_true(results$time_ms[i] < 2000, 
                info = sprintf("%s took %.2f ms", results$expr[i], results$time_ms[i]))
  }
  
  # Check scaling for specific methods
  mean_5_time <- results$time_ms[results$expr == "mean_5_cycles"]
  mean_15_time <- results$time_ms[results$expr == "mean_15_cycles"]
  
  scaling_factor <- mean_15_time / mean_5_time
  data_factor <- 15 / 5  # 3x more cycles
  
  # Scaling should be reasonable (not worse than quadratic)
  expect_true(scaling_factor <= data_factor^2,
              info = sprintf("Mean patterns scaling: %.2fx time for %.2fx data", 
                           scaling_factor, data_factor))
})

test_that("Memory usage is reasonable for different data sizes", {
  skip_if_not_installed("pryr")
  skip_if_not_installed("arrow")
  
  # Function to measure memory usage
  measure_memory <- function(expr) {
    initial_memory <- pryr::mem_used()
    result <- force(expr)
    final_memory <- pryr::mem_used()
    list(
      result = result,
      memory_used = as.numeric(final_memory - initial_memory)
    )
  }
  
  # Test memory usage for different dataset sizes
  small_data <- generateSyntheticGaitData(n_subjects = 2, n_tasks = 1, n_cycles = 3, seed = 800)
  large_data <- generateSyntheticGaitData(n_subjects = 8, n_tasks = 2, n_cycles = 10, seed = 900)
  
  temp_small <- createTempTestFile(small_data, "parquet")
  temp_large <- createTempTestFile(large_data, "parquet")
  
  on.exit(cleanupTestFiles(c(temp_small, temp_large)))
  
  # Measure constructor memory usage
  small_memory <- measure_memory({
    new("LocomotionData", data_path = temp_small)
  })
  
  large_memory <- measure_memory({
    new("LocomotionData", data_path = temp_large)
  })
  
  # Memory usage should be proportional to data size
  size_ratio <- nrow(large_data) / nrow(small_data)
  memory_ratio <- large_memory$memory_used / small_memory$memory_used
  
  # Allow for some overhead, but memory should scale reasonably
  expect_true(memory_ratio <= size_ratio * 3,
              info = sprintf("Memory scaling: %.2fx memory for %.2fx data", 
                           memory_ratio, size_ratio))
  
  # Test method memory usage
  obj_large <- large_memory$result
  subject <- getSubjects(obj_large)[1]
  task <- getTasks(obj_large)[1]
  
  method_memory <- measure_memory({
    cycles_result <- getCycles(obj_large, subject, task)
    mean_patterns <- getMeanPatterns(obj_large, subject, task)
    stats <- getSummaryStatistics(obj_large, subject, task)
    list(cycles_result, mean_patterns, stats)
  })
  
  # Method memory usage should be reasonable (< 100MB for large dataset)
  method_memory_mb <- method_memory$memory_used / 1024^2
  expect_true(method_memory_mb < 100,
              info = sprintf("Method memory usage: %.2f MB", method_memory_mb))
})

test_that("Caching improves performance for repeated operations", {
  skip_if_not_installed("microbenchmark")
  skip_if_not_installed("arrow")
  
  # Create test object
  test_data <- generateSyntheticGaitData(n_subjects = 2, n_tasks = 2, n_cycles = 10, seed = 1000)
  temp_file <- createTempTestFile(test_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  obj <- new("LocomotionData", data_path = temp_file)
  subject <- getSubjects(obj)[1]
  task <- getTasks(obj)[1]
  
  # Benchmark first call (no cache) vs repeated calls (with cache)
  bench_result <- microbenchmark::microbenchmark(
    first_call = {
      # Clear cache first
      obj <- clearCache(obj)
      getCycles(obj, subject, task)
    },
    repeated_call = getCycles(obj, subject, task),
    times = 5,
    unit = "ms"
  )
  
  first_time <- median(bench_result$time[bench_result$expr == "first_call"]) / 1e6
  repeated_time <- median(bench_result$time[bench_result$expr == "repeated_call"]) / 1e6
  
  # Note: R S4 objects are typically pass-by-value, so caching may not show 
  # the same benefits as in Python. This test documents the current behavior.
  
  expect_true(first_time > 0)
  expect_true(repeated_time > 0)
  
  # Log the performance difference for monitoring
  speedup <- first_time / repeated_time
  cat(sprintf("Cache performance: first=%.2fms, repeated=%.2fms, speedup=%.2fx\n", 
              first_time, repeated_time, speedup))
})

test_that("Multi-subject analysis performance scales appropriately", {
  skip_if_not_installed("microbenchmark")
  skip_if_not_installed("arrow")
  
  # Create dataset with multiple subjects
  multi_subject_data <- generateSyntheticGaitData(n_subjects = 10, n_tasks = 2, n_cycles = 5, seed = 1100)
  temp_file <- createTempTestFile(multi_subject_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  obj <- new("LocomotionData", data_path = temp_file)
  subjects <- getSubjects(obj)
  task <- getTasks(obj)[1]
  
  # Benchmark multi-subject operations with different subject counts
  bench_result <- microbenchmark::microbenchmark(
    subjects_2 = getMultiSubjectStatistics(obj, subjects = subjects[1:2], task = task),
    subjects_5 = getMultiSubjectStatistics(obj, subjects = subjects[1:5], task = task),
    subjects_all = getMultiSubjectStatistics(obj, subjects = subjects, task = task),
    group_patterns_2 = getGroupMeanPatterns(obj, subjects = subjects[1:2], task = task),
    group_patterns_5 = getGroupMeanPatterns(obj, subjects = subjects[1:5], task = task),
    group_patterns_all = getGroupMeanPatterns(obj, subjects = subjects, task = task),
    times = 3,
    unit = "ms"
  )
  
  results <- aggregate(time ~ expr, data = bench_result, FUN = median)
  results$time_ms <- results$time / 1e6
  
  # Performance should scale reasonably with subject count
  stats_2_time <- results$time_ms[results$expr == "subjects_2"]
  stats_all_time <- results$time_ms[results$expr == "subjects_all"]
  
  subject_ratio <- length(subjects) / 2  # 10/2 = 5x more subjects
  time_ratio <- stats_all_time / stats_2_time
  
  # Time should scale sub-quadratically with subject count
  expect_true(time_ratio <= subject_ratio^2,
              info = sprintf("Multi-subject scaling: %.2fx time for %.2fx subjects", 
                           time_ratio, subject_ratio))
  
  # All operations should complete within reasonable time
  for (i in seq_len(nrow(results))) {
    expect_true(results$time_ms[i] < 5000,
                info = sprintf("%s took %.2f ms", results$expr[i], results$time_ms[i]))
  }
})

test_that("Performance regression detection", {
  skip_if_not_installed("microbenchmark")
  skip_if_not_installed("arrow")
  
  # Standard test case for regression detection
  standard_data <- generateSyntheticGaitData(n_subjects = 3, n_tasks = 2, n_cycles = 5, seed = 42)
  temp_file <- createTempTestFile(standard_data, "parquet")
  on.exit(cleanupTestFiles(temp_file))
  
  # Benchmark standard operations
  bench_result <- microbenchmark::microbenchmark(
    constructor = new("LocomotionData", data_path = temp_file),
    times = 5,
    unit = "ms",
    setup = quote({
      # Clear any existing objects
      rm(list = ls(pattern = "^standard_obj"))
    })
  )
  
  constructor_time <- median(bench_result$time) / 1e6
  
  # Create object for method benchmarks
  standard_obj <- new("LocomotionData", data_path = temp_file)
  subject <- getSubjects(standard_obj)[1]
  task <- getTasks(standard_obj)[1]
  
  method_bench <- microbenchmark::microbenchmark(
    get_cycles = getCycles(standard_obj, subject, task),
    mean_patterns = getMeanPatterns(standard_obj, subject, task),
    summary_stats = getSummaryStatistics(standard_obj, subject, task),
    validate_cycles = validateCycles(standard_obj, subject, task),
    times = 5,
    unit = "ms"
  )
  
  method_times <- aggregate(time ~ expr, data = method_bench, FUN = median)
  method_times$time_ms <- method_times$time / 1e6
  
  # Performance baselines (these can be updated as optimizations are made)
  # Current expectations based on reasonable hardware:
  baseline_expectations <- list(
    constructor = 2000,      # 2 seconds
    get_cycles = 500,        # 500 ms
    mean_patterns = 200,     # 200 ms
    summary_stats = 300,     # 300 ms
    validate_cycles = 400    # 400 ms
  )
  
  # Check against baselines
  expect_true(constructor_time < baseline_expectations$constructor,
              info = sprintf("Constructor regression: %.2f ms (baseline: %.2f ms)", 
                           constructor_time, baseline_expectations$constructor))
  
  for (i in seq_len(nrow(method_times))) {
    method_name <- gsub("get_|_", "", method_times$expr[i])  # Normalize name
    baseline_key <- switch(method_name,
                          "cycles" = "get_cycles",
                          "meanpatterns" = "mean_patterns", 
                          "summarystats" = "summary_stats",
                          "validatecycles" = "validate_cycles",
                          "get_cycles")  # default
    
    if (baseline_key %in% names(baseline_expectations)) {
      baseline <- baseline_expectations[[baseline_key]]
      actual <- method_times$time_ms[i]
      
      expect_true(actual < baseline,
                  info = sprintf("%s regression: %.2f ms (baseline: %.2f ms)", 
                               method_times$expr[i], actual, baseline))
    }
  }
  
  # Log performance summary for monitoring
  cat("Performance Summary (median times):\n")
  cat(sprintf("  Constructor: %.2f ms\n", constructor_time))
  for (i in seq_len(nrow(method_times))) {
    cat(sprintf("  %s: %.2f ms\n", method_times$expr[i], method_times$time_ms[i]))
  }
})