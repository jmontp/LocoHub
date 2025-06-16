---
title: Data Contracts
tags: [data, contracts, interfaces]
status: ready
---

# Data Contracts

**Method signatures and behavioral contracts for all critical components.**

*Detailed specifications with requirements traceability and standardized error handling patterns.*

## Requirements Traceability

Each interface contract directly supports specific user requirements from Document 10 and workflow sequences from Document 06:

### Workflow Integration Mapping
- **Sequence 1 (Dataset Conversion)** → PhaseValidator, TimeValidator, QualityAssessor
- **Sequence 2A (Manual Validation)** → ValidationSpecManager, PhaseValidator  
- **Sequence 2B (Automatic Validation)** → AutomatedFineTuner, ValidationSpecManager
- **Sequence 3 (Quality Assessment)** → PhaseValidator, QualityAssessor
- **Sequence 4 (ML Benchmarks)** → BenchmarkCreator

### Requirements Mapping (Document 10)
- **PhaseValidator** → Requirements F1 (Dataset Validation Infrastructure), User Stories C02, V01, V03
- **TimeValidator** → Requirements F4 (Phase-Indexed Dataset Generation), User Story C03
- **QualityAssessor** → Requirements F1 (Dataset Validation Infrastructure), User Story C02
- **DatasetComparator** → Requirements F5 (Dataset Comparison), User Story V01
- **ValidationSpecManager** → Requirements F2 (Validation Specification Management), User Stories V04, V05
- **AutomatedFineTuner** → Requirements F2 (Validation Specification Management), User Story V05
- **BenchmarkCreator** → Requirements F6 (Administrative Tools), User Story A01

## Consolidated Error Handling

All components implement standardized error handling patterns from Interface Standards (Document 09):

```python
class LocomotionToolError(Exception):
    """Base exception for all locomotion tools with user context"""
    def __init__(self, message: str, file_path: str = None, context: str = None, suggestion: str = None):
        self.message = message
        self.file_path = file_path
        self.context = context
        self.suggestion = suggestion
        super().__init__(self.message)

class DataFormatError(LocomotionToolError):
    """Issues with data format or structure"""
    pass

class ValidationError(LocomotionToolError):
    """Data validation failures"""
    pass

class QualityError(LocomotionToolError):
    """Data quality issues"""
    pass

class ConfigurationError(LocomotionToolError):
    """Configuration file or parameter issues"""
    pass
```

## PhaseValidator - Phase-Indexed Dataset Validation

**Requirements Traceability:** User Stories C02 (Dataset Quality Assessment), V01 (Dataset Comparison), V03 (Debug Validation Failures)  
**User Personas:** Dr. Sarah Chen (Biomechanical Validation), Marcus Rodriguez (Programmer)  
**CLI Entry Point:** `validation_dataset_report.py` (implements interface via dataset_validator_phase.py)  
**Workflow Integration:** Core component in Sequences 1, 2A, 2B, 3 - all validation workflows converge on this tool

