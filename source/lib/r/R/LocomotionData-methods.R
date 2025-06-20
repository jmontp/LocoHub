#' @title LocomotionData Core Methods
#' @description Core analysis methods for LocomotionData class
#' @name LocomotionData-methods
NULL

# Define S4 generics
if (!isGeneric("getSubjects")) setGeneric("getSubjects", function(object) standardGeneric("getSubjects"))
if (!isGeneric("getTasks")) setGeneric("getTasks", function(object) standardGeneric("getTasks"))
if (!isGeneric("getFeatures")) setGeneric("getFeatures", function(object) standardGeneric("getFeatures"))
if (!isGeneric("getCycles")) setGeneric("getCycles", function(object, subject, task, features = NULL) standardGeneric("getCycles"))
if (!isGeneric("getMeanPatterns")) setGeneric("getMeanPatterns", function(object, subject, task, features = NULL) standardGeneric("getMeanPatterns"))
if (!isGeneric("getStdPatterns")) setGeneric("getStdPatterns", function(object, subject, task, features = NULL) standardGeneric("getStdPatterns"))
if (!isGeneric("validateCycles")) setGeneric("validateCycles", function(object, subject, task, features = NULL) standardGeneric("validateCycles"))
if (!isGeneric("findOutlierCycles")) setGeneric("findOutlierCycles", function(object, subject, task, features = NULL, threshold = 2.0) standardGeneric("findOutlierCycles"))
if (!isGeneric("getSummaryStatistics")) setGeneric("getSummaryStatistics", function(object, subject, task, features = NULL) standardGeneric("getSummaryStatistics"))
if (!isGeneric("calculateROM")) setGeneric("calculateROM", function(object, subject, task, features = NULL, by_cycle = TRUE) standardGeneric("calculateROM"))
if (!isGeneric("getValidationReport")) setGeneric("getValidationReport", function(object) standardGeneric("getValidationReport"))
if (!isGeneric("getPhaseCorrelations")) setGeneric("getPhaseCorrelations", function(object, subject, task, features = NULL) standardGeneric("getPhaseCorrelations"))
if (!isGeneric("mergeWithTaskData")) setGeneric("mergeWithTaskData", function(object, task_data, join_keys = NULL, how = "outer") standardGeneric("mergeWithTaskData"))
if (!isGeneric("filterSubjects")) setGeneric("filterSubjects", function(object, subjects) standardGeneric("filterSubjects"))
if (!isGeneric("filterTasks")) setGeneric("filterTasks", function(object, tasks) standardGeneric("filterTasks"))
if (!isGeneric("clearCache")) setGeneric("clearCache", function(object) standardGeneric("clearCache"))
if (!isGeneric("getMultiSubjectStatistics")) setGeneric("getMultiSubjectStatistics", function(object, subjects = NULL, task, features = NULL) standardGeneric("getMultiSubjectStatistics"))
if (!isGeneric("getMultiTaskStatistics")) setGeneric("getMultiTaskStatistics", function(object, subject, tasks = NULL, features = NULL) standardGeneric("getMultiTaskStatistics"))
if (!isGeneric("getGroupMeanPatterns")) setGeneric("getGroupMeanPatterns", function(object, subjects = NULL, task, features = NULL) standardGeneric("getGroupMeanPatterns"))

#' @title Get Subjects
#' @description Get list of unique subjects
#' @param object LocomotionData object
#' @return character vector of unique subject IDs
#' @export
setMethod("getSubjects", "LocomotionData",
  function(object) {
    return(object@subjects)
  }
)

#' @title Get Tasks  
#' @description Get list of unique tasks
#' @param object LocomotionData object
#' @return character vector of unique task names
#' @export
setMethod("getTasks", "LocomotionData",
  function(object) {
    return(object@tasks)
  }
)

#' @title Get Features
#' @description Get list of available biomechanical features
#' @param object LocomotionData object
#' @return character vector of feature names
#' @export
setMethod("getFeatures", "LocomotionData",
  function(object) {
    return(object@features)
  }
)

