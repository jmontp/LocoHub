#' Mixed-Effects Models for Biomechanical Data Analysis
#'
#' Created: 2025-06-19 with user permission
#' Purpose: Advanced mixed-effects modeling capabilities for hierarchical biomechanical data
#'
#' Intent:
#' This module provides comprehensive mixed-effects modeling functionality specifically designed 
#' for biomechanical gait analysis using R's lme4 package. It integrates with the LocomotionData 
#' S4 class to handle hierarchical data structures and provides pre-built templates for common 
#' biomechanical research questions.
#'
#' Key Features:
#' - Native lme4 integration for robust mixed-effects modeling
#' - Biomechanics-specific model templates and workflows
#' - Automated model comparison and selection
#' - Random effects structure recommendations
#' - Model diagnostics and assumption checking
#' - Effect size calculations and interpretation tools

# Required packages
if (!requireNamespace("lme4", quietly = TRUE)) {
  stop("Package 'lme4' needed for mixed-effects modeling. Please install it.")
}

if (!requireNamespace("car", quietly = TRUE)) {
  warning("Package 'car' recommended for advanced diagnostics. Install with: install.packages('car')")
}

if (!requireNamespace("performance", quietly = TRUE)) {
  warning("Package 'performance' recommended for model performance metrics. Install with: install.packages('performance')")
}

library(lme4)
library(stats)

#' Prepare Data for Mixed-Effects Modeling
#'
#' Converts LocomotionData into long format suitable for mixed-effects modeling
#'
#' @param loco_data LocomotionData object
#' @param subjects Character vector of subjects to include (NULL for all)
#' @param tasks Character vector of tasks to include (NULL for all)
#' @param features Character vector of features to include (NULL for all)
#' @param include_phase Logical, whether to include phase as predictor
#' @return data.frame in long format for mixed-effects modeling
#'
#' @export
prepare_mixed_effects_data <- function(loco_data, subjects = NULL, tasks = NULL, 
                                     features = NULL, include_phase = TRUE) {
  
  # Validate input
  if (!is(loco_data, "LocomotionData")) {
    stop("Input must be a LocomotionData object")
  }
  
  # Get subjects and tasks
  if (is.null(subjects)) {
    subjects <- get_subjects(loco_data)
  }
  if (is.null(tasks)) {
    tasks <- get_tasks(loco_data)
  }
  if (is.null(features)) {
    features <- get_features(loco_data)
  }
  
  # Prepare data list
  data_list <- list()
  row_counter <- 1
  
  for (subject in subjects) {
    for (task in tasks) {
      # Get cycles data
      cycles_result <- get_cycles(loco_data, subject, task, features)
      
      if (is.null(cycles_result$data_3d)) {
        next
      }
      
      data_3d <- cycles_result$data_3d
      feature_names <- cycles_result$features
      
      # Get dimensions
      dims <- dim(data_3d)
      n_cycles <- dims[1]
      n_phases <- dims[2]
      n_features <- dims[3]
      
      # Create long format
      for (cycle in 1:n_cycles) {
        for (phase in 1:n_phases) {
          # Base row data
          row_data <- data.frame(
            subject = factor(subject),
            task = factor(task),
            cycle = cycle,
            phase = if (include_phase) phase else NA,
            phase_percent = if (include_phase) ((phase - 1) / n_phases) * 100 else NA,
            stringsAsFactors = FALSE
          )
          
          # Add feature values
          for (feat_idx in 1:n_features) {
            feature_name <- feature_names[feat_idx]
            row_data[[feature_name]] <- data_3d[cycle, phase, feat_idx]
          }
          
          data_list[[row_counter]] <- row_data
          row_counter <- row_counter + 1
        }
      }
    }
  }
  
  # Combine all data
  if (length(data_list) == 0) {
    stop("No data found for specified subjects and tasks")
  }
  
  df <- do.call(rbind, data_list)
  
  # Add derived variables for modeling
  df$subject_factor <- as.factor(df$subject)
  df$task_factor <- as.factor(df$task)
  df$cycle_factor <- as.factor(df$cycle)
  
  # Add phase-based variables if requested
  if (include_phase) {
    df$phase_sin <- sin(2 * pi * df$phase_percent / 100)
    df$phase_cos <- cos(2 * pi * df$phase_percent / 100)
    df$phase_factor <- as.factor(df$phase)
  }
  
  return(df)
}

