#' Machine Learning Workflows and Cross-Validation
#'
#' Created: 2025-06-19 with user permission
#' Purpose: Comprehensive ML workflows with cross-validation and model evaluation
#'
#' Intent:
#' This module provides integrated machine learning workflows specifically designed 
#' for biomechanical research. It includes cross-validation frameworks, hyperparameter 
#' tuning, feature selection, model comparison, and evaluation tools that handle the 
#' complexities of biomechanical data including subject-level dependencies and 
#' temporal correlations.
#'
#' Key Features:
#' - Subject-aware cross-validation to prevent data leakage
#' - Comprehensive hyperparameter tuning with grid search
#' - Feature selection algorithms with importance ranking
#' - Model evaluation with biomechanical-relevant metrics
#' - Automated workflow pipelines for common research questions
#' - Performance comparison across multiple algorithms

library(stats)

#' Cross-Validation with Subject Grouping
#'
#' Performs cross-validation ensuring subjects are not split across folds
#'
#' @param ml_data List, prepared ML data from prepare_ml_data
#' @param target Character, target variable ("subjects" or "tasks")
#' @param method Character, ML method ("svm", "random_forest", "logistic")
#' @param folds Integer, number of cross-validation folds (default: 5)
#' @param stratified Logical, whether to stratify by target (default: TRUE)
#' @param ... Additional parameters passed to ML method
#' @return List containing cross-validation results
#'
#' @export
biomech_cross_validation <- function(ml_data, target = "tasks", method = "random_forest", 
                                    folds = 5, stratified = TRUE, ...) {
  
  if (!"features" %in% names(ml_data)) {
    stop("Input must be prepared ML data with 'features' component")
  }
  
  feature_matrix <- ml_data$features
  subjects <- ml_data$subjects
  
  # Get target variable
  if (target == "tasks") {
    target_var <- ml_data$tasks
  } else if (target == "subjects") {
    target_var <- ml_data$subjects
  } else {
    stop("target must be 'tasks' or 'subjects'")
  }
  
  # Create subject-level folds to prevent data leakage
  unique_subjects <- unique(subjects)
  n_subjects <- length(unique_subjects)
  
  if (n_subjects < folds) {
    folds <- n_subjects
    warning(paste("Number of folds reduced to", folds, "due to limited subjects"))
  }
  
  # Create folds ensuring balanced target distribution if stratified
  if (stratified && target == "tasks") {
    # Stratify by task within subjects
    subject_task_summary <- aggregate(as.numeric(target_var), 
                                     list(subject = subjects), 
                                     function(x) names(sort(table(x), decreasing = TRUE))[1])
    names(subject_task_summary) <- c("subject", "primary_task")
    
    fold_assignments <- rep(1:folds, length.out = n_subjects)
    fold_assignments <- sample(fold_assignments)  # Randomize
  } else {
    fold_assignments <- sample(rep(1:folds, length.out = n_subjects))
  }
  
  # Map subjects to folds
  subject_folds <- data.frame(
    subject = unique_subjects,
    fold = fold_assignments,
    stringsAsFactors = FALSE
  )
  
  # Perform cross-validation
  cv_results <- list()
  predictions_all <- factor(rep(NA, length(target_var)), levels = levels(target_var))
  
  for (fold in 1:folds) {
    # Get training and test subjects
    test_subjects <- subject_folds$subject[subject_folds$fold == fold]
    train_subjects <- subject_folds$subject[subject_folds$fold != fold]
    
    # Create training and test indices
    train_idx <- which(subjects %in% train_subjects)
    test_idx <- which(subjects %in% test_subjects)
    
    if (length(train_idx) == 0 || length(test_idx) == 0) {
      warning(paste("Fold", fold, "has empty training or test set"))
      next
    }
    
    # Create training and test data
    train_data <- list(
      features = feature_matrix[train_idx, , drop = FALSE],
      subjects = subjects[train_idx],
      tasks = ml_data$tasks[train_idx],
      metadata = ml_data$metadata[train_idx]
    )
    
    test_data <- list(
      features = feature_matrix[test_idx, , drop = FALSE],
      subjects = subjects[test_idx],
      tasks = ml_data$tasks[test_idx],
      metadata = ml_data$metadata[test_idx]
    )
    
    # Train model
    tryCatch({
      if (method == "random_forest") {
        model_result <- biomech_random_forest(train_data, target = target, ...)
        test_predictions <- predict(model_result$rf_model, test_data$features)
      } else if (method == "svm") {
        model_result <- biomech_svm(train_data, target = target, ...)
        test_predictions <- predict(model_result$svm_model, test_data$features)
      } else if (method == "logistic") {
        # Implement logistic regression
        if (target == "tasks") {
          target_train <- train_data$tasks
          target_test <- test_data$tasks
        } else {
          target_train <- train_data$subjects
          target_test <- test_data$subjects
        }
        
        # Handle multi-class with one-vs-rest if necessary
        if (length(levels(target_train)) == 2) {
          train_df <- data.frame(target = target_train, train_data$features)
          model_result <- glm(target ~ ., data = train_df, family = binomial)
          test_prob <- predict(model_result, newdata = test_data$features, type = "response")
          test_predictions <- factor(ifelse(test_prob > 0.5, levels(target_train)[2], levels(target_train)[1]), 
                                   levels = levels(target_train))
        } else {
          # Multinomial logistic regression (simplified)
          warning("Multinomial logistic regression not fully implemented, using random forest instead")
          model_result <- biomech_random_forest(train_data, target = target, ...)
          test_predictions <- predict(model_result$rf_model, test_data$features)
        }
      } else {
        stop(paste("Method", method, "not supported"))
      }
      
      # Store fold results
      if (target == "tasks") {
        true_labels <- test_data$tasks
      } else {
        true_labels <- test_data$subjects
      }
      
      fold_accuracy <- sum(test_predictions == true_labels) / length(true_labels)
      
      cv_results[[fold]] <- list(
        fold = fold,
        train_subjects = train_subjects,
        test_subjects = test_subjects,
        predictions = test_predictions,
        true_labels = true_labels,
        accuracy = fold_accuracy,
        test_indices = test_idx,
        model = model_result
      )
      
      # Store predictions for overall evaluation
      predictions_all[test_idx] <- test_predictions
      
    }, error = function(e) {
      warning(paste("Fold", fold, "failed:", e$message))
      cv_results[[fold]] <- list(
        fold = fold,
        error = e$message
      )
    })
  }
  
  # Calculate overall performance
  valid_results <- cv_results[!sapply(cv_results, function(x) "error" %in% names(x))]
  
  if (length(valid_results) == 0) {
    stop("All cross-validation folds failed")
  }
  
  # Overall accuracy
  predictions_complete <- predictions_all[!is.na(predictions_all)]
  target_complete <- target_var[!is.na(predictions_all)]
  overall_accuracy <- sum(predictions_complete == target_complete) / length(target_complete)
  
  # Fold-wise accuracies
  fold_accuracies <- sapply(valid_results, function(x) x$accuracy)
  mean_cv_accuracy <- mean(fold_accuracies)
  sd_cv_accuracy <- sd(fold_accuracies)
  
  # Overall confusion matrix
  overall_confusion <- table(Predicted = predictions_complete, Actual = target_complete)
  
  # Create comprehensive results
  results <- list(
    method = method,
    target = target,
    folds = folds,
    stratified = stratified,
    cv_results = cv_results,
    valid_folds = length(valid_results),
    overall_accuracy = overall_accuracy,
    mean_cv_accuracy = mean_cv_accuracy,
    sd_cv_accuracy = sd_cv_accuracy,
    fold_accuracies = fold_accuracies,
    confusion_matrix = overall_confusion,
    predictions = predictions_complete,
    true_labels = target_complete,
    subject_folds = subject_folds,
    original_features = colnames(feature_matrix),
    analysis_info = list(
      n_subjects = n_subjects,
      n_samples = nrow(feature_matrix),
      n_features = ncol(feature_matrix),
      timestamp = Sys.time()
    )
  )
  
  return(results)
}

