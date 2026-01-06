#' @title Data Loading Functions
#' @description Enhanced Parquet file reading and data validation for LocomotionData
#' @name data-loading
NULL

#' @title Load Parquet Data with Arrow
#' @description Memory-efficient parquet file loading with streaming support
#' 
#' @param file_path character path to parquet file
#' @param chunk_size integer number of rows to read at once for large files (default: 100000)
#' @param memory_limit numeric maximum memory usage in GB (default: 2)
#' @param show_progress logical whether to show progress for large files (default: TRUE)
#' @param validate_structure logical whether to validate parquet structure (default: TRUE)
#' 
#' @return data.table with loaded data
#' @export
#' 
#' @examples
#' \dontrun{
#' # Load standard parquet file
#' data <- loadParquetData("gait_data.parquet")
#' 
#' # Load large file with chunking
#' data <- loadParquetData("large_dataset.parquet", chunk_size = 50000)
#' 
#' # Load with memory constraints
#' data <- loadParquetData("dataset.parquet", memory_limit = 1.5)
#' }
loadParquetData <- function(file_path, chunk_size = 100000L, memory_limit = 2.0, 
                           show_progress = TRUE, validate_structure = TRUE) {
  
  # Validate input parameters
  if (!file.exists(file_path)) {
    stop(sprintf("Parquet file not found: %s", file_path))
  }
  
  if (!requireNamespace("arrow", quietly = TRUE)) {
    stop("Package 'arrow' is required but not installed. Install with: install.packages('arrow')")
  }
  
  if (chunk_size <= 0) {
    stop("chunk_size must be positive")
  }
  
  if (memory_limit <= 0) {
    stop("memory_limit must be positive")
  }
  
  # Check file size and determine loading strategy
  file_info <- file.info(file_path)
  file_size_gb <- file_info$size / (1024^3)
  
  if (show_progress) {
    cat(sprintf("Loading parquet file: %s (%.2f GB)\n", basename(file_path), file_size_gb))
  }
  
  # Try to open parquet file to get metadata
  tryCatch({
    parquet_file <- arrow::open_dataset(file_path)
    schema <- parquet_file$schema
    
    if (validate_structure) {
      validation_result <- validateParquetStructure(file_path, parquet_file = parquet_file)
      if (!validation_result$valid) {
        warning(sprintf("Parquet structure validation issues: %s", 
                       paste(validation_result$issues, collapse = "; ")))
      }
    }
    
  }, error = function(e) {
    stop(sprintf("Failed to open parquet file: %s", e$message))
  })
  
  # Determine loading strategy based on file size
  if (file_size_gb > memory_limit) {
    if (show_progress) {
      cat(sprintf("Large file detected (%.2f GB > %.2f GB limit). Using chunked loading...\n", 
                  file_size_gb, memory_limit))
    }
    
    # Use chunked loading for large files
    data <- .loadParquetChunked(parquet_file, chunk_size, show_progress)
    
  } else {
    # Load entire file for smaller files
    if (show_progress) {
      cat("Loading entire file into memory...\n")
    }
    
    tryCatch({
      data <- data.table::setDT(arrow::read_parquet(file_path))
    }, error = function(e) {
      stop(sprintf("Failed to read parquet file: %s", e$message))
    })
  }
  
  # Basic data validation
  if (nrow(data) == 0) {
    stop("Loaded dataset is empty")
  }
  
  if (show_progress) {
    cat(sprintf("Successfully loaded %d rows x %d columns\n", nrow(data), ncol(data)))
  }
  
  return(data)
}