```python
class PhaseValidator:
    def __init__(self, spec_manager: SpecificationManager, error_handler: ErrorHandler, 
                 progress_reporter: ProgressReporter = None):
        """
        Initialize validator with dependencies and standardized interfaces.
        
        Requirements: C02 - Auto-detect dataset type, comprehensive validation
        Dependencies: SpecificationManager, ErrorHandler, ProgressReporter (Interface Standards)
        """
    
    def validate_dataset(self, file_path: str, generate_plots: bool = True, 
                        generate_gifs: bool = False, output_dir: str = None) -> PhaseValidationResult:
        """
        Run comprehensive validation on phase-indexed dataset with stride-level filtering.
        
        Requirements Traceability:
        - C02: Comprehensive validation against biomechanical standards
        - C02: Dataset summary statistics and metadata
        - C02: Coverage statistics (subjects, tasks, gait cycles)
        - C02: Missing data patterns and outlier identification
        - C02: Detailed validation report with pass/fail status
        - C02: Automatically generated static validation plots
        - C02: Optional animated GIFs with --generate-gifs flag
        - V03: Deep-dive analysis of failed data points with context
        
        Interface Standards Compliance:
        - Uses standardized ProgressReporter for operation tracking
        - Implements standardized error handling with context
        - Follows CLI argument patterns (--generate-gifs flag)
        - Returns structured results with exit codes
        
        MUST perform stride-level validation and filtering
        MUST show which strides are kept vs deleted in validation report
        MUST report stride pass rate as quality metric
        MUST only fail dataset if NO strides pass validation AND basic structure is invalid
        MUST create visual validation plots for manual review (generate_plots=True)
        MUST create animated GIFs when requested (generate_gifs=True, computationally intensive)
        MUST export validation summary with stride statistics
        MUST use task-specific and phase-specific validation ranges
        MUST read tasks from data['task'] column
        MUST validate against known tasks from feature_constants
        MUST handle unknown tasks gracefully with clear error messages
        MUST integrate with LocomotionData library for efficient 3D operations
        MUST use StepClassifier.validate_data_against_specs() for consistency
        
        Raises:
        - DataFormatError: Invalid parquet structure or missing required columns
        - ValidationError: Critical validation failures preventing analysis
        - ConfigurationError: Invalid output directory or configuration
        """
    
    def filter_valid_strides(self, data: pd.DataFrame, available_variables: List[str] = None) -> StrideFilterResult:
        """
        Filter dataset to keep only valid strides based on task-specific validation specifications.
        
        Requirements: C02 - Biomechanical plausibility scores, V03 - Investigation analysis
        
        MUST identify valid vs invalid strides using task and phase-specific ranges
        MUST check each stride against available validation specifications
        MUST validate at 0%, 25%, 50%, 75% phases for each stride (representative phases)
        MUST provide detailed reasons for stride rejection with biomechanical context
        MUST return filtered dataset with only valid strides
        MUST maintain audit trail of filtering decisions
        
        Raises:
        - ValidationError: No valid strides found or specification loading failure
        """
    
    def get_available_tasks(self, data: pd.DataFrame) -> List[str]:
        """
        Get unique tasks from dataset, filtered to known standard tasks.
        
        Requirements: C02 - Task coverage analysis
        MUST validate against feature_constants.TASK_DEFINITIONS
        MUST log warnings for unknown tasks
        """
    
    def analyze_standard_spec_coverage(self, data: pd.DataFrame) -> Dict[str, Dict[str, bool]]:
        """
        Analyze which standard specification variables are available in the dataset.
        
        Requirements: C02 - Coverage statistics, missing data patterns
        MUST check against kinematic and kinetic variable specifications
        MUST identify missing variables by task type
        MUST calculate coverage percentages
        """
    
    def validate_batch(self, file_paths: List[str], parallel: bool = True, 
                      max_workers: int = None) -> BatchValidationResult:
        """
        Validate multiple datasets with stride-level summary reporting.
        
        Requirements: V01 - Systematic comparison across datasets
        MUST provide parallel processing for efficiency
        MUST aggregate stride-level statistics across datasets
        MUST identify cross-dataset inconsistencies
        MUST respect memory limits and provide progress reporting
        
        Raises:
        - ResourceError: Insufficient memory or processing resources
        """
    
    def generate_validation_report(self, result: PhaseValidationResult, 
                                 output_path: str) -> ReportGenerationResult:
        """
        Generate comprehensive markdown validation report.
        
        Requirements: C02 - Export comprehensive report for contribution documentation
        Interface Standards: Follows report structure standards from Document 09
        
        MUST follow standardized report format with tool metadata
        MUST include summary, validation results, quality metrics, recommendations
        MUST provide actionable insights for dataset improvement
        """
```

## TimeValidator - Time-Indexed Dataset Validation

**Requirements Traceability:** User Story C03 (Generate Phase-Indexed Dataset - requires time validation)  
**User Personas:** Marcus Rodriguez (Programmer)  
**CLI Entry Point:** `conversion_generate_phase_dataset.py` (validates input before conversion)  
**Workflow Integration:** Essential for Sequence 1 (Dataset Conversion) when time-indexed data needs phase conversion