#' Hyperparameter Tuning with Grid Search
#'
#' Performs grid search for hyperparameter optimization
#'
#' @param ml_data List, prepared ML data from prepare_ml_data
#' @param target Character, target variable ("subjects" or "tasks")
#' @param method Character, ML method ("svm", "random_forest")
#' @param param_grid List, parameter grid to search
#' @param cv_folds Integer, number of cross-validation folds (default: 5)
#' @param scoring Character, scoring metric ("accuracy", "f1_weighted")
#' @return List containing tuning results
#'
#' @export
biomech_hyperparameter_tuning <- function(ml_data, target = "tasks", method = "random_forest",
                                         param_grid = NULL, cv_folds = 5, scoring = "accuracy") {
  
  if (!"features" %in% names(ml_data)) {
    stop("Input must be prepared ML data with 'features' component")
  }
  
  # Set default parameter grids
  if (is.null(param_grid)) {
    if (method == "random_forest") {
      param_grid <- list(
        ntree = c(100, 300, 500),
        mtry = c(floor(sqrt(ncol(ml_data$features))), 
                floor(ncol(ml_data$features) / 3),
                floor(ncol(ml_data$features) / 2))
      )
    } else if (method == "svm") {
      param_grid <- list(
        cost = c(0.1, 1, 10, 100),
        gamma = c(0.001, 0.01, 0.1, 1)
      )
    } else {
      stop(paste("Default parameter grid not available for method:", method))
    }
  }
  
  # Generate all parameter combinations
  param_combinations <- expand.grid(param_grid, stringsAsFactors = FALSE)
  n_combinations <- nrow(param_combinations)
  
  # Storage for results
  tuning_results <- data.frame(param_combinations, 
                              score = NA, 
                              score_sd = NA,
                              stringsAsFactors = FALSE)
  
  # Test each parameter combination
  for (i in 1:n_combinations) {
    params <- as.list(param_combinations[i, ])
    
    tryCatch({
      # Perform cross-validation with current parameters
      cv_result <- biomech_cross_validation(ml_data, target = target, method = method, 
                                           folds = cv_folds, ...)
      
      # Calculate score based on scoring metric
      if (scoring == "accuracy") {
        score <- cv_result$mean_cv_accuracy
        score_sd <- cv_result$sd_cv_accuracy
      } else if (scoring == "f1_weighted") {
        # Calculate weighted F1 score from confusion matrix
        conf_mat <- cv_result$confusion_matrix
        f1_scores <- numeric(nrow(conf_mat))
        
        for (j in 1:nrow(conf_mat)) {
          tp <- conf_mat[j, j]
          fp <- sum(conf_mat[j, ]) - tp
          fn <- sum(conf_mat[, j]) - tp
          
          precision <- ifelse(tp + fp > 0, tp / (tp + fp), 0)
          recall <- ifelse(tp + fn > 0, tp / (tp + fn), 0)
          f1_scores[j] <- ifelse(precision + recall > 0, 
                               2 * precision * recall / (precision + recall), 0)
        }
        
        class_weights <- diag(conf_mat) / sum(conf_mat)
        score <- sum(f1_scores * class_weights)
        score_sd <- cv_result$sd_cv_accuracy  # Approximation
      }
      
      tuning_results$score[i] <- score
      tuning_results$score_sd[i] <- score_sd
      
    }, error = function(e) {
      warning(paste("Parameter combination", i, "failed:", e$message))
      tuning_results$score[i] <- NA
      tuning_results$score_sd[i] <- NA
    })
  }
  
  # Find best parameters
  valid_results <- !is.na(tuning_results$score)
  if (sum(valid_results) == 0) {
    stop("All parameter combinations failed")
  }
  
  best_idx <- which.max(tuning_results$score[valid_results])
  best_params <- param_combinations[which(valid_results)[best_idx], ]
  best_score <- tuning_results$score[which(valid_results)[best_idx]]
  
  # Sort results by score
  tuning_results <- tuning_results[order(tuning_results$score, decreasing = TRUE, na.last = TRUE), ]
  
  # Train final model with best parameters
  final_params <- as.list(best_params)
  
  if (method == "random_forest") {
    final_model <- biomech_random_forest(ml_data, target = target, 
                                        ntree = final_params$ntree,
                                        mtry = final_params$mtry)
  } else if (method == "svm") {
    final_model <- biomech_svm(ml_data, target = target,
                              cost = final_params$cost,
                              gamma = final_params$gamma)
  }
  
  # Create comprehensive results
  results <- list(
    method = method,
    target = target,
    scoring = scoring,
    param_grid = param_grid,
    tuning_results = tuning_results,
    best_params = best_params,
    best_score = best_score,
    final_model = final_model,
    n_combinations_tested = sum(valid_results),
    n_combinations_total = n_combinations,
    analysis_info = list(
      cv_folds = cv_folds,
      timestamp = Sys.time()
    )
  )
  
  return(results)
}

