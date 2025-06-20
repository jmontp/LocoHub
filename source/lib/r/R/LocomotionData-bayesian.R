#' Bayesian Statistical Analysis for Biomechanical Data
#'
#' Created: 2025-06-19 with user permission
#' Purpose: Advanced Bayesian analysis capabilities for biomechanical locomotion data
#'
#' Intent:
#' This module provides comprehensive Bayesian statistical analysis functionality specifically 
#' designed for biomechanical research using the BayesFactor R package. It integrates with 
#' the LocomotionData S4 class to provide Bayesian alternatives to traditional frequentist 
#' approaches, including t-tests, ANOVA, correlation analysis, and model comparison.
#'
#' Key Features:
#' - Bayesian t-tests for group comparisons with Bayes factors
#' - Bayesian ANOVA for multi-group analysis with evidence ratios
#' - Bayesian correlation analysis for feature relationships
#' - Model comparison using Bayes factors and posterior probabilities
#' - Prior specification and sensitivity analysis
#' - Posterior summaries and credible intervals

# Required packages
if (!requireNamespace("BayesFactor", quietly = TRUE)) {
  stop("Package 'BayesFactor' needed for Bayesian analysis. Please install it with: install.packages('BayesFactor')")
}

if (!requireNamespace("coda", quietly = TRUE)) {
  warning("Package 'coda' recommended for MCMC diagnostics. Install with: install.packages('coda')")
}

library(BayesFactor)
library(stats)

