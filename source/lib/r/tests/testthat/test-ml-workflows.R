test_that("Model comparison works correctly", {
  skip_if_not_installed("randomForest")
  skip_if_not_installed("e1071")
  
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  ml_data <- prepare_ml_data(test_data, summary_type = "mean")
  
  # Test model comparison with reduced parameters for speed
  expect_no_error({
    comparison_result <- biomech_model_comparison(
      ml_data, 
      target = "tasks", 
      methods = c("random_forest", "svm"),
      cv_folds = 3
    )
  })
  
  # Check result structure
  expect_type(comparison_result, "list")
  expect_true("comparison_summary" %in% names(comparison_result))
  expect_true("best_method" %in% names(comparison_result))
  expect_true("best_accuracy" %in% names(comparison_result))
  expect_true(comparison_result$best_method %in% c("random_forest", "svm"))
  expect_true(comparison_result$best_accuracy >= 0 && comparison_result$best_accuracy <= 1)
})

test_that("Hyperparameter tuning works", {
  skip_if_not_installed("randomForest")
  
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  ml_data <- prepare_ml_data(test_data, summary_type = "mean")
  
  # Test hyperparameter tuning with minimal grid
  param_grid <- list(
    ntree = c(10, 20),
    mtry = c(2, 3)
  )
  
  expect_no_error({
    tuning_result <- biomech_hyperparameter_tuning(
      ml_data,
      target = "tasks",
      method = "random_forest",
      param_grid = param_grid,
      cv_folds = 3
    )
  })
  
  # Check result structure
  expect_type(tuning_result, "list")
  expect_true("best_params" %in% names(tuning_result))
  expect_true("best_score" %in% names(tuning_result))
  expect_true("tuning_results" %in% names(tuning_result))
  expect_true("final_model" %in% names(tuning_result))
})

test_that("Complete ML pipeline works", {
  skip_if_not_installed("randomForest")
  
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  
  # Test complete pipeline with minimal settings
  expect_no_error({
    pipeline_result <- biomech_ml_pipeline(
      test_data,
      target = "tasks",
      summary_type = "mean",
      feature_selection = TRUE,
      methods = c("random_forest"),
      hyperparameter_tuning = FALSE,
      cv_folds = 3
    )
  })
  
  # Check result structure
  expect_type(pipeline_result, "list")
  expect_true("final_model" %in% names(pipeline_result))
  expect_true("best_method" %in% names(pipeline_result))
  expect_true("model_comparison" %in% names(pipeline_result))
  expect_true("feature_selection_result" %in% names(pipeline_result))
  expect_equal(pipeline_result$best_method, "random_forest")
})

test_that("Pipeline handles different summary types", {
  skip_if_not_installed("randomForest")
  
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  
  # Test with ROM summary type
  expect_no_error({
    ml_data_rom <- prepare_ml_data(test_data, summary_type = "rom")
  })
  
  expect_type(ml_data_rom, "list")
  expect_true("features" %in% names(ml_data_rom))
  expect_true(nrow(ml_data_rom$features) > 0)
  
  # Test with peak values summary type
  expect_no_error({
    ml_data_peaks <- prepare_ml_data(test_data, summary_type = "peak_values")
  })
  
  expect_type(ml_data_peaks, "list")
  expect_true("features" %in% names(ml_data_peaks))
  expect_true(nrow(ml_data_peaks$features) > 0)
})

test_that("Error handling works correctly", {
  # Test with invalid data
  expect_error({
    prepare_ml_data("not_locomotion_data")
  })
  
  # Test with empty feature list
  test_data <- helper_create_test_locomotion_data()
  expect_error({
    prepare_ml_data(test_data, features = character(0))
  })
  
  # Test invalid target variable
  ml_data <- prepare_ml_data(test_data, summary_type = "mean")
  expect_error({
    biomech_random_forest(ml_data, target = "invalid_target")
  })
})