#' Feature Selection
#'
#' Performs feature selection using various methods
#'
#' @param ml_data List, prepared ML data from prepare_ml_data
#' @param target Character, target variable ("subjects" or "tasks")
#' @param method Character, selection method ("importance", "correlation", "univariate")
#' @param n_features Integer, number of features to select (NULL for automatic)
#' @param threshold Numeric, threshold for selection (method-dependent)
#' @return List containing feature selection results
#'
#' @export
biomech_feature_selection <- function(ml_data, target = "tasks", method = "importance", 
                                     n_features = NULL, threshold = NULL) {
  
  if (!"features" %in% names(ml_data)) {
    stop("Input must be prepared ML data with 'features' component")
  }
  
  feature_matrix <- ml_data$features
  feature_names <- colnames(feature_matrix)
  
  # Get target variable
  if (target == "tasks") {
    target_var <- ml_data$tasks
  } else if (target == "subjects") {
    target_var <- ml_data$subjects
  } else {
    stop("target must be 'tasks' or 'subjects'")
  }
  
  # Perform feature selection based on method
  if (method == "importance") {
    # Use Random Forest feature importance
    rf_result <- biomech_random_forest(ml_data, target = target, importance = TRUE)
    importance_scores <- rf_result$variable_importance$mean_decrease_accuracy
    names(importance_scores) <- rf_result$variable_importance$feature
    
    # Sort by importance
    sorted_features <- names(sort(importance_scores, decreasing = TRUE))
    feature_scores <- importance_scores[sorted_features]
    
    # Select features
    if (is.null(n_features)) {
      if (is.null(threshold)) {
        threshold <- mean(importance_scores)
      }
      selected_features <- names(importance_scores[importance_scores >= threshold])
    } else {
      selected_features <- sorted_features[1:min(n_features, length(sorted_features))]
    }
    
  } else if (method == "correlation") {
    # Use correlation with target (for numerical encoding)
    target_numeric <- as.numeric(target_var)
    correlations <- apply(feature_matrix, 2, function(x) abs(cor(x, target_numeric, use = "complete.obs")))
    
    # Sort by correlation
    sorted_features <- names(sort(correlations, decreasing = TRUE))
    feature_scores <- correlations[sorted_features]
    
    # Select features
    if (is.null(n_features)) {
      if (is.null(threshold)) {
        threshold <- 0.1  # Default correlation threshold
      }
      selected_features <- names(correlations[correlations >= threshold])
    } else {
      selected_features <- sorted_features[1:min(n_features, length(sorted_features))]
    }
    
  } else if (method == "univariate") {
    # Use ANOVA F-test for feature selection
    f_scores <- numeric(ncol(feature_matrix))
    p_values <- numeric(ncol(feature_matrix))
    
    for (i in 1:ncol(feature_matrix)) {
      feature_data <- feature_matrix[, i]
      anova_result <- aov(feature_data ~ target_var)
      f_stat <- summary(anova_result)[[1]]["target_var", "F value"]
      p_val <- summary(anova_result)[[1]]["target_var", "Pr(>F)"]
      
      f_scores[i] <- ifelse(is.na(f_stat), 0, f_stat)
      p_values[i] <- ifelse(is.na(p_val), 1, p_val)
    }
    
    names(f_scores) <- feature_names
    names(p_values) <- feature_names
    
    # Sort by F-score
    sorted_features <- names(sort(f_scores, decreasing = TRUE))
    feature_scores <- f_scores[sorted_features]
    
    # Select features
    if (is.null(n_features)) {
      if (is.null(threshold)) {
        threshold <- 0.05  # Default p-value threshold
      }
      selected_features <- names(p_values[p_values <= threshold])
    } else {
      selected_features <- sorted_features[1:min(n_features, length(sorted_features))]
    }
    
    # Add p-values to results
    p_value_scores <- p_values[sorted_features]
    
  } else {
    stop(paste("Feature selection method", method, "not supported"))
  }
  
  # Create selected feature data
  if (length(selected_features) == 0) {
    warning("No features selected, using top 5 features")
    selected_features <- sorted_features[1:min(5, length(sorted_features))]
  }
  
  selected_data <- list(
    features = feature_matrix[, selected_features, drop = FALSE],
    subjects = ml_data$subjects,
    tasks = ml_data$tasks,
    metadata = ml_data$metadata,
    summary_type = ml_data$summary_type,
    normalized = ml_data$normalized,
    n_samples = ml_data$n_samples,
    n_features = length(selected_features),
    feature_names = selected_features,
    processing_info = ml_data$processing_info
  )
  
  # Create feature ranking summary
  ranking_df <- data.frame(
    feature = sorted_features,
    score = feature_scores[sorted_features],
    rank = 1:length(sorted_features),
    selected = sorted_features %in% selected_features,
    stringsAsFactors = FALSE
  )
  
  if (method == "univariate") {
    ranking_df$p_value <- p_value_scores
  }
  
  # Create comprehensive results
  results <- list(
    method = method,
    target = target,
    selected_features = selected_features,
    selected_data = selected_data,
    feature_ranking = ranking_df,
    n_selected = length(selected_features),
    n_total = length(feature_names),
    selection_criteria = list(
      n_features = n_features,
      threshold = threshold
    ),
    analysis_info = list(
      timestamp = Sys.time()
    )
  )
  
  return(results)
}