#' Bayesian T-Test for Biomechanical Data
#'
#' Performs Bayesian t-test comparing biomechanical features between conditions
#'
#' @param loco_data LocomotionData object
#' @param feature Character, biomechanical feature to analyze
#' @param condition1 Character, first condition/task name
#' @param condition2 Character, second condition/task name (NULL for one-sample)
#' @param subjects Character vector, subjects to include (NULL for all)
#' @param summary_type Character, "mean" (default) or "rom" for analysis type
#' @param prior_scale Numeric, Cauchy prior scale (default: sqrt(2)/2)
#' @param iterations Integer, MCMC iterations (default: 10000)
#' @return List containing Bayes factor results and posterior summaries
#'
#' @export
bayes_ttest_biomech <- function(loco_data, feature, condition1, condition2 = NULL, 
                               subjects = NULL, summary_type = "mean", 
                               prior_scale = sqrt(2)/2, iterations = 10000) {
  
  # Validate inputs
  if (!is(loco_data, "LocomotionData")) {
    stop("Input must be a LocomotionData object")
  }
  
  if (!feature %in% get_features(loco_data)) {
    stop(paste("Feature", feature, "not found in data"))
  }
  
  # Get subjects
  if (is.null(subjects)) {
    subjects <- get_subjects(loco_data)
  }
  
  # Extract data for condition 1
  tryCatch({
    if (summary_type == "mean") {
      data1_list <- lapply(subjects, function(s) {
        patterns <- get_mean_patterns(loco_data, s, condition1, feature)
        if (!is.null(patterns) && length(patterns) > 0) {
          return(mean(patterns[[feature]], na.rm = TRUE))
        }
        return(NA)
      })
    } else if (summary_type == "rom") {
      data1_list <- lapply(subjects, function(s) {
        rom_result <- calculate_rom(loco_data, s, condition1, feature, by_cycle = FALSE)
        if (!is.null(rom_result) && feature %in% names(rom_result)) {
          return(rom_result[[feature]])
        }
        return(NA)
      })
    } else {
      stop("summary_type must be 'mean' or 'rom'")
    }
    
    data1 <- unlist(data1_list)
    data1 <- data1[!is.na(data1)]
    
    if (length(data1) == 0) {
      stop(paste("No valid data found for condition", condition1))
    }
    
  }, error = function(e) {
    stop(paste("Error extracting data for condition 1:", e$message))
  })
  
  # Extract data for condition 2 (if two-sample test)
  if (!is.null(condition2)) {
    tryCatch({
      if (summary_type == "mean") {
        data2_list <- lapply(subjects, function(s) {
          patterns <- get_mean_patterns(loco_data, s, condition2, feature)
          if (!is.null(patterns) && length(patterns) > 0) {
            return(mean(patterns[[feature]], na.rm = TRUE))
          }
          return(NA)
        })
      } else if (summary_type == "rom") {
        data2_list <- lapply(subjects, function(s) {
          rom_result <- calculate_rom(loco_data, s, condition2, feature, by_cycle = FALSE)
          if (!is.null(rom_result) && feature %in% names(rom_result)) {
            return(rom_result[[feature]])
          }
          return(NA)
        })
      }
      
      data2 <- unlist(data2_list)
      data2 <- data2[!is.na(data2)]
      
      if (length(data2) == 0) {
        stop(paste("No valid data found for condition", condition2))
      }
      
    }, error = function(e) {
      stop(paste("Error extracting data for condition 2:", e$message))
    })
  }
  
  # Perform Bayesian t-test
  tryCatch({
    if (is.null(condition2)) {
      # One-sample test against zero
      bf_result <- ttestBF(data1, rscale = prior_scale, iterations = iterations)
      test_type <- "one_sample"
      sample_info <- list(
        n1 = length(data1),
        mean1 = mean(data1),
        sd1 = sd(data1)
      )
    } else {
      # Two-sample test
      bf_result <- ttestBF(data1, data2, rscale = prior_scale, iterations = iterations)
      test_type <- "two_sample"
      sample_info <- list(
        n1 = length(data1),
        n2 = length(data2),
        mean1 = mean(data1),
        mean2 = mean(data2),
        sd1 = sd(data1),
        sd2 = sd(data2),
        mean_diff = mean(data1) - mean(data2)
      )
    }
    
    # Extract Bayes factor
    bayes_factor <- extractBF(bf_result)$bf[1]
    
    # Interpret Bayes factor
    interpretation <- interpret_bayes_factor(bayes_factor)
    
    # Sample from posterior for credible intervals
    posterior_samples <- posterior(bf_result, iterations = iterations)
    
    # Calculate posterior summaries
    if (requireNamespace("coda", quietly = TRUE)) {
      posterior_summary <- summary(posterior_samples)
      hpd_intervals <- coda::HPDinterval(posterior_samples)
    } else {
      posterior_summary <- summary(posterior_samples)
      hpd_intervals <- NULL
    }
    
    # Compile results
    results <- list(
      test_type = test_type,
      feature = feature,
      condition1 = condition1,
      condition2 = condition2,
      summary_type = summary_type,
      sample_info = sample_info,
      bayes_factor = bayes_factor,
      log_bayes_factor = log(bayes_factor),
      interpretation = interpretation,
      bf_object = bf_result,
      posterior_samples = posterior_samples,
      posterior_summary = posterior_summary,
      credible_intervals = hpd_intervals,
      prior_info = list(
        prior_type = "Cauchy",
        prior_scale = prior_scale
      ),
      analysis_info = list(
        iterations = iterations,
        subjects_analyzed = subjects,
        timestamp = Sys.time()
      )
    )
    
    return(results)
    
  }, error = function(e) {
    stop(paste("Bayesian t-test failed:", e$message))
  })
}

