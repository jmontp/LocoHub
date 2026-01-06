#' @title LocomotionData Plotting Methods
#' @description Visualization methods for LocomotionData class
#' @name LocomotionData-plotting
NULL

# Define plotting generics
if (!isGeneric("plotPhasePatterns")) setGeneric("plotPhasePatterns", function(object, subject, task, features, plot_type = "both", save_path = NULL) standardGeneric("plotPhasePatterns"))
if (!isGeneric("plotTaskComparison")) setGeneric("plotTaskComparison", function(object, subject, tasks, features, save_path = NULL) standardGeneric("plotTaskComparison"))
if (!isGeneric("plotTimeSeries")) setGeneric("plotTimeSeries", function(object, subject, task, features, time_col = "time_s", save_path = NULL) standardGeneric("plotTimeSeries"))

#' @title Plot Method for LocomotionData
#' @description Default plot method that creates phase pattern plots
#' @param x LocomotionData object
#' @param subject character subject ID
#' @param task character task name
#' @param features character vector of features to plot
#' @param plot_type character 'mean', 'spaghetti', or 'both' (default: 'both')
#' @param ... additional arguments passed to plotting functions
#' @export
setMethod("plot", "LocomotionData",
  function(x, subject, task, features, plot_type = "both", ...) {
    plotPhasePatterns(x, subject, task, features, plot_type, ...)
  }
)