#' @title Chunked Parquet Loading
#' @description Load large parquet files in chunks to manage memory usage
#' @param parquet_file arrow dataset object
#' @param chunk_size integer rows per chunk
#' @param show_progress logical whether to show progress
#' @return data.table with combined data
#' @keywords internal
.loadParquetChunked <- function(parquet_file, chunk_size, show_progress) {
  
  # Get total row count if possible
  total_rows <- tryCatch({
    nrow(parquet_file)
  }, error = function(e) {
    NA_integer_
  })
  
  chunks <- list()
  chunk_idx <- 1
  rows_read <- 0
  
  # Create scanner for batch reading
  scanner <- arrow::Scanner$create(parquet_file)
  
  if (show_progress && !is.na(total_rows)) {
    cat(sprintf("Reading %d total rows in chunks of %d...\n", total_rows, chunk_size))
  }
  
  # Read in batches
  tryCatch({
    batch_reader <- scanner$ToRecordBatchReader()
    
    while (TRUE) {
      batch <- batch_reader$read_next_batch()
      if (is.null(batch)) break
      
      # Convert batch to data.table
      chunk_df <- data.table::setDT(as.data.frame(batch))
      chunks[[chunk_idx]] <- chunk_df
      
      rows_read <- rows_read + nrow(chunk_df)
      
      if (show_progress) {
        if (!is.na(total_rows)) {
          progress_pct <- 100 * rows_read / total_rows
          cat(sprintf("\rProgress: %d/%d rows (%.1f%%)", rows_read, total_rows, progress_pct))
        } else {
          cat(sprintf("\rRows read: %d", rows_read))
        }
        flush.console()
      }
      
      chunk_idx <- chunk_idx + 1
      
      # Memory check
      if (chunk_idx %% 10 == 0) {
        gc(verbose = FALSE)
      }
    }
    
  }, error = function(e) {
    stop(sprintf("Error during chunked reading: %s", e$message))
  })
  
  if (show_progress) {
    cat(sprintf("\nCombining %d chunks...\n", length(chunks)))
  }
  
  # Combine all chunks
  if (length(chunks) == 0) {
    stop("No data chunks were successfully read")
  }
  
  data <- data.table::rbindlist(chunks, use.names = TRUE, fill = TRUE)
  
  # Clean up
  rm(chunks)
  gc(verbose = FALSE)
  
  return(data)
}

#' @title Validate Parquet Structure
#' @description Validate parquet file structure and required columns
#' 
#' @param file_path character path to parquet file
#' @param required_columns character vector of required column names
#' @param subject_col character name of subject column (default: "subject")
#' @param task_col character name of task column (default: "task") 
#' @param phase_col character name of phase column (default: "phase")
#' @param parquet_file optional already opened arrow dataset
#' 
#' @return list with validation results
#' @export
#' 
#' @examples
#' \dontrun{
#' # Basic structure validation
#' result <- validateParquetStructure("data.parquet")
#' 
#' # Validate specific columns
#' result <- validateParquetStructure("data.parquet", 
#'                                   required_columns = c("knee_angle", "hip_moment"))
#' }
validateParquetStructure <- function(file_path, required_columns = NULL,
                                   subject_col = "subject", task_col = "task", 
                                   phase_col = "phase", parquet_file = NULL) {
  
  if (!requireNamespace("arrow", quietly = TRUE)) {
    stop("Package 'arrow' is required but not installed. Install with: install.packages('arrow')")
  }
  
  validation_result <- list(
    valid = TRUE,
    issues = character(0),
    warnings = character(0),
    file_info = list(),
    column_info = list(),
    data_format_info = list()
  )
  
  # Open parquet file if not provided
  if (is.null(parquet_file)) {
    tryCatch({
      parquet_file <- arrow::open_dataset(file_path)
    }, error = function(e) {
      validation_result$valid <<- FALSE  
      validation_result$issues <<- c(validation_result$issues, 
                                   sprintf("Cannot open parquet file: %s", e$message))
      return(validation_result)
    })
  }
  
  # Get schema information
  tryCatch({
    schema <- parquet_file$schema
    column_names <- names(schema)
    
    # Store file info
    if (file.exists(file_path)) {
      file_info <- file.info(file_path)
      validation_result$file_info <- list(
        size_mb = round(file_info$size / (1024^2), 2),
        modified = file_info$mtime
      )
    }
    
    # Store column info
    validation_result$column_info <- list(
      total_columns = length(column_names),
      column_names = column_names,
      column_types = sapply(schema, function(field) field$type$ToString())
    )
    
  }, error = function(e) {
    validation_result$valid <<- FALSE
    validation_result$issues <<- c(validation_result$issues,
                                 sprintf("Cannot read schema: %s", e$message))
    return(validation_result)
  })
  
  # Check for required core columns
  core_required <- c(subject_col, task_col, phase_col)
  missing_core <- setdiff(core_required, column_names)
  
  if (length(missing_core) > 0) {
    validation_result$valid <- FALSE
    validation_result$issues <- c(validation_result$issues, 
                                sprintf("Missing required columns: %s", 
                                       paste(missing_core, collapse = ", ")))
  }
  
  # Check for additional required columns
  if (!is.null(required_columns)) {
    missing_additional <- setdiff(required_columns, column_names)
    if (length(missing_additional) > 0) {
      validation_result$valid <- FALSE
      validation_result$issues <- c(validation_result$issues,
                                  sprintf("Missing specified columns: %s",
                                         paste(missing_additional, collapse = ", ")))
    }
  }
  
  # Try to read a small sample to validate data format
  tryCatch({
    sample_data <- data.table::setDT(
      as.data.frame(arrow::compute_table(parquet_file$head(1000)))
    )
    
    # Validate phase indexing if phase column exists
    if (phase_col %in% column_names) {
      phase_validation <- .validatePhaseIndexing(sample_data, phase_col, subject_col, task_col)
      validation_result$data_format_info$phase_validation <- phase_validation
      
      if (!phase_validation$is_phase_indexed) {
        validation_result$warnings <- c(validation_result$warnings,
                                      phase_validation$message)
      }
    }
    
    # Check for missing values in core columns
    for (col in core_required) {
      if (col %in% column_names) {
        na_count <- sum(is.na(sample_data[[col]]))
        if (na_count > 0) {
          validation_result$warnings <- c(validation_result$warnings,
                                        sprintf("Column '%s' has %d missing values in sample", 
                                               col, na_count))
        }
      }
    }
    
    # Basic data type validation
    if (phase_col %in% column_names && !is.numeric(sample_data[[phase_col]])) {
      validation_result$warnings <- c(validation_result$warnings,
                                    sprintf("Phase column '%s' is not numeric", phase_col))
    }
    
  }, error = function(e) {
    validation_result$warnings <- c(validation_result$warnings,
                                  sprintf("Could not validate data sample: %s", e$message))
  })
  
  return(validation_result)
}

