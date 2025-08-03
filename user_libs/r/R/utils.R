#' @title Utility Functions
#' @description Helper functions for LocomotionData package
#' @name utils
NULL

#' @title Check Package Dependencies
#' @description Check if required packages are available
#' @param packages character vector of package names to check
#' @param suggest logical whether to suggest installation if missing
#' @return logical vector indicating which packages are available
#' @keywords internal
.checkPackages <- function(packages, suggest = TRUE) {
  available <- sapply(packages, requireNamespace, quietly = TRUE)
  
  if (suggest && any(!available)) {
    missing <- packages[!available]
    message(sprintf(
      "Suggested packages not available: %s\nInstall with: install.packages(c(%s))",
      paste(missing, collapse = ", "),
      paste(sprintf("'%s'", missing), collapse = ", ")
    ))
  }
  
  return(available)
}

#' @title Convert Degrees to Radians
#' @description Convert angle measurements from degrees to radians
#' @param degrees numeric vector of angles in degrees
#' @return numeric vector of angles in radians
#' @export
deg2rad <- function(degrees) {
  return(degrees * pi / 180)
}

#' @title Convert Radians to Degrees
#' @description Convert angle measurements from radians to degrees
#' @param radians numeric vector of angles in radians
#' @return numeric vector of angles in degrees
#' @export
rad2deg <- function(radians) {
  return(radians * 180 / pi)
}

#' @title Calculate Phase from Time
#' @description Calculate gait cycle phase from time data
#' @param time numeric vector of time values
#' @param events numeric vector of gait event times (heel strikes)
#' @return numeric vector of phase values (0-100)
#' @export
calculatePhase <- function(time, events) {
  if (length(events) < 2) {
    stop("Need at least 2 gait events to calculate phase")
  }
  
  phase <- numeric(length(time))
  
  for (i in seq_len(length(events) - 1)) {
    # Find time points in this gait cycle
    cycle_mask <- time >= events[i] & time < events[i + 1]
    cycle_time <- time[cycle_mask]
    
    if (length(cycle_time) > 0) {
      # Calculate phase as percentage of cycle
      cycle_duration <- events[i + 1] - events[i]
      cycle_phase <- 100 * (cycle_time - events[i]) / cycle_duration
      phase[cycle_mask] <- cycle_phase
    }
  }
  
  return(phase)
}

#' @title Interpolate to Phase Grid
#' @description Interpolate data to standard phase grid (0-100% with n points)
#' @param phase numeric vector of original phase values
#' @param data numeric vector of data values
#' @param n_points integer number of points in output grid (default: 150)
#' @return numeric vector of interpolated data
#' @export
interpolateToPhase <- function(phase, data, n_points = 150L) {
  if (length(phase) != length(data)) {
    stop("Phase and data vectors must have same length")
  }
  
  # Remove NAs
  valid_idx <- !is.na(phase) & !is.na(data)
  if (sum(valid_idx) < 2) {
    return(rep(NA_real_, n_points))
  }
  
  phase_clean <- phase[valid_idx]
  data_clean <- data[valid_idx]
  
  # Sort by phase
  sort_idx <- order(phase_clean)
  phase_clean <- phase_clean[sort_idx]
  data_clean <- data_clean[sort_idx]
  
  # Create target phase grid
  phase_grid <- seq(0, 100, length.out = n_points)
  
  # Interpolate
  if (min(phase_clean) > 0 || max(phase_clean) < 100) {
    warning("Phase data does not cover full 0-100% range")
  }
  
  interpolated <- stats::approx(
    x = phase_clean, 
    y = data_clean, 
    xout = phase_grid,
    method = "linear",
    rule = 2  # Use nearest value for extrapolation
  )$y
  
  return(interpolated)
}

#' @title Detect Gait Events
#' @description Simple heel strike detection from vertical ground reaction force
#' @param time numeric vector of time values
#' @param vgrf numeric vector of vertical ground reaction force values
#' @param threshold numeric threshold for heel strike detection (default: 50N)
#' @param min_cycle_time numeric minimum time between heel strikes (default: 0.5s)
#' @return numeric vector of heel strike times
#' @export
detectGaitEvents <- function(time, vgrf, threshold = 50, min_cycle_time = 0.5) {
  if (length(time) != length(vgrf)) {
    stop("Time and vGRF vectors must have same length")
  }
  
  # Find threshold crossings (foot contact)
  above_threshold <- vgrf > threshold
  crossings <- which(diff(above_threshold) == 1)  # Rising edge
  
  if (length(crossings) == 0) {
    warning("No heel strikes detected")
    return(numeric(0))
  }
  
  # Convert to time
  heel_strikes <- time[crossings + 1]  # +1 because diff reduces length by 1
  
  # Filter out events that are too close together
  if (length(heel_strikes) > 1) {
    valid_events <- logical(length(heel_strikes))
    valid_events[1] <- TRUE
    
    for (i in seq(2, length(heel_strikes))) {
      if (heel_strikes[i] - heel_strikes[which(valid_events)[length(which(valid_events))]] >= min_cycle_time) {
        valid_events[i] <- TRUE
      }
    }
    
    heel_strikes <- heel_strikes[valid_events]
  }
  
  return(heel_strikes)
}

