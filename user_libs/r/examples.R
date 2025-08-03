#' @title LocomotionData R Library Examples
#' @description Comprehensive examples demonstrating the R LocomotionData API
#' 
#' Created: 2025-06-19 with user permission
#' Purpose: Provide real-world usage examples for the R LocomotionData library
#' 
#' Intent: This file demonstrates the complete API functionality of the R LocomotionData
#' library, showing how to perform common biomechanical analysis tasks. Examples include
#' basic gait analysis, data quality assessment, comparative studies, and population-level
#' analyses that match the Python API capabilities.

# Load required libraries
if (!requireNamespace("data.table", quietly = TRUE)) {
  stop("Package 'data.table' is required but not installed. Install with: install.packages('data.table')")
}

if (!requireNamespace("ggplot2", quietly = TRUE)) {
  stop("Package 'ggplot2' is required but not installed. Install with: install.packages('ggplot2')")
}

library(data.table)
library(ggplot2)

#' @title Example 1: Basic Gait Analysis
#' @description Demonstrates basic loading, analysis, and visualization
#' @param data_path character path to parquet file
example_basic_gait_analysis <- function(data_path) {
  cat("=== Example 1: Basic Gait Analysis ===\n")
  
  # Load data
  cat("Loading locomotion data...\n")
  loco <- loadLocomotionData(data_path)
  
  # Show basic information
  cat("\nData overview:\n")
  show(loco)
  
  # Get available subjects and tasks
  subjects <- getSubjects(loco)
  tasks <- getTasks(loco)
  features <- getFeatures(loco)
  
  cat(sprintf("\nAvailable subjects: %s\n", paste(head(subjects, 3), collapse = ", ")))
  cat(sprintf("Available tasks: %s\n", paste(tasks, collapse = ", ")))
  cat(sprintf("Available features: %d total\n", length(features)))
  
  # Analyze specific subject and task
  if (length(subjects) > 0 && length(tasks) > 0) {
    subject <- subjects[1]
    task <- tasks[1]
    
    cat(sprintf("\nAnalyzing %s - %s:\n", subject, task))
    
    # Get 3D cycles data
    cycles_result <- getCycles(loco, subject, task)
    if (!is.null(cycles_result$data_3d)) {
      dims <- dim(cycles_result$data_3d)
      cat(sprintf("3D data shape: %d cycles x %d phases x %d features\n", 
                  dims[1], dims[2], dims[3]))
    }
    
    # Get mean patterns
    mean_patterns <- getMeanPatterns(loco, subject, task)
    cat(sprintf("Mean patterns calculated for %d features\n", length(mean_patterns)))
    
    # Calculate ROM
    rom_data <- calculateROM(loco, subject, task, by_cycle = FALSE)
    cat(sprintf("Range of motion calculated for %d features\n", length(rom_data)))
    
    # Validate cycles
    valid_mask <- validateCycles(loco, subject, task)
    cat(sprintf("Cycle validation: %d/%d cycles valid\n", 
                sum(valid_mask), length(valid_mask)))
    
    # Find outliers
    outliers <- findOutlierCycles(loco, subject, task)
    cat(sprintf("Outlier detection: %d outlier cycles found\n", length(outliers)))
    
    # Create visualization
    if (length(features) > 0) {
      plot_features <- head(features, 3)  # Plot first 3 features
      cat(sprintf("\nCreating phase pattern plot for: %s\n", 
                  paste(plot_features, collapse = ", ")))
      
      p <- plotPhasePatterns(loco, subject, task, plot_features, plot_type = "both")
      print(p)
    }
  }
  
  cat("\n=== Example 1 Complete ===\n\n")
}

