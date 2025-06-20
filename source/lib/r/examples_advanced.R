#' Advanced Statistical and Machine Learning Examples
#'
#' Created: 2025-06-19 with user permission
#' Purpose: Comprehensive examples demonstrating advanced statistical and ML capabilities
#'
#' Intent:
#' This file provides practical examples of using the advanced statistical and machine
#' learning functionality in the LocomotionData R package. It demonstrates Bayesian 
#' analysis, mixed-effects modeling, dimensionality reduction, clustering, classification,
#' and complete machine learning workflows for biomechanical research.

# Load required packages
library(LocomotionData)

#' Example 1: Comprehensive Bayesian Analysis Workflow
#' 
#' This example demonstrates how to perform Bayesian statistical analysis
#' comparing different locomotion conditions.
example_bayesian_workflow <- function() {
  cat("=== Bayesian Analysis Workflow ===\n")
  
  # Load sample data (replace with actual data file)
  # loco_data <- loadLocomotionData("sample_gait_data.parquet")
  
  # For demonstration, create sample data
  loco_data <- helper_create_test_locomotion_data()
  
  cat("1. Bayesian t-test comparing walking speeds...\n")
  # Compare normal vs fast walking for knee flexion
  bayes_ttest_result <- bayes_ttest_biomech(
    loco_data,
    feature = "knee_flexion_angle_contra_rad",
    condition1 = "normal_walk",
    condition2 = "fast_walk",
    summary_type = "mean",
    iterations = 5000
  )
  
  cat("Bayes Factor:", round(bayes_ttest_result$bayes_factor, 3), "\n")
  cat("Interpretation:", bayes_ttest_result$interpretation, "\n")
  cat("Mean difference:", round(bayes_ttest_result$sample_info$mean_diff, 4), "\n\n")
  
  cat("2. Bayesian ANOVA across multiple conditions...\n")
  # Compare multiple walking conditions
  bayes_anova_result <- bayes_anova_biomech(
    loco_data,
    feature = "knee_flexion_angle_contra_rad",
    conditions = c("normal_walk", "fast_walk"),
    summary_type = "mean"
  )
  
  cat("Bayes Factor:", round(bayes_anova_result$bayes_factor, 3), "\n")
  cat("Interpretation:", bayes_anova_result$interpretation, "\n\n")
  
  cat("3. Bayesian correlation analysis...\n")
  # Analyze relationship between knee and hip angles
  bayes_corr_result <- bayes_correlation_biomech(
    loco_data,
    feature1 = "knee_flexion_angle_contra_rad",
    feature2 = "hip_flexion_angle_contra_rad",
    condition = "normal_walk",
    summary_type = "mean"
  )
  
  cat("Classical correlation:", round(bayes_corr_result$classical_correlation, 3), "\n")
  cat("Bayes Factor:", round(bayes_corr_result$bayes_factor, 3), "\n")
  cat("Interpretation:", bayes_corr_result$interpretation, "\n\n")
  
  cat("4. Robustness analysis across different priors...\n")
  # Test robustness across different prior specifications
  robustness_result <- bayes_robustness_check(
    analysis_function = bayes_ttest_biomech,
    prior_scales = c(0.1, 0.5, 1.0, sqrt(2)/2),
    loco_data = loco_data,
    feature = "knee_flexion_angle_contra_rad",
    condition1 = "normal_walk",
    condition2 = "fast_walk",
    summary_type = "mean",
    iterations = 1000
  )
  
  cat("Robustness across priors:\n")
  print(robustness_result$robustness_table[, c("prior_scale", "bayes_factor", "interpretation")])
  cat("Consistent direction:", robustness_result$consistent_direction, "\n\n")
  
  return(list(
    ttest = bayes_ttest_result,
    anova = bayes_anova_result,
    correlation = bayes_corr_result,
    robustness = robustness_result
  ))
}