#' @title Validate Phase Indexing
#' @description Check if data uses proper phase indexing (150 points per cycle)
#' @param data data.table with sample data
#' @param phase_col character name of phase column
#' @param subject_col character name of subject column  
#' @param task_col character name of task column
#' @return list with phase validation results
#' @keywords internal
.validatePhaseIndexing <- function(data, phase_col, subject_col, task_col) {
  
  result <- list(
    is_phase_indexed = FALSE,
    message = "",
    points_per_cycle = NA_integer_,
    phase_range = c(NA_real_, NA_real_)
  )
  
  if (!phase_col %in% names(data)) {
    result$message <- sprintf("Phase column '%s' not found", phase_col)
    return(result)
  }
  
  phase_values <- data[[phase_col]]
  phase_values <- phase_values[!is.na(phase_values)]
  
  if (length(phase_values) == 0) {
    result$message <- "Phase column contains only missing values"
    return(result)
  }
  
  result$phase_range <- c(min(phase_values), max(phase_values))
  
  # Check if we have subject-task combinations to analyze
  if (subject_col %in% names(data) && task_col %in% names(data)) {
    
    # Calculate unique phases per subject-task combination
    phase_summary <- data[, .(
      unique_phases = length(unique(get(phase_col)[!is.na(get(phase_col))])),
      total_points = .N
    ), by = c(subject_col, task_col)]
    
    avg_unique_phases <- mean(phase_summary$unique_phases, na.rm = TRUE)
    result$points_per_cycle <- round(avg_unique_phases)
    
    # Check if this looks like phase-indexed data (expecting ~150 unique phases)
    if (avg_unique_phases >= 140 && avg_unique_phases <= 160) {
      result$is_phase_indexed <- TRUE
      result$message <- sprintf("Data appears phase-indexed with ~%.0f points per cycle", avg_unique_phases)
    } else if (avg_unique_phases < 50) {
      result$message <- sprintf("Data appears time-indexed (%.0f unique phases per cycle). Consider converting to phase-indexed format.", avg_unique_phases)
    } else {
      result$message <- sprintf("Unusual phase distribution (%.0f unique phases per cycle)", avg_unique_phases)
    }
    
  } else {
    # Can't determine without subject/task grouping
    unique_phases <- length(unique(phase_values))
    result$points_per_cycle <- unique_phases
    
    if (unique_phases >= 140 && unique_phases <= 160) {
      result$is_phase_indexed <- TRUE
      result$message <- sprintf("Data appears phase-indexed with %d unique phases", unique_phases)
    } else {
      result$message <- sprintf("Cannot determine phase indexing format (%d unique phases)", unique_phases)
    }
  }
  
  return(result)
}