```python
class TimeValidator:
    def __init__(self, spec_manager: SpecificationManager, error_handler: ErrorHandler,
                 progress_reporter: ProgressReporter = None):
        """
        Initialize time-indexed validator with standardized dependencies.
        
        Requirements: C03 - Input time-indexed parquet validation
        Dependencies: SpecificationManager, ErrorHandler, ProgressReporter (Interface Standards)
        """
    
    def validate_dataset(self, file_path: str, generate_plots: bool = True, 
                        output_dir: str = None) -> TimeValidationResult:
        """
        Run comprehensive validation on time-indexed dataset.
        
        Requirements Traceability:
        - C03: Input time-indexed parquet with vertical ground reaction forces
        - C03: Robust handling of incomplete or irregular gait cycles
        - C03: Quality report showing cycle detection success rates
        
        Interface Standards Compliance:
        - Uses standardized error handling and progress reporting
        - Follows CLI argument patterns and exit codes
        
        MUST validate sampling frequency consistency across all data
        MUST check temporal data integrity and identify gaps
        MUST validate biomechanical ranges where applicable
        MUST verify ground reaction force data for gait cycle detection
        MUST identify incomplete or irregular cycles for conversion readiness
        MUST generate quality metrics for temporal data assessment
        
        Raises:
        - DataFormatError: Invalid time-indexed structure or missing time columns
        - ValidationError: Critical temporal integrity issues
        """
    
    def check_temporal_integrity(self, data: pd.DataFrame) -> TemporalIntegrityResult:
        """
        Validate time series consistency and gaps.
        
        Requirements: C03 - Robust handling of incomplete data
        MUST identify time gaps, duplicates, and inconsistent sampling
        MUST calculate data completeness percentages
        MUST flag problematic time series for review
        """
    
    def validate_sampling_frequency(self, data: pd.DataFrame) -> SamplingValidationResult:
        """
        Check sampling rate consistency across subjects and tasks.
        
        Requirements: C03 - Preservation of original variables and metadata
        MUST detect sampling frequency variations
        MUST validate frequency consistency within subjects
        MUST identify resampling requirements for conversion
        """
    
    def assess_gait_cycle_readiness(self, data: pd.DataFrame) -> GaitCycleReadinessResult:
        """
        Assess data readiness for gait cycle detection and phase conversion.
        
        Requirements: C03 - Automatic gait cycle detection from force data
        MUST verify presence and quality of vertical ground reaction forces
        MUST identify potential gait cycles and estimate success rate
        MUST provide recommendations for improving cycle detection
        """
```

## QualityAssessor - Dataset Quality Assessment

**Requirements Traceability:** User Story C02 (Assess Dataset Quality and Validation)  
**User Personas:** Dr. Sarah Chen (Biomechanical Validation), Marcus Rodriguez (Programmer)  
**Integration:** Used by PhaseValidator for comprehensive quality assessment  
**Workflow Integration:** Supports Sequences 1 and 3 for dataset quality evaluation and contribution decisions