#' Example 2: Mixed-Effects Modeling for Longitudinal Analysis
#'
#' This example shows how to use mixed-effects models for analyzing
#' hierarchical biomechanical data.
example_mixed_effects_workflow <- function() {
  cat("=== Mixed-Effects Modeling Workflow ===\n")
  
  # Load sample data
  loco_data <- helper_create_test_locomotion_data()
  
  cat("1. Preparing data for mixed-effects modeling...\n")
  # Prepare data in long format for modeling
  mixed_data <- prepare_mixed_effects_data(
    loco_data,
    tasks = c("normal_walk", "fast_walk"),
    features = c("knee_flexion_angle_contra_rad", "hip_flexion_angle_contra_rad"),
    include_phase = TRUE
  )
  
  cat("Data shape:", nrow(mixed_data), "observations,", ncol(mixed_data), "variables\n")
  cat("Subjects:", length(unique(mixed_data$subject)), "\n")
  cat("Tasks:", paste(unique(mixed_data$task), collapse = ", "), "\n\n")
  
  cat("2. Fitting gait analysis model...\n")
  # Standard gait analysis model comparing tasks across gait cycle
  gait_model <- fit_gait_analysis_model(
    loco_data,
    outcome = "knee_flexion_angle_contra_rad",
    tasks = c("normal_walk", "fast_walk"),
    include_phase = TRUE
  )
  
  cat("Model converged:", gait_model$converged, "\n")
  cat("AIC:", round(gait_model$aic, 2), "\n")
  cat("Number of observations:", gait_model$n_obs, "\n\n")
  
  cat("3. Random effects structure recommendations...\n")
  # Get recommendations for random effects structure
  recommendations <- recommend_random_effects(
    mixed_data,
    outcome = "knee_flexion_angle_contra_rad",
    predictors = c("task_factor", "phase_sin", "phase_cos")
  )
  
  cat("Data summary:\n")
  print(recommendations$data_summary)
  cat("\nRecommended structures:\n")
  for (i in seq_along(recommendations$recommendations)) {
    rec <- recommendations$recommendations[[i]]
    cat(paste(i, ".", rec$structure, "-", rec$description, "\n"))
  }
  cat("\n")
  
  cat("4. Model diagnostics and assumptions...\n")
  # Run comprehensive model diagnostics
  diagnostics <- run_model_diagnostics(gait_model)
  assumptions <- check_model_assumptions(gait_model)
  
  cat("Model diagnostics:\n")
  cat("- Converged:", diagnostics$model_info$converged, "\n")
  cat("- Residual mean:", round(diagnostics$residuals$mean, 6), "\n")
  cat("- Overall assessment:", assumptions$overall_assessment, "\n\n")
  
  return(list(
    data = mixed_data,
    model = gait_model,
    recommendations = recommendations,
    diagnostics = diagnostics
  ))
}

