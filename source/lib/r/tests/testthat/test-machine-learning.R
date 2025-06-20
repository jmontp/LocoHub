test_that("ML data preparation works correctly", {
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  
  # Test data preparation
  expect_no_error({
    ml_data <- prepare_ml_data(
      test_data,
      summary_type = "mean",
      normalize = TRUE
    )
  })
  
  # Check result structure
  expect_type(ml_data, "list")
  expect_true("features" %in% names(ml_data))
  expect_true("subjects" %in% names(ml_data))
  expect_true("tasks" %in% names(ml_data))
  expect_true(is.data.frame(ml_data$features))
  expect_true(is.factor(ml_data$subjects))
  expect_true(is.factor(ml_data$tasks))
  expect_equal(nrow(ml_data$features), length(ml_data$subjects))
})

test_that("PCA analysis works", {
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  ml_data <- prepare_ml_data(test_data, summary_type = "mean")
  
  # Test PCA
  expect_no_error({
    pca_result <- biomech_pca(ml_data, n_components = 3)
  })
  
  # Check result structure
  expect_type(pca_result, "list")
  expect_true("scores" %in% names(pca_result))
  expect_true("loadings" %in% names(pca_result))
  expect_true("variance_explained" %in% names(pca_result))
  expect_equal(ncol(pca_result$scores), 3)
  expect_equal(ncol(pca_result$loadings), 3)
  expect_equal(length(pca_result$variance_explained), 3)
})

test_that("k-means clustering works", {
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  ml_data <- prepare_ml_data(test_data, summary_type = "mean")
  
  # Test k-means with specified k
  expect_no_error({
    kmeans_result <- biomech_kmeans(ml_data, k = 3)
  })
  
  # Check result structure
  expect_type(kmeans_result, "list")
  expect_true("cluster_assignments" %in% names(kmeans_result))
  expect_true("cluster_summary" %in% names(kmeans_result))
  expect_true("avg_silhouette" %in% names(kmeans_result))
  expect_equal(kmeans_result$k, 3)
  expect_true(is.data.frame(kmeans_result$cluster_assignments))
})

test_that("Random Forest classification works", {
  skip_if_not_installed("randomForest")
  
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  ml_data <- prepare_ml_data(test_data, summary_type = "mean")
  
  # Test Random Forest
  expect_no_error({
    rf_result <- biomech_random_forest(ml_data, target = "tasks", ntree = 50)
  })
  
  # Check result structure
  expect_type(rf_result, "list")
  expect_true("rf_model" %in% names(rf_result))
  expect_true("predictions" %in% names(rf_result))
  expect_true("accuracy" %in% names(rf_result))
  expect_true("confusion_matrix" %in% names(rf_result))
  expect_true(rf_result$accuracy >= 0 && rf_result$accuracy <= 1)
})

test_that("SVM classification works", {
  skip_if_not_installed("e1071")
  
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  ml_data <- prepare_ml_data(test_data, summary_type = "mean")
  
  # Test SVM
  expect_no_error({
    svm_result <- biomech_svm(ml_data, target = "tasks", cost = 1)
  })
  
  # Check result structure
  expect_type(svm_result, "list")
  expect_true("svm_model" %in% names(svm_result))
  expect_true("predictions" %in% names(svm_result))
  expect_true("accuracy" %in% names(svm_result))
  expect_true("confusion_matrix" %in% names(svm_result))
  expect_true(svm_result$accuracy >= 0 && svm_result$accuracy <= 1)
})

test_that("Feature selection works", {
  skip_if_not_installed("randomForest")
  
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  ml_data <- prepare_ml_data(test_data, summary_type = "mean")
  
  # Test feature selection
  expect_no_error({
    fs_result <- biomech_feature_selection(ml_data, target = "tasks", method = "importance", n_features = 3)
  })
  
  # Check result structure
  expect_type(fs_result, "list")
  expect_true("selected_features" %in% names(fs_result))
  expect_true("selected_data" %in% names(fs_result))
  expect_true("feature_ranking" %in% names(fs_result))
  expect_equal(length(fs_result$selected_features), 3)
  expect_equal(ncol(fs_result$selected_data$features), 3)
})

test_that("Cross-validation works", {
  skip_if_not_installed("randomForest")
  
  # Load test data
  test_data <- helper_create_test_locomotion_data()
  ml_data <- prepare_ml_data(test_data, summary_type = "mean")
  
  # Test cross-validation
  expect_no_error({
    cv_result <- biomech_cross_validation(ml_data, target = "tasks", method = "random_forest", folds = 3, ntree = 50)
  })
  
  # Check result structure
  expect_type(cv_result, "list")
  expect_true("overall_accuracy" %in% names(cv_result))
  expect_true("mean_cv_accuracy" %in% names(cv_result))
  expect_true("cv_results" %in% names(cv_result))
  expect_true(cv_result$overall_accuracy >= 0 && cv_result$overall_accuracy <= 1)
})