```python
class QualityAssessor:
    def __init__(self, spec_manager: SpecificationManager, error_handler: ErrorHandler,
                 progress_reporter: ProgressReporter = None):
        """
        Initialize quality assessor with standardized dependencies.
        
        Requirements: C02 - Quality assessment as part of validation pipeline
        Dependencies: SpecificationManager, ErrorHandler, ProgressReporter (Interface Standards)
        """
    
    def assess_dataset_quality(self, file_path: str, generate_comparisons: bool = True) -> QualityAssessmentResult:
        """
        Generate comprehensive quality reports for datasets.
        
        Requirements Traceability:
        - C02: Coverage statistics (subjects, tasks, gait cycles)
        - C02: Missing data patterns and outlier identification
        - C02: Biomechanical plausibility scores and population comparisons
        - C02: Export comprehensive report for contribution documentation
        
        Interface Standards Compliance:
        - Uses standardized progress reporting and error handling
        - Provides structured quality metrics for tracking
        
        MUST calculate coverage statistics (subjects, tasks, gait cycles)
        MUST identify missing data patterns and outliers with biomechanical context
        MUST generate biomechanical plausibility scores using task-specific criteria
        MUST compare against population norms from literature (when available)
        MUST export quality metrics for tracking over time
        MUST provide actionable recommendations for data improvement
        
        Raises:
        - QualityError: Insufficient data for reliable quality assessment
        - DataFormatError: Invalid dataset structure preventing analysis
        """
    
    def calculate_coverage_statistics(self, data: pd.DataFrame) -> CoverageStats:
        """
        Calculate subject, task, and cycle coverage metrics.
        
        Requirements: C02 - Coverage statistics reporting
        MUST calculate completeness percentages by variable and task
        MUST identify data sparsity patterns
        MUST assess balance across subjects and conditions
        """
    
    def identify_outliers(self, data: pd.DataFrame, method: str = "biomechanical") -> OutlierAnalysis:
        """
        Identify outlier patterns and data quality issues.
        
        Requirements: C02 - Outlier identification with biomechanical context
        MUST use biomechanical criteria for outlier detection
        MUST distinguish between statistical outliers and biomechanical impossibilities
        MUST provide detailed context for each outlier identification
        MUST suggest potential causes and remediation strategies
        """
    
    def generate_population_comparison(self, data: pd.DataFrame) -> PopulationComparisonResult:
        """
        Compare dataset against established population norms.
        
        Requirements: C02 - Population comparisons for validation context
        MUST compare means, ranges, and distributions against literature
        MUST identify systematic deviations from expected values
        MUST provide interpretation guidance for observed differences
        """
```

## Core Result Types

### PhaseValidationResult
```python
@dataclass
class PhaseValidationResult:
    # Core validation result
    file_path: str
    validation_passed: bool
    stride_statistics: StrideStatistics
    coverage_analysis: CoverageAnalysis
    
    # Output files and paths
    validation_report_path: str
    plot_paths: List[str]
    
    # Error tracking and completeness
    errors: List[ValidationError]
    warnings: List[ValidationError]
    processing_time: float
    validation_timestamp: datetime
    
    # Enhanced metadata for traceability
    metadata: Dict[str, Any]
    input_parameters: Dict[str, Any]
    validation_spec_version: str
    step_classifier_version: str
    
    # Quality assessment integration
    quality_metrics: Optional[QualityMetrics] = None
    
    def validate_completeness(self) -> CompletionCheck:
        """Verify this result meets interface contract requirements"""
        pass
    
    def export_summary(self, format: str = 'json') -> str:
        """Export validation summary in specified format"""
        pass
```

### StrideFilterResult
```python
@dataclass
class StrideFilterResult:
    # Core filtering results
    filtered_data: pd.DataFrame
    total_strides: int
    valid_strides: int
    invalid_strides: int
    pass_rate: float
    
    # Detailed rejection analysis
    rejection_reasons: List[StrideRejection]
    rejection_categories: Dict[str, int]
    most_common_rejections: List[Tuple[str, int]]
    
    # Coverage and completeness
    coverage_info: CoverageInfo
    task_specific_pass_rates: Dict[str, float]
    variable_specific_pass_rates: Dict[str, float]
    phase_specific_pass_rates: Dict[int, float]
    
    # Traceability and metadata
    filtering_timestamp: datetime
    filtering_parameters: Dict[str, Any]
    validation_spec_applied: str
    step_classifier_config: StepClassifierConfig
    
    # Quality indicators
    data_quality_score: float
    confidence_intervals: Dict[str, Tuple[float, float]]
    
    def get_rejection_summary(self) -> Dict[str, Any]:
        """Generate human-readable rejection summary"""
        pass
    
    def export_filtered_dataset(self, output_path: str) -> str:
        """Export filtered dataset to file"""
        pass
```