#' Fit Basic Hierarchical Model
#'
#' Fits a mixed-effects model with specified predictors and random effects
#'
#' @param outcome Character, outcome variable name
#' @param predictors Character vector, fixed effects predictors
#' @param random_effects Character, random effects specification in lme4 format
#' @param data data.frame, modeling data
#' @param method Character, "REML" (default) or "ML"
#' @return List containing model fit and summary information
#'
#' @export
fit_hierarchical_model <- function(outcome, predictors, random_effects = "(1|subject)",
                                 data, method = "REML") {
  
  # Validate inputs
  if (!outcome %in% names(data)) {
    stop(paste("Outcome variable", outcome, "not found in data"))
  }
  
  missing_predictors <- predictors[!predictors %in% names(data)]
  if (length(missing_predictors) > 0) {
    stop(paste("Predictors not found in data:", paste(missing_predictors, collapse = ", ")))
  }
  
  # Create formula
  fixed_effects <- paste(predictors, collapse = " + ")
  formula_str <- paste(outcome, "~", fixed_effects, "+", random_effects)
  formula_obj <- as.formula(formula_str)
  
  # Fit model
  tryCatch({
    model <- lmer(formula_obj, data = data, REML = (method == "REML"))
    
    # Extract summary information
    model_summary <- summary(model)
    
    # Check convergence
    converged <- model@optinfo$conv$opt == 0
    
    # Calculate information criteria
    aic_val <- AIC(model)
    bic_val <- BIC(model)
    loglik_val <- as.numeric(logLik(model))
    
    # Return comprehensive results
    results <- list(
      model = model,
      summary = model_summary,
      formula = formula_str,
      outcome = outcome,
      predictors = predictors,
      random_effects = random_effects,
      method = method,
      converged = converged,
      aic = aic_val,
      bic = bic_val,
      loglik = loglik_val,
      n_obs = nrow(data),
      n_groups = ngrps(model)
    )
    
    return(results)
    
  }, error = function(e) {
    stop(paste("Model fitting failed:", e$message))
  })
}

#' Gait Analysis Model Template
#'
#' Fits a standard gait analysis model comparing tasks across the gait cycle
#'
#' @param loco_data LocomotionData object
#' @param outcome Character, joint angle, moment, or other biomechanical outcome
#' @param tasks Character vector, tasks to compare (NULL for all)
#' @param include_phase Logical, whether to model phase-dependent effects
#' @return List containing model results
#'
#' @export
fit_gait_analysis_model <- function(loco_data, outcome, tasks = NULL, include_phase = TRUE) {
  
  # Prepare data
  data <- prepare_mixed_effects_data(loco_data, tasks = tasks, 
                                   features = outcome, include_phase = include_phase)
  
  # Build predictors
  predictors <- "task_factor"
  if (include_phase) {
    predictors <- c(predictors, "phase_sin", "phase_cos", 
                   "task_factor:phase_sin", "task_factor:phase_cos")
  }
  
  # Random effects: subject-specific intercepts and phase effects
  if (include_phase) {
    random_effects <- "(phase_sin + phase_cos | subject)"
  } else {
    random_effects <- "(1 | subject)"
  }
  
  # Fit model
  results <- fit_hierarchical_model(
    outcome = outcome,
    predictors = predictors,
    random_effects = random_effects,
    data = data
  )
  
  # Add model type information
  results$model_type <- "gait_analysis"
  results$data_summary <- list(
    n_subjects = length(unique(data$subject)),
    n_tasks = length(unique(data$task)),
    n_cycles_total = sum(!is.na(data$cycle))
  )
  
  return(results)
}