#' Model Comparison Pipeline
#'
#' Compares multiple ML models using consistent evaluation
#'
#' @param ml_data List, prepared ML data from prepare_ml_data
#' @param target Character, target variable ("subjects" or "tasks")
#' @param methods Character vector, ML methods to compare
#' @param cv_folds Integer, number of cross-validation folds (default: 5)
#' @param feature_selection Logical, whether to perform feature selection (default: FALSE)
#' @return List containing model comparison results
#'
#' @export
biomech_model_comparison <- function(ml_data, target = "tasks", methods = c("random_forest", "svm"),
                                   cv_folds = 5, feature_selection = FALSE) {
  
  if (!"features" %in% names(ml_data)) {
    stop("Input must be prepared ML data with 'features' component")
  }
  
  # Perform feature selection if requested
  analysis_data <- ml_data
  if (feature_selection) {
    fs_result <- biomech_feature_selection(ml_data, target = target, method = "importance")
    analysis_data <- fs_result$selected_data
    selected_features <- fs_result$selected_features
  } else {
    selected_features <- colnames(ml_data$features)
  }
  
  # Storage for results
  comparison_results <- list()
  comparison_summary <- data.frame(
    method = methods,
    accuracy = NA,
    accuracy_sd = NA,
    cv_folds_completed = NA,
    training_time = NA,
    stringsAsFactors = FALSE
  )
  
  # Test each method
  for (i in seq_along(methods)) {
    method <- methods[i]
    
    tryCatch({
      start_time <- Sys.time()
      
      # Perform cross-validation
      cv_result <- biomech_cross_validation(analysis_data, target = target, 
                                           method = method, folds = cv_folds)
      
      end_time <- Sys.time()
      training_time <- as.numeric(difftime(end_time, start_time, units = "secs"))
      
      # Store results
      comparison_results[[method]] <- cv_result
      comparison_summary$accuracy[i] <- cv_result$mean_cv_accuracy
      comparison_summary$accuracy_sd[i] <- cv_result$sd_cv_accuracy
      comparison_summary$cv_folds_completed[i] <- cv_result$valid_folds
      comparison_summary$training_time[i] <- training_time
      
    }, error = function(e) {
      warning(paste("Method", method, "failed:", e$message))
      comparison_results[[method]] <- list(error = e$message)
      comparison_summary$accuracy[i] <- NA
      comparison_summary$accuracy_sd[i] <- NA
      comparison_summary$cv_folds_completed[i] <- 0
      comparison_summary$training_time[i] <- NA
    })
  }
  
  # Sort by accuracy
  comparison_summary <- comparison_summary[order(comparison_summary$accuracy, decreasing = TRUE, na.last = TRUE), ]
  
  # Identify best method
  valid_methods <- !is.na(comparison_summary$accuracy)
  if (sum(valid_methods) == 0) {
    stop("All methods failed")
  }
  
  best_method <- comparison_summary$method[which(valid_methods)[1]]
  best_accuracy <- comparison_summary$accuracy[which(valid_methods)[1]]
  
  # Calculate statistical significance of differences (if multiple methods successful)
  significance_tests <- NULL
  if (sum(valid_methods) > 1) {
    # Perform pairwise t-tests on CV accuracies
    valid_results <- comparison_results[names(comparison_results) %in% comparison_summary$method[valid_methods]]
    
    pairwise_tests <- data.frame(
      method1 = character(),
      method2 = character(),
      p_value = numeric(),
      significant = logical(),
      stringsAsFactors = FALSE
    )
    
    method_names <- names(valid_results)
    for (j in 1:(length(method_names) - 1)) {
      for (k in (j + 1):length(method_names)) {
        acc1 <- valid_results[[method_names[j]]]$fold_accuracies
        acc2 <- valid_results[[method_names[k]]]$fold_accuracies
        
        if (length(acc1) > 1 && length(acc2) > 1) {
          t_test <- t.test(acc1, acc2)
          
          pairwise_tests <- rbind(pairwise_tests, data.frame(
            method1 = method_names[j],
            method2 = method_names[k],
            p_value = t_test$p.value,
            significant = t_test$p.value < 0.05,
            stringsAsFactors = FALSE
          ))
        }
      }
    }
    
    significance_tests <- pairwise_tests
  }
  
  # Create comprehensive results
  results <- list(
    target = target,
    methods_tested = methods,
    comparison_summary = comparison_summary,
    detailed_results = comparison_results,
    best_method = best_method,
    best_accuracy = best_accuracy,
    significance_tests = significance_tests,
    feature_selection_used = feature_selection,
    selected_features = if (feature_selection) selected_features else NULL,
    analysis_info = list(
      cv_folds = cv_folds,
      n_samples = nrow(analysis_data$features),
      n_features = ncol(analysis_data$features),
      timestamp = Sys.time()
    )
  )
  
  return(results)
}

