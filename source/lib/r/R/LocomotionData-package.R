#' @title LocomotionData: Standardized Locomotion Data Analysis
#' @description An R package for loading, processing, and analyzing standardized biomechanical locomotion data
#' 
#' @details
#' The LocomotionData package provides S4 classes and methods for efficient handling 
#' of phase-indexed gait cycle data with comprehensive validation, statistical
#' analysis, and publication-ready visualization tools. It implements the 
#' locomotion data standardization framework with strict variable naming 
#' conventions and quality assessment methods.
#' 
#' @section Features:
#' \itemize{
#'   \item Strict variable name validation with standard convention enforcement
#'   \item Efficient 3D array operations for gait cycle analysis
#'   \item Comprehensive data quality assessment
#'   \item Statistical analysis and outlier detection
#'   \item Publication-ready visualization tools with ggplot2
#'   \item Multi-format data loading (parquet, CSV)
#' }
#' 
#' @section Quick Start:
#' \preformatted{
#' library(LocomotionData)
#' 
#' # Load standardized locomotion data
#' loco <- loadLocomotionData("gait_data.parquet")
#' 
#' # Basic analysis
#' cycles_result <- getCycles(loco, "SUB01", "normal_walk")
#' mean_patterns <- getMeanPatterns(loco, "SUB01", "normal_walk")
#' rom_data <- calculateROM(loco, "SUB01", "normal_walk")
#' 
#' # Quality assessment
#' valid_mask <- validateCycles(loco, "SUB01", "normal_walk")
#' outliers <- findOutlierCycles(loco, "SUB01", "normal_walk")
#' 
#' # Variable name validation
#' validation_report <- getValidationReport(loco)
#' 
#' # Visualization
#' plotPhasePatterns(loco, "SUB01", "normal_walk", 
#'                   c("knee_flexion_angle_contra_rad"))
#' }
#' 
#' @section Variable Naming Convention:
#' Standard convention: <joint>_<motion>_<measurement>_<side>_<unit>
#' \itemize{
#'   \item knee_flexion_angle_contra_rad
#'   \item hip_flexion_moment_ipsi_Nm
#'   \item ankle_flexion_velocity_contra_rad_s
#' }
#' 
#' All variable names must follow the standard convention. Non-compliant names will raise an error.
#' 
#' @section Main Classes:
#' \itemize{
#'   \item \code{\link{LocomotionData-class}}: Main S4 class for locomotion data analysis
#' }
#' 
#' @section Key Functions:
#' \itemize{
#'   \item \code{\link{loadLocomotionData}}: Load data into LocomotionData object
#'   \item \code{\link{getCycles}}: Extract 3D array of gait cycles
#'   \item \code{\link{getMeanPatterns}}: Calculate mean patterns across cycles
#'   \item \code{\link{validateCycles}}: Validate cycles based on biomechanical constraints
#'   \item \code{\link{plotPhasePatterns}}: Create phase-normalized pattern plots
#'   \item \code{\link{efficientReshape3D}}: Standalone 3D reshaping function
#' }
#' 
#' @section Feature Constants:
#' \itemize{
#'   \item \code{\link{ANGLE_FEATURES}}: Standard joint angle features
#'   \item \code{\link{VELOCITY_FEATURES}}: Standard joint velocity features  
#'   \item \code{\link{MOMENT_FEATURES}}: Standard joint moment features
#'   \item \code{\link{getFeatureConstants}}: Access all feature constants
#' }
#' 
#' @author José A. Montes Pérez \email{jmontp@@umich.edu}
#' @author Claude AI Assistant (code generation and architecture design)
#' 
#' @references
#' Locomotion Data Standardization Framework Documentation:
#' \url{https://github.com/jmontp/locomotion-data-standardization}
#' 
#' @keywords package locomotion biomechanics gait analysis
#' @docType package
#' @name LocomotionData-package
#' @aliases LocomotionData-package
NULL

# Package startup message
.onAttach <- function(libname, pkgname) {
  packageStartupMessage(
    "LocomotionData v", utils::packageVersion("LocomotionData"), " loaded.\n",
    "For help getting started, see: vignette('getting-started', package = 'LocomotionData')\n",
    "Variable naming convention: <joint>_<motion>_<measurement>_<side>_<unit>"
  )
}

# Global variables to avoid R CMD check notes
utils::globalVariables(c(
  ".",
  "get",
  "..actual_columns",
  "..valid_features"
))