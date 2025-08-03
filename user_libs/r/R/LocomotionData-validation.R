#' @title LocomotionData Validation Functions
#' @description Internal validation functions for LocomotionData class
#' @name LocomotionData-validation
NULL

#' @title Load Data With Validation
#' @description Load data with format detection and validation
#' @param object LocomotionData object
#' @param file_type character file type specification
#' @return data.table with loaded data
#' @keywords internal
.loadDataWithValidation <- function(object, file_type) {
  data_path <- object@data_path
  
  # Auto-detect file type
  if (file_type == "auto") {
    ext <- tools::file_ext(tolower(data_path))
    if (ext == "parquet") {
      file_type <- "parquet"
    } else if (ext %in% c("csv", "txt")) {
      file_type <- "csv"
    } else {
      # Try to detect based on file content
      tryCatch({
        # Try parquet first
        df <- data.table::setDT(arrow::read_parquet(data_path))
        return(df)
      }, error = function(e1) {
        tryCatch({
          # Fall back to CSV
          df <- data.table::fread(data_path)
          return(df)
        }, error = function(e2) {
          stop(sprintf("Unable to determine file format for extension: %s", ext))
        })
      })
    }
  }
  
  # Load based on specified type
  if (file_type == "parquet") {
    tryCatch({
      # Use enhanced parquet loading with memory management
      df <- loadParquetData(data_path, 
                           chunk_size = 100000L,
                           memory_limit = 2.0,
                           show_progress = TRUE,
                           validate_structure = TRUE)
    }, error = function(e) {
      stop(sprintf("Failed to read parquet file: %s", e$message))
    })
  } else if (file_type == "csv") {
    tryCatch({
      df <- data.table::fread(data_path)
    }, error = function(e) {
      stop(sprintf("Failed to read CSV file: %s", e$message))
    })
  } else {
    stop(sprintf("Unsupported file type: %s. Use 'parquet', 'csv', or 'auto'", file_type))
  }
  
  return(df)
}

#' @title Validate Required Columns
#' @description Validate that required columns exist in the dataset
#' @param object LocomotionData object
#' @keywords internal
.validateRequiredColumns <- function(object) {
  required_cols <- c(object@subject_col, object@task_col, object@phase_col)
  missing_cols <- setdiff(required_cols, names(object@data))
  
  if (length(missing_cols) > 0) {
    available_cols <- names(object@data)
    stop(sprintf(
      "Missing required columns: %s\nAvailable columns: %s\nHint: Use custom column names in constructor if your data uses different names",
      paste(missing_cols, collapse = ", "),
      paste(available_cols, collapse = ", ")
    ))
  }
}

#' @title Validate Data Format
#' @description Validate basic data format requirements
#' @param object LocomotionData object
#' @keywords internal
.validateDataFormat <- function(object) {
  # Check for empty dataset
  if (nrow(object@data) == 0) {
    stop("Dataset is empty")
  }
  
  # Check for phase data format  
  if (object@phase_col %in% names(object@data)) {
    phase_values <- object@data[[object@phase_col]]
    phase_values <- phase_values[!is.na(phase_values)]
    
    if (length(phase_values) == 0) {
      warning("Phase column contains only NA values")
    } else {
      # Check phase range
      min_phase <- min(phase_values, na.rm = TRUE)
      max_phase <- max(phase_values, na.rm = TRUE)
      
      if (min_phase < 0 || max_phase > 100) {
        warning(sprintf("Phase values outside expected range [0-100]: [%.1f, %.1f]", 
                       min_phase, max_phase))
      }
      
      # Check for time-indexed vs phase-indexed data
      if ("time" %in% names(object@data) || "time_s" %in% names(object@data)) {
        # Detect if this is time-indexed data
        phase_unique_per_subject_task <- object@data[, 
          .(unique_phases = length(unique(get(object@phase_col)))),
          by = c(object@subject_col, object@task_col)
        ]
        
        avg_unique_phases <- mean(phase_unique_per_subject_task$unique_phases)
        
        if (avg_unique_phases < 100) {  # Likely time-indexed
          warning(sprintf(
            "Data appears to be time-indexed (avg %.1f unique phase values per subject-task). LocomotionData works best with phase-indexed data (150 points per cycle). Consider converting to phase-indexed format.",
            avg_unique_phases
          ))
        }
      }
    }
  }
  
  # Check for reasonable data dimensions
  n_subjects <- length(unique(object@data[[object@subject_col]]))
  n_tasks <- length(unique(object@data[[object@task_col]]))
  
  if (n_subjects == 0) {
    stop("No subjects found in dataset")
  }
  if (n_tasks == 0) {
    stop("No tasks found in dataset")
  }
  
  cat(sprintf("Data validation passed: %d subjects, %d tasks\n", 
              n_subjects, n_tasks))
}

#' @title Identify Features
#' @description Identify available biomechanical features in the dataset
#' @param object LocomotionData object
#' @return Updated LocomotionData object
#' @keywords internal
.identifyFeatures <- function(object) {
  exclude_cols <- c(object@subject_col, object@task_col, object@phase_col,
                   'time', 'time_s', 'step_number', 'is_reconstructed_r',
                   'is_reconstructed_l', 'task_info', 'activity_number', 'cycle', 'step')
  
  # Identify biomechanical features - only standard naming accepted
  feature_keywords <- c('angle', 'velocity', 'moment', 'power')
  potential_features <- names(object@data)
  
  object@features <- potential_features[
    !potential_features %in% exclude_cols &
    sapply(potential_features, function(col) {
      any(sapply(feature_keywords, function(keyword) grepl(keyword, col)))
    })
  ]
  
  # Create identity mapping for standard features
  object@feature_mappings <- setNames(object@features, object@features)
  
  # Store unique subjects and tasks for external access
  object@subjects <- sort(unique(object@data[[object@subject_col]]))
  object@tasks <- sort(unique(object@data[[object@task_col]]))
  
  cat(sprintf("Loaded data with %d rows, %d subjects, %d tasks, %d features\n",
              nrow(object@data), length(object@subjects), 
              length(object@tasks), length(object@features)))
  
  return(object)
}