#' @title Example 2: Data Quality Assessment
#' @description Demonstrates comprehensive data quality assessment workflows
#' @param data_path character path to parquet file
example_data_quality_assessment <- function(data_path) {
  cat("=== Example 2: Data Quality Assessment ===\n")
  
  # Load data
  loco <- loadLocomotionData(data_path)
  
  # Get validation report
  validation_report <- getValidationReport(loco)
  cat("Variable name validation:\n")
  cat(sprintf("  Standard compliant: %d\n", length(validation_report$standard_compliant)))
  cat(sprintf("  Non-standard: %d\n", length(validation_report$non_standard)))
  
  if (length(validation_report$non_standard) > 0) {
    cat("  Non-standard variables:\n")
    for (var in head(validation_report$non_standard, 3)) {
      cat(sprintf("    - %s\n", var))
    }
  }
  
  # Assess data quality across all subjects and tasks
  subjects <- getSubjects(loco)
  tasks <- getTasks(loco)
  
  quality_summary <- data.frame(
    subject = character(0),
    task = character(0),
    n_cycles = integer(0),
    valid_cycles = integer(0),
    outlier_cycles = integer(0),
    quality_score = numeric(0),
    stringsAsFactors = FALSE
  )
  
  cat("\nAssessing data quality across subjects and tasks...\n")
  for (subject in head(subjects, 5)) {  # Limit to first 5 subjects for demo
    for (task in tasks) {
      cycles_result <- getCycles(loco, subject, task)
      
      if (!is.null(cycles_result$data_3d)) {
        n_cycles <- dim(cycles_result$data_3d)[1]
        valid_mask <- validateCycles(loco, subject, task)
        outliers <- findOutlierCycles(loco, subject, task)
        
        valid_cycles <- sum(valid_mask)
        outlier_cycles <- length(outliers)
        
        # Calculate quality score (0-100)
        quality_score <- 100 * (valid_cycles - outlier_cycles) / n_cycles
        quality_score <- max(0, quality_score)
        
        quality_summary <- rbind(quality_summary, data.frame(
          subject = subject,
          task = task,
          n_cycles = n_cycles,
          valid_cycles = valid_cycles,
          outlier_cycles = outlier_cycles,
          quality_score = quality_score,
          stringsAsFactors = FALSE
        ))
      }
    }
  }
  
  if (nrow(quality_summary) > 0) {
    cat("\nData Quality Summary:\n")
    cat(sprintf("Mean quality score: %.1f%%\n", mean(quality_summary$quality_score)))
    cat(sprintf("Subjects with quality < 80%%: %d\n", 
                sum(quality_summary$quality_score < 80)))
    
    # Show top and bottom quality scores
    quality_summary <- quality_summary[order(quality_summary$quality_score, decreasing = TRUE), ]
    cat("\nTop 3 quality scores:\n")
    print(head(quality_summary[, c("subject", "task", "quality_score")], 3))
    
    cat("\nBottom 3 quality scores:\n")
    print(tail(quality_summary[, c("subject", "task", "quality_score")], 3))
  }
  
  cat("\n=== Example 2 Complete ===\n\n")
}