#' Example 3: Complete Machine Learning Pipeline
#'
#' This example demonstrates a complete machine learning workflow
#' for biomechanical pattern classification.
example_ml_pipeline <- function() {
  cat("=== Machine Learning Pipeline ===\n")
  
  # Load sample data
  loco_data <- helper_create_test_locomotion_data()
  
  cat("1. Data preparation and exploration...\n")
  # Prepare data for machine learning
  ml_data <- prepare_ml_data(
    loco_data,
    summary_type = "mean",
    normalize = TRUE,
    remove_na = TRUE
  )
  
  cat("ML data shape:", nrow(ml_data$features), "samples,", ncol(ml_data$features), "features\n")
  cat("Target classes:", paste(levels(ml_data$tasks), collapse = ", "), "\n")
  cat("Class distribution:")
  print(table(ml_data$tasks))
  cat("\n")
  
  cat("2. Dimensionality reduction analysis...\n")
  # Principal Component Analysis
  pca_result <- biomech_pca(ml_data, variance_threshold = 0.90)
  cat("PCA: Retained", pca_result$n_components, "components explaining", 
      round(pca_result$analysis_info$total_variance_explained * 100, 1), "% variance\n")
  
  # t-SNE for visualization (with small dataset, reduce perplexity)
  if (nrow(ml_data$features) > 10) {
    tsne_result <- biomech_tsne(ml_data, dims = 2, perplexity = min(5, floor(nrow(ml_data$features)/4)))
    cat("t-SNE: Generated 2D embedding for visualization\n")
  } else {
    cat("t-SNE: Skipped due to small sample size\n")
    tsne_result <- NULL
  }
  cat("\n")
  
  cat("3. Clustering analysis...\n")
  # K-means clustering
  kmeans_result <- biomech_kmeans(ml_data, k = length(levels(ml_data$tasks)))
  cat("K-means: Found", kmeans_result$k, "clusters\n")
  cat("Average silhouette score:", round(kmeans_result$avg_silhouette, 3), "\n")
  
  # Hierarchical clustering
  hclust_result <- biomech_hierarchical(ml_data, method = "ward.D2", k = length(levels(ml_data$tasks)))
  cat("Hierarchical clustering: Average silhouette score:", round(hclust_result$avg_silhouette, 3), "\n\n")
  
  cat("4. Feature selection...\n")
  # Feature selection using Random Forest importance
  fs_result <- biomech_feature_selection(
    ml_data,
    target = "tasks",
    method = "importance",
    n_features = min(5, ncol(ml_data$features))
  )
  
  cat("Selected", fs_result$n_selected, "out of", fs_result$n_total, "features:\n")
  cat(paste("-", fs_result$selected_features, collapse = "\n"), "\n\n")
  
  cat("5. Model comparison with cross-validation...\n")
  # Compare multiple ML algorithms
  comparison_result <- biomech_model_comparison(
    ml_data,
    target = "tasks",
    methods = c("random_forest", "svm"),
    cv_folds = min(3, length(unique(ml_data$subjects))),
    feature_selection = TRUE
  )
  
  cat("Model comparison results:\n")
  print(comparison_result$comparison_summary[, c("method", "accuracy", "accuracy_sd")])
  cat("Best method:", comparison_result$best_method, 
      "with accuracy:", round(comparison_result$best_accuracy, 3), "\n\n")
  
  cat("6. Complete automated pipeline...\n")
  # Run complete ML pipeline
  pipeline_result <- biomech_ml_pipeline(
    loco_data,
    target = "tasks",
    summary_type = "mean",
    feature_selection = TRUE,
    methods = c("random_forest"),
    hyperparameter_tuning = FALSE,  # Skip for speed in example
    cv_folds = min(3, length(unique(ml_data$subjects)))
  )
  
  cat("Pipeline completed successfully!\n")
  cat("Final model:", pipeline_result$best_method, "\n")
  cat("Final accuracy:", round(pipeline_result$best_accuracy, 3), "\n")
  cat("Runtime:", round(pipeline_result$pipeline_info$total_runtime_seconds, 2), "seconds\n\n")
  
  return(list(
    ml_data = ml_data,
    pca = pca_result,
    tsne = tsne_result,
    clustering = list(kmeans = kmeans_result, hierarchical = hclust_result),
    feature_selection = fs_result,
    comparison = comparison_result,
    pipeline = pipeline_result
  ))
}