#' @title Get Cycles
#' @description Get 3D array of cycles for a subject-task combination
#' @param object LocomotionData object
#' @param subject character subject ID
#' @param task character task name
#' @param features character vector of features to extract (optional)
#' @return list with 'data_3d' (array) and 'feature_names' (character vector)
#' @export
setMethod("getCycles", "LocomotionData",
  function(object, subject, task, features = NULL) {
    # Check cache
    cache_key <- paste(subject, task, 
                      if(is.null(features)) "all" else paste(features, collapse = "_"),
                      sep = "|")
    if (cache_key %in% names(object@cache)) {
      return(object@cache[[cache_key]])
    }
    
    # Filter data
    subset_data <- object@data[
      get(object@subject_col) == subject & get(object@task_col) == task
    ]
    
    if (nrow(subset_data) == 0) {
      warning(sprintf("No data found for subject '%s', task '%s'", subject, task))
      return(list(data_3d = NULL, feature_names = character(0)))
    }
    
    # Check data length
    n_points <- nrow(subset_data)
    if (n_points %% object@points_per_cycle != 0) {
      warning(sprintf("Data length %d not divisible by %d", 
                     n_points, object@points_per_cycle))
      return(list(data_3d = NULL, feature_names = character(0)))
    }
    
    n_cycles <- n_points %/% object@points_per_cycle
    
    # Select features
    if (is.null(features)) {
      features <- object@features
    }
    
    # Map requested features to actual column names
    valid_features <- character(0)
    actual_columns <- character(0)
    
    for (feature in features) {
      if (feature %in% names(object@feature_mappings)) {
        actual_col <- object@feature_mappings[[feature]]
        if (actual_col %in% names(subset_data)) {
          valid_features <- c(valid_features, feature)
          actual_columns <- c(actual_columns, actual_col)
        }
      }
    }
    
    if (length(valid_features) == 0) {
      warning(sprintf("No valid features found among: %s", 
                     paste(features, collapse = ", ")))
      return(list(data_3d = NULL, feature_names = character(0)))
    }
    
    # Extract and reshape to 3D using actual column names
    feature_data <- as.matrix(subset_data[, ..actual_columns])
    data_3d <- array(feature_data, 
                    dim = c(n_cycles, object@points_per_cycle, length(valid_features)))
    
    # Set dimension names
    dimnames(data_3d) <- list(
      cycles = paste0("cycle_", 1:n_cycles),
      phases = paste0("phase_", 1:object@points_per_cycle),
      features = valid_features
    )
    
    # Cache result (Note: R S4 objects are pass-by-value, so cache is not persistent here)
    result <- list(data_3d = data_3d, feature_names = valid_features)
    
    return(result)
  }
)

#' @title Get Mean Patterns
#' @description Get mean patterns for each feature
#' @param object LocomotionData object
#' @param subject character subject ID
#' @param task character task name
#' @param features character vector of features (optional)
#' @return named list mapping feature names to mean patterns (150 points)
#' @export
setMethod("getMeanPatterns", "LocomotionData",
  function(object, subject, task, features = NULL) {
    cycles_result <- getCycles(object, subject, task, features)
    
    if (is.null(cycles_result$data_3d)) {
      return(list())
    }
    
    # Calculate means across cycles (dimension 1)
    mean_patterns <- apply(cycles_result$data_3d, c(2, 3), mean, na.rm = TRUE)
    
    # Return as named list
    result <- list()
    for (i in seq_along(cycles_result$feature_names)) {
      result[[cycles_result$feature_names[i]]] <- mean_patterns[, i]
    }
    
    return(result)
  }
)

#' @title Get Standard Deviation Patterns
#' @description Get standard deviation patterns for each feature
#' @param object LocomotionData object
#' @param subject character subject ID
#' @param task character task name
#' @param features character vector of features (optional)
#' @return named list mapping feature names to std patterns (150 points)
#' @export
setMethod("getStdPatterns", "LocomotionData",
  function(object, subject, task, features = NULL) {
    cycles_result <- getCycles(object, subject, task, features)
    
    if (is.null(cycles_result$data_3d)) {
      return(list())
    }
    
    # Calculate standard deviations across cycles (dimension 1)
    std_patterns <- apply(cycles_result$data_3d, c(2, 3), sd, na.rm = TRUE)
    
    # Return as named list
    result <- list()
    for (i in seq_along(cycles_result$feature_names)) {
      result[[cycles_result$feature_names[i]]] <- std_patterns[, i]
    }
    
    return(result)
  }
)