### StrideRejection
```python
@dataclass
class StrideRejection:
    # Core identification
    stride_id: str
    subject_id: str
    task: str
    variable: str
    phase: int
    
    # Violation details
    value: float
    expected_min: float
    expected_max: float
    reason: str
    violation_severity: str  # 'minor', 'major', 'critical'
    
    # Context and traceability
    validation_rule_applied: str
    specification_source: str
    detection_timestamp: datetime
    
    # Additional metadata
    phase_percentage: float  # 0.0, 0.25, 0.50, 0.75
    variable_units: str
    typical_range: Optional[Tuple[float, float]]
    population_percentile: Optional[float]
```

### QualityAssessmentResult
```python
@dataclass
class QualityAssessmentResult:
    file_path: str
    coverage_stats: CoverageStats
    outlier_analysis: OutlierAnalysis
    plausibility_scores: PlausibilityScores
    population_comparison: PopulationComparison
    quality_metrics: QualityMetrics
    report_path: str
```

### ValidationConfig
```python
@dataclass
class ValidationConfig:
    phase_tolerance: float
    outlier_threshold: float
    minimum_stride_count: int
    required_phases: List[int]
    validation_spec_path: str
    plot_generation: bool
    parallel_processing: bool
    max_workers: int
```

## Validation Workflow Data Structures

### ValidationWorkflowConfig
```python
@dataclass
class ValidationWorkflowConfig:
    dataset_path: str
    output_directory: str
    generate_plots: bool
    generate_gifs: bool
    validation_spec_path: str
    step_classifier_config: StepClassifierConfig
    plot_config: PlotGenerationConfig
    parallel_processing: bool
    max_workers: int
    memory_limit_gb: float
```

### StepClassifierConfig
```python
@dataclass
class StepClassifierConfig:
    representative_phases: List[int]  # [0, 25, 50, 75]
    validation_tolerance: float
    contralateral_offset: bool
    kinematic_variables: List[str]
    kinetic_variables: List[str]
    required_tasks: List[str]
```

### ValidationReport
```python
@dataclass
class ValidationReport:
    dataset_name: str
    validation_timestamp: datetime
    total_processing_time: float
    validation_result: PhaseValidationResult
    stride_filter_result: StrideFilterResult
    coverage_analysis: CoverageAnalysis
    generated_plots: List[PlotReference]
    generated_gifs: List[str]
    error_summary: ErrorSummary
    recommendations: List[str]
    report_path: str
```

## Supporting Infrastructure

### ConfigurationManager
```python
class ConfigurationManager:
    def __init__(self, tool_name: str):
        """
        Initialize configuration manager with tool-specific defaults.
        
        Requirements: Interface Standards - Standardized configuration management
        MUST load default configuration for tool
        MUST support configuration file overrides (--config flag)
        MUST validate configuration format and required parameters
        """
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with dot notation support.
        
        Interface Standards: get_setting("processing.memory_limit_gb", 4)
        MUST support nested key access with dot notation
        MUST provide sensible defaults for missing keys
        MUST log configuration access for debugging
        """
```

### ErrorHandler
```python
class ErrorHandler:
    def __init__(self, tool_name: str, verbose: bool = False):
        """
        Initialize error handler with tool context and logging configuration.
        
        Interface Standards: Standardized error handling and logging
        MUST configure logging according to interface standards
        MUST set up error reporting consistent with CLI patterns
        """
    
    def handle_error(self, error: LocomotionToolError, context: str = "") -> ErrorResponse:
        """
        Handle all tool errors with standardized response format.
        
        Interface Standards: Error message format and exit codes
        MUST format errors according to standardized pattern:
        ERROR: {error_type}: {error_description}
          File: {file_path}
          Context: {additional_context}
          Suggestion: {recommended_action}
        
        MUST map exceptions to appropriate exit codes
        MUST log errors with appropriate severity levels
        MUST provide actionable suggestions based on error type
        """
```

## Critical Interface: validation_dataset_report.py

The **validation_dataset_report.py** CLI tool is the primary entry point for dataset quality assessment and represents the integration of multiple interface contracts:

