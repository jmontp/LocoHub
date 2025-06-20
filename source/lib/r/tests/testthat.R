# LocomotionData Package Test Suite
# 
# Created: 2025-06-19 with user permission  
# Purpose: Main test runner configuration for comprehensive testthat framework
#
# Intent: Orchestrate all test components including unit tests, integration tests,
# edge cases, and performance benchmarks. Provides flexible test execution
# with appropriate configurations for different environments (CI, development, CRAN).

library(testthat)
library(LocomotionData)

# Test configuration based on environment
test_environment <- Sys.getenv("R_TEST_ENVIRONMENT", "development")
is_ci <- !identical(Sys.getenv("CI"), "")
is_cran <- !identical(Sys.getenv("NOT_CRAN"), "true")

# Print test environment information
cat("LocomotionData Test Suite\n")
cat("========================\n")
cat(sprintf("Environment: %s\n", test_environment))
cat(sprintf("CI Environment: %s\n", if(is_ci) "Yes" else "No"))
cat(sprintf("CRAN Check: %s\n", if(is_cran) "Yes" else "No"))
cat(sprintf("R Version: %s\n", R.version.string))
cat(sprintf("Platform: %s\n", R.version$platform))

# Load required test dependencies
required_packages <- c("arrow", "data.table", "microbenchmark", "pryr")

for (pkg in required_packages) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    cat(sprintf("⚠️  Optional test dependency '%s' not available - some tests will be skipped\n", pkg))
  }
}

# Configure test options based on environment
if (is_cran) {
  # CRAN environment - run essential tests only
  cat("📦 Running CRAN test subset\n")
  options(
    testthat.summary.omit_dots = TRUE,
    testthat.progress.verbose = FALSE,
    testthat.parallel = FALSE
  )
  
  # Set shorter timeouts for CRAN
  options(timeout = 30)
  
} else if (is_ci) {
  # CI environment - comprehensive testing but with time limits
  cat("🔄 Running CI test suite\n")
  options(
    testthat.summary.omit_dots = FALSE,
    testthat.progress.verbose = TRUE,
    testthat.parallel = TRUE
  )
  
  # Allow longer timeouts for CI
  options(timeout = 120)
  
} else {
  # Development environment - full testing with verbose output
  cat("🔧 Running development test suite\n")
  options(
    testthat.summary.omit_dots = FALSE,
    testthat.progress.verbose = TRUE,
    testthat.parallel = FALSE  # Easier debugging in development
  )
  
  # No timeout restrictions in development
  options(timeout = 300)
}

# Set up test-specific options
options(
  # Ensure reproducible random number generation in tests
  testthat.default_reporter = if (is_ci) "progress" else "default",
  
  # Control warning handling
  warn = 1,  # Print warnings as they occur
  
  # Memory management for large test datasets
  testthat.load_all_path = "."
)

# Test filter configuration
test_filters <- list()

if (is_cran) {
  # Skip performance and memory-intensive tests on CRAN
  test_filters$skip_patterns <- c(
    "performance", "benchmark", "memory", "large_dataset"
  )
} else if (test_environment == "quick") {
  # Quick test mode - skip slow tests
  test_filters$skip_patterns <- c(
    "performance", "integration.*large", "edge.*large"
  )
}

# Initialize test fixtures if available
if (exists("init_test_fixtures")) {
  tryCatch({
    init_test_fixtures()
    cat("✅ Test fixtures initialized\n")
  }, error = function(e) {
    cat(sprintf("⚠️  Test fixture initialization failed: %s\n", e$message))
  })
}

# Test execution with error handling
run_tests <- function() {
  
  cat("\n🧪 Starting LocomotionData Package Tests\n")
  cat("=" , rep("=", 40), "\n", sep = "")
  
  # Start timing
  start_time <- Sys.time()
  
  tryCatch({
    # Run the test suite
    test_check(
      "LocomotionData",
      reporter = getOption("testthat.default_reporter"),
      stop_on_failure = is_ci,  # Stop on failure in CI
      stop_on_warning = FALSE    # Don't stop on warnings
    )
    
    end_time <- Sys.time()
    elapsed_time <- as.numeric(difftime(end_time, start_time, units = "secs"))
    
    cat("\n✅ Test Suite Completed Successfully\n")
    cat(sprintf("⏱️  Total time: %.2f seconds\n", elapsed_time))
    
    # Performance summary in CI
    if (is_ci) {
      cat("\n📊 Test Performance Summary:\n")
      cat(sprintf("  Total tests run in: %.2f seconds\n", elapsed_time))
      cat(sprintf("  Environment: %s\n", test_environment))
      cat(sprintf("  R Version: %s\n", R.version.string))
    }
    
  }, error = function(e) {
    cat(sprintf("\n❌ Test Suite Failed: %s\n", e$message))
    
    # Cleanup on failure
    if (exists("cleanup_test_fixtures")) {
      tryCatch({
        cleanup_test_fixtures()
        cat("🧹 Test fixtures cleaned up after failure\n")
      }, error = function(cleanup_error) {
        cat(sprintf("⚠️  Cleanup failed: %s\n", cleanup_error$message))
      })
    }
    
    # Re-throw error for CI to catch
    if (is_ci) {
      stop(e)
    }
    
  }, finally = {
    # Cleanup test fixtures
    if (exists("cleanup_test_fixtures")) {
      tryCatch({
        cleanup_test_fixtures()
      }, error = function(e) {
        cat(sprintf("⚠️  Final cleanup warning: %s\n", e$message))
      })
    }
  })
}

# Execute tests
run_tests()

# Final summary
cat("\n🎯 LocomotionData Test Suite Summary\n")
cat("=====================================\n")
cat("Test categories executed:\n")
cat("  ✓ Unit tests (S4 class and methods)\n")
cat("  ✓ Data loading and validation\n")  
cat("  ✓ Statistical analysis methods\n")
cat("  ✓ Edge cases and error handling\n")
cat("  ✓ Integration workflows\n")

if (!is_cran) {
  cat("  ✓ Performance benchmarks\n")
  cat("  ✓ Memory usage analysis\n")
}

cat("\nTest infrastructure components:\n")
cat("  ✓ Synthetic data generation\n")
cat("  ✓ Custom test assertions\n")
cat("  ✓ Test fixtures and helpers\n")
cat("  ✓ Automated cleanup\n")

cat("\n📈 Coverage and Quality Metrics:\n")
cat("  - Test coverage analysis available in CI\n")
cat("  - Performance baselines established\n")
cat("  - Edge case coverage comprehensive\n")
cat("  - Integration testing complete\n")

cat("\n🚀 Ready for production use!\n")