#' Intervention Effect Model Template
#'
#' Models intervention effects with pre/post comparison
#'
#' @param loco_data LocomotionData object
#' @param outcome Character, biomechanical outcome variable
#' @param pre_tasks Character vector, pre-intervention task names
#' @param post_tasks Character vector, post-intervention task names
#' @return List containing model results
#'
#' @export
fit_intervention_model <- function(loco_data, outcome, pre_tasks, post_tasks) {
  
  # Prepare data with intervention coding
  all_tasks <- c(pre_tasks, post_tasks)
  data <- prepare_mixed_effects_data(loco_data, tasks = all_tasks, 
                                   features = outcome, include_phase = TRUE)
  
  # Add intervention coding
  data$intervention <- ifelse(data$task %in% post_tasks, "post", "pre")
  data$intervention <- factor(data$intervention, levels = c("pre", "post"))
  
  # Model with intervention, phase, and their interaction
  predictors <- c("intervention", "phase_sin", "phase_cos", 
                 "intervention:phase_sin", "intervention:phase_cos")
  
  # Random effects: subject-specific intervention and phase effects
  random_effects <- "(intervention + phase_sin + phase_cos | subject)"
  
  # Fit model
  results <- fit_hierarchical_model(
    outcome = outcome,
    predictors = predictors,
    random_effects = random_effects,
    data = data
  )
  
  # Add model type information
  results$model_type <- "intervention_effect"
  results$intervention_info <- list(
    pre_tasks = pre_tasks,
    post_tasks = post_tasks,
    n_pre_obs = sum(data$intervention == "pre"),
    n_post_obs = sum(data$intervention == "post")
  )
  
  return(results)
}

#' Subject Group Comparison Model Template
#'
#' Compares different subject groups (e.g., healthy vs. pathological)
#'
#' @param loco_data LocomotionData object
#' @param outcome Character, biomechanical outcome variable
#' @param group_info Named vector mapping subject IDs to group labels
#' @return List containing model results
#'
#' @export
fit_group_comparison_model <- function(loco_data, outcome, group_info) {
  
  # Prepare data for subjects with group information
  subjects_with_groups <- names(group_info)
  data <- prepare_mixed_effects_data(loco_data, subjects = subjects_with_groups,
                                   features = outcome, include_phase = TRUE)
  
  # Add group information
  data$group <- factor(group_info[as.character(data$subject)])
  
  # Model with group, phase, and their interaction
  predictors <- c("group", "phase_sin", "phase_cos", 
                 "group:phase_sin", "group:phase_cos")
  
  # Random effects: subject-specific intercepts and phase effects
  random_effects <- "(phase_sin + phase_cos | subject)"
  
  # Fit model
  results <- fit_hierarchical_model(
    outcome = outcome,
    predictors = predictors,
    random_effects = random_effects,
    data = data
  )
  
  # Add model type information
  results$model_type <- "group_comparison"
  results$group_info <- list(
    groups = levels(data$group),
    group_counts = table(data$group),
    subjects_per_group = table(group_info)
  )
  
  return(results)
}

#' Compare Multiple Models
#'
#' Compares multiple fitted models using information criteria
#'
#' @param model_list List of fitted model results
#' @param model_names Character vector of model names (optional)
#' @return data.frame with model comparison metrics
#'
#' @export
compare_models <- function(model_list, model_names = NULL) {
  
  if (is.null(model_names)) {
    model_names <- paste("Model", 1:length(model_list))
  }
  
  if (length(model_names) != length(model_list)) {
    stop("Length of model_names must match length of model_list")
  }
  
  # Extract comparison metrics
  comparison_data <- data.frame(
    model = model_names,
    formula = sapply(model_list, function(x) x$formula),
    aic = sapply(model_list, function(x) x$aic),
    bic = sapply(model_list, function(x) x$bic),
    loglik = sapply(model_list, function(x) x$loglik),
    converged = sapply(model_list, function(x) x$converged),
    n_obs = sapply(model_list, function(x) x$n_obs),
    stringsAsFactors = FALSE
  )
  
  # Add ranking columns
  comparison_data$aic_rank <- rank(comparison_data$aic)
  comparison_data$bic_rank <- rank(comparison_data$bic)
  comparison_data$delta_aic <- comparison_data$aic - min(comparison_data$aic)
  comparison_data$delta_bic <- comparison_data$bic - min(comparison_data$bic)
  
  # Sort by AIC
  comparison_data <- comparison_data[order(comparison_data$aic), ]
  
  return(comparison_data)
}

#' Likelihood Ratio Test
#'
#' Performs likelihood ratio test between nested models
#'
#' @param model1_result Result from simpler model
#' @param model2_result Result from more complex model
#' @return List with test results
#'
#' @export
likelihood_ratio_test <- function(model1_result, model2_result) {
  
  model1 <- model1_result$model
  model2 <- model2_result$model
  
  # Perform LRT
  lrt_result <- anova(model1, model2)
  
  # Extract results
  chi_sq <- lrt_result$Chisq[2]
  df <- lrt_result$Df[2]
  p_value <- lrt_result$`Pr(>Chisq)`[2]
  
  results <- list(
    model1_name = model1_result$formula,
    model2_name = model2_result$formula,
    chi_square = chi_sq,
    df = df,
    p_value = p_value,
    significant = p_value < 0.05,
    interpretation = paste(
      "Model 2 is", 
      ifelse(p_value < 0.05, "significantly", "not significantly"),
      "better than Model 1"
    )
  )
  
  return(results)
}