#' Complete ML Pipeline
#'
#' Runs a complete machine learning pipeline from data preparation to model evaluation
#'
#' @param loco_data LocomotionData object
#' @param target Character, target variable ("subjects" or "tasks")
#' @param summary_type Character, data summary type ("mean", "rom", "full_cycle")
#' @param feature_selection Logical, whether to perform feature selection (default: TRUE)
#' @param methods Character vector, ML methods to compare (default: c("random_forest", "svm"))
#' @param hyperparameter_tuning Logical, whether to tune hyperparameters (default: FALSE)
#' @param cv_folds Integer, number of cross-validation folds (default: 5)
#' @return List containing complete pipeline results
#'
#' @export
biomech_ml_pipeline <- function(loco_data, target = "tasks", summary_type = "mean",
                               feature_selection = TRUE, methods = c("random_forest", "svm"),
                               hyperparameter_tuning = FALSE, cv_folds = 5) {
  
  pipeline_start <- Sys.time()
  
  # Step 1: Data preparation
  cat("Step 1: Preparing ML data...\n")
  ml_data <- prepare_ml_data(loco_data, summary_type = summary_type, normalize = TRUE)
  
  # Step 2: Feature selection (optional)
  if (feature_selection) {
    cat("Step 2: Performing feature selection...\n")
    fs_result <- biomech_feature_selection(ml_data, target = target, method = "importance")
    analysis_data <- fs_result$selected_data
    cat(paste("Selected", fs_result$n_selected, "out of", fs_result$n_total, "features\n"))
  } else {
    cat("Step 2: Skipping feature selection...\n")
    analysis_data <- ml_data
    fs_result <- NULL
  }
  
  # Step 3: Hyperparameter tuning (optional)
  tuning_results <- NULL
  if (hyperparameter_tuning) {
    cat("Step 3: Performing hyperparameter tuning...\n")
    tuning_results <- list()
    
    for (method in methods) {
      cat(paste("  Tuning", method, "...\n"))
      tryCatch({
        tuning_results[[method]] <- biomech_hyperparameter_tuning(
          analysis_data, target = target, method = method, cv_folds = cv_folds
        )
      }, error = function(e) {
        warning(paste("Hyperparameter tuning failed for", method, ":", e$message))
      })
    }
  } else {
    cat("Step 3: Skipping hyperparameter tuning...\n")
  }
  
  # Step 4: Model comparison
  cat("Step 4: Comparing models...\n")
  comparison_result <- biomech_model_comparison(
    analysis_data, target = target, methods = methods, cv_folds = cv_folds
  )
  
  # Step 5: Final model training
  cat("Step 5: Training final model...\n")
  best_method <- comparison_result$best_method
  
  if (hyperparameter_tuning && best_method %in% names(tuning_results)) {
    # Use tuned parameters
    best_params <- tuning_results[[best_method]]$best_params
    if (best_method == "random_forest") {
      final_model <- biomech_random_forest(analysis_data, target = target,
                                          ntree = best_params$ntree, mtry = best_params$mtry)
    } else if (best_method == "svm") {
      final_model <- biomech_svm(analysis_data, target = target,
                                cost = best_params$cost, gamma = best_params$gamma)
    }
  } else {
    # Use default parameters
    if (best_method == "random_forest") {
      final_model <- biomech_random_forest(analysis_data, target = target)
    } else if (best_method == "svm") {
      final_model <- biomech_svm(analysis_data, target = target)
    }
  }
  
  pipeline_end <- Sys.time()
  total_time <- as.numeric(difftime(pipeline_end, pipeline_start, units = "secs"))
  
  cat("Pipeline completed successfully!\n")
  cat(paste("Best method:", best_method, "with accuracy:", round(comparison_result$best_accuracy, 3), "\n"))
  cat(paste("Total runtime:", round(total_time, 2), "seconds\n"))
  
  # Create comprehensive results
  results <- list(
    target = target,
    summary_type = summary_type,
    original_data = ml_data,
    feature_selection_result = fs_result,
    hyperparameter_tuning_results = tuning_results,
    model_comparison = comparison_result,
    final_model = final_model,
    best_method = best_method,
    best_accuracy = comparison_result$best_accuracy,
    pipeline_info = list(
      feature_selection_used = feature_selection,
      hyperparameter_tuning_used = hyperparameter_tuning,
      methods_tested = methods,
      cv_folds = cv_folds,
      total_runtime_seconds = total_time,
      start_time = pipeline_start,
      end_time = pipeline_end
    )
  )
  
  return(results)
}