#' @title Validate Cycles
#' @description Validate cycles based on biomechanical constraints
#' @param object LocomotionData object
#' @param subject character subject ID
#' @param task character task name
#' @param features character vector of features (optional)
#' @return logical vector indicating valid cycles
#' @export
setMethod("validateCycles", "LocomotionData",
  function(object, subject, task, features = NULL) {
    cycles_result <- getCycles(object, subject, task, features)
    
    if (is.null(cycles_result$data_3d)) {
      return(logical(0))
    }
    
    data_3d <- cycles_result$data_3d
    feature_names <- cycles_result$feature_names
    n_cycles <- dim(data_3d)[1]
    
    valid_mask <- rep(TRUE, n_cycles)
    
    # Check each feature
    for (i in seq_along(feature_names)) {
      feature <- feature_names[i]
      feat_data <- data_3d[, , i]  # (n_cycles, 150)
      
      # Range checks
      if (grepl("angle", feature)) {
        # Angles are now in radians
        out_of_range <- apply(feat_data < -pi | feat_data > pi, 1, any, na.rm = TRUE)
        valid_mask <- valid_mask & !out_of_range
        
        # Check for large discontinuities
        diffs <- abs(apply(feat_data, 1, diff))
        large_jumps <- apply(diffs > 0.5236, 2, any, na.rm = TRUE)  # 30 degrees = 0.5236 radians
        valid_mask <- valid_mask & !large_jumps
        
      } else if (grepl("velocity", feature)) {
        # Velocities in rad/s
        out_of_range <- apply(abs(feat_data) > 17.45, 1, any, na.rm = TRUE)  # 1000 deg/s = 17.45 rad/s
        valid_mask <- valid_mask & !out_of_range
        
      } else if (grepl("moment", feature)) {
        out_of_range <- apply(abs(feat_data) > 300, 1, any, na.rm = TRUE)
        valid_mask <- valid_mask & !out_of_range
      }
      
      # Check for NaN or inf
      has_invalid <- apply(!is.finite(feat_data), 1, any)
      valid_mask <- valid_mask & !has_invalid
    }
    
    return(valid_mask)
  }
)

#' @title Find Outlier Cycles
#' @description Find outlier cycles based on deviation from mean pattern
#' @param object LocomotionData object
#' @param subject character subject ID
#' @param task character task name
#' @param features character vector of features (optional)
#' @param threshold numeric number of standard deviations for outlier threshold (default: 2.0)
#' @return integer vector of outlier cycle indices
#' @export
setMethod("findOutlierCycles", "LocomotionData",
  function(object, subject, task, features = NULL, threshold = 2.0) {
    cycles_result <- getCycles(object, subject, task, features)
    
    if (is.null(cycles_result$data_3d)) {
      return(integer(0))
    }
    
    data_3d <- cycles_result$data_3d
    
    # Calculate mean pattern across cycles
    mean_patterns <- apply(data_3d, c(2, 3), mean, na.rm = TRUE)  # (150, n_features)
    
    # Calculate deviation for each cycle
    deviations <- sweep(data_3d, c(2, 3), mean_patterns, "-")
    rmse_per_cycle <- sqrt(apply(deviations^2, 1, mean, na.rm = TRUE))
    
    # Find outliers
    outlier_threshold <- mean(rmse_per_cycle, na.rm = TRUE) + 
                       threshold * sd(rmse_per_cycle, na.rm = TRUE)
    outlier_indices <- which(rmse_per_cycle > outlier_threshold)
    
    return(outlier_indices)
  }
)

#' @title Get Summary Statistics
#' @description Get summary statistics for all features
#' @param object LocomotionData object
#' @param subject character subject ID
#' @param task character task name
#' @param features character vector of features (optional)
#' @return data.frame with summary statistics
#' @export
setMethod("getSummaryStatistics", "LocomotionData",
  function(object, subject, task, features = NULL) {
    cycles_result <- getCycles(object, subject, task, features)
    
    if (is.null(cycles_result$data_3d)) {
      return(data.frame())
    }
    
    data_3d <- cycles_result$data_3d
    feature_names <- cycles_result$feature_names
    
    # Reshape to (n_cycles * 150, n_features) for easier statistics
    dims <- dim(data_3d)
    data_2d <- array(data_3d, c(dims[1] * dims[2], dims[3]))
    
    # Calculate statistics
    stats_df <- data.frame(
      feature = feature_names,
      mean = apply(data_2d, 2, mean, na.rm = TRUE),
      std = apply(data_2d, 2, sd, na.rm = TRUE),
      min = apply(data_2d, 2, min, na.rm = TRUE),
      max = apply(data_2d, 2, max, na.rm = TRUE),
      median = apply(data_2d, 2, median, na.rm = TRUE),
      q25 = apply(data_2d, 2, quantile, 0.25, na.rm = TRUE),
      q75 = apply(data_2d, 2, quantile, 0.75, na.rm = TRUE),
      stringsAsFactors = FALSE
    )
    
    return(stats_df)
  }
)