#' Example 4: Advanced Pattern Recognition for Clinical Research
#'
#' This example shows how to use the package for clinical biomechanics
#' research with patient vs control group analysis.
example_clinical_research <- function() {
  cat("=== Clinical Research Example ===\n")
  
  # Load sample data
  loco_data <- helper_create_test_locomotion_data()
  
  cat("1. Group comparison setup...\n")
  # Define subject groups (in real application, this would come from metadata)
  subjects <- getSubjects(loco_data)
  group_info <- setNames(c("control", "patient")[rep(1:2, length.out = length(subjects))], subjects)
  
  cat("Group assignment:\n")
  print(table(group_info))
  cat("\n")
  
  cat("2. Bayesian group comparison...\n")
  # Prepare data for group comparison
  control_subjects <- names(group_info)[group_info == "control"]
  patient_subjects <- names(group_info)[group_info == "patient"]
  
  # Create separate datasets for each group
  control_data <- filterSubjects(loco_data, control_subjects)
  patient_data <- filterSubjects(loco_data, patient_subjects)
  
  # Bayesian t-test comparing groups
  if (length(control_subjects) > 0 && length(patient_subjects) > 0) {
    # Get mean values for each group
    control_means <- sapply(control_subjects, function(s) {
      patterns <- getMeanPatterns(control_data, s, "normal_walk", "knee_flexion_angle_contra_rad")
      if (!is.null(patterns)) mean(patterns$knee_flexion_angle_contra_rad, na.rm = TRUE) else NA
    })
    
    patient_means <- sapply(patient_subjects, function(s) {
      patterns <- getMeanPatterns(patient_data, s, "normal_walk", "knee_flexion_angle_contra_rad")
      if (!is.null(patterns)) mean(patterns$knee_flexion_angle_contra_rad, na.rm = TRUE) else NA
    })
    
    control_means <- control_means[!is.na(control_means)]
    patient_means <- patient_means[!is.na(patient_means)]
    
    if (length(control_means) > 0 && length(patient_means) > 0) {
      # Manual Bayesian t-test using BayesFactor
      library(BayesFactor)
      group_bayes_result <- ttestBF(control_means, patient_means)
      bf_value <- extractBF(group_bayes_result)$bf[1]
      
      cat("Group comparison Bayes Factor:", round(bf_value, 3), "\n")
      cat("Interpretation:", interpret_bayes_factor(bf_value), "\n")
      cat("Control mean:", round(mean(control_means), 4), "±", round(sd(control_means), 4), "\n")
      cat("Patient mean:", round(mean(patient_means), 4), "±", round(sd(patient_means), 4), "\n\n")
    } else {
      cat("Insufficient data for group comparison\n\n")
    }
  }
  
  cat("3. Mixed-effects model for group differences...\n")
  # Fit group comparison model
  group_model <- fit_group_comparison_model(
    loco_data,
    outcome = "knee_flexion_angle_contra_rad",
    group_info = group_info
  )
  
  cat("Group model AIC:", round(group_model$aic, 2), "\n")
  cat("Model converged:", group_model$converged, "\n")
  cat("Groups analyzed:", paste(group_model$group_info$groups, collapse = ", "), "\n\n")
  
  cat("4. Machine learning for group classification...\n")
  # Prepare ML data with group labels
  ml_data <- prepare_ml_data(loco_data, summary_type = "mean", normalize = TRUE)
  
  # Add group information to ML data
  ml_data$groups <- factor(group_info[as.character(ml_data$subjects)])
  
  # Classification to distinguish groups
  group_rf_result <- biomech_random_forest(
    ml_data,
    target = "groups",  # Custom target variable
    ntree = 100,
    importance = TRUE
  )
  
  cat("Group classification accuracy:", round(group_rf_result$accuracy, 3), "\n")
  cat("Most important features for group distinction:\n")
  if (!is.null(group_rf_result$variable_importance)) {
    top_features <- head(group_rf_result$variable_importance, 3)
    for (i in 1:nrow(top_features)) {
      cat(paste("-", top_features$feature[i], 
                "(importance:", round(top_features$mean_decrease_accuracy[i], 3), ")\n"))
    }
  }
  cat("\n")
  
  cat("5. Clinical interpretation summary...\n")
  cat("This analysis provides:\n")
  cat("- Bayesian evidence for group differences\n")
  cat("- Mixed-effects modeling accounting for individual variation\n")
  cat("- Machine learning identification of discriminative features\n")
  cat("- Quantitative assessment suitable for clinical decision support\n\n")
  
  return(list(
    group_info = group_info,
    group_model = group_model,
    classification = group_rf_result
  ))
}

#' Run All Advanced Examples
#'
#' Executes all advanced analysis examples and returns comprehensive results
#'
#' @return List containing results from all example analyses
#' @export
run_advanced_examples <- function() {
  cat("Running Advanced Statistical and Machine Learning Examples\n")
  cat("=========================================================\n\n")
  
  # Check if required packages are available
  required_packages <- c("BayesFactor", "randomForest", "e1071", "cluster")
  missing_packages <- required_packages[!sapply(required_packages, requireNamespace, quietly = TRUE)]
  
  if (length(missing_packages) > 0) {
    cat("Warning: Missing packages:", paste(missing_packages, collapse = ", "), "\n")
    cat("Some examples may be skipped. Install with: install.packages(c(", 
        paste(paste0("'", missing_packages, "'"), collapse = ", "), "))\n\n")
  }
  
  results <- list()
  
  # Example 1: Bayesian Analysis
  tryCatch({
    results$bayesian <- example_bayesian_workflow()
  }, error = function(e) {
    cat("Bayesian analysis example failed:", e$message, "\n\n")
    results$bayesian <<- NULL
  })
  
  # Example 2: Mixed-Effects Modeling
  tryCatch({
    results$mixed_effects <- example_mixed_effects_workflow()
  }, error = function(e) {
    cat("Mixed-effects modeling example failed:", e$message, "\n\n")
    results$mixed_effects <<- NULL
  })
  
  # Example 3: Machine Learning Pipeline
  tryCatch({
    results$machine_learning <- example_ml_pipeline()
  }, error = function(e) {
    cat("Machine learning pipeline example failed:", e$message, "\n\n")
    results$machine_learning <<- NULL
  })
  
  # Example 4: Clinical Research
  tryCatch({
    results$clinical_research <- example_clinical_research()
  }, error = function(e) {
    cat("Clinical research example failed:", e$message, "\n\n")
    results$clinical_research <<- NULL
  })
  
  cat("All examples completed!\n")
  cat("========================\n\n")
  
  # Summary
  successful_examples <- sum(!sapply(results, is.null))
  cat("Successfully completed", successful_examples, "out of 4 examples\n")
  
  if (successful_examples > 0) {
    cat("\nExample results available in returned list:\n")
    if (!is.null(results$bayesian)) cat("- results$bayesian: Bayesian analysis results\n")
    if (!is.null(results$mixed_effects)) cat("- results$mixed_effects: Mixed-effects modeling results\n")
    if (!is.null(results$machine_learning)) cat("- results$machine_learning: ML pipeline results\n")
    if (!is.null(results$clinical_research)) cat("- results$clinical_research: Clinical research results\n")
  }
  
  return(results)
}