#' Bayesian ANOVA for Multiple Groups
#'
#' Performs Bayesian ANOVA comparing biomechanical features across multiple conditions
#'
#' @param loco_data LocomotionData object
#' @param feature Character, biomechanical feature to analyze
#' @param conditions Character vector, condition/task names to compare
#' @param subjects Character vector, subjects to include (NULL for all)
#' @param summary_type Character, "mean" (default) or "rom" for analysis type
#' @param prior_scale Numeric, prior scale parameter (default: 0.5)
#' @param iterations Integer, MCMC iterations (default: 10000)
#' @return List containing Bayesian ANOVA results
#'
#' @export
bayes_anova_biomech <- function(loco_data, feature, conditions, subjects = NULL,
                               summary_type = "mean", prior_scale = 0.5, 
                               iterations = 10000) {
  
  # Validate inputs
  if (!is(loco_data, "LocomotionData")) {
    stop("Input must be a LocomotionData object")
  }
  
  if (length(conditions) < 2) {
    stop("At least 2 conditions required for ANOVA")
  }
  
  if (!feature %in% get_features(loco_data)) {
    stop(paste("Feature", feature, "not found in data"))
  }
  
  # Get subjects
  if (is.null(subjects)) {
    subjects <- get_subjects(loco_data)
  }
  
  # Extract data for all conditions
  data_list <- list()
  condition_labels <- c()
  
  for (condition in conditions) {
    tryCatch({
      if (summary_type == "mean") {
        cond_data_list <- lapply(subjects, function(s) {
          patterns <- get_mean_patterns(loco_data, s, condition, feature)
          if (!is.null(patterns) && length(patterns) > 0) {
            return(mean(patterns[[feature]], na.rm = TRUE))
          }
          return(NA)
        })
      } else if (summary_type == "rom") {
        cond_data_list <- lapply(subjects, function(s) {
          rom_result <- calculate_rom(loco_data, s, condition, feature, by_cycle = FALSE)
          if (!is.null(rom_result) && feature %in% names(rom_result)) {
            return(rom_result[[feature]])
          }
          return(NA)
        })
      } else {
        stop("summary_type must be 'mean' or 'rom'")
      }
      
      cond_data <- unlist(cond_data_list)
      cond_data <- cond_data[!is.na(cond_data)]
      
      if (length(cond_data) > 0) {
        data_list <- c(data_list, list(cond_data))
        condition_labels <- c(condition_labels, rep(condition, length(cond_data)))
      }
      
    }, error = function(e) {
      warning(paste("Error extracting data for condition", condition, ":", e$message))
    })
  }
  
  if (length(data_list) == 0) {
    stop("No valid data found for any conditions")
  }
  
  # Create data frame for analysis
  all_data <- unlist(data_list)
  all_conditions <- factor(condition_labels)
  
  analysis_df <- data.frame(
    value = all_data,
    condition = all_conditions
  )
  
  # Perform Bayesian ANOVA
  tryCatch({
    bf_result <- anovaBF(value ~ condition, data = analysis_df, 
                        rscaleFixed = prior_scale, iterations = iterations)
    
    # Extract Bayes factor (comparing model with condition effect to null)
    bayes_factor <- extractBF(bf_result)$bf[1]
    
    # Interpret Bayes factor
    interpretation <- interpret_bayes_factor(bayes_factor)
    
    # Calculate descriptive statistics by condition
    descriptives <- aggregate(value ~ condition, data = analysis_df, 
                             function(x) c(mean = mean(x), sd = sd(x), n = length(x)))
    
    # Sample from posterior
    posterior_samples <- posterior(bf_result, iterations = iterations)
    
    # Calculate posterior summaries
    if (requireNamespace("coda", quietly = TRUE)) {
      posterior_summary <- summary(posterior_samples)
      hpd_intervals <- coda::HPDinterval(posterior_samples)
    } else {
      posterior_summary <- summary(posterior_samples)
      hpd_intervals <- NULL
    }
    
    # Compile results
    results <- list(
      feature = feature,
      conditions = conditions,
      summary_type = summary_type,
      descriptives = descriptives,
      sample_sizes = table(all_conditions),
      bayes_factor = bayes_factor,
      log_bayes_factor = log(bayes_factor),
      interpretation = interpretation,
      bf_object = bf_result,
      posterior_samples = posterior_samples,
      posterior_summary = posterior_summary,
      credible_intervals = hpd_intervals,
      prior_info = list(
        prior_type = "JZS",
        prior_scale = prior_scale
      ),
      analysis_info = list(
        iterations = iterations,
        subjects_analyzed = subjects,
        total_observations = nrow(analysis_df),
        timestamp = Sys.time()
      )
    )
    
    return(results)
    
  }, error = function(e) {
    stop(paste("Bayesian ANOVA failed:", e$message))
  })
}

