#' @title LocomotionData S4 Class
#' @description S4 class for locomotion data analysis using efficient 3D array operations
#' 
#' @details
#' Main class for locomotion data analysis that mirrors the Python LocomotionData API.
#' Provides methods for loading, validating, and analyzing phase-indexed biomechanical data
#' with comprehensive quality assessment and visualization capabilities.
#' 
#' @slot data data.table containing the raw locomotion data
#' @slot subjects character vector of unique subject IDs
#' @slot tasks character vector of unique task names
#' @slot features character vector of biomechanical feature names
#' @slot data_path character path to the original data file
#' @slot subject_col character name of the subject column
#' @slot task_col character name of the task column  
#' @slot phase_col character name of the phase column
#' @slot feature_mappings named list mapping feature names to column names
#' @slot validation_report list containing variable name validation results
#' @slot cache list for caching 3D array results
#' @slot points_per_cycle integer number of points per gait cycle (default: 150)
#' 
#' @name LocomotionData-class
#' @aliases LocomotionData
#' @exportClass LocomotionData
setClass("LocomotionData",
  slots = list(
    data = "data.table",
    subjects = "character",
    tasks = "character", 
    features = "character",
    data_path = "character",
    subject_col = "character",
    task_col = "character",
    phase_col = "character",
    feature_mappings = "list",
    validation_report = "list",
    cache = "list",
    points_per_cycle = "integer"
  ),
  prototype = list(
    data = data.table::data.table(),
    subjects = character(0),
    tasks = character(0),
    features = character(0),
    data_path = character(0),
    subject_col = "subject",
    task_col = "task", 
    phase_col = "phase",
    feature_mappings = list(),
    validation_report = list(),
    cache = list(),
    points_per_cycle = 150L
  )
)

#' @title Initialize LocomotionData Object
#' @description Initialize with phase-indexed locomotion data
#' 
#' @param .Object LocomotionData object
#' @param data_path character path to parquet or CSV file with phase-indexed data
#' @param subject_col character column name for subject IDs (default: "subject")
#' @param task_col character column name for task names (default: "task")
#' @param phase_col character column name for phase values (default: "phase")
#' @param file_type character 'parquet', 'csv', or 'auto' to detect from extension (default: "auto")
#' 
#' @return Initialized LocomotionData object
#' @export
setMethod("initialize", "LocomotionData",
  function(.Object, data_path, subject_col = "subject", task_col = "task", 
           phase_col = "phase", file_type = "auto") {
    
    # Validate file existence
    if (!file.exists(data_path)) {
      stop(sprintf("Data file not found: %s", data_path))
    }
    
    # Set basic slots
    .Object@data_path <- data_path
    .Object@subject_col <- subject_col
    .Object@task_col <- task_col
    .Object@phase_col <- phase_col
    .Object@points_per_cycle <- 150L
    
    # Load data with enhanced error handling
    tryCatch({
      .Object@data <- .loadDataWithValidation(.Object, file_type)
    }, error = function(e) {
      stop(sprintf("Failed to load data from %s: %s", data_path, e$message))
    })
    
    # Validate required columns
    .validateRequiredColumns(.Object)
    
    # Validate data format
    .validateDataFormat(.Object)
    
    # Initialize cache
    .Object@cache <- list()
    
    # Identify biomechanical features
    .Object <- .identifyFeatures(.Object)
    
    # Validate variable names
    .Object <- .validateVariableNames(.Object)
    
    return(.Object)
  }
)

#' @title Show LocomotionData Object
#' @description Display summary information about the LocomotionData object
#' @param object LocomotionData object
#' @export
setMethod("show", "LocomotionData",
  function(object) {
    cat("LocomotionData object\n")
    cat("=====================\n")
    cat(sprintf("Data file: %s\n", object@data_path))
    cat(sprintf("Dimensions: %d rows x %d columns\n", nrow(object@data), ncol(object@data)))
    cat(sprintf("Subjects: %d (%s%s)\n", 
        length(object@subjects), 
        paste(head(object@subjects, 3), collapse = ", "),
        if(length(object@subjects) > 3) "..." else ""))
    cat(sprintf("Tasks: %d (%s%s)\n", 
        length(object@tasks),
        paste(head(object@tasks, 3), collapse = ", "),
        if(length(object@tasks) > 3) "..." else ""))
    cat(sprintf("Features: %d biomechanical variables\n", length(object@features)))
    cat(sprintf("Points per cycle: %d\n", object@points_per_cycle))
    
    # Validation summary
    if (length(object@validation_report) > 0) {
      n_standard <- length(object@validation_report$standard_compliant)
      n_non_standard <- length(object@validation_report$non_standard)
      cat(sprintf("Variable validation: %d standard, %d non-standard\n", 
          n_standard, n_non_standard))
    }
    
    # Cache info
    if (length(object@cache) > 0) {
      cat(sprintf("Cached results: %d subject-task combinations\n", length(object@cache)))
    }
  }
)

#' @title Summary of LocomotionData Object
#' @description Provide detailed summary statistics
#' @param object LocomotionData object
#' @param ... Additional arguments (unused)
#' @export
setMethod("summary", "LocomotionData",
  function(object, ...) {
    cat("LocomotionData Summary\n")
    cat("======================\n")
    
    # Basic info
    show(object)
    
    # Data quality summary
    cat("\nData Quality Summary:\n")
    cat("---------------------\n")
    
    # Check for missing values
    missing_counts <- sapply(object@features, function(feat) {
      sum(is.na(object@data[[feat]]))
    })
    
    if (any(missing_counts > 0)) {
      cat("Features with missing values:\n")
      for (feat in names(missing_counts[missing_counts > 0])) {
        cat(sprintf("  %s: %d missing (%.1f%%)\n", 
            feat, missing_counts[feat], 
            100 * missing_counts[feat] / nrow(object@data)))
      }
    } else {
      cat("No missing values detected\n")
    }
    
    # Phase coverage
    phase_coverage <- object@data[, .(
      min_phase = min(get(object@phase_col), na.rm = TRUE),
      max_phase = max(get(object@phase_col), na.rm = TRUE),
      unique_phases = length(unique(get(object@phase_col)))
    )]
    
    cat(sprintf("\nPhase coverage: %.1f - %.1f%% (%d unique values)\n",
        phase_coverage$min_phase, phase_coverage$max_phase, 
        phase_coverage$unique_phases))
        
    # Feature types
    angle_features <- sum(grepl("angle", object@features))
    velocity_features <- sum(grepl("velocity", object@features))
    moment_features <- sum(grepl("moment", object@features))
    
    cat(sprintf("\nFeature breakdown:\n"))
    cat(sprintf("  Angles: %d\n", angle_features))
    cat(sprintf("  Velocities: %d\n", velocity_features))
    cat(sprintf("  Moments: %d\n", moment_features))
    cat(sprintf("  Other: %d\n", length(object@features) - angle_features - velocity_features - moment_features))
  }
)