#' @title Calculate Range of Motion
#' @description Calculate Range of Motion (ROM) for features
#' @param object LocomotionData object
#' @param subject character subject ID
#' @param task character task name
#' @param features character vector of features (optional)
#' @param by_cycle logical if TRUE, calculate ROM per cycle. If FALSE, overall ROM
#' @return named list with ROM values for each feature
#' @export
setMethod("calculateROM", "LocomotionData",
  function(object, subject, task, features = NULL, by_cycle = TRUE) {
    cycles_result <- getCycles(object, subject, task, features)
    
    if (is.null(cycles_result$data_3d)) {
      return(list())
    }
    
    data_3d <- cycles_result$data_3d
    feature_names <- cycles_result$feature_names
    
    rom_data <- list()
    
    for (i in seq_along(feature_names)) {
      feature <- feature_names[i]
      feat_data <- data_3d[, , i]  # (n_cycles, 150)
      
      if (by_cycle) {
        # ROM per cycle
        rom_data[[feature]] <- apply(feat_data, 1, function(x) max(x, na.rm = TRUE) - min(x, na.rm = TRUE))
      } else {
        # Overall ROM
        rom_data[[feature]] <- max(feat_data, na.rm = TRUE) - min(feat_data, na.rm = TRUE)
      }
    }
    
    return(rom_data)
  }
)

#' @title Get Validation Report
#' @description Get variable name validation report
#' @param object LocomotionData object
#' @return list with validation report components
#' @export
setMethod("getValidationReport", "LocomotionData",
  function(object) {
    return(object@validation_report)
  }
)

#' @title Efficient 3D Reshape
#' @description Standalone function for efficient 3D reshaping
#' @param data data.table with phase-indexed locomotion data
#' @param subject character subject ID to extract
#' @param task character task name to extract
#' @param features character vector of features to extract
#' @param subject_col character column name for subjects (default: "subject")
#' @param task_col character column name for tasks (default: "task")
#' @param points_per_cycle integer number of points per gait cycle (default: 150)
#' @return list with 'data_3d' (array or NULL) and 'valid_features' (character vector)
#' @export
efficientReshape3D <- function(data, subject, task, features,
                              subject_col = "subject", task_col = "task", 
                              points_per_cycle = 150L) {
  
  # Convert to data.table if necessary
  if (!data.table::is.data.table(data)) {
    data <- data.table::setDT(data)
  }
  
  # Filter data
  subset_data <- data[get(subject_col) == subject & get(task_col) == task]
  
  if (nrow(subset_data) == 0) {
    return(list(data_3d = NULL, valid_features = character(0)))
  }
  
  # Check data length
  n_points <- nrow(subset_data)
  if (n_points %% points_per_cycle != 0) {
    warning(sprintf("Data length %d not divisible by %d", n_points, points_per_cycle))
    return(list(data_3d = NULL, valid_features = character(0)))
  }
  
  n_cycles <- n_points %/% points_per_cycle
  
  # Filter to valid features
  valid_features <- features[features %in% names(subset_data)]
  if (length(valid_features) == 0) {
    return(list(data_3d = NULL, valid_features = character(0)))
  }
  
  # Extract all features at once
  feature_data <- as.matrix(subset_data[, ..valid_features])
  
  # Reshape to 3D
  data_3d <- array(feature_data, c(n_cycles, points_per_cycle, length(valid_features)))
  
  # Set dimension names
  dimnames(data_3d) <- list(
    cycles = paste0("cycle_", 1:n_cycles),
    phases = paste0("phase_", 1:points_per_cycle),
    features = valid_features
  )
  
  return(list(data_3d = data_3d, valid_features = valid_features))
}