#' Bayesian Correlation Analysis
#'
#' Performs Bayesian correlation analysis between biomechanical features
#'
#' @param loco_data LocomotionData object
#' @param feature1 Character, first biomechanical feature
#' @param feature2 Character, second biomechanical feature
#' @param condition Character, condition/task name for analysis
#' @param subjects Character vector, subjects to include (NULL for all)
#' @param summary_type Character, "mean" (default) or "rom" for analysis type
#' @param prior_scale Numeric, prior scale parameter (default: sqrt(2)/2)
#' @param iterations Integer, MCMC iterations (default: 10000)
#' @return List containing Bayesian correlation results
#'
#' @export
bayes_correlation_biomech <- function(loco_data, feature1, feature2, condition, 
                                     subjects = NULL, summary_type = "mean",
                                     prior_scale = sqrt(2)/2, iterations = 10000) {
  
  # Validate inputs
  if (!is(loco_data, "LocomotionData")) {
    stop("Input must be a LocomotionData object")
  }
  
  features <- get_features(loco_data)
  if (!feature1 %in% features) {
    stop(paste("Feature", feature1, "not found in data"))
  }
  if (!feature2 %in% features) {
    stop(paste("Feature", feature2, "not found in data"))
  }
  
  # Get subjects
  if (is.null(subjects)) {
    subjects <- get_subjects(loco_data)
  }
  
  # Extract data for both features
  data1_list <- list()
  data2_list <- list()
  
  for (subject in subjects) {
    tryCatch({
      if (summary_type == "mean") {
        patterns1 <- get_mean_patterns(loco_data, subject, condition, feature1)
        patterns2 <- get_mean_patterns(loco_data, subject, condition, feature2)
        
        if (!is.null(patterns1) && !is.null(patterns2) && 
            length(patterns1) > 0 && length(patterns2) > 0) {
          val1 <- mean(patterns1[[feature1]], na.rm = TRUE)
          val2 <- mean(patterns2[[feature2]], na.rm = TRUE)
          
          if (!is.na(val1) && !is.na(val2)) {
            data1_list <- c(data1_list, val1)
            data2_list <- c(data2_list, val2)
          }
        }
      } else if (summary_type == "rom") {
        rom1 <- calculate_rom(loco_data, subject, condition, feature1, by_cycle = FALSE)
        rom2 <- calculate_rom(loco_data, subject, condition, feature2, by_cycle = FALSE)
        
        if (!is.null(rom1) && !is.null(rom2) && 
            feature1 %in% names(rom1) && feature2 %in% names(rom2)) {
          val1 <- rom1[[feature1]]
          val2 <- rom2[[feature2]]
          
          if (!is.na(val1) && !is.na(val2)) {
            data1_list <- c(data1_list, val1)
            data2_list <- c(data2_list, val2)
          }
        }
      }
    }, error = function(e) {
      warning(paste("Error extracting data for subject", subject, ":", e$message))
    })
  }
  
  # Convert to vectors
  data1 <- unlist(data1_list)
  data2 <- unlist(data2_list)
  
  if (length(data1) < 3 || length(data2) < 3) {
    stop("Insufficient data for correlation analysis (need at least 3 pairs)")
  }
  
  # Perform Bayesian correlation
  tryCatch({
    bf_result <- correlationBF(data1, data2, rscale = prior_scale, iterations = iterations)
    
    # Extract Bayes factor
    bayes_factor <- extractBF(bf_result)$bf[1]
    
    # Interpret Bayes factor
    interpretation <- interpret_bayes_factor(bayes_factor)
    
    # Calculate classical correlation for comparison
    classical_cor <- cor(data1, data2)
    classical_test <- cor.test(data1, data2)
    
    # Sample from posterior
    posterior_samples <- posterior(bf_result, iterations = iterations)
    
    # Calculate posterior summaries
    if (requireNamespace("coda", quietly = TRUE)) {
      posterior_summary <- summary(posterior_samples)
      hpd_intervals <- coda::HPDinterval(posterior_samples)
    } else {
      posterior_summary <- summary(posterior_samples)
      hpd_intervals <- NULL
    }
    
    # Compile results
    results <- list(
      feature1 = feature1,
      feature2 = feature2,
      condition = condition,
      summary_type = summary_type,
      sample_size = length(data1),
      classical_correlation = classical_cor,
      classical_p_value = classical_test$p.value,
      classical_ci = classical_test$conf.int,
      bayes_factor = bayes_factor,
      log_bayes_factor = log(bayes_factor),
      interpretation = interpretation,
      bf_object = bf_result,
      posterior_samples = posterior_samples,
      posterior_summary = posterior_summary,
      credible_intervals = hpd_intervals,
      prior_info = list(
        prior_type = "Beta",
        prior_scale = prior_scale
      ),
      analysis_info = list(
        iterations = iterations,
        subjects_analyzed = subjects,
        timestamp = Sys.time()
      )
    )
    
    return(results)
    
  }, error = function(e) {
    stop(paste("Bayesian correlation analysis failed:", e$message))
  })
}