#' @title Auto-detect Data Format
#' @description Automatically detect if data is phase-indexed or time-indexed
#' 
#' @param file_path character path to data file
#' @param sample_size integer number of rows to sample for detection (default: 5000)
#' @param subject_col character name of subject column (default: "subject")
#' @param task_col character name of task column (default: "task")
#' @param phase_col character name of phase column (default: "phase")
#' 
#' @return list with format detection results
#' @export
#' 
#' @examples
#' \dontrun{
#' format_info <- detectDataFormat("dataset.parquet")
#' if (format_info$format == "time_indexed") {
#'   # Convert to phase-indexed
#'   data <- convertTimeToPhase(file_path)
#' }
#' }
detectDataFormat <- function(file_path, sample_size = 5000L, 
                           subject_col = "subject", task_col = "task", 
                           phase_col = "phase") {
  
  if (!file.exists(file_path)) {
    stop(sprintf("File not found: %s", file_path))
  }
  
  # Load sample data
  if (tools::file_ext(tolower(file_path)) == "parquet") {
    sample_data <- data.table::setDT(
      as.data.frame(arrow::read_parquet(file_path, n_max = sample_size))
    )
  } else {
    sample_data <- data.table::fread(file_path, nrows = sample_size)
  }
  
  result <- list(
    format = "unknown",
    confidence = 0.0,
    details = list(),
    recommendations = character(0)
  )
  
  # Check for time columns
  time_cols <- names(sample_data)[grepl("time", names(sample_data), ignore.case = TRUE)]
  has_time_col <- length(time_cols) > 0
  
  # Analyze phase column if present
  if (phase_col %in% names(sample_data)) {
    phase_validation <- .validatePhaseIndexing(sample_data, phase_col, subject_col, task_col)
    result$details$phase_info <- phase_validation
    
    if (phase_validation$is_phase_indexed) {
      result$format <- "phase_indexed"
      result$confidence <- 0.9
      result$recommendations <- c("Data is properly phase-indexed and ready for analysis")
      
    } else if (has_time_col) {
      result$format <- "time_indexed"  
      result$confidence <- 0.8
      result$recommendations <- c(
        "Data appears time-indexed. Consider converting to phase-indexed format using convertTimeToPhase()",
        sprintf("Time columns detected: %s", paste(time_cols, collapse = ", "))
      )
      
    } else {
      result$format <- "unknown"
      result$confidence <- 0.3
      result$recommendations <- c(
        "Cannot determine format. Check phase column values and consider data preprocessing"
      )
    }
    
  } else {
    # No phase column
    if (has_time_col) {
      result$format <- "time_indexed"
      result$confidence <- 0.7
      result$recommendations <- c(
        "No phase column found. Data appears time-indexed.",
        "You may need to calculate gait cycle phases from gait events",
        sprintf("Time columns detected: %s", paste(time_cols, collapse = ", "))
      )
    } else {
      result$format <- "unknown"
      result$confidence <- 0.1
      result$recommendations <- c(
        "Cannot determine data format. No phase or time columns detected.",
        "Check column names and data structure"
      )
    }
  }
  
  # Additional format clues
  result$details$column_info <- list(
    total_columns = ncol(sample_data),
    has_time_columns = has_time_col,
    time_columns = time_cols,
    has_phase_column = phase_col %in% names(sample_data),
    sample_rows = nrow(sample_data)
  )
  
  return(result)
}