#' @title Validate Variable Names
#' @description Validate variable names against standard naming convention
#' @param object LocomotionData object  
#' @return Updated LocomotionData object
#' @keywords internal
.validateVariableNames <- function(object) {
  object@validation_report <- list(
    standard_compliant = character(0),
    non_standard = character(0),
    warnings = character(0),
    errors = character(0)
  )
  
  for (feature in object@features) {
    if (.isStandardCompliant(feature)) {
      object@validation_report$standard_compliant <- c(
        object@validation_report$standard_compliant, feature
      )
    } else {
      object@validation_report$non_standard <- c(
        object@validation_report$non_standard, feature
      )
      error_msg <- sprintf(
        "Variable '%s' does not follow standard naming convention: <joint>_<motion>_<measurement>_<side>_<unit>",
        feature
      )
      object@validation_report$errors <- c(
        object@validation_report$errors, error_msg
      )
      # Raise error for ALL non-compliant names
      stop(sprintf(
        "Non-standard variable name detected: '%s'. Expected format: <joint>_<motion>_<measurement>_<side>_<unit>. Suggestion: %s",
        feature, suggestStandardName(feature)
      ))
    }
  }
  
  # Print validation summary
  n_standard <- length(object@validation_report$standard_compliant)
  n_non_standard <- length(object@validation_report$non_standard)
  
  if (n_non_standard > 0) {
    cat(sprintf("Variable name validation: %d standard, %d non-standard\n", 
                n_standard, n_non_standard))
  } else {
    cat(sprintf("Variable name validation: All %d variables are standard compliant\n", 
                n_standard))
  }
  
  return(object)
}

#' @title Check Standard Compliance
#' @description Check if variable name follows standard convention
#' @param variable_name character variable name to check
#' @return logical TRUE if compliant, FALSE otherwise
#' @keywords internal
.isStandardCompliant <- function(variable_name) {
  parts <- strsplit(variable_name, "_")[[1]]
  
  # Get standard constants
  constants <- getFeatureConstants()
  
  # Handle compound units like 'rad_s', 'Nm_kg', etc.
  if (length(parts) == 6 && paste(parts[5:6], collapse = "_") %in% constants$standard_units) {
    # Recombine the unit
    unit <- paste(parts[5:6], collapse = "_")
    joint <- parts[1]
    motion <- parts[2] 
    measurement <- parts[3]
    side <- parts[4]
  } else if (length(parts) == 5) {
    joint <- parts[1]
    motion <- parts[2]
    measurement <- parts[3] 
    side <- parts[4]
    unit <- parts[5]
  } else {
    return(FALSE)
  }
  
  return(
    joint %in% constants$standard_joints &&
    motion %in% constants$standard_motions &&
    measurement %in% constants$standard_measurements &&
    side %in% constants$standard_sides &&
    unit %in% constants$standard_units
  )
}

#' @title Check Standard Compliance (Exported)
#' @description Check if variable name follows standard convention
#' @param variable_name character variable name to check
#' @return logical TRUE if compliant, FALSE otherwise
#' @export
isStandardCompliant <- function(variable_name) {
  .isStandardCompliant(variable_name)
}

#' @title Suggest Standard Name
#' @description Suggest standard compliant name for a variable
#' @param variable_name character variable name
#' @return character suggested standard name
#' @export
suggestStandardName <- function(variable_name) {
  # Basic heuristics for suggestion
  lower_name <- tolower(variable_name)
  constants <- getFeatureConstants()
  
  # Try to identify joint
  joint <- "unknown"
  for (j in constants$standard_joints) {
    if (grepl(j, lower_name)) {
      joint <- j
      break
    }
  }
  
  # Try to identify motion
  motion <- "flexion"
  for (m in constants$standard_motions) {
    if (grepl(m, lower_name)) {
      motion <- m
      break
    }
  }
  
  # Try to identify measurement  
  measurement <- "angle"
  for (meas in constants$standard_measurements) {
    if (grepl(meas, lower_name)) {
      measurement <- meas
      break
    }
  }
  
  # Try to identify side
  if (grepl("contra|contralateral", lower_name)) {
    side <- "contra"
  } else if (grepl("ipsi|ipsilateral", lower_name)) {
    side <- "ipsi"
  } else {
    side <- "ipsi"  # default
  }
  
  # Try to identify unit
  if (grepl("rad", lower_name) && grepl("s", lower_name)) {
    unit <- "rad_s"
  } else if (grepl("rad", lower_name)) {
    unit <- "rad"
  } else if (grepl("deg", lower_name) && grepl("s", lower_name)) {
    unit <- "deg_s"
  } else if (grepl("deg", lower_name)) {
    unit <- "deg"
  } else if (grepl("nm", lower_name) && grepl("kg", lower_name)) {
    unit <- "Nm_kg"
  } else if (grepl("nm", lower_name)) {
    unit <- "Nm"
  } else {
    unit <- "rad"  # default for angles
  }
  
  return(paste(joint, motion, measurement, side, unit, sep = "_"))
}