#' @title Get Phase Correlations
#' @description Calculate correlation between features at each phase point
#' @param object LocomotionData object
#' @param subject character subject ID
#' @param task character task name
#' @param features character vector of features (optional)
#' @return array of shape (150, n_features, n_features) with correlation matrices
#' @export
setMethod("getPhaseCorrelations", "LocomotionData",
  function(object, subject, task, features = NULL) {
    cycles_result <- getCycles(object, subject, task, features)
    
    if (is.null(cycles_result$data_3d) || dim(cycles_result$data_3d)[1] < 2) {
      return(NULL)
    }
    
    data_3d <- cycles_result$data_3d
    n_phases <- object@points_per_cycle
    n_features <- length(cycles_result$feature_names)
    
    correlations <- array(NA, dim = c(n_phases, n_features, n_features))
    dimnames(correlations) <- list(
      phases = paste0("phase_", 1:n_phases),
      features1 = cycles_result$feature_names,
      features2 = cycles_result$feature_names
    )
    
    for (phase in seq_len(n_phases)) {
      phase_data <- data_3d[, phase, ]  # (n_cycles, n_features)
      
      # Calculate correlation matrix for this phase
      if (ncol(phase_data) > 1) {
        cor_matrix <- tryCatch({
          cor(phase_data, use = "complete.obs")
        }, error = function(e) {
          matrix(NA, nrow = n_features, ncol = n_features)
        })
        correlations[phase, , ] <- cor_matrix
      } else {
        # Single feature case
        correlations[phase, 1, 1] <- 1.0
      }
    }
    
    return(correlations)
  }
)

#' @title Merge With Task Data
#' @description Merge locomotion data with task information
#' @param object LocomotionData object
#' @param task_data data.frame with task information
#' @param join_keys character vector of keys to join on (optional)
#' @param how character type of join ('inner', 'outer', 'left', 'right')
#' @return data.table with merged data
#' @export
setMethod("mergeWithTaskData", "LocomotionData",
  function(object, task_data, join_keys = NULL, how = "outer") {
    
    if (is.null(join_keys)) {
      join_keys <- c(object@subject_col, object@task_col)
    }
    
    # Convert task_data to data.table if necessary
    if (!data.table::is.data.table(task_data)) {
      task_data <- data.table::setDT(task_data)
    }
    
    # Ensure join keys exist in both datasets
    missing_keys <- setdiff(join_keys, names(object@data))
    if (length(missing_keys) > 0) {
      stop(sprintf("Join keys %s not found in locomotion data", 
                   paste(missing_keys, collapse = ", ")))
    }
    
    missing_keys <- setdiff(join_keys, names(task_data))
    if (length(missing_keys) > 0) {
      stop(sprintf("Join keys %s not found in task data", 
                   paste(missing_keys, collapse = ", ")))
    }
    
    # Perform merge based on join type
    merged_data <- switch(how,
      "inner" = merge(object@data, task_data, by = join_keys, all = FALSE),
      "outer" = merge(object@data, task_data, by = join_keys, all = TRUE),
      "left" = merge(object@data, task_data, by = join_keys, all.x = TRUE),
      "right" = merge(object@data, task_data, by = join_keys, all.y = TRUE),
      stop(sprintf("Unsupported join type: %s. Use 'inner', 'outer', 'left', or 'right'", how))
    )
    
    return(merged_data)
  }
)

#' @title Filter Subjects
#' @description Create subset of LocomotionData with specified subjects
#' @param object LocomotionData object
#' @param subjects character vector of subject IDs to keep
#' @return LocomotionData object with filtered data
#' @export
setMethod("filterSubjects", "LocomotionData", 
  function(object, subjects) {
    
    # Validate subjects exist
    available_subjects <- object@subjects
    missing_subjects <- setdiff(subjects, available_subjects)
    if (length(missing_subjects) > 0) {
      warning(sprintf("Subjects not found: %s", paste(missing_subjects, collapse = ", ")))
    }
    
    valid_subjects <- intersect(subjects, available_subjects)
    if (length(valid_subjects) == 0) {
      stop("No valid subjects found")
    }
    
    # Filter data
    filtered_data <- object@data[get(object@subject_col) %in% valid_subjects]
    
    # Create new object with filtered data
    # Note: Since we can't easily modify existing object, we create a copy
    filtered_object <- object
    filtered_object@data <- filtered_data
    filtered_object@subjects <- sort(unique(filtered_data[[object@subject_col]]))
    filtered_object@tasks <- sort(unique(filtered_data[[object@task_col]]))
    filtered_object@cache <- list()  # Clear cache for new subset
    
    return(filtered_object)
  }
)