#' @title Create Feature Summary
#' @description Create a summary table of available features
#' @param features character vector of feature names
#' @return data.frame with feature breakdown
#' @export
createFeatureSummary <- function(features) {
  if (length(features) == 0) {
    return(data.frame(
      type = character(0),
      count = integer(0),
      examples = character(0),
      stringsAsFactors = FALSE
    ))
  }
  
  # Categorize features
  angle_features <- features[grepl("angle", features)]
  velocity_features <- features[grepl("velocity", features)]
  moment_features <- features[grepl("moment", features)]
  power_features <- features[grepl("power", features)]
  grf_features <- features[grepl("grf", features)]
  cop_features <- features[grepl("cop", features)]
  other_features <- features[!grepl("angle|velocity|moment|power|grf|cop", features)]
  
  # Create summary
  summary_df <- data.frame(
    type = c("Angles", "Velocities", "Moments", "Powers", "GRF", "COP", "Other"),
    count = c(
      length(angle_features), length(velocity_features), length(moment_features),
      length(power_features), length(grf_features), length(cop_features), length(other_features)
    ),
    examples = c(
      if(length(angle_features) > 0) paste(head(angle_features, 2), collapse = ", ") else "",
      if(length(velocity_features) > 0) paste(head(velocity_features, 2), collapse = ", ") else "",
      if(length(moment_features) > 0) paste(head(moment_features, 2), collapse = ", ") else "",
      if(length(power_features) > 0) paste(head(power_features, 2), collapse = ", ") else "",
      if(length(grf_features) > 0) paste(head(grf_features, 2), collapse = ", ") else "",
      if(length(cop_features) > 0) paste(head(cop_features, 2), collapse = ", ") else "",
      if(length(other_features) > 0) paste(head(other_features, 2), collapse = ", ") else ""
    ),
    stringsAsFactors = FALSE
  )
  
  # Remove empty categories
  summary_df <- summary_df[summary_df$count > 0, ]
  
  return(summary_df)
}

#' @title Validate Data Dimensions
#' @description Validate that data dimensions are consistent for 3D reshaping
#' @param n_points integer total number of data points
#' @param points_per_cycle integer points per gait cycle
#' @return logical TRUE if dimensions are valid
#' @export
validateDataDimensions <- function(n_points, points_per_cycle = 150L) {
  if (n_points <= 0) {
    warning("No data points")
    return(FALSE)
  }
  
  if (points_per_cycle <= 0) {
    warning("Invalid points per cycle")
    return(FALSE)
  }
  
  if (n_points %% points_per_cycle != 0) {
    warning(sprintf(
      "Data length %d not divisible by %d points per cycle. Data may be incomplete or incorrectly formatted.",
      n_points, points_per_cycle
    ))
    return(FALSE)
  }
  
  n_cycles <- n_points %/% points_per_cycle
  if (n_cycles < 1) {
    warning("Less than one complete gait cycle")
    return(FALSE)
  }
  
  return(TRUE)
}

#' @title Format Feature Name
#' @description Format feature name for display (replace underscores with spaces)
#' @param feature_name character feature name
#' @return character formatted name
#' @export
formatFeatureName <- function(feature_name) {
  # Replace underscores with spaces
  formatted <- gsub("_", " ", feature_name)
  
  # Capitalize first letter of each word
  formatted <- tools::toTitleCase(formatted)
  
  # Fix common abbreviations
  formatted <- gsub("\\bRad\\b", "rad", formatted)
  formatted <- gsub("\\bNm\\b", "Nm", formatted)
  formatted <- gsub("\\bKg\\b", "kg", formatted)
  formatted <- gsub("\\bGrf\\b", "GRF", formatted)
  formatted <- gsub("\\bCop\\b", "COP", formatted)
  
  return(formatted)
}