# Helper function for creating test data (if not available from main package)
if (!exists("helper_create_test_locomotion_data")) {
  helper_create_test_locomotion_data <- function() {
    # Create minimal test data for examples
    # This would be replaced with actual data loading in practice
    
    # Create simple synthetic data
    n_subjects <- 4
    n_cycles_per_task <- 3
    n_phases <- 150
    
    subjects <- paste0("SUB", sprintf("%02d", 1:n_subjects))
    tasks <- c("normal_walk", "fast_walk")
    features <- c("knee_flexion_angle_contra_rad", "hip_flexion_angle_contra_rad", 
                 "ankle_flexion_angle_contra_rad")
    
    # Generate synthetic biomechanical data
    data_list <- list()
    row_count <- 1
    
    for (subject in subjects) {
      for (task in tasks) {
        for (cycle in 1:n_cycles_per_task) {
          for (phase in 1:n_phases) {
            phase_percent <- (phase - 1) / (n_phases - 1) * 100
            
            # Generate realistic gait patterns with some noise
            knee_angle <- 0.3 * sin(2 * pi * phase_percent / 100) + 
                         rnorm(1, 0, 0.05) + 
                         ifelse(task == "fast_walk", 0.1, 0)
            
            hip_angle <- 0.2 * sin(2 * pi * phase_percent / 100 + pi/4) + 
                        rnorm(1, 0, 0.03) +
                        ifelse(task == "fast_walk", 0.05, 0)
            
            ankle_angle <- 0.15 * sin(2 * pi * phase_percent / 100 + pi/2) + 
                          rnorm(1, 0, 0.02)
            
            data_list[[row_count]] <- data.frame(
              subject = subject,
              task = task,
              cycle = cycle,
              phase = phase_percent,
              knee_flexion_angle_contra_rad = knee_angle,
              hip_flexion_angle_contra_rad = hip_angle,
              ankle_flexion_angle_contra_rad = ankle_angle,
              stringsAsFactors = FALSE
            )
            row_count <- row_count + 1
          }
        }
      }
    }
    
    # Combine into data frame
    test_df <- do.call(rbind, data_list)
    
    # Create mock LocomotionData object
    # In real implementation, this would use the actual LocomotionData constructor
    mock_loco_data <- list(
      data = test_df,
      subjects = unique(test_df$subject),
      tasks = unique(test_df$task),
      features = features,
      class = "LocomotionData"
    )
    
    # Add basic methods that examples might use
    class(mock_loco_data) <- "LocomotionData"
    
    return(mock_loco_data)
  }
  
  # Mock functions for the examples
  getSubjects <- function(loco_data) {
    return(loco_data$subjects)
  }
  
  getTasks <- function(loco_data) {
    return(loco_data$tasks)
  }
  
  getFeatures <- function(loco_data) {
    return(loco_data$features)
  }
  
  filterSubjects <- function(loco_data, subjects) {
    filtered_data <- loco_data$data[loco_data$data$subject %in% subjects, ]
    loco_data$data <- filtered_data
    loco_data$subjects <- intersect(loco_data$subjects, subjects)
    return(loco_data)
  }
  
  getMeanPatterns <- function(loco_data, subject, task, features) {
    subset_data <- loco_data$data[loco_data$data$subject == subject & 
                                 loco_data$data$task == task, ]
    if (nrow(subset_data) == 0) return(NULL)
    
    result <- list()
    for (feature in features) {
      if (feature %in% names(subset_data)) {
        result[[feature]] <- subset_data[[feature]]
      }
    }
    return(result)
  }
}