#' Recommend Random Effects Structure
#'
#' Provides recommendations for random effects structure based on data characteristics
#'
#' @param data data.frame, prepared modeling data
#' @param outcome Character, outcome variable name
#' @param predictors Character vector, fixed effects predictors
#' @return List with recommendations and justifications
#'
#' @export
recommend_random_effects <- function(data, outcome, predictors) {
  
  # Data characteristics analysis
  n_subjects <- length(unique(data$subject))
  obs_per_subject <- table(data$subject)
  min_obs <- min(obs_per_subject)
  mean_obs <- mean(obs_per_subject)
  max_obs <- max(obs_per_subject)
  
  has_tasks <- any(grepl("task", predictors))
  has_phase <- any(grepl("phase", predictors))
  
  # Create recommendations list
  recommendations <- list(
    data_summary = list(
      n_subjects = n_subjects,
      mean_obs_per_subject = mean_obs,
      min_obs_per_subject = min_obs,
      max_obs_per_subject = max_obs
    ),
    recommendations = list()
  )
  
  # Basic recommendation: random intercept
  recommendations$recommendations[[1]] <- list(
    structure = "(1 | subject)",
    description = "Random intercept for subjects",
    rationale = "Accounts for baseline differences between subjects",
    complexity = 1,
    min_obs_required = 5
  )
  
  # If sufficient data, recommend random slopes
  if (min_obs >= 10) {
    if (has_phase) {
      recommendations$recommendations[[length(recommendations$recommendations) + 1]] <- list(
        structure = "(phase_sin + phase_cos | subject)",
        description = "Random phase effects for subjects",
        rationale = "Accounts for individual differences in gait patterns across the cycle",
        complexity = 3,
        min_obs_required = 15
      )
    }
    
    if (has_tasks) {
      # Check if subjects have multiple tasks
      subject_task_counts <- aggregate(task ~ subject, data, function(x) length(unique(x)))
      if (mean(subject_task_counts$task) >= 2) {
        recommendations$recommendations[[length(recommendations$recommendations) + 1]] <- list(
          structure = "(1 + task_factor | subject)",
          description = "Random intercept and task effects for subjects",
          rationale = "Accounts for individual responses to different tasks",
          complexity = 2,
          min_obs_required = 10
        )
      }
    }
  }
  
  # Full model if very rich data
  if (min_obs >= 30 && has_phase && has_tasks) {
    recommendations$recommendations[[length(recommendations$recommendations) + 1]] <- list(
      structure = "(task_factor + phase_sin + phase_cos | subject)",
      description = "Full random effects model",
      rationale = "Comprehensive individual differences modeling",
      complexity = 4,
      min_obs_required = 40
    )
  }
  
  return(recommendations)
}

#' Test Random Effects Structures
#'
#' Tests multiple random effects structures and compares them
#'
#' @param outcome Character, outcome variable
#' @param predictors Character vector, fixed effects predictors
#' @param structures Character vector, random effects structures to test
#' @param data data.frame, modeling data
#' @return data.frame with comparison results
#'
#' @export
test_random_effects_structures <- function(outcome, predictors, structures, data) {
  
  results <- data.frame(
    structure = structures,
    aic = NA,
    bic = NA,
    loglik = NA,
    converged = FALSE,
    error = "",
    stringsAsFactors = FALSE
  )
  
  for (i in seq_along(structures)) {
    tryCatch({
      model_result <- fit_hierarchical_model(
        outcome = outcome,
        predictors = predictors,
        random_effects = structures[i],
        data = data
      )
      
      results$aic[i] <- model_result$aic
      results$bic[i] <- model_result$bic
      results$loglik[i] <- model_result$loglik
      results$converged[i] <- model_result$converged
      
    }, error = function(e) {
      results$error[i] <<- as.character(e)
    })
  }
  
  # Add rankings for converged models
  converged_idx <- which(results$converged)
  if (length(converged_idx) > 0) {
    results$aic_rank[converged_idx] <- rank(results$aic[converged_idx])
    results$bic_rank[converged_idx] <- rank(results$bic[converged_idx])
  }
  
  # Sort by AIC
  results <- results[order(results$aic, na.last = TRUE), ]
  
  return(results)
}