#' @title Plot Phase Patterns
#' @description Plot phase-normalized patterns with ggplot2
#' @param object LocomotionData object
#' @param subject character subject ID
#' @param task character task name
#' @param features character vector of features to plot
#' @param plot_type character 'mean', 'spaghetti', or 'both' (default: 'both')
#' @param save_path character path to save plot (optional)
#' @return ggplot object
#' @export
setMethod("plotPhasePatterns", "LocomotionData",
  function(object, subject, task, features, plot_type = "both", save_path = NULL) {
    
    cycles_result <- getCycles(object, subject, task, features)
    
    if (is.null(cycles_result$data_3d)) {
      stop(sprintf("No data found for %s - %s", subject, task))
    }
    
    # Get valid cycles
    valid_mask <- validateCycles(object, subject, task, features)
    
    data_3d <- cycles_result$data_3d
    feature_names <- cycles_result$feature_names
    
    # Prepare data for ggplot
    phase_x <- seq(0, 100, length.out = object@points_per_cycle)
    plot_data_list <- list()
    
    for (i in seq_along(feature_names)) {
      feature <- feature_names[i]
      feat_data <- data_3d[, , i]
      
      # Create data for individual cycles
      if (plot_type %in% c("spaghetti", "both")) {
        for (cycle_idx in seq_len(nrow(feat_data))) {
          cycle_data <- data.frame(
            phase = phase_x,
            value = feat_data[cycle_idx, ],
            feature = feature,
            cycle = cycle_idx,
            valid = valid_mask[cycle_idx],
            type = "individual",
            stringsAsFactors = FALSE
          )
          plot_data_list[[length(plot_data_list) + 1]] <- cycle_data
        }
      }
      
      # Create mean pattern data
      if (plot_type %in% c("mean", "both")) {
        valid_data <- feat_data[valid_mask, , drop = FALSE]
        if (nrow(valid_data) > 0) {
          mean_curve <- apply(valid_data, 2, mean, na.rm = TRUE)
          std_curve <- apply(valid_data, 2, sd, na.rm = TRUE)
          
          mean_data <- data.frame(
            phase = phase_x,
            value = mean_curve,
            feature = feature,
            cycle = NA,
            valid = TRUE,
            type = "mean",
            std = std_curve,
            stringsAsFactors = FALSE
          )
          plot_data_list[[length(plot_data_list) + 1]] <- mean_data
        }
      }
    }
    
    # Combine all data
    plot_data <- do.call(rbind, plot_data_list)
    
    # Create the plot
    p <- ggplot2::ggplot(plot_data, ggplot2::aes(x = phase, y = value))
    
    # Add individual cycles if requested
    if (plot_type %in% c("spaghetti", "both")) {
      individual_data <- plot_data[plot_data$type == "individual", ]
      if (nrow(individual_data) > 0) {
        # Valid cycles in gray
        valid_individual <- individual_data[individual_data$valid, ]
        if (nrow(valid_individual) > 0) {
          p <- p + ggplot2::geom_line(
            data = valid_individual,
            ggplot2::aes(group = cycle),
            color = "gray70", alpha = 0.3, linewidth = 0.5
          )
        }
        
        # Invalid cycles in red
        invalid_individual <- individual_data[!individual_data$valid, ]
        if (nrow(invalid_individual) > 0) {
          p <- p + ggplot2::geom_line(
            data = invalid_individual,
            ggplot2::aes(group = cycle),
            color = "red", alpha = 0.5, linewidth = 0.5
          )
        }
      }
    }
    
    # Add mean pattern if requested
    if (plot_type %in% c("mean", "both")) {
      mean_data <- plot_data[plot_data$type == "mean" & !is.na(plot_data$type), ]
      if (nrow(mean_data) > 0) {
        if (plot_type == "mean") {
          # Add confidence bands for mean-only plots
          p <- p + ggplot2::geom_ribbon(
            data = mean_data,
            ggplot2::aes(ymin = value - std, ymax = value + std),
            alpha = 0.3, fill = "blue"
          )
        }
        
        p <- p + ggplot2::geom_line(
          data = mean_data,
          color = "blue", linewidth = 1.2
        )
      }
    }
    
    # Facet by feature
    p <- p + ggplot2::facet_wrap(~ feature, scales = "free_y", labeller = ggplot2::label_wrap_gen(15))
    
    # Styling
    p <- p + 
      ggplot2::theme_minimal() +
      ggplot2::labs(
        x = "Gait Cycle (%)",
        y = "Value",
        title = sprintf("%s - %s", subject, task),
        subtitle = sprintf("Valid: %d/%d cycles", sum(valid_mask), length(valid_mask))
      ) +
      ggplot2::theme(
        strip.text = ggplot2::element_text(size = 8),
        axis.text = ggplot2::element_text(size = 8),
        axis.title = ggplot2::element_text(size = 10),
        plot.title = ggplot2::element_text(size = 12),
        plot.subtitle = ggplot2::element_text(size = 10)
      ) +
      ggplot2::scale_x_continuous(limits = c(0, 100))
    
    # Save if requested
    if (!is.null(save_path)) {
      ggplot2::ggsave(save_path, plot = p, width = 12, height = 8, dpi = 300)
      cat(sprintf("Plot saved to %s\n", save_path))
    }
    
    return(p)
  }
)