#' @title Convert Time-indexed to Phase-indexed Data
#' @description Convert time-indexed locomotion data to phase-indexed format
#' 
#' @param file_path character path to time-indexed data file
#' @param output_path character path for output phase-indexed file (optional)
#' @param time_col character name of time column (default: "time")
#' @param subject_col character name of subject column (default: "subject")
#' @param task_col character name of task column (default: "task")
#' @param gait_events_col character name of gait events column (optional)
#' @param points_per_cycle integer target points per cycle (default: 150)
#' @param show_progress logical whether to show conversion progress (default: TRUE)
#' 
#' @return data.table with phase-indexed data
#' @export
#' 
#' @examples
#' \dontrun{
#' # Convert time-indexed data to phase-indexed
#' phase_data <- convertTimeToPhase("time_data.parquet", "phase_data.parquet")
#' 
#' # Convert with custom parameters
#' phase_data <- convertTimeToPhase("time_data.csv", 
#'                                 time_col = "time_s",
#'                                 points_per_cycle = 101)
#' }
convertTimeToPhase <- function(file_path, output_path = NULL, time_col = "time",
                              subject_col = "subject", task_col = "task", 
                              gait_events_col = NULL, points_per_cycle = 150L,
                              show_progress = TRUE) {
  
  if (!file.exists(file_path)) {
    stop(sprintf("File not found: %s", file_path))
  }
  
  # Load time-indexed data
  if (show_progress) {
    cat("Loading time-indexed data...\n")
  }
  
  if (tools::file_ext(tolower(file_path)) == "parquet") {
    data <- loadParquetData(file_path, show_progress = show_progress, validate_structure = FALSE)
  } else {
    data <- data.table::fread(file_path)
  }
  
  # Validate required columns
  required_cols <- c(time_col, subject_col, task_col)
  missing_cols <- setdiff(required_cols, names(data))
  if (length(missing_cols) > 0) {
    stop(sprintf("Missing required columns: %s", paste(missing_cols, collapse = ", ")))
  }
  
  if (show_progress) {
    cat(sprintf("Converting %d rows for %d subjects...\n", 
                nrow(data), length(unique(data[[subject_col]]))))
  }
  
  # Identify biomechanical feature columns  
  exclude_cols <- c(subject_col, task_col, time_col, "step_number", "gait_event", 
                   "is_reconstructed_r", "is_reconstructed_l", "task_info", 
                   "activity_number", "cycle", "step")
  
  if (!is.null(gait_events_col)) {
    exclude_cols <- c(exclude_cols, gait_events_col)
  }
  
  feature_cols <- setdiff(names(data), exclude_cols)
  
  if (length(feature_cols) == 0) {
    stop("No biomechanical feature columns found")
  }
  
  # Convert each subject-task combination
  phase_data_list <- list()
  
  subject_task_combinations <- data[, .N, by = c(subject_col, task_col)][N > 0]
  
  if (show_progress) {
    cat(sprintf("Processing %d subject-task combinations...\n", nrow(subject_task_combinations)))
  }
  
  for (i in seq_len(nrow(subject_task_combinations))) {
    subject_id <- subject_task_combinations[[subject_col]][i]
    task_id <- subject_task_combinations[[task_col]][i]
    
    if (show_progress && i %% 10 == 0) {
      cat(sprintf("\rProgress: %d/%d combinations", i, nrow(subject_task_combinations)))
      flush.console()
    }
    
    # Extract subject-task data
    subset_data <- data[get(subject_col) == subject_id & get(task_col) == task_id]
    
    if (nrow(subset_data) < 10) {
      next  # Skip combinations with too little data
    }
    
    # Convert to phase-indexed
    tryCatch({
      phase_subset <- .convertSubjectTaskToPhase(
        subset_data, time_col, feature_cols, points_per_cycle, 
        gait_events_col, subject_id, task_id, subject_col, task_col
      )
      
      if (!is.null(phase_subset) && nrow(phase_subset) > 0) {
        phase_data_list[[length(phase_data_list) + 1]] <- phase_subset
      }
      
    }, error = function(e) {
      warning(sprintf("Failed to convert subject %s, task %s: %s", 
                     subject_id, task_id, e$message))
    })
  }
  
  if (show_progress) {
    cat(sprintf("\nCombining data from %d successful conversions...\n", length(phase_data_list)))
  }
  
  # Combine all phase-indexed data
  if (length(phase_data_list) == 0) {
    stop("No data could be successfully converted to phase-indexed format")
  }
  
  phase_data <- data.table::rbindlist(phase_data_list, use.names = TRUE, fill = TRUE)
  
  # Save output if path provided
  if (!is.null(output_path)) {
    if (show_progress) {
      cat(sprintf("Saving phase-indexed data to %s...\n", output_path))
    }
    
    if (tools::file_ext(tolower(output_path)) == "parquet") {
      arrow::write_parquet(phase_data, output_path)
    } else {
      data.table::fwrite(phase_data, output_path)
    }
  }
  
  if (show_progress) {
    cat(sprintf("Conversion complete: %d rows x %d columns\n", nrow(phase_data), ncol(phase_data)))
  }
  
  return(phase_data)
}