### Implementation Architecture
```python
# validation_dataset_report.py - CLI Entry Point
def main():
    """
    Primary CLI for comprehensive dataset validation and quality assessment.
    
    Requirements Traceability: User Story C02 (Dataset Quality Assessment)
    User Personas: Dr. Sarah Chen (Biomechanical Validation), Marcus Rodriguez (Programmer)
    
    Interface Integration:
    - PhaseValidator: Core validation logic and stride-level filtering
    - QualityAssessor: Quality metrics and population comparisons
    - ValidationSpecManager: Specification loading and range application
    - ErrorHandler: Standardized error handling and user feedback
    - ProgressReporter: User experience and operation tracking
    - DataLoader: File access and metadata extraction
    """
    
    # CLI Argument Processing (Interface Standards Compliance)
    parser = argparse.ArgumentParser(description="Comprehensive dataset validation and quality assessment")
    parser.add_argument("dataset_path", help="Path to phase-indexed parquet dataset")
    parser.add_argument("--output-dir", default="./validation_reports", help="Output directory for reports")
    parser.add_argument("--generate-gifs", action="store_true", help="Generate animated GIF visualizations")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output for automation")
    
    # Interface Contract Implementation
    try:
        # Initialize standardized dependencies (Interface Standards)
        config_manager = ConfigurationManager("validation_dataset_report")
        error_handler = ErrorHandler("validation_dataset_report", verbose=args.verbose)
        progress_reporter = ProgressReporter(verbose=args.verbose, quiet=args.quiet)
        
        # Initialize validation components (Interface Contracts)
        spec_manager = ValidationSpecManager(config_manager, error_handler, progress_reporter)
        quality_assessor = QualityAssessor(spec_manager, error_handler, progress_reporter)
        phase_validator = PhaseValidator(spec_manager, error_handler, progress_reporter)
        
        # Execute comprehensive validation (Requirements C02)
        result = phase_validator.validate_dataset(
            file_path=args.dataset_path,
            generate_plots=True,
            generate_gifs=args.generate_gifs,
            output_dir=args.output_dir
        )
        
        # Generate comprehensive report (Requirements C02)
        report_path = os.path.join(args.output_dir, f"{dataset_name}_validation_report.md")
        phase_validator.generate_validation_report(result, report_path)
        
        return EXIT_SUCCESS
        
    except LocomotionToolError as e:
        return error_handler.handle_error(e).exit_code
```

### Interface Standards Compliance Summary

All interface contracts ensure consistency with Document 09 (Interface Standards):

1. **CLI Argument Patterns**: Consistent `--generate-gifs`, `--verbose`, `--quiet` flags
2. **Exit Codes**: Standardized error codes for different failure types
3. **Error Handling**: Structured error messages with context and suggestions
4. **Progress Reporting**: Consistent progress display across verbosity levels
5. **Configuration Management**: Standard YAML configuration loading and validation
6. **File Operations**: Consistent file access patterns and safety checks

### Requirements Traceability Summary

**User Story C02 (Dataset Quality Assessment)** - Complete implementation through:
- PhaseValidator: Comprehensive validation and stride-level filtering
- QualityAssessor: Coverage statistics and biomechanical plausibility
- ValidationSpecManager: Task-specific validation ranges
- Supporting Infrastructure: Consistent user experience and error handling

**Dr. Sarah Chen (Biomechanical Validation)** needs:
✅ Biomechanical correctness validation (PhaseValidator)
✅ Statistical analysis and outlier identification (QualityAssessor)  
✅ Validation range management (ValidationSpecManager)
✅ Clear error reporting and actionable suggestions (ErrorHandler)

**Marcus Rodriguez (Programmer)** needs:
✅ Clear validation feedback for conversion debugging (PhaseValidator)
✅ Progress reporting for long-running operations (ProgressReporter)
✅ Consistent CLI interface patterns (Interface Standards)
✅ Comprehensive error messages with context (ErrorHandler)

This interface contract specification ensures all components work together seamlessly to deliver the comprehensive dataset validation capabilities required by the locomotion data standardization project.