#' @title Plot Task Comparison
#' @description Plot comparison of mean patterns across tasks
#' @param object LocomotionData object
#' @param subject character subject ID
#' @param tasks character vector of tasks to compare
#' @param features character vector of features to plot
#' @param save_path character path to save plot (optional)
#' @return ggplot object
#' @export
setMethod("plotTaskComparison", "LocomotionData",
  function(object, subject, tasks, features, save_path = NULL) {
    
    # Collect mean patterns for all tasks
    plot_data_list <- list()
    phase_x <- seq(0, 100, length.out = object@points_per_cycle)
    
    for (task in tasks) {
      mean_patterns <- getMeanPatterns(object, subject, task, features)
      
      for (feature in names(mean_patterns)) {
        if (feature %in% features) {
          task_data <- data.frame(
            phase = phase_x,
            value = mean_patterns[[feature]],
            feature = feature,
            task = task,
            stringsAsFactors = FALSE
          )
          plot_data_list[[length(plot_data_list) + 1]] <- task_data
        }
      }
    }
    
    if (length(plot_data_list) == 0) {
      stop("No valid data found for the specified subject, tasks, and features")
    }
    
    # Combine all data
    plot_data <- do.call(rbind, plot_data_list)
    
    # Create the plot
    p <- ggplot2::ggplot(plot_data, ggplot2::aes(x = phase, y = value, color = task)) +
      ggplot2::geom_line(linewidth = 1.2) +
      ggplot2::facet_wrap(~ feature, scales = "free_y", labeller = ggplot2::label_wrap_gen(15)) +
      ggplot2::theme_minimal() +
      ggplot2::labs(
        x = "Gait Cycle (%)",
        y = "Value", 
        title = sprintf("%s - Task Comparison", subject),
        color = "Task"
      ) +
      ggplot2::theme(
        strip.text = ggplot2::element_text(size = 8),
        axis.text = ggplot2::element_text(size = 8),
        axis.title = ggplot2::element_text(size = 10),
        plot.title = ggplot2::element_text(size = 12),
        legend.position = "bottom"
      ) +
      ggplot2::scale_x_continuous(limits = c(0, 100)) +
      ggplot2::guides(color = ggplot2::guide_legend(override.aes = list(linewidth = 2)))
    
    # Save if requested
    if (!is.null(save_path)) {
      ggplot2::ggsave(save_path, plot = p, width = 12, height = 8, dpi = 300)
      cat(sprintf("Plot saved to %s\n", save_path))
    }
    
    return(p)
  }
)

#' @title Plot Time Series
#' @description Plot time series data for specific features
#' @param object LocomotionData object
#' @param subject character subject ID
#' @param task character task name
#' @param features character vector of features to plot
#' @param time_col character column name for time data (default: "time_s")
#' @param save_path character path to save plot (optional)
#' @return ggplot object
#' @export
setMethod("plotTimeSeries", "LocomotionData",
  function(object, subject, task, features, time_col = "time_s", save_path = NULL) {
    
    # Filter data
    subset_data <- object@data[
      get(object@subject_col) == subject & get(object@task_col) == task
    ]
    
    if (nrow(subset_data) == 0) {
      stop(sprintf("No data found for %s - %s", subject, task))
    }
    
    if (!time_col %in% names(subset_data)) {
      stop(sprintf("Time column '%s' not found in data", time_col))
    }
    
    # Check for valid features
    valid_features <- features[features %in% names(subset_data)]
    if (length(valid_features) == 0) {
      stop(sprintf("No valid features found among: %s", paste(features, collapse = ", ")))
    }
    
    # Prepare data for plotting
    plot_data_list <- list()
    for (feature in valid_features) {
      feature_data <- data.frame(
        time = subset_data[[time_col]],
        value = subset_data[[feature]],
        feature = feature,
        stringsAsFactors = FALSE
      )
      plot_data_list[[length(plot_data_list) + 1]] <- feature_data
    }
    
    plot_data <- do.call(rbind, plot_data_list)
    
    # Create the plot
    p <- ggplot2::ggplot(plot_data, ggplot2::aes(x = time, y = value)) +
      ggplot2::geom_line(color = "blue", linewidth = 0.8) +
      ggplot2::facet_wrap(~ feature, scales = "free_y", labeller = ggplot2::label_wrap_gen(15)) +
      ggplot2::theme_minimal() +
      ggplot2::labs(
        x = "Time (s)",
        y = "Value",
        title = sprintf("%s - %s (Time Series)", subject, task)
      ) +
      ggplot2::theme(
        strip.text = ggplot2::element_text(size = 8),
        axis.text = ggplot2::element_text(size = 8),
        axis.title = ggplot2::element_text(size = 10),
        plot.title = ggplot2::element_text(size = 12)
      )
    
    # Save if requested
    if (!is.null(save_path)) {
      ggplot2::ggsave(save_path, plot = p, width = 12, height = 8, dpi = 300)
      cat(sprintf("Plot saved to %s\n", save_path))
    }
    
    return(p)
  }
)