#' Compare Bayesian Models
#'
#' Compares multiple Bayesian models using Bayes factors
#'
#' @param model_list List of Bayesian model results
#' @param model_names Character vector of model names (optional)
#' @return List containing model comparison results
#'
#' @export
compare_bayes_models <- function(model_list, model_names = NULL) {
  
  if (is.null(model_names)) {
    model_names <- paste("Model", 1:length(model_list))
  }
  
  if (length(model_names) != length(model_list)) {
    stop("Length of model_names must match length of model_list")
  }
  
  # Extract Bayes factors
  bayes_factors <- sapply(model_list, function(x) x$bayes_factor)
  log_bayes_factors <- sapply(model_list, function(x) x$log_bayes_factor)
  
  # Calculate relative Bayes factors (compared to best model)
  max_log_bf <- max(log_bayes_factors)
  relative_log_bf <- log_bayes_factors - max_log_bf
  relative_bf <- exp(relative_log_bf)
  
  # Calculate posterior model probabilities (assuming equal priors)
  total_relative_bf <- sum(relative_bf)
  posterior_probs <- relative_bf / total_relative_bf
  
  # Create comparison data frame
  comparison_df <- data.frame(
    model = model_names,
    bayes_factor = bayes_factors,
    log_bayes_factor = log_bayes_factors,
    relative_bayes_factor = relative_bf,
    posterior_probability = posterior_probs,
    interpretation = sapply(bayes_factors, interpret_bayes_factor),
    stringsAsFactors = FALSE
  )
  
  # Sort by posterior probability
  comparison_df <- comparison_df[order(comparison_df$posterior_probability, decreasing = TRUE), ]
  
  # Add ranking
  comparison_df$rank <- 1:nrow(comparison_df)
  
  # Summary information
  best_model <- comparison_df$model[1]
  best_prob <- comparison_df$posterior_probability[1]
  
  results <- list(
    comparison_table = comparison_df,
    best_model = best_model,
    best_model_probability = best_prob,
    model_evidence_summary = paste(
      "Best model:", best_model,
      "with posterior probability:", round(best_prob, 3)
    ),
    analysis_timestamp = Sys.time()
  )
  
  return(results)
}

#' Interpret Bayes Factor
#'
#' Provides interpretation of Bayes factor values
#'
#' @param bf Numeric, Bayes factor value
#' @return Character, interpretation string
#'
#' @export
interpret_bayes_factor <- function(bf) {
  
  if (is.na(bf) || !is.numeric(bf)) {
    return("Invalid Bayes factor")
  }
  
  # Use Jeffreys' scale for interpretation
  if (bf >= 100) {
    return("Extreme evidence for alternative")
  } else if (bf >= 30) {
    return("Very strong evidence for alternative")
  } else if (bf >= 10) {
    return("Strong evidence for alternative")
  } else if (bf >= 3) {
    return("Moderate evidence for alternative")
  } else if (bf >= 1) {
    return("Weak evidence for alternative")
  } else if (bf >= 1/3) {
    return("Weak evidence for null")
  } else if (bf >= 1/10) {
    return("Moderate evidence for null")
  } else if (bf >= 1/30) {
    return("Strong evidence for null")
  } else if (bf >= 1/100) {
    return("Very strong evidence for null")
  } else {
    return("Extreme evidence for null")
  }
}

