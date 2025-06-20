test_that("Bayesian t-test works with biomechanical data", {
  skip_if_not_installed("BayesFactor")
  
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  
  # Test one-sample Bayesian t-test
  expect_no_error({
    result <- bayes_ttest_biomech(
      test_data, 
      feature = "knee_flexion_angle_contra_rad",
      condition1 = "normal_walk",
      summary_type = "mean"
    )
  })
  
  # Check result structure
  expect_type(result, "list")
  expect_true("bayes_factor" %in% names(result))
  expect_true("interpretation" %in% names(result))
  expect_true("posterior_samples" %in% names(result))
  expect_true(is.numeric(result$bayes_factor))
  expect_true(result$bayes_factor > 0)
})

test_that("Bayesian ANOVA works with multiple conditions", {
  skip_if_not_installed("BayesFactor")
  
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  
  # Test Bayesian ANOVA
  expect_no_error({
    result <- bayes_anova_biomech(
      test_data,
      feature = "knee_flexion_angle_contra_rad",
      conditions = c("normal_walk", "fast_walk"),
      summary_type = "mean"
    )
  })
  
  # Check result structure
  expect_type(result, "list")
  expect_true("bayes_factor" %in% names(result))
  expect_true("descriptives" %in% names(result))
  expect_true(is.numeric(result$bayes_factor))
})

test_that("Bayesian correlation analysis works", {
  skip_if_not_installed("BayesFactor")
  
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  
  # Test Bayesian correlation
  expect_no_error({
    result <- bayes_correlation_biomech(
      test_data,
      feature1 = "knee_flexion_angle_contra_rad",
      feature2 = "hip_flexion_angle_contra_rad",
      condition = "normal_walk",
      summary_type = "mean"
    )
  })
  
  # Check result structure
  expect_type(result, "list")
  expect_true("bayes_factor" %in% names(result))
  expect_true("classical_correlation" %in% names(result))
  expect_true(is.numeric(result$bayes_factor))
  expect_true(is.numeric(result$classical_correlation))
})

test_that("Bayes factor interpretation works correctly", {
  # Test various Bayes factor values
  expect_equal(interpret_bayes_factor(150), "Extreme evidence for alternative")
  expect_equal(interpret_bayes_factor(50), "Very strong evidence for alternative")
  expect_equal(interpret_bayes_factor(15), "Strong evidence for alternative")
  expect_equal(interpret_bayes_factor(5), "Moderate evidence for alternative")
  expect_equal(interpret_bayes_factor(1.5), "Weak evidence for alternative")
  expect_equal(interpret_bayes_factor(0.5), "Weak evidence for null")
  expect_equal(interpret_bayes_factor(0.1), "Moderate evidence for null")
  expect_equal(interpret_bayes_factor(0.01), "Strong evidence for null")
})

test_that("Bayesian model comparison works", {
  skip_if_not_installed("BayesFactor")
  
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  
  # Create mock model results
  model1 <- list(bayes_factor = 10.5, log_bayes_factor = log(10.5))
  model2 <- list(bayes_factor = 2.3, log_bayes_factor = log(2.3))
  model_list <- list(model1, model2)
  
  # Test model comparison
  expect_no_error({
    result <- compare_bayes_models(model_list, c("Model1", "Model2"))
  })
  
  # Check result structure
  expect_type(result, "list")
  expect_true("comparison_table" %in% names(result))
  expect_true("best_model" %in% names(result))
  expect_equal(result$best_model, "Model1")  # Higher BF should be best
})