#' @title Convert Single Subject-Task to Phase
#' @description Convert single subject-task combination from time to phase indexing
#' @param data data.table with time-indexed data for single subject-task
#' @param time_col character name of time column
#' @param feature_cols character vector of feature column names
#' @param points_per_cycle integer target points per cycle
#' @param gait_events_col character name of gait events column (optional)
#' @param subject_id character subject identifier
#' @param task_id character task identifier  
#' @param subject_col character name of subject column
#' @param task_col character name of task column
#' @return data.table with phase-indexed data
#' @keywords internal
.convertSubjectTaskToPhase <- function(data, time_col, feature_cols, points_per_cycle,
                                      gait_events_col, subject_id, task_id, 
                                      subject_col, task_col) {
  
  # Sort by time
  data <- data[order(get(time_col))]
  time_vec <- data[[time_col]]
  
  # Detect gait events if not provided
  if (is.null(gait_events_col)) {
    # Simple heel strike detection - look for vertical GRF if available
    vgrf_cols <- names(data)[grepl("grf.*vertical|vgrf", names(data), ignore.case = TRUE)]
    
    if (length(vgrf_cols) > 0) {
      vgrf_data <- data[[vgrf_cols[1]]]
      heel_strikes <- detectGaitEvents(time_vec, vgrf_data)
    } else {
      # Fallback: assume regular gait cycles based on typical walking cadence
      typical_cycle_time <- 1.2  # seconds
      heel_strikes <- seq(min(time_vec), max(time_vec), by = typical_cycle_time)
    }
  } else {
    # Use provided gait events
    heel_strikes <- data[get(gait_events_col) == 1][[time_col]]
  }
  
  if (length(heel_strikes) < 2) {
    return(NULL)  # Need at least 2 heel strikes for one cycle
  }
  
  # Calculate phases for each gait cycle
  phase_data_list <- list()
  
  for (cycle_idx in seq_len(length(heel_strikes) - 1)) {
    cycle_start <- heel_strikes[cycle_idx]
    cycle_end <- heel_strikes[cycle_idx + 1]
    
    # Extract data for this cycle
    cycle_mask <- time_vec >= cycle_start & time_vec < cycle_end
    cycle_data <- data[cycle_mask]
    
    if (nrow(cycle_data) < 5) {
      next  # Skip cycles with too little data
    }
    
    cycle_time <- cycle_data[[time_col]]
    
    # Calculate phases (0-100%)
    cycle_duration <- cycle_end - cycle_start
    cycle_phases <- 100 * (cycle_time - cycle_start) / cycle_duration
    
    # Create phase grid
    phase_grid <- seq(0, 100, length.out = points_per_cycle)
    
    # Interpolate each feature to phase grid
    phase_row_list <- list()
    
    for (phase_idx in seq_along(phase_grid)) {
      target_phase <- phase_grid[phase_idx]
      
      # Create output row
      phase_row <- list()
      phase_row[[subject_col]] <- subject_id
      phase_row[[task_col]] <- task_id
      phase_row[["phase"]] <- target_phase
      
      # Interpolate each feature
      for (feature in feature_cols) {
        feature_data <- cycle_data[[feature]]
        
        if (all(is.na(feature_data))) {
          phase_row[[feature]] <- NA_real_
        } else {
          # Linear interpolation
          interp_value <- tryCatch({
            stats::approx(cycle_phases, feature_data, xout = target_phase, 
                         method = "linear", rule = 2)$y
          }, error = function(e) {
            NA_real_
          })
          
          phase_row[[feature]] <- interp_value
        }
      }
      
      phase_row_list[[phase_idx]] <- phase_row
    }
    
    # Combine phase points for this cycle
    if (length(phase_row_list) > 0) {
      cycle_phase_data <- data.table::rbindlist(phase_row_list, use.names = TRUE, fill = TRUE)
      phase_data_list[[cycle_idx]] <- cycle_phase_data
    }
  }
  
  # Combine all cycles
  if (length(phase_data_list) == 0) {
    return(NULL)
  }
  
  result <- data.table::rbindlist(phase_data_list, use.names = TRUE, fill = TRUE)
  return(result)
}

#' @title Get Memory Usage Information
#' @description Get current R session memory usage
#' @return list with memory usage information
#' @export
getMemoryUsage <- function() {
  
  # Get memory usage using pryr if available, otherwise use gc()
  if (requireNamespace("pryr", quietly = TRUE)) {
    mem_used <- pryr::mem_used() / (1024^3)  # Convert to GB
  } else {
    # Fallback to gc() output
    gc_info <- gc()
    mem_used <- sum(gc_info[, "max used"]) / 1024  # Convert to GB (rough estimate)
  }
  
  # Get object sizes in global environment
  objects <- ls(envir = .GlobalEnv)
  object_sizes <- sapply(objects, function(obj) {
    tryCatch({
      object.size(get(obj, envir = .GlobalEnv)) / (1024^2)  # MB
    }, error = function(e) 0)
  })
  
  return(list(
    total_memory_gb = round(mem_used, 3),
    largest_objects = head(sort(object_sizes, decreasing = TRUE), 5),
    r_version = R.version.string,
    memory_method = if (requireNamespace("pryr", quietly = TRUE)) "pryr" else "gc_fallback"
  ))
}