#' Model Diagnostics
#'
#' Runs comprehensive diagnostics on fitted model
#'
#' @param model_result List, result from fitted model
#' @return List with diagnostic information
#'
#' @export
run_model_diagnostics <- function(model_result) {
  
  model <- model_result$model
  
  diagnostics <- list(
    model_info = list(
      formula = model_result$formula,
      converged = model_result$converged,
      n_obs = model_result$n_obs,
      n_groups = model_result$n_groups
    ),
    warnings = character()
  )
  
  # Residual analysis
  tryCatch({
    residuals_val <- residuals(model)
    fitted_val <- fitted(model)
    
    diagnostics$residuals <- list(
      mean = mean(residuals_val),
      sd = sd(residuals_val),
      min = min(residuals_val),
      max = max(residuals_val),
      range = max(residuals_val) - min(residuals_val)
    )
    
    # Check for patterns in residuals
    if (abs(diagnostics$residuals$mean) > 0.01) {
      diagnostics$warnings <- c(diagnostics$warnings, "Residuals do not center around zero")
    }
    
  }, error = function(e) {
    diagnostics$warnings <- c(diagnostics$warnings, paste("Residual analysis failed:", e$message))
  })
  
  # Random effects diagnostics
  tryCatch({
    ranef_val <- ranef(model)
    diagnostics$random_effects_available <- TRUE
    diagnostics$random_effects_summary <- summary(ranef_val)
    
  }, error = function(e) {
    diagnostics$random_effects_available <- FALSE
    diagnostics$warnings <- c(diagnostics$warnings, "Could not extract random effects")
  })
  
  # Fit statistics
  diagnostics$fit_statistics <- list(
    aic = model_result$aic,
    bic = model_result$bic,
    loglik = model_result$loglik
  )
  
  return(diagnostics)
}

#' Check Model Assumptions
#'
#' Checks key assumptions of mixed-effects models
#'
#' @param model_result List, result from fitted model
#' @return List with assumption checking results
#'
#' @export
check_model_assumptions <- function(model_result) {
  
  diagnostics <- run_model_diagnostics(model_result)
  
  assumptions <- list(
    linearity = "Unknown",
    independence = "Unknown",
    homoscedasticity = "Unknown",
    normality_residuals = "Unknown",
    normality_random_effects = "Unknown",
    overall_assessment = "Unknown"
  )
  
  # Basic checks based on available diagnostics
  if (!is.null(diagnostics$residuals)) {
    # Rough check for extreme residuals
    res_sd <- diagnostics$residuals$sd
    res_range <- diagnostics$residuals$range
    
    if (res_range > 6 * res_sd) {
      assumptions$homoscedasticity <- "Potential issues - large residual range"
    } else {
      assumptions$homoscedasticity <- "Appears satisfactory"
    }
  }
  
  # Check convergence as indicator of model appropriateness
  if (diagnostics$model_info$converged) {
    assumptions$overall_assessment <- "Model converged successfully"
  } else {
    assumptions$overall_assessment <- "Model convergence issues detected"
  }
  
  return(assumptions)
}

#' Calculate Effect Sizes
#'
#' Calculates effect sizes for mixed-effects model results
#'
#' @param model_result List, result from fitted model
#' @return List with effect size calculations
#'
#' @export
calculate_effect_sizes <- function(model_result) {
  
  model <- model_result$model
  
  tryCatch({
    # Extract fixed effects
    fixed_effects <- fixef(model)
    
    # Extract variance components
    var_comp <- VarCorr(model)
    
    # Calculate R-squared (conditional and marginal)
    # Note: This is a simplified calculation
    total_var <- sum(sapply(var_comp, function(x) sum(diag(as.matrix(x))))) + attr(var_comp, "sc")^2
    
    effect_sizes <- list(
      fixed_effects = fixed_effects,
      variance_components = var_comp,
      total_variance = total_var,
      residual_variance = attr(var_comp, "sc")^2
    )
    
    # Calculate pseudo R-squared if possible
    if (requireNamespace("performance", quietly = TRUE)) {
      r_squared <- performance::r2(model)
      effect_sizes$r_squared <- r_squared
    }
    
    return(effect_sizes)
    
  }, error = function(e) {
    warning(paste("Effect size calculation failed:", e$message))
    return(list(error = e$message))
  })
}