#' Bayesian Model Averaging
#'
#' Performs Bayesian model averaging across multiple models
#'
#' @param model_list List of Bayesian model results
#' @param parameter Character, parameter name to average (e.g., "mu", "delta")
#' @return List with model-averaged results
#'
#' @export
bayes_model_averaging <- function(model_list, parameter = "mu") {
  
  # Calculate model weights (posterior probabilities)
  comparison <- compare_bayes_models(model_list)
  weights <- comparison$comparison_table$posterior_probability
  
  # Extract parameter samples from each model
  parameter_samples_list <- list()
  
  for (i in seq_along(model_list)) {
    model <- model_list[[i]]
    if (!is.null(model$posterior_samples)) {
      samples <- model$posterior_samples
      if (parameter %in% colnames(samples)) {
        parameter_samples_list[[i]] <- samples[, parameter]
      } else {
        warning(paste("Parameter", parameter, "not found in model", i))
        parameter_samples_list[[i]] <- NULL
      }
    } else {
      warning(paste("No posterior samples found in model", i))
      parameter_samples_list[[i]] <- NULL
    }
  }
  
  # Remove NULL entries
  valid_indices <- !sapply(parameter_samples_list, is.null)
  parameter_samples_list <- parameter_samples_list[valid_indices]
  weights <- weights[valid_indices]
  
  if (length(parameter_samples_list) == 0) {
    stop("No valid posterior samples found for specified parameter")
  }
  
  # Renormalize weights
  weights <- weights / sum(weights)
  
  # Combine samples with weights
  all_samples <- c()
  sample_weights <- c()
  
  for (i in seq_along(parameter_samples_list)) {
    samples <- parameter_samples_list[[i]]
    n_samples <- length(samples)
    
    all_samples <- c(all_samples, samples)
    sample_weights <- c(sample_weights, rep(weights[i] / n_samples, n_samples))
  }
  
  # Calculate weighted statistics
  weighted_mean <- sum(all_samples * sample_weights) / sum(sample_weights)
  weighted_var <- sum(sample_weights * (all_samples - weighted_mean)^2) / sum(sample_weights)
  weighted_sd <- sqrt(weighted_var)
  
  # Calculate credible intervals using weighted quantiles
  sorted_indices <- order(all_samples)
  sorted_samples <- all_samples[sorted_indices]
  sorted_weights <- sample_weights[sorted_indices]
  cum_weights <- cumsum(sorted_weights) / sum(sorted_weights)
  
  ci_lower <- sorted_samples[which.min(abs(cum_weights - 0.025))]
  ci_upper <- sorted_samples[which.min(abs(cum_weights - 0.975))]
  
  results <- list(
    parameter = parameter,
    model_weights = weights,
    weighted_mean = weighted_mean,
    weighted_sd = weighted_sd,
    credible_interval_95 = c(ci_lower, ci_upper),
    all_samples = all_samples,
    sample_weights = sample_weights,
    n_models = length(parameter_samples_list),
    total_samples = length(all_samples),
    analysis_timestamp = Sys.time()
  )
  
  return(results)
}

#' Bayesian Robustness Check
#'
#' Performs sensitivity analysis across different prior specifications
#'
#' @param analysis_function Function to run Bayesian analysis
#' @param prior_scales Numeric vector, different prior scale values to test
#' @param ... Additional arguments passed to analysis_function
#' @return List with robustness analysis results
#'
#' @export
bayes_robustness_check <- function(analysis_function, prior_scales = c(0.1, 0.5, 1.0, sqrt(2)/2, 2.0), ...) {
  
  results_list <- list()
  bf_values <- numeric(length(prior_scales))
  
  for (i in seq_along(prior_scales)) {
    tryCatch({
      result <- analysis_function(prior_scale = prior_scales[i], ...)
      results_list[[i]] <- result
      bf_values[i] <- result$bayes_factor
    }, error = function(e) {
      warning(paste("Analysis failed for prior scale", prior_scales[i], ":", e$message))
      results_list[[i]] <- NULL
      bf_values[i] <- NA
    })
  }
  
  # Create robustness summary
  robustness_df <- data.frame(
    prior_scale = prior_scales,
    bayes_factor = bf_values,
    log_bayes_factor = log(bf_values),
    interpretation = sapply(bf_values, function(x) if (!is.na(x)) interpret_bayes_factor(x) else "Failed"),
    stringsAsFactors = FALSE
  )
  
  # Calculate robustness metrics
  valid_bf <- bf_values[!is.na(bf_values)]
  if (length(valid_bf) > 1) {
    bf_range <- range(valid_bf)
    bf_cv <- sd(valid_bf) / mean(valid_bf)
    consistent_direction <- all(valid_bf > 1) || all(valid_bf < 1)
  } else {
    bf_range <- c(NA, NA)
    bf_cv <- NA
    consistent_direction <- NA
  }
  
  robustness_summary <- list(
    robustness_table = robustness_df,
    bayes_factor_range = bf_range,
    coefficient_of_variation = bf_cv,
    consistent_direction = consistent_direction,
    n_successful_analyses = sum(!is.na(bf_values)),
    n_total_analyses = length(prior_scales),
    detailed_results = results_list,
    analysis_timestamp = Sys.time()
  )
  
  return(robustness_summary)
}