#' @title Filter Tasks
#' @description Create subset of LocomotionData with specified tasks
#' @param object LocomotionData object
#' @param tasks character vector of task names to keep
#' @return LocomotionData object with filtered data
#' @export
setMethod("filterTasks", "LocomotionData",
  function(object, tasks) {
    
    # Validate tasks exist
    available_tasks <- object@tasks
    missing_tasks <- setdiff(tasks, available_tasks)
    if (length(missing_tasks) > 0) {
      warning(sprintf("Tasks not found: %s", paste(missing_tasks, collapse = ", ")))
    }
    
    valid_tasks <- intersect(tasks, available_tasks)
    if (length(valid_tasks) == 0) {
      stop("No valid tasks found")
    }
    
    # Filter data
    filtered_data <- object@data[get(object@task_col) %in% valid_tasks]
    
    # Create new object with filtered data
    filtered_object <- object
    filtered_object@data <- filtered_data
    filtered_object@subjects <- sort(unique(filtered_data[[object@subject_col]]))
    filtered_object@tasks <- sort(unique(filtered_data[[object@task_col]]))
    filtered_object@cache <- list()  # Clear cache for new subset
    
    return(filtered_object)
  }
)

#' @title Clear Cache
#' @description Clear cached 3D array results
#' @param object LocomotionData object
#' @return LocomotionData object with cleared cache
#' @export
setMethod("clearCache", "LocomotionData",
  function(object) {
    object@cache <- list()
    cat("Cache cleared\n")
    return(object)
  }
)

#' @title Get Multi-Subject Statistics
#' @description Get summary statistics across multiple subjects for a single task
#' @param object LocomotionData object
#' @param subjects character vector of subject IDs (NULL for all subjects)
#' @param task character task name
#' @param features character vector of features (optional)
#' @return data.frame with multi-subject statistics
#' @export
setMethod("getMultiSubjectStatistics", "LocomotionData",
  function(object, subjects = NULL, task, features = NULL) {
    
    if (is.null(subjects)) {
      subjects <- object@subjects
    }
    
    # Validate subjects exist
    valid_subjects <- intersect(subjects, object@subjects)
    if (length(valid_subjects) == 0) {
      stop("No valid subjects found")
    }
    
    if (length(valid_subjects) < length(subjects)) {
      missing <- setdiff(subjects, valid_subjects)
      warning(sprintf("Some subjects not found: %s", paste(missing, collapse = ", ")))
    }
    
    # Collect statistics for each subject
    stats_list <- list()
    
    for (subject in valid_subjects) {
      subject_stats <- getSummaryStatistics(object, subject, task, features)
      if (nrow(subject_stats) > 0) {
        subject_stats$subject <- subject
        stats_list[[length(stats_list) + 1]] <- subject_stats
      }
    }
    
    if (length(stats_list) == 0) {
      return(data.frame())
    }
    
    # Combine all subject statistics
    all_stats <- do.call(rbind, stats_list)
    
    # Calculate group statistics
    group_stats <- all_stats[, .(
      group_mean = mean(mean, na.rm = TRUE),
      group_std = sd(mean, na.rm = TRUE),
      group_min = min(min, na.rm = TRUE),
      group_max = max(max, na.rm = TRUE),
      subject_count = .N,
      between_subject_cv = 100 * sd(mean, na.rm = TRUE) / mean(mean, na.rm = TRUE)
    ), by = feature]
    
    return(group_stats)
  }
)