#' @title Example 3: Comparative Biomechanics Study
#' @description Demonstrates multi-task and multi-subject comparisons
#' @param data_path character path to parquet file
example_comparative_study <- function(data_path) {
  cat("=== Example 3: Comparative Biomechanics Study ===\n")
  
  # Load data
  loco <- loadLocomotionData(data_path)
  
  subjects <- getSubjects(loco)
  tasks <- getTasks(loco)
  features <- getFeatures(loco)
  
  if (length(subjects) > 0 && length(tasks) > 1) {
    subject <- subjects[1]
    analysis_tasks <- head(tasks, 3)  # Analyze first 3 tasks
    analysis_features <- head(features, 2)  # Analyze first 2 features
    
    cat(sprintf("Comparing tasks for subject %s:\n", subject))
    cat(sprintf("Tasks: %s\n", paste(analysis_tasks, collapse = ", ")))
    cat(sprintf("Features: %s\n", paste(analysis_features, collapse = ", ")))
    
    # Multi-task statistics for single subject
    multi_task_stats <- getMultiTaskStatistics(loco, subject, analysis_tasks, analysis_features)
    cat("\nMulti-task statistics:\n")
    print(multi_task_stats)
    
    # Create task comparison plot
    cat("\nCreating task comparison plot...\n")
    p <- plotTaskComparison(loco, subject, analysis_tasks, analysis_features)
    print(p)
    
    # Calculate phase correlations for each task
    cat("\nCalculating phase correlations...\n")
    for (task in analysis_tasks) {
      correlations <- getPhaseCorrelations(loco, subject, task, analysis_features)
      if (!is.null(correlations)) {
        # Report correlation at mid-stance (75% of gait cycle)
        mid_stance_idx <- round(0.75 * dim(correlations)[1])
        mid_stance_cor <- correlations[mid_stance_idx, , ]
        
        cat(sprintf("Task %s - Correlations at 75%% gait cycle:\n", task))
        print(round(mid_stance_cor, 3))
      }
    }
  }
  
  if (length(subjects) > 1 && length(tasks) > 0) {
    task <- tasks[1]
    analysis_subjects <- head(subjects, 5)  # Analyze first 5 subjects
    analysis_features <- head(features, 2)  # Analyze first 2 features
    
    cat(sprintf("\n\nComparing subjects for task %s:\n", task))
    cat(sprintf("Subjects: %s\n", paste(analysis_subjects, collapse = ", ")))
    
    # Multi-subject statistics
    multi_subject_stats <- getMultiSubjectStatistics(loco, analysis_subjects, task, analysis_features)
    cat("\nMulti-subject statistics:\n")
    print(multi_subject_stats)
    
    # Group mean patterns
    group_patterns <- getGroupMeanPatterns(loco, analysis_subjects, task, analysis_features)
    cat(sprintf("\nGroup patterns calculated for %d subjects\n", group_patterns$subject_count))
    cat(sprintf("Features: %s\n", paste(names(group_patterns$group_means), collapse = ", ")))
  }
  
  cat("\n=== Example 3 Complete ===\n\n")
}