#' @title Get Multi-Task Statistics  
#' @description Get summary statistics across multiple tasks for a single subject
#' @param object LocomotionData object
#' @param subject character subject ID
#' @param tasks character vector of task names (NULL for all tasks)
#' @param features character vector of features (optional)
#' @return data.frame with multi-task statistics
#' @export
setMethod("getMultiTaskStatistics", "LocomotionData",
  function(object, subject, tasks = NULL, features = NULL) {
    
    if (is.null(tasks)) {
      tasks <- object@tasks
    }
    
    # Validate tasks exist
    valid_tasks <- intersect(tasks, object@tasks)
    if (length(valid_tasks) == 0) {
      stop("No valid tasks found")
    }
    
    if (length(valid_tasks) < length(tasks)) {
      missing <- setdiff(tasks, valid_tasks)
      warning(sprintf("Some tasks not found: %s", paste(missing, collapse = ", ")))
    }
    
    # Collect statistics for each task
    stats_list <- list()
    
    for (task in valid_tasks) {
      task_stats <- getSummaryStatistics(object, subject, task, features)
      if (nrow(task_stats) > 0) {
        task_stats$task <- task
        stats_list[[length(stats_list) + 1]] <- task_stats
      }
    }
    
    if (length(stats_list) == 0) {
      return(data.frame())
    }
    
    # Combine all task statistics
    all_stats <- do.call(rbind, stats_list)
    
    # Calculate across-task statistics
    task_stats <- all_stats[, .(
      across_task_mean = mean(mean, na.rm = TRUE),
      across_task_std = sd(mean, na.rm = TRUE),
      across_task_min = min(min, na.rm = TRUE),
      across_task_max = max(max, na.rm = TRUE),
      task_count = .N,
      between_task_cv = 100 * sd(mean, na.rm = TRUE) / mean(mean, na.rm = TRUE)
    ), by = feature]
    
    return(task_stats)
  }
)

#' @title Get Group Mean Patterns
#' @description Get mean patterns across multiple subjects for a single task
#' @param object LocomotionData object
#' @param subjects character vector of subject IDs (NULL for all subjects)
#' @param task character task name
#' @param features character vector of features (optional)
#' @return list with group mean patterns and statistics
#' @export
setMethod("getGroupMeanPatterns", "LocomotionData",
  function(object, subjects = NULL, task, features = NULL) {
    
    if (is.null(subjects)) {
      subjects <- object@subjects
    }
    
    # Validate subjects exist
    valid_subjects <- intersect(subjects, object@subjects)
    if (length(valid_subjects) == 0) {
      stop("No valid subjects found")
    }
    
    if (length(valid_subjects) < length(subjects)) {
      missing <- setdiff(subjects, valid_subjects)
      warning(sprintf("Some subjects not found: %s", paste(missing, collapse = ", ")))
    }
    
    # Collect mean patterns for each subject
    all_patterns <- list()
    
    for (subject in valid_subjects) {
      subject_patterns <- getMeanPatterns(object, subject, task, features)
      if (length(subject_patterns) > 0) {
        all_patterns[[subject]] <- subject_patterns
      }
    }
    
    if (length(all_patterns) == 0) {
      return(list(group_means = list(), group_stds = list(), subject_count = 0))
    }
    
    # Get common features across all subjects
    common_features <- Reduce(intersect, lapply(all_patterns, names))
    if (length(common_features) == 0) {
      warning("No common features found across subjects")
      return(list(group_means = list(), group_stds = list(), subject_count = 0))
    }
    
    # Calculate group statistics
    group_means <- list()
    group_stds <- list()
    
    for (feature in common_features) {
      # Extract patterns for this feature from all subjects
      feature_patterns <- sapply(all_patterns, function(subj_patterns) {
        subj_patterns[[feature]]
      })
      
      # Calculate group mean and std across subjects
      if (is.matrix(feature_patterns)) {
        group_means[[feature]] <- apply(feature_patterns, 1, mean, na.rm = TRUE)
        group_stds[[feature]] <- apply(feature_patterns, 1, sd, na.rm = TRUE)
      } else {
        # Single subject case
        group_means[[feature]] <- feature_patterns
        group_stds[[feature]] <- rep(0, length(feature_patterns))
      }
    }
    
    return(list(
      group_means = group_means,
      group_stds = group_stds,
      subject_count = length(all_patterns),
      subjects_included = names(all_patterns)
    ))
  }
)

#' @title Load Locomotion Data
#' @description Convenience function to create LocomotionData object
#' @param data_path character path to data file
#' @param ... additional arguments passed to LocomotionData constructor
#' @return LocomotionData object
#' @export
loadLocomotionData <- function(data_path, ...) {
  return(new("LocomotionData", data_path = data_path, ...))
}