#' @title Example 4: Population-Level Analysis
#' @description Demonstrates large-scale analysis across entire dataset
#' @param data_path character path to parquet file
example_population_analysis <- function(data_path) {
  cat("=== Example 4: Population-Level Analysis ===\n")
  
  # Load data
  loco <- loadLocomotionData(data_path)
  
  subjects <- getSubjects(loco)
  tasks <- getTasks(loco)
  features <- getFeatures(loco)
  
  cat(sprintf("Population overview: %d subjects, %d tasks, %d features\n",
              length(subjects), length(tasks), length(features)))
  
  # Filter to specific task for population analysis
  if (length(tasks) > 0) {
    target_task <- tasks[1]  # Use first task
    target_features <- head(features, 3)  # Use first 3 features
    
    cat(sprintf("\nPopulation analysis for task: %s\n", target_task))
    cat(sprintf("Features: %s\n", paste(target_features, collapse = ", ")))
    
    # Create filtered dataset
    filtered_loco <- filterTasks(loco, target_task)
    cat(sprintf("Filtered dataset: %d subjects for task %s\n", 
                length(getSubjects(filtered_loco)), target_task))
    
    # Calculate population statistics
    pop_stats <- getMultiSubjectStatistics(filtered_loco, NULL, target_task, target_features)
    cat("\nPopulation statistics:\n")
    print(pop_stats)
    
    # Calculate group patterns
    group_patterns <- getGroupMeanPatterns(filtered_loco, NULL, target_task, target_features)
    
    if (group_patterns$subject_count > 0) {
      cat(sprintf("\nGroup patterns based on %d subjects:\n", group_patterns$subject_count))
      
      # Show range of motion for population
      for (feature in names(group_patterns$group_means)) {
        pattern <- group_patterns$group_means[[feature]]
        rom <- max(pattern, na.rm = TRUE) - min(pattern, na.rm = TRUE)
        cat(sprintf("  %s: ROM = %.3f\n", feature, rom))
      }
      
      # Create population visualization
      cat("\nCreating population mean pattern visualization...\n")
      
      # Prepare data for plotting
      phase_x <- seq(0, 100, length.out = 150)
      plot_data_list <- list()
      
      for (feature in names(group_patterns$group_means)) {
        mean_pattern <- group_patterns$group_means[[feature]]
        std_pattern <- group_patterns$group_stds[[feature]]
        
        feature_data <- data.frame(
          phase = phase_x,
          mean = mean_pattern,
          std = std_pattern,
          feature = feature,
          stringsAsFactors = FALSE
        )
        plot_data_list[[length(plot_data_list) + 1]] <- feature_data
      }
      
      plot_data <- do.call(rbind, plot_data_list)
      
      # Create population plot
      p <- ggplot(plot_data, aes(x = phase, y = mean)) +
        geom_ribbon(aes(ymin = mean - std, ymax = mean + std), 
                   alpha = 0.3, fill = "blue") +
        geom_line(color = "blue", linewidth = 1.2) +
        facet_wrap(~ feature, scales = "free_y") +
        theme_minimal() +
        labs(
          x = "Gait Cycle (%)",
          y = "Value",
          title = sprintf("Population Mean Patterns - %s", target_task),
          subtitle = sprintf("N = %d subjects", group_patterns$subject_count)
        ) +
        scale_x_continuous(limits = c(0, 100))
      
      print(p)
    }
  }
  
  # Summary of dataset coverage
  cat("\nDataset Coverage Summary:\n")
  coverage_data <- data.frame(
    subject = character(0),
    tasks_available = integer(0),
    total_cycles = integer(0),
    stringsAsFactors = FALSE
  )
  
  for (subject in head(subjects, 10)) {  # Limit to first 10 subjects for demo
    subject_tasks <- 0
    total_cycles <- 0
    
    for (task in tasks) {
      cycles_result <- getCycles(loco, subject, task)
      if (!is.null(cycles_result$data_3d)) {
        subject_tasks <- subject_tasks + 1
        total_cycles <- total_cycles + dim(cycles_result$data_3d)[1]
      }
    }
    
    coverage_data <- rbind(coverage_data, data.frame(
      subject = subject,
      tasks_available = subject_tasks,
      total_cycles = total_cycles,
      stringsAsFactors = FALSE
    ))
  }
  
  if (nrow(coverage_data) > 0) {
    cat(sprintf("Mean tasks per subject: %.1f\n", mean(coverage_data$tasks_available)))
    cat(sprintf("Mean cycles per subject: %.1f\n", mean(coverage_data$total_cycles)))
    cat(sprintf("Total cycles analyzed: %d\n", sum(coverage_data$total_cycles)))
  }
  
  cat("\n=== Example 4 Complete ===\n\n")
}

#' @title Run All Examples
#' @description Execute all example workflows
#' @param data_path character path to parquet file
#' @export
run_all_examples <- function(data_path) {
  cat("Running all LocomotionData R library examples...\n\n")
  
  if (!file.exists(data_path)) {
    stop(sprintf("Data file not found: %s", data_path))
  }
  
  tryCatch({
    example_basic_gait_analysis(data_path)
  }, error = function(e) {
    cat(sprintf("Example 1 failed: %s\n", e$message))
  })
  
  tryCatch({
    example_data_quality_assessment(data_path)
  }, error = function(e) {
    cat(sprintf("Example 2 failed: %s\n", e$message))
  })
  
  tryCatch({
    example_comparative_study(data_path)
  }, error = function(e) {
    cat(sprintf("Example 3 failed: %s\n", e$message))
  })
  
  tryCatch({
    example_population_analysis(data_path)
  }, error = function(e) {
    cat(sprintf("Example 4 failed: %s\n", e$message))
  })
  
  cat("All examples completed!\n")
}

# Example usage:
# run_all_examples("path/to/